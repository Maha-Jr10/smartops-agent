# ADR 0003 : Répartition Git, DVC et MLflow

**Statut :** accepté

## Contexte
Le cahier demande de versionner le code, les données, les configurations et les artefacts.

## Décision
- **Git :** code, configurations, scénarios (petits fichiers relus en pull request).
- **DVC :** pipeline reproductible, base fictive générée, résultats d'évaluation.
- **MLflow :** chaque run d'évaluation avec paramètres, métriques, version du prompt,
  identifiant du modèle et hash du jeu de scénarios.

## Conséquences
N'importe quel résultat du rapport peut être reconstruit à partir d'un commit et d'un run MLflow.
