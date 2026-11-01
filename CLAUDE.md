# SmartOps Agent (mini-projet MLOps ENSAF, Projet 3)

Agent d'assistance avec outils simulés, traces, évaluation, quality gates. Binôme.
Brief : `docs/cadrage.md` et `docs/plan.md` (ne pas relire le PDF dans `docs/brief/`).

## Commandes
- `make ci` : lint, types, tests, sécurité. Doit passer avant tout commit.
- `make test-unit`, `make test-integration`, `make serve`, `make repro`
- Toujours passer par `uv run` ; jamais `pip install`.

## Carte du code
- `src/smartops_agent/` : api, agent, tools, guardrails, tracing, evaluation, monitoring, data
- `configs/` : agent, models, policies (permissions), gates (seuils justifiés)
- `tests/` : unit, integration (LLM simulé), e2e, load
- Specs outils : `docs/specs/outils.md`. Décisions : `docs/adr/`.

## Règles
- Code, noms et commentaires en anglais ; documentation en français simple.
- Jamais de tiret cadratin ni de double tiret dans la documentation.
- Les montants (commissions) sont calculés en code, jamais par le LLM (ADR 0002).
- Aucune action à effet métier sans `request_human_action` (configs/policies.yaml).
- Pas de raisonnement interne du modèle dans les traces ; masquer emails et téléphones.
- Aucun secret ni donnée réelle dans Git. Données fictives uniquement.
- mypy strict et ruff doivent passer. Tests pour chaque règle métier et garde-fou.
- Changer un prompt ou un modèle : incrémenter `prompt_version`, relancer l'évaluation.

## Construire le projet
- `/build <n>` ou `/build all` : instructions par phase dans `.claude/phases/` (ne lire que la phase en cours).
- Ne jamais inventer un chiffre : tout résultat cité vient d'un vrai run, avec son identifiant MLflow.
  Sans clé API, construire et tester avec un LLM simulé et laisser un emplacement marqué.
- Pas de push, pas de tag : le binôme s'en charge.

## Économie de tokens
- Lire seulement les fichiers nécessaires ; utiliser Grep avant Read.
- Ne pas lire : `uv.lock`, `mlruns/`, `data/seed/`, `reports/eval/results.jsonl`, `.venv/`.
- Pour lancer les tests, déléguer à l'agent `test-runner` (rapport court).
- Réponses courtes : résultat, fichiers modifiés, prochaine étape.
