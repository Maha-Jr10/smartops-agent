"""API FastAPI : /chat, /approvals, /health, /metrics."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from pydantic import BaseModel

from smartops_agent import __version__
from smartops_agent.agent.llm_client import build_llm_client
from smartops_agent.agent.loop import AgentLoop
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

    app = FastAPI(title="SmartOps Agent", version=__version__)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3001"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__, "env": settings.app_env}

    @app.post("/chat", response_model=ChatResponse)
    def chat(req: ChatRequest, request: Request) -> ChatResponse:
        client_ip = request.client.host if request.client else "unknown"
        _check_rate_limit(client_ip, settings.rate_limit_per_minute)
        _check_daily_llm_cap(settings.daily_llm_call_cap)

        role_label = _safe_role_label(req.role)
        t0 = time.monotonic()
        try:
            # Key on (user_id, session_id) so a user cannot access another user's history
            session_key = (req.user_id, req.session_id) if req.session_id else None
            prior_history = _session_history.get(session_key, []) if session_key else []
            agent, tracer = _make_agent()
            answer, new_history = agent.run(
                user_message=req.message,
                role=req.role,
                user_id=req.user_id,
                history=prior_history,
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
    def list_approvals() -> list[dict[str, Any]]:
        items = effective_queue.get_all()
        approval_queue_size.set(len([i for i in items if i["status"] == "pending"]))
        return items

    @app.post("/approvals/{request_id}")
    def decide_approval(request_id: str, body: ApprovalDecision) -> dict[str, Any]:
        if body.decision not in ("approved", "rejected"):
            raise HTTPException(status_code=422, detail="decision must be 'approved' or 'rejected'")
        ok = effective_queue.approve(request_id, body.decision, body.comment)
        if not ok:
            raise HTTPException(status_code=404, detail="Demande introuvable.")
        return {"request_id": request_id, "status": body.decision}

    app.mount("/metrics", make_asgi_app())
    return app


app = create_app()
