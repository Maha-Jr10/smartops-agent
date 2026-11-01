# Phase 1: agent core
Spec: docs/specs/outils.md, configs/policies.yaml, configs/agent.yaml, monitoring/README.md, ADR 0001 and 0002.

1. `data/seed.py`: deterministic fictional CRM in SQLite (clients, leads, projects, invoices, team with roles, direct costs, GMD/MAD/USD never converted), seeded from params.yaml. Include traps: two similar client names, an unpaid invoice, an opted-out lead, a lead whose notes contain a prompt injection.
2. `tools/`: the 5 tools, Pydantic in/out models, typed errors. `calculate_commission` is pure code with exhaustive rule tests.
3. `guardrails/`: role permissions, own_only scope, human approval queue, PII masking, tool outputs treated as data.
4. `agent/`: simple loop, Groq native tool calling and Ollama behind one interface. Validate args before each call, max iterations, timeouts, one retry on invalid output, clean failure and escalation. Prompt as a versioned file.
5. `tracing/`: JSONL with every field of cahier 5.4, PII masked, no model reasoning. MLflow Tracing when available.
6. API: `POST /chat` (with role), `GET /approvals`, `POST /approvals/{id}`, rate limit and daily LLM cap, Prometheus metrics per the contract.
7. Integration tests with a fake LLM: invalid args, timeout, iteration limit, injection, permission denial, risky action routed to approval.
