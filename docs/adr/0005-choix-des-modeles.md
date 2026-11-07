# ADR 0005 : Groq par défaut, Ollama en comparaison

**Statut :** accepté

## Contexte
Le cahier propose Groq (vu en TP) ou un modèle local via Ollama.

## Décision
Groq pour la qualité et la latence ; Ollama pour comparer le coût, la latence et la
confidentialité (les données ne quittent pas la machine). Les deux sont évalués sur le
même jeu de scénarios dans MLflow.

## Identifiants de modeles (v2, 2026-11-01)

Les modeles llama-3.3-70b-versatile et llama-3.1-8b-instant n'etaient plus disponibles
sur ce compte Groq. Remplacement par les modeles disponibles :

| Alias | Ancien | Nouveau |
|---|---|---|
| groq-large | llama-3.3-70b-versatile | openai/gpt-oss-120b |
| groq-small | llama-3.1-8b-instant | openai/gpt-oss-20b |

Les deux nouveaux modeles supportent le tool calling au format OpenAI (verifie avant l'evaluation).
Le changement entraine un increment de prompt_version (v1 -> v2) et un nouveau run d'evaluation.

## Conséquences
Le choix final est justifié par des mesures. Ollama sert aussi de solution de repli
si l'API Groq est indisponible.

## Mise a jour v4 (2026-11-07)

Fournisseur OpenRouter ajoute comme alternative gratuite et sans abonnement :

| Alias | Modele | Fournisseur |
|---|---|---|
| openrouter-large | nvidia/nemotron-3.5-lightning:free | OpenRouter |
| openrouter-small | google/gemma-4-31b-it:free | OpenRouter |

Ces modeles supportent le tool calling au format OpenAI. Ils sont utiles quand le quota
Groq est epuise ou pour comparer la qualite. Les modeles Groq (openai/gpt-oss-120b) restent
le defaut.

Le prompt systeme est maintenant a la version v4 (interdiction des tableaux, retention des IDs,
resolution automatique des noms en identifiants). Un run d'evaluation v4 est a effectuer
et a enregistrer dans `docs/reproductibilite.md`.
