# ADR 0005 : Groq par défaut, Ollama en comparaison

**Statut :** accepté

## Contexte
Le cahier propose Groq (vu en TP) ou un modèle local via Ollama.

## Décision
Groq pour la qualité et la latence ; Ollama pour comparer le coût, la latence et la
confidentialité (les données ne quittent pas la machine). Les deux sont évalués sur le
même jeu de scénarios dans MLflow.

## Conséquences
Le choix final est justifié par des mesures. Ollama sert aussi de solution de repli
si l'API Groq est indisponible.
