"""API FastAPI : /chat, /approvals, /health, /metrics."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from collections import defaultdict
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from prometheus_client import make_asgi_app
from pydantic import BaseModel

from smartops_agent import __version__
from smartops_agent.agent.llm_client import (
    AVAILABLE_MODELS,
    build_llm_client,
    get_effective_groq_key,
    get_effective_model_id,
    get_effective_openrouter_key,
    invalidate_groq_key_cache,
    invalidate_model_cache,
    invalidate_openrouter_key_cache,
)
from smartops_agent.agent.loop import AgentLoop
from smartops_agent.api.auth import AuthUser, require_admin, require_auth
from smartops_agent.config import get_settings, load_config
from smartops_agent.guardrails.approval_queue import ApprovalQueue, get_queue
from smartops_agent.monitoring.metrics import (
    approval_queue_size,
    chat_latency_seconds,
    chat_requests_total,
    llm_calls_daily,
)
from smartops_agent.tracing.tracer import Tracer

log = logging.getLogger(__name__)

_VALID_ROLES = frozenset({"commercial", "delivery", "admin"})


def _safe_role_label(role: str) -> str:
    return role if role in _VALID_ROLES else "unknown"


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str
    role: str = "commercial"
    user_id: str = "anonymous"
    session_id: str = ""


class ChatResponse(BaseModel):
    answer: str
    trace_id: str = ""


class ApprovalDecision(BaseModel):
    decision: str  # "approved" | "rejected"
    comment: str = ""


class GroqKeyUpdate(BaseModel):
    api_key: str


class ModelUpdate(BaseModel):
    model_id: str


class OpenRouterKeyUpdate(BaseModel):
    api_key: str


# ---------------------------------------------------------------------------
# Simple in-memory rate limiter
# ---------------------------------------------------------------------------

_rate_windows: dict[str, list[float]] = defaultdict(list)
_daily_llm_count: dict[str, int] = defaultdict(int)
_daily_window_start: float = time.time()

# In-memory conversation history per session_id (system-prompt messages excluded)
_MAX_HISTORY_TURNS = 20
_MAX_SESSIONS = 1000  # evict oldest when full to bound memory
_session_history: dict[tuple[str, str], list[dict[str, Any]]] = {}


def _check_rate_limit(client_ip: str, limit_per_minute: int) -> None:
    now = time.time()
    window = _rate_windows[client_ip]
    _rate_windows[client_ip] = [t for t in window if now - t < 60]
    if len(_rate_windows[client_ip]) >= limit_per_minute:
        raise HTTPException(status_code=429, detail="Trop de requêtes. Réessayez dans une minute.")
    _rate_windows[client_ip].append(now)


def _check_daily_llm_cap(cap: int) -> None:
    global _daily_window_start
    now = time.time()
    if now - _daily_window_start > 86400:
        _daily_llm_count.clear()
        _daily_window_start = now
    total = sum(_daily_llm_count.values())
    if total >= cap:
        raise HTTPException(status_code=429, detail="Quota LLM journalier atteint.")
    _daily_llm_count["global"] = _daily_llm_count.get("global", 0) + 1
    llm_calls_daily.set(sum(_daily_llm_count.values()))


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app(
    db_path: str | None = None,
    queue: ApprovalQueue | None = None,
) -> FastAPI:
    settings = get_settings()
    effective_db = db_path or str(Path("data/seed/crm.db").resolve())
    effective_queue = queue or get_queue()

    agent_cfg = load_config("agent").get("agent", {})
    models_cfg = load_config("models")
    default_model_name = models_cfg.get("default", "groq-large")
    model_info = models_cfg["models"][default_model_name]

    trace_dir = Path("reports/traces")
    _prompt_version = agent_cfg.get("prompt_version", "v1")
    _model_id = model_info.get("model_id", "unknown")

    def _make_agent() -> tuple[AgentLoop, Tracer]:
        tracer = Tracer(trace_dir=trace_dir, prompt_version=_prompt_version, model_id=_model_id)
        llm = build_llm_client(
            provider=model_info["provider"],
            model_id=model_info["model_id"],
        )
        loop = AgentLoop(
            llm=llm,
            db_path=effective_db,
            queue=effective_queue,
            tracer=tracer,
            prompt_version=_prompt_version,
            max_iterations=agent_cfg.get("max_iterations", 6),
            llm_timeout=agent_cfg.get("llm_timeout_s", 20.0),
            tool_timeout=agent_cfg.get("tool_timeout_s", 5.0),
            retries_on_invalid=agent_cfg.get("retries_on_invalid_output", 1),
        )
        return loop, tracer

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        from smartops_agent.data.seed import SeedParams, seed_database
        from smartops_agent.data.seed_traces import startup_replay
        from smartops_agent.monitoring.scheduler import start_scheduler_task

        # Create the CRM database if it is missing (e.g. first deploy on Railway
        # where the ephemeral filesystem starts empty).
        db_path_obj = Path(effective_db)
        if not db_path_obj.exists():
            log.info("CRM database not found at %s — seeding now", db_path_obj)
            await asyncio.to_thread(seed_database, db_path_obj, SeedParams())
            log.info("CRM database ready")

        # Restore Prometheus counters from persisted traces so Grafana shows
        # historical activity immediately after a container redeploy.
        await asyncio.to_thread(startup_replay)
        task = start_scheduler_task()
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title="SmartOps Agent", version=__version__, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__, "env": settings.app_env}

    @app.post("/chat", response_model=ChatResponse)
    def chat(
        req: ChatRequest,
        request: Request,
        user: AuthUser = Depends(require_auth),  # noqa: B008
    ) -> ChatResponse:
        client_ip = request.client.host if request.client else "unknown"
        _check_rate_limit(client_ip, settings.rate_limit_per_minute)
        _check_daily_llm_cap(settings.daily_llm_call_cap)

        # Role from verified JWT only — never trust req.role (prevents privilege escalation)
        verified_role = _safe_role_label(user.role)
        role_label = verified_role
        t0 = time.monotonic()
        try:
            # Use authenticated user_id; session keyed on verified identity
            verified_user_id = user.user_id
            session_key = (verified_user_id, req.session_id) if req.session_id else None
            prior_history = _session_history.get(session_key, []) if session_key else []
            agent, tracer = _make_agent()
            answer, new_history = agent.run(
                user_message=req.message,
                role=verified_role,
                user_id=verified_user_id,
                history=prior_history,
                crm_member_id=user.crm_member_id,
                display_name=user.display_name,
            )
            if session_key:
                if len(_session_history) >= _MAX_SESSIONS and session_key not in _session_history:
                    _session_history.pop(next(iter(_session_history)))
                _session_history[session_key] = new_history[-_MAX_HISTORY_TURNS * 2 :]
            chat_requests_total.labels(role=role_label, status="ok").inc()
            return ChatResponse(answer=answer, trace_id=tracer._data.get("trace_id", ""))
        except Exception as exc:
            log.exception("Unhandled error in /chat")
            chat_requests_total.labels(role=role_label, status="error").inc()
            raise HTTPException(
                status_code=500, detail="Erreur interne. Contactez l'administrateur."
            ) from exc
        finally:
            chat_latency_seconds.observe(time.monotonic() - t0)

    @app.get("/approvals")
    def list_approvals(user: AuthUser = Depends(require_auth)) -> list[dict[str, Any]]:  # noqa: B008
        items = effective_queue.get_all()
        approval_queue_size.set(len([i for i in items if i["status"] == "pending"]))
        # Admins see all; others see only their own requests
        if not user.is_admin:
            items = [i for i in items if i.get("requested_by") == user.user_id]
        return items

    @app.post("/approvals/{request_id}")
    def decide_approval(
        request_id: str,
        body: ApprovalDecision,
        user: AuthUser = Depends(require_admin),  # noqa: B008  # admin-only
    ) -> dict[str, Any]:
        if body.decision not in ("approved", "rejected"):
            raise HTTPException(status_code=422, detail="decision must be 'approved' or 'rejected'")
        # Prevent self-approval
        all_items = effective_queue.get_all()
        item = next((i for i in all_items if i.get("request_id") == request_id), None)
        if item and item.get("requested_by") == user.user_id:
            raise HTTPException(status_code=403, detail="Auto-approbation interdite.")
        ok = effective_queue.approve(request_id, body.decision, body.comment)
        if not ok:
            raise HTTPException(status_code=404, detail="Demande introuvable.")
        return {"request_id": request_id, "status": body.decision}

    @app.get("/settings/groq-key")
    def get_groq_key_status(
        _user: AuthUser = Depends(require_admin),  # noqa: B008
    ) -> dict[str, str]:
        current = get_effective_groq_key()
        masked = (
            (current[:8] + "…" + current[-4:]) if len(current) > 12 else ("***" if current else "")
        )
        # Determine whether the key comes from Supabase override or env var
        source = "env"
        if settings.supabase_url and settings.supabase_service_role_key:
            try:
                from supabase import create_client

                client = create_client(
                    settings.supabase_url,
                    settings.supabase_service_role_key.get_secret_value(),
                )
                resp = (
                    client.table("app_settings")
                    .select("value")
                    .eq("key", "groq_api_key")
                    .single()
                    .execute()
                )
                if isinstance(resp.data, dict) and resp.data.get("value"):
                    source = "override"
            except Exception:
                log.debug("Could not determine Groq key source from Supabase", exc_info=True)
        return {"has_key": "true" if current else "false", "masked": masked, "source": source}

    @app.put("/settings/groq-key")
    def update_groq_key(
        body: GroqKeyUpdate,
        _user: AuthUser = Depends(require_admin),  # noqa: B008
    ) -> dict[str, str]:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise HTTPException(status_code=503, detail="Supabase non configuré.")
        from supabase import create_client

        client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key.get_secret_value(),
        )
        client.table("app_settings").upsert(
            {"key": "groq_api_key", "value": body.api_key}
        ).execute()
        invalidate_groq_key_cache()
        return {"status": "updated"}

    @app.get("/settings/openrouter-key")
    def get_openrouter_key_status(
        _user: AuthUser = Depends(require_admin),  # noqa: B008
    ) -> dict[str, str]:
        current = get_effective_openrouter_key()
        masked = (
            (current[:8] + "..." + current[-4:])
            if len(current) > 12
            else ("***" if current else "")
        )
        return {"has_key": "true" if current else "false", "masked": masked}

    @app.put("/settings/openrouter-key")
    def update_openrouter_key(
        body: OpenRouterKeyUpdate,
        _user: AuthUser = Depends(require_admin),  # noqa: B008
    ) -> dict[str, str]:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise HTTPException(status_code=503, detail="Supabase non configuré.")
        from supabase import create_client

        client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key.get_secret_value(),
        )
        client.table("app_settings").upsert(
            {"key": "openrouter_api_key", "value": body.api_key}
        ).execute()
        invalidate_openrouter_key_cache()
        return {"status": "updated"}

    @app.get("/settings/model")
    def get_model_status(
        _user: AuthUser = Depends(require_admin),  # noqa: B008
    ) -> dict[str, object]:
        return {"current": get_effective_model_id(), "models": AVAILABLE_MODELS}

    @app.put("/settings/model")
    def update_model(
        body: ModelUpdate,
        _user: AuthUser = Depends(require_admin),  # noqa: B008
    ) -> dict[str, str]:
        valid_ids = {m["id"] for m in AVAILABLE_MODELS}
        if body.model_id not in valid_ids:
            raise HTTPException(status_code=422, detail="Modèle non reconnu.")
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise HTTPException(status_code=503, detail="Supabase non configuré.")
        from supabase import create_client

        client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key.get_secret_value(),
        )
        client.table("app_settings").upsert(
            {"key": "active_model_id", "value": body.model_id}
        ).execute()
        invalidate_model_cache()
        return {"status": "updated", "model_id": body.model_id}

    _drift_report_path = Path("reports/monitoring/drift_report.html")
    _drift_bucket = "reports"
    _drift_object = "monitoring/drift_report.html"
    _not_found_html = (
        "<html><body style='font-family:sans-serif;padding:40px'>"
        "<h2>Rapport non disponible</h2>"
        "<p>Lancez <code>make monitor</code> pour générer le rapport Evidently.</p>"
        "</body></html>"
    )

    @app.get("/report/drift", response_model=None)
    def drift_report(_user: AuthUser = Depends(require_admin)) -> FileResponse | HTMLResponse:  # noqa: B008
        # Supabase Storage takes priority (works in production without a local disk).
        if settings.supabase_url and settings.supabase_service_role_key:
            try:
                from supabase import create_client

                sb = create_client(
                    settings.supabase_url,
                    settings.supabase_service_role_key.get_secret_value(),
                )
                data: bytes = sb.storage.from_(_drift_bucket).download(_drift_object)
                if data:
                    return HTMLResponse(content=data.decode("utf-8"), status_code=200)
            except Exception:
                log.debug(
                    "Supabase Storage indisponible pour drift report; fallback disque",
                    exc_info=True,
                )
        # Fallback: local file (dev / CI).
        if not _drift_report_path.exists():
            return HTMLResponse(_not_found_html, status_code=200)
        return FileResponse(str(_drift_report_path), media_type="text/html")

    # ── Seed data endpoints (admin-only) ────────────────────────────────────

    @app.post("/admin/seed-data")
    def seed_demo_data(
        _user: AuthUser = Depends(require_admin),  # noqa: B008
    ) -> dict[str, Any]:
        from smartops_agent.data.seed_traces import seed_traces
        from smartops_agent.monitoring.report import run_report

        n = seed_traces()
        ok = run_report()
        return {"seeded_traces": n, "report": "generated" if ok else "mlops_deps_missing"}

    @app.delete("/admin/seed-data")
    def delete_demo_data(
        _user: AuthUser = Depends(require_admin),  # noqa: B008
    ) -> dict[str, Any]:
        from smartops_agent.data.seed_traces import delete_traces

        deleted = delete_traces()
        sb_cleaned = False
        if settings.supabase_url and settings.supabase_service_role_key:
            try:
                from supabase import create_client

                sb = create_client(
                    settings.supabase_url,
                    settings.supabase_service_role_key.get_secret_value(),
                )
                sb.storage.from_("reports").remove(["monitoring/drift_report.html"])
                sb_cleaned = True
            except Exception:
                log.debug("Could not remove drift report from Supabase Storage", exc_info=True)
        return {"traces_deleted": deleted, "supabase_cleaned": sb_cleaned}

    # ── Monitoring status ────────────────────────────────────────────────────

    @app.get("/monitoring/status")
    def monitoring_status(
        _user: AuthUser = Depends(require_admin),  # noqa: B008
    ) -> dict[str, Any]:
        if settings.supabase_url and settings.supabase_service_role_key:
            try:
                from supabase import create_client

                sb = create_client(
                    settings.supabase_url,
                    settings.supabase_service_role_key.get_secret_value(),
                )
                resp = (
                    sb.table("app_settings")
                    .select("value")
                    .eq("key", "monitoring_alert")
                    .single()
                    .execute()
                )
                if isinstance(resp.data, dict) and resp.data.get("value"):
                    return dict(json.loads(resp.data["value"]))
            except Exception:
                log.debug("Could not fetch monitoring alert", exc_info=True)
        return {"status": "never_run", "message": "Monitoring non encore lancé."}

    app.mount("/metrics", make_asgi_app())
    return app


app = create_app()
