# SmartOps Agent : commandes du projet.
# Toutes les commandes passent par uv pour garantir les mêmes versions partout.
.RECIPEPREFIX = >
.DEFAULT_GOAL := help
.PHONY: help setup lint format typecheck test test-unit test-integration test-e2e coverage \
        security ci seed eval gates repro serve mlflow-ui monitor load-test \
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
> $(UV) pip-audit --ignore-vuln PYSEC-2026-2447

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

mlflow-ui: ## Ouvre l'interface MLflow
> $(UV) mlflow ui --backend-store-uri ./mlruns --port 5000

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
