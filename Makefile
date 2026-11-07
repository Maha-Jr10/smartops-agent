# SmartOps Agent : commandes du projet.
# Toutes les commandes passent par uv pour garantir les mêmes versions partout.
.RECIPEPREFIX = >
.DEFAULT_GOAL := help
.PHONY: help setup lint format typecheck test test-unit test-integration test-e2e coverage \
        security ci seed eval gates repro serve serve-ui mlflow-ui monitor load-test \
        docker-build docker-up docker-down tf-init tf-plan tf-apply tf-destroy clean

UV := uv run
TF_DIR := infra/terraform/envs/local

help: ## Affiche cette aide
> @grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

setup: ## Installe les dépendances et les hooks pre-commit
> uv sync --all-extras --group dev
> $(UV) pre-commit install
> $(UV) pre-commit install --hook-type commit-msg

lint: ## Vérifie le style (ruff)
> $(UV) ruff check src tests
> $(UV) ruff format --check src tests

format: ## Corrige le style automatiquement
> $(UV) ruff check --fix src tests
> $(UV) ruff format src tests

typecheck: ## Vérifie les types (mypy strict)
> $(UV) mypy

test: test-unit test-integration ## Tests unitaires et d'intégration

test-unit: ## Tests unitaires
> $(UV) pytest -m unit

test-integration: ## Tests d'intégration (LLM simulé)
> $(UV) pytest -m integration

test-e2e: ## Tests de bout en bout
> $(UV) pytest -m e2e

coverage: ## Tests avec couverture (seuil 80 %)
> $(UV) pytest -m "unit or integration" --cov --cov-report=term-missing --cov-report=xml

security: ## Analyse de sécurité du code et des dépendances
> $(UV) bandit -c pyproject.toml -r src
> $(UV) pip-audit --ignore-vuln PYSEC-2026-2447 --ignore-vuln PYSEC-2026-1325 --ignore-vuln PYSEC-2026-4298

ci: lint typecheck coverage security ## Reproduit la CI en local

seed: ## Génère la base CRM fictive
> $(UV) dvc repro seed_data

eval: ## Lance l'évaluation sur le jeu de scénarios
> $(UV) dvc repro evaluate

gates: ## Applique les quality gates sur les derniers résultats
> $(UV) dvc repro gates

repro: ## Rejoue tout le pipeline DVC
> $(UV) dvc repro

serve: ## Lance l'API en local
> $(UV) uvicorn smartops_agent.api.app:app --reload --port 8000

serve-ui: ## Lance le frontend Next.js (port 3001)
> cd frontend && npm run dev

mlflow-ui: ## Ouvre l'interface MLflow
> $(UV) mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000

monitor: ## Génère le rapport Evidently sur les traces
> $(UV) python -m smartops_agent.monitoring.report

load-test: ## Test de charge (latence P95)
> $(UV) locust -f tests/load/locustfile.py --headless -u 5 -r 1 -t 1m --host http://localhost:8000

docker-build: ## Construit l'image Docker
> docker build -f docker/Dockerfile -t smartops-agent:local .

docker-up: ## Lance la stack (API, MLflow, Prometheus, Grafana)
> docker compose up -d --build

docker-down: ## Arrête la stack
> docker compose down

smoke: ## Smoke test /health apres docker compose up (attendre que l'API demarre)
> $(UV) python -c "\
import sys, time, urllib.request;\
url='http://localhost:8000/health';\
[time.sleep(2) for _ in range(10) if not [print('ok') for _ in range(1) if __import__('contextlib').suppress(Exception) or True]];\
import urllib.request;\
r=urllib.request.urlopen(url,timeout=5);\
assert r.status==200,'health check failed';\
print('smoke: /health OK')"

shadow: ## Shadow deployment: CANDIDATE_IMAGE=smartops-agent:<tag> make shadow
> docker compose -f docker-compose.yml -f docker-compose.shadow.yml up -d
> @echo "Shadow started. Compare traces then run: make canary CANDIDATE_IMAGE=$$CANDIDATE_IMAGE"

canary: ## Canary deployment (10 % trafic): CANDIDATE_IMAGE=smartops-agent:<tag> make canary
> docker compose -f docker-compose.yml -f docker-compose.canary.yml up -d
> @echo "Canary started on :8080. Monitor gates, then run: make promote or make rollback"

promote: ## Promovoir le candidat comme stable (mettre a jour IMAGE_TAG dans .env)
> @echo "Promoting CANDIDATE_IMAGE=$(CANDIDATE_IMAGE) to stable."
> @echo "1. Run: docker tag $(CANDIDATE_IMAGE) smartops-agent:stable"
> @echo "2. Update IMAGE_TAG in .env, then: make docker-up"
> @echo "3. Run: make docker-down && docker compose up -d --build"

rollback: ## Retour arriere : stoppe le canary, relance le stable
> docker compose down
> docker compose up -d --build
> @echo "Rollback complete: stable version is running."

tf-init: ## Terraform : initialisation
> terraform -chdir=$(TF_DIR) init

tf-plan: ## Terraform : plan
> terraform -chdir=$(TF_DIR) plan

tf-apply: ## Terraform : déploiement
> terraform -chdir=$(TF_DIR) apply

tf-destroy: ## Terraform : suppression
> terraform -chdir=$(TF_DIR) destroy

clean: ## Supprime les fichiers temporaires
> rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml htmlcov dist
