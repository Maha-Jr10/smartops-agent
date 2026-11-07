# Dossier de reproductibilite

## Prerequis

- Python 3.12, uv (versions exactes figees dans `uv.lock`)
- Docker et Terraform (optionnels, pour le stack complet)
- Une cle Groq dans `.env` (voir `.env.example`) pour relancer avec un vrai LLM

## Reconstruire un resultat

1. `git checkout <tag>` (ex. `v1.0.0`)
2. `make setup` (installe les dependances via uv, active pre-commit)
3. `make repro` (regenere la base fictive avec la graine de `params.yaml`,
   relance l'evaluation et les gates)
4. Comparer avec le run MLflow correspondant (identifiant note dans le rapport)

Sans cle API Groq : `uv run python -m smartops_agent.evaluation.run --stub --repeats 1`
reproduit exactement le run de reference (LLM simule, graine fixe).

## Table des runs de reference

| Tag | Run MLflow | Modele | Prompt | Scenarios | task_success | commission_accuracy | injection |
|---|---|---|---|---|---|---|---|
| v1.0.0 | `e5bdad4e6961471dad462a6cf81658ea` | groq-large (stub) | v2 | 75 x1 | 0.6667 | 1.0 | 1.0 |
| v1.0.0 | `d1ecc86a0a2446ac9518db7e2c4a1680` | openai/gpt-oss-120b (reel) | v2 | 75 x1 | 0.5467 | 1.0 | 0.875 |
| v1.0.0 | `b247be0c129b4204975f57c3d797ea7e` | openai/gpt-oss-20b (reel) | v2 | 75 x1 | 0.4533 | 1.0 | 0.75 |
| v1.0.0 | `reports/eval/metrics.json (2026-11-02)` | openai/gpt-oss-120b (reel) | v2 | 75 x1 | 0.4933 | 1.0 | 0.75 |
| post-v1.0.0 | (a renseigner apres eval v4) | openai/gpt-oss-120b (reel) | v4 | 75 x1 | - | - | - |

Note : la variabilite entre runs groq-large (0.4933 a 0.5467) est due au non-determinisme du LLM avec repeats=1. Relancer avec repeats=3 pour des resultats plus stables.

## Graine des donnees

```
params.yaml : seed.random_seed = 42
```

La base fictive est regeneree deterministe par `make repro`. Tout run doit indiquer
le hash du fichier de scenarios (`scenario_hash` dans les parametres MLflow).

## Changer un prompt ou un modele

1. Modifier `configs/agent.yaml` (incrementer `prompt_version`) ou `configs/models.yaml`.
2. Lancer `make ci` : lint, types, tests, gates avec le LLM simule.
3. Lancer une evaluation avec le vrai LLM : `uv run python -m smartops_agent.evaluation.run --repeats 3`.
4. Enregistrer le nouvel identifiant MLflow dans cette table.
5. Mettre a jour `configs/gates.yaml` si les seuils `baseline` changent.

**Historique des versions de prompt :**
- v2 : modeles Groq remplaces (openai/gpt-oss-120b, openai/gpt-oss-20b), runs enregistres ci-dessus.
- v4 (actuelle) : interdiction des tableaux markdown, retention des IDs, agent ne demande jamais d'ID.
  Un eval run v4 est a lancer et son identifiant MLflow est a renseigner dans la table ci-dessus.
