# Phase 4: deployment
Spec: ADR 0004, configs/agent.yaml, infra/terraform/, docker-compose.yml.

1. Shadow then canary between stable and candidate versions, promotion and rollback in the Makefile, routing tests.
2. `docker compose up` and the Terraform local env both start and pass `/health`. Add a smoke test.
3. Prepare v1.0.0 (CHANGELOG, tag instructions). Never push or tag.
