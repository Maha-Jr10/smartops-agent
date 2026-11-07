"""Boucle d'agent : appel LLM → validation des arguments → exécution outil → répétition."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from smartops_agent.agent.llm_client import LLMClient, LLMResponse
from smartops_agent.agent.tool_registry import TOOL_SCHEMAS
from smartops_agent.config import load_config
from smartops_agent.guardrails.approval_queue import ApprovalQueue
from smartops_agent.guardrails.permissions import check_permission, get_allowed_human_actions
from smartops_agent.monitoring.metrics import escalations_total, tool_calls_total
from smartops_agent.tools import (
    CalculateCommissionInput,
    DraftFollowupInput,
    GetInvoiceStatusInput,
    RequestHumanActionInput,
    SearchCrmInput,
    ToolError,
    ToolErrorCode,
    calculate_commission,
    draft_followup,
    get_invoice_status,
    request_human_action,
    search_crm,
)
from smartops_agent.tracing.tracer import Tracer

log = logging.getLogger(__name__)

_PROMPT_DIR = Path(__file__).parent / "prompts"
_KNOWN_TOOL_NAMES: frozenset[str] = frozenset(s["function"]["name"] for s in TOOL_SCHEMAS)


def _load_system_prompt(version: str) -> str:
    path = _PROMPT_DIR / f"system_{version}.txt"
    return path.read_text(encoding="utf-8")


def _build_context_block(
    role: str,
    user_id: str,
    crm_member_id: str | None,
    display_name: str,
) -> str:
    name_part = f" — {display_name}" if display_name else ""
    if crm_member_id:
        crm_line = (
            f"- Identifiant CRM (person_id pour les outils) : {crm_member_id}\n"
            "- Pour calculate_commission sans précision de personne, "
            f"utilise toujours person_id = {crm_member_id}."
        )
    else:
        crm_line = (
            "- Identifiant CRM : non configuré. "
            "Demande à l'administrateur de lier ton compte à un membre de l'équipe."
        )

    if role == "admin":
        access_line = (
            "Accès admin : tu peux consulter les commissions de n'importe quel membre. "
            "Si la personne n'est pas précisée, demande son identifiant ou son nom."
        )
    else:
        who = crm_member_id or user_id
        access_line = (
            f"Accès {role} : tu ne peux consulter que tes propres données. "
            f"N'utilise jamais un autre person_id que {who}."
        )

    return (
        f"## Contexte de session\n"
        f"Utilisateur : {user_id}{name_part}\n"
        f"Rôle : {role}\n"
        f"{crm_line}\n"
        f"{access_line}\n\n"
    )


def _call_tool(
    name: str,
    args: dict[str, Any],
    role: str,
    user_id: str,
    db_path: str,
    queue: ApprovalQueue,
) -> dict[str, Any]:
    """Valide les arguments Pydantic puis appelle l'outil correspondant."""
    check_permission(name, role)
    if name == "search_crm":
        inp = SearchCrmInput(**args)
        return search_crm(inp, db_path).model_dump()
    if name == "get_invoice_status":
        inp2 = GetInvoiceStatusInput(**args)
        return get_invoice_status(inp2, db_path, role, user_id).model_dump()
    if name == "calculate_commission":
        inp3 = CalculateCommissionInput(**args)
        return calculate_commission(inp3, db_path, role, user_id).model_dump()
    if name == "draft_followup":
        inp4 = DraftFollowupInput(**args)
        return draft_followup(inp4, db_path, role).model_dump()
    if name == "request_human_action":
        inp5 = RequestHumanActionInput(**args)
        return request_human_action(inp5, get_allowed_human_actions(), queue).model_dump()
    raise ToolError(ToolErrorCode.FORBIDDEN, f"Outil inconnu : {name}")


class AgentLoop:
    def __init__(
        self,
        llm: LLMClient,
        db_path: str,
        queue: ApprovalQueue,
        tracer: Tracer,
        prompt_version: str = "v1",
        max_iterations: int = 6,
        llm_timeout: float = 20.0,
        tool_timeout: float = 5.0,
        retries_on_invalid: int = 1,
    ) -> None:
        self._llm = llm
        self._db_path = db_path
        self._queue = queue
        self._tracer = tracer
        self._system_base = _load_system_prompt(prompt_version)
        self._max_iter = max_iterations
        self._llm_timeout = llm_timeout
        self._tool_timeout = tool_timeout
        self._retries = retries_on_invalid
        agent_cfg = load_config("agent").get("agent", {})
        self._temperature: float = agent_cfg.get("temperature", 0.0)

    def run(
        self,
        user_message: str,
        role: str,
        user_id: str,
        history: list[dict[str, Any]] | None = None,
        crm_member_id: str | None = None,
        display_name: str = "",
    ) -> tuple[str, list[dict[str, Any]]]:
        """Exécute la boucle pour un message utilisateur.

        Returns (answer, updated_history) so callers can persist multi-turn context.
        crm_member_id: the user's CRM team member ID (tm_XXXXXXXX), if linked.
        """
        context_block = _build_context_block(role, user_id, crm_member_id, display_name)
        full_system = context_block + self._system_base
        # For CRM tool access control: use crm_member_id if available, else Supabase UUID
        effective_id = crm_member_id if crm_member_id else user_id

        if history:
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": full_system},
                *history,
                {"role": "user", "content": user_message},
            ]
        else:
            messages = [
                {"role": "system", "content": full_system},
                {"role": "user", "content": user_message},
            ]

        self._tracer.start(user_message=user_message, role=role, user_id=user_id)
        invalid_retries_left = self._retries

        for iteration in range(self._max_iter):
            t0 = time.monotonic()
            try:
                response: LLMResponse = self._llm.chat(
                    messages=messages,
                    tools=TOOL_SCHEMAS,
                    temperature=self._temperature,
                    timeout=self._llm_timeout,
                )
            except Exception as exc:
                self._tracer.llm_error(str(exc))
                return f"Erreur de communication avec le modèle : {exc}", []

            llm_latency = time.monotonic() - t0
            self._tracer.llm_step(iteration=iteration, latency=llm_latency)

            if not response.has_tool_calls:
                answer = response.content or ""
                self._tracer.finish(answer=answer, iterations=iteration + 1)
                # Return history without the system prompt for storage
                user_and_assistant = [m for m in messages if m["role"] != "system"]
                return answer, user_and_assistant

            # Validate + execute all tool calls
            tool_results: list[dict[str, Any]] = []
            bad_call = False
            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["arguments"]
                t1 = time.monotonic()
                try:
                    result = _call_tool(
                        tool_name, tool_args, role, effective_id, self._db_path, self._queue
                    )
                    _tool_label = tool_name if tool_name in _KNOWN_TOOL_NAMES else "unknown"
                    tool_calls_total.labels(tool=_tool_label, status="ok").inc()
                    self._tracer.tool_call(
                        name=tool_name,
                        args=tool_args,
                        result=result,
                        latency=time.monotonic() - t1,
                    )
                    tool_results.append(
                        {"tool_call_id": tc["id"], "name": tool_name, "result": result}
                    )
                except ValidationError as ve:
                    # Invalid arguments from LLM — retry once
                    bad_call = True
                    _tool_label = tool_name if tool_name in _KNOWN_TOOL_NAMES else "unknown"
                    tool_calls_total.labels(tool=_tool_label, status="error").inc()
                    self._tracer.tool_error(name=tool_name, error=str(ve))
                    if invalid_retries_left > 0:
                        invalid_retries_left -= 1
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": json.dumps({"error": "INVALID_ARGS", "detail": str(ve)}),
                            }
                        )
                    break
                except ToolError as te:
                    _tool_label = tool_name if tool_name in _KNOWN_TOOL_NAMES else "unknown"
                    tool_calls_total.labels(tool=_tool_label, status="error").inc()
                    self._tracer.tool_error(name=tool_name, error=te.code.value)
                    tool_results.append(
                        {
                            "tool_call_id": tc["id"],
                            "name": tool_name,
                            "result": te.to_dict(),
                        }
                    )
                except Exception as exc:
                    # Unexpected infrastructure failure (DB missing, IO error, …)
                    log.exception("Unexpected error in tool %s", tool_name)
                    _tool_label = tool_name if tool_name in _KNOWN_TOOL_NAMES else "unknown"
                    tool_calls_total.labels(tool=_tool_label, status="error").inc()
                    self._tracer.tool_error(name=tool_name, error=str(exc))
                    tool_results.append(
                        {
                            "tool_call_id": tc["id"],
                            "name": tool_name,
                            "result": {
                                "error": "TOOL_INTERNAL_ERROR",
                                "detail": "Erreur interne de l'outil. Contactez l'administrateur.",
                            },
                        }
                    )

            if bad_call and invalid_retries_left >= 0:
                # The tool-error message was appended without a preceding assistant message,
                # which makes the history invalid for the LLM API. Insert it before.
                assistant_retry: dict[str, Any] = {"role": "assistant", "content": response.content}
                if response.tool_calls:
                    assistant_retry["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["arguments"]),
                            },
                        }
                        for tc in response.tool_calls
                    ]
                messages.insert(len(messages) - 1, assistant_retry)
                continue

            # Append assistant message with tool calls + tool results
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": response.content}
            if response.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])},
                    }
                    for tc in response.tool_calls
                ]
            messages.append(assistant_msg)
            for tr in tool_results:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tr["tool_call_id"],
                        "content": json.dumps(tr["result"]),
                    }
                )

        # Max iterations reached
        escalation_msg = (
            "Limite d'itérations atteinte. "
            "La demande est transmise à l'équipe pour traitement manuel."
        )
        escalations_total.labels(reason="max_iterations").inc()
        self._tracer.finish(answer=escalation_msg, iterations=self._max_iter, escalated=True)
        user_and_assistant = [m for m in messages if m["role"] != "system"]
        return escalation_msg, user_and_assistant
