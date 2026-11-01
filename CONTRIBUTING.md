# Contribuer

## Branches
- `main` : protégée, toujours déployable, seulement par pull request
- `develop` : intégration
- `feature/<sujet>`, `fix/<sujet>` : travail en cours

## Commits (convention vérifiée par pre-commit)
`feat:`, `fix:`, `test:`, `docs:`, `ci:`, `refactor:`, `chore:`
Exemple : `feat(tools): add commission calculation rules`

## Avant chaque push
`make ci` doit passer.

## Pull requests
- relue et approuvée par l'autre membre du binôme
- si le prompt, le modèle ou une configuration change : évaluation relancée et run MLflow joint
- jamais de secret ni de donnée personnelle

## Versions
Version sémantique. Un tag `vX.Y.Z` sur `main` déclenche la publication de l'image.
