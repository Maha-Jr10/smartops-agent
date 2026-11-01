"""Métriques Prometheus exposées sur /metrics."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

chat_requests_total = Counter(
    "smartops_chat_requests_total",
    "Nombre total de requêtes POST /chat",
    ["role", "status"],
)

chat_latency_seconds = Histogram(
    "smartops_chat_latency_seconds",
    "Latence de bout en bout des requêtes /chat (secondes)",
    buckets=[0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0],
)

tool_calls_total = Counter(
    "smartops_tool_calls_total",
    "Nombre d'appels à chaque outil",
    ["tool", "status"],
)

iterations_total = Histogram(
    "smartops_agent_iterations",
    "Nombre d'itérations par requête",
    buckets=[1, 2, 3, 4, 5, 6],
)

llm_calls_daily = Gauge(
    "smartops_llm_calls_daily_current",
    "Appels LLM dans la fenêtre journalière courante",
)

approval_queue_size = Gauge(
    "smartops_approval_queue_size",
    "Nombre de demandes d'approbation en attente",
)

escalations_total = Counter(
    "smartops_escalations_total",
    "Nombre d'escalades vers un humain",
    ["reason"],
)

unconfirmed_risky_actions_total = Counter(
    "smartops_unconfirmed_risky_actions_total",
    "Actions metier executees sans validation humaine",
)
