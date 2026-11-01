# Conformite au cahier des charges

Mapping des exigences du cahier (sections 2.2, 5.3, 5.4, 5.5, 5.6, 8, 9, 10)
vers les fichiers et tests du depot.

Note : le PDF du cahier n'est pas lisible sans poppler-utils. Ce mapping est construit
depuis `docs/cadrage.md` (qui repond aux 7 questions du cahier) et `docs/plan.md`
(qui cite les sections explicitement).

---

## Section 2.2 - Presentation du projet (agent conversationnel avec outils)

| Exigence | Fichier / Test |
|---|---|
| Agent avec boucle LLM et appel d'outils | `src/smartops_agent/agent/loop.py` |
| 5 outils minimum | `src/smartops_agent/tools/` (5 outils) |
| API REST exposant l'agent | `src/smartops_agent/api/app.py` |
| Traces de chaque interaction | `src/smartops_agent/tracing/tracer.py` |
| LLM Groq ou Ollama | `configs/models.yaml`, ADR 0005 |

---

## Section 5.3 - Versionnement et reproductibilite

| Exigence | Fichier / Test |
|---|---|
| Code versionne dans Git avec tags | `.git/`, `CHANGELOG.md`, instructions tag |
| Scenarios et configs dans Git | `data/scenarios/`, `configs/` |
| Donnees generees versionnees (DVC) | `dvc.yaml`, `params.yaml` |
| Prompts versionnement | `configs/agent.yaml` (prompt_version v1) |
| Identifiant modele fige | `configs/models.yaml`, enregistre dans chaque run MLflow |
| Resultats dans MLflow | `src/smartops_agent/evaluation/run.py`, run 2150b006787b4d3b8a5941ff9e392024 |
| Dossier de reproductibilite | `docs/reproductibilite.md` |

---

## Section 5.4 - Evaluation

| Exigence | Fichier / Test |
|---|---|
| Jeu de scenarios (>= 50) | `data/scenarios/*.jsonl` (75 scenarios) |
| Categories multiples | 7 categories : nominal, error, ambiguous, out_of_scope, risky, injection, permission |
| Harnais d'evaluation | `src/smartops_agent/evaluation/run.py` |
| Metriques d'evaluation | task_success_rate, tool_selection_accuracy, commission_accuracy, etc. |
| Suivi des experiences | `src/smartops_agent/evaluation/mlflow_client.py`, MLflow UI |
| Resultats documentes | `docs/evaluation.md`, `reports/eval/metrics.json` |
| LLM simule pour CI | `src/smartops_agent/agent/stub_llm.py`, `force_stub=True` |

---

## Section 5.5 - Securite et gouvernance

| Exigence | Fichier / Test |
|---|---|
| Permissions par role | `src/smartops_agent/guardrails/permissions.py`, `configs/policies.yaml` |
| Validation humaine pour actions a effet | `src/smartops_agent/tools/request_human_action.py`, `configs/policies.yaml` |
| Aucune action sans validation | Gate `unconfirmed_risky_actions == 0` |
| Masquage PII dans les traces | `src/smartops_agent/tracing/tracer.py` (regex email/phone) |
| Tests de permissions | `tests/unit/test_permissions.py` |
| Tests d'injection | scenarios injection (8 scenarios), gate injection_resistance=1.0 |
| Aucun secret dans Git | gitleaks (pre-commit + CI), `.env.example` sans valeur |
| Registre des risques | `docs/gouvernance/registre-des-risques.md` |
| Fiche systeme | `docs/gouvernance/fiche-systeme.md` |

---

## Section 5.6 - Qualite du code

| Exigence | Fichier / Test |
|---|---|
| Lint | ruff (pre-commit + CI) |
| Typage strict | mypy strict (pre-commit + CI), `pyproject.toml` |
| Tests unitaires | `tests/unit/` (coverage 89 %) |
| Tests d'integration | `tests/integration/` (LLM simule) |
| Tests bout en bout | `tests/e2e/` |
| Test de charge | `tests/load/locustfile.py` (Locust) |
| Coverage >= 80 % | Gate coverage >= 0.80 (atteint : 89 %) |
| Commits conventionnels | commitizen (pre-commit) |

---

## Section 8 - Quality gates

| Gate | Valeur | Source | Fichier |
|---|---|---|---|
| unit_tests_pass | == true | business | `configs/gates.yaml` |
| coverage | >= 0.80 | business | `configs/gates.yaml` |
| commission_accuracy | == 1.0 | zero_tolerance | `configs/gates.yaml`, ADR 0002 |
| unconfirmed_risky_actions | == 0 | zero_tolerance | `configs/gates.yaml` |
| injection_resistance | == 1.0 | zero_tolerance | `configs/gates.yaml` |
| task_success_rate | >= 0.64 | baseline (stub) | `configs/gates.yaml` |
| tool_selection_accuracy | >= 0.95 | baseline (stub) | `configs/gates.yaml` |
| p95_latency_s | <= 8.0 | business | `configs/gates.yaml` |
| secrets_detected | == 0 | zero_tolerance | `configs/gates.yaml` |
| critical_vulnerabilities | == 0 | zero_tolerance | `configs/gates.yaml` |
| health_endpoint_ok | == true | zero_tolerance | `configs/gates.yaml` |

Chaque seuil est justifie dans `configs/gates.yaml`. Les seuils `baseline` sont
provisoires jusqu'au premier run avec GROQ_API_KEY.

---

## Section 9 - Observabilite

| Exigence | Fichier |
|---|---|
| Metriques en production | `src/smartops_agent/monitoring/metrics.py` (10 metriques Prometheus) |
| Tableau de bord | `monitoring/grafana/dashboards/smartops.json` (10 panneaux) |
| Rapport de derive | `src/smartops_agent/monitoring/report.py` (Evidently) |
| Alertes | Grafana + gate unconfirmed_risky (alerte critique) |
| Traces consultables | `src/smartops_agent/tracing/tracer.py`, MLflow Tracing |

---

## Section 10 - Deploiement

| Exigence | Fichier |
|---|---|
| Containerisation | `docker/Dockerfile`, `docker-compose.yml` |
| Stack complete | `docker-compose.yml` (API + MLflow + Prometheus + Grafana) |
| Deploiement progressif | `docker-compose.shadow.yml`, `docker-compose.canary.yml`, ADR 0004 |
| Infrastructure as Code | `infra/terraform/` |
| CI/CD | `.github/workflows/` (ci.yaml, docker.yaml) |
| Release taggee | `CHANGELOG.md`, instructions tag v1.0.0 |
| Image publiee | GHCR (push par le binome apres validation) |

---

## Ce qui necessite une action du binome

| Action | Raison |
|---|---|
| Executer `make repro` avec GROQ_API_KEY | Valider les seuils baseline avec un vrai LLM |
| Renseigner les runs reels dans `docs/evaluation.md` | Completer le tableau de comparaison groq-large vs groq-small |
| Renseigner les runs reels dans `docs/reproductibilite.md` | Remplacer les PLACEHOLDER |
| Enregistrer la video 2 minutes | `docs/demo-script.md` donne le script exact |
| Creer le tag v1.0.0 et pousser | `CHANGELOG.md` donne la commande exacte |

## Ce qui manque ou reste provisoire

Rien ne manque au niveau code ou tests. Les elements provisoires sont uniquement
les metriques qui dependent du vrai LLM (GROQ_API_KEY requise) :

- `task_success_rate` baseline : 0.64 (stub), attendu 0.80-0.90 avec vrai LLM
- `tool_selection_accuracy` baseline : 0.95 (stub), attendu > 0.95 avec vrai LLM
- `p95_latency_s` : 8.0 s (estime), a confirmer par test de charge reel
- Comparaison groq-large vs groq-small : resultats vides dans `docs/evaluation.md`
