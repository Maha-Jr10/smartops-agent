"""Traçage JSONL structuré (cahier 5.4) + MLflow Tracing quand disponible.

Champs obligatoires par trace :
  trace_id, session_id, timestamp, role, user_id_hash,
  user_message (PII masqué), steps[], answer (PII masqué),
  iterations, escalated, prompt_version, model_id
Pas de raisonnement interne du modèle, pas d'email, pas de téléphone.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any

import structlog

from smartops_agent.config import get_settings
from smartops_agent.guardrails.pii import mask_pii_in_dict

log = structlog.get_logger()

_MLFLOW_AVAILABLE = False
try:
    import mlflow

    _MLFLOW_AVAILABLE = True
except ImportError:
    pass


class Tracer:
    """Collecte les données d'une exécution et les persiste en JSONL."""

    def __init__(
        self, trace_dir: Path, prompt_version: str = "v1", model_id: str = "unknown"
    ) -> None:
        self._dir = trace_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._prompt_version = prompt_version
        self._model_id = model_id
        self._data: dict[str, Any] = {}
        self._steps: list[dict[str, Any]] = []

    def start(self, user_message: str, role: str, user_id: str) -> None:
        self._data = {
            "trace_id": str(uuid.uuid4()),
            "session_id": str(uuid.uuid4()),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "role": role,
            "user_id_hash": hashlib.sha256(user_id.encode()).hexdigest()[:16],
            "user_message": mask_pii_in_dict(user_message),
            "prompt_version": self._prompt_version,
            "model_id": self._model_id,
        }
        self._steps = []

    def llm_step(self, iteration: int, latency: float) -> None:
        self._steps.append({"type": "llm", "iteration": iteration, "latency_s": round(latency, 3)})

    def llm_error(self, error: str) -> None:
        self._steps.append({"type": "llm_error", "error": mask_pii_in_dict(error)})

    def tool_call(
        self, name: str, args: dict[str, Any], result: dict[str, Any], latency: float
    ) -> None:
        self._steps.append(
            {
                "type": "tool_call",
                "tool": name,
                "args": mask_pii_in_dict(args),
                "result": mask_pii_in_dict(result),
                "latency_s": round(latency, 3),
            }
        )

    def tool_error(self, name: str, error: str) -> None:
        self._steps.append({"type": "tool_error", "tool": name, "error": mask_pii_in_dict(error)})

    def finish(self, answer: str, iterations: int, escalated: bool = False) -> None:
        self._data["steps"] = self._steps
        self._data["answer"] = mask_pii_in_dict(answer)
        self._data["iterations"] = iterations
        self._data["escalated"] = escalated

        trace_file = self._dir / "traces.jsonl"
        with trace_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(self._data, ensure_ascii=False) + "\n")

        log.info("trace_saved", trace_id=self._data["trace_id"], iterations=iterations)

        if _MLFLOW_AVAILABLE:
            self._log_to_mlflow()

    def _log_to_mlflow(self) -> None:
        try:
            mlflow.set_tracking_uri(get_settings().mlflow_tracking_uri)
            mlflow.set_experiment("smartops-agent-monitoring")
            # nested=False: each chat turn is an independent top-level run on remote trackers
            tool_calls = [s for s in self._data.get("steps", []) if s.get("type") == "tool_call"]
            tools_used = ",".join(dict.fromkeys(s["tool"] for s in tool_calls)) or "none"
            run_name = f"agent_run [{self._data.get('role', '?')}]"
            with mlflow.start_run(run_name=run_name, nested=False):
                mlflow.set_tags(
                    {
                        "role": self._data.get("role", ""),
                        "trace_id": self._data.get("trace_id", ""),
                        "tools_used": tools_used,
                        "escalated": str(self._data.get("escalated", False)),
                        "prompt_version": self._data.get("prompt_version", ""),
                    }
                )
                mlflow.log_params(
                    {
                        "role": self._data.get("role", ""),
                        "prompt_version": self._data.get("prompt_version", ""),
                        "model_id": self._data.get("model_id", ""),
                    }
                )
                mlflow.log_metrics(
                    {
                        "iterations": float(self._data.get("iterations", 0)),
                        "escalated": float(self._data.get("escalated", False)),
                        "answer_length": float(len(str(self._data.get("answer", "")))),
                        "tool_call_count": float(len(tool_calls)),
                        "total_latency_s": float(
                            sum(
                                s.get("latency_s", 0.0)
                                for s in self._data.get("steps", [])
                                if "latency_s" in s
                            )
                        ),
                    }
                )
        except Exception as exc:
            log.warning("mlflow_run_failed", error_type=type(exc).__name__)


class NullTracer(Tracer):
    """Tracer no-op pour les tests qui n'ont pas besoin de JSONL."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._steps: list[dict[str, Any]] = []
        self._prompt_version = "v1"
        self._model_id = "mock"

    def finish(self, answer: str, iterations: int, escalated: bool = False) -> None:
        self._data["steps"] = self._steps
        self._data["answer"] = answer
        self._data["iterations"] = iterations
        self._data["escalated"] = escalated
