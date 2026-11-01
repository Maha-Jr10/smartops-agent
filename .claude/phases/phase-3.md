# Phase 3: observability
Spec: monitoring/README.md, monitoring/prometheus/alerts.yml.

1. Grafana dashboard JSON in monitoring/grafana/dashboards/: errors, P50/P95 latency, tool usage, escalations, tokens and cost.
2. `monitoring/report.py` (Evidently): reference vs current window from traces. Add a replay script that sends scenarios as simulated traffic.
3. Locust test on `/chat` with the fake LLM; confirm or adjust the P95 gate and document why.
