# Dossier de reproductibilité (à compléter en phase 5)

## Prérequis
- Python 3.12, uv (versions exactes figées dans `uv.lock`)
- Docker et Terraform (optionnels)
- Une clé Groq dans `.env` (voir `.env.example`)

## Reconstruire un résultat
1. `git checkout <tag>`
2. `make setup`
3. `make repro` (régénère la base fictive avec la graine de `params.yaml`, relance l'évaluation et les gates)
4. Comparer avec le run MLflow correspondant (identifiant noté dans le rapport)

## Table des runs de référence
| Tag | Run MLflow | Modèle | Prompt | Scénarios | Résultat |
|---|---|---|---|---|---|
| à compléter | | | | | |
