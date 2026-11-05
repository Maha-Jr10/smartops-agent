"""Chargement de la configuration : variables d'environnement et fichiers YAML versionnés."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = Path(os.environ.get("SMARTOPS_CONFIG_DIR", PROJECT_ROOT / "configs"))


class Settings(BaseSettings):
    """Paramètres d'exécution. Les secrets viennent de l'environnement, jamais du dépôt."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["local", "ci", "staging", "production"] = "local"
    log_level: str = "INFO"
    groq_api_key: SecretStr | None = None
    openrouter_api_key: SecretStr | None = None
    ollama_base_url: str = "http://localhost:11434"
    mlflow_tracking_uri: str = "sqlite:///mlflow.db"
    daily_llm_call_cap: int = 500
    rate_limit_per_minute: int = 10

    # Supabase — required in staging/production, optional for local dev
    supabase_url: str = ""
    supabase_anon_key: SecretStr | None = None
    supabase_service_role_key: SecretStr | None = None
    supabase_jwt_secret: SecretStr | None = None  # Project Settings → API → JWT Settings

    # Public URL of the deployed API (used by the frontend in production)
    api_public_url: str = "http://localhost:8000"

    # Allowed CORS origins (JSON list in env: '["https://app.netlify.app"]')
    cors_origins: list[str] = ["http://localhost:3001", "http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_config(name: str, config_dir: Path | None = None) -> dict[str, Any]:
    """Lit configs/<name>.yaml et vérifie qu'il s'agit bien d'un objet."""
    path = (config_dir or CONFIG_DIR) / f"{name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Configuration introuvable : {path}")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Configuration invalide (objet attendu) : {path}")
    return data
