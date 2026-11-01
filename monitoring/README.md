# Monitoring

Deux niveaux, complémentaires :

1. **Temps réel (Prometheus et Grafana)** : erreurs, latence P50/P95, appels d'outils,
   escalades, tokens et coût. Alertes dans `prometheus/alerts.yml`.
2. **Analyse de dérive (Evidently)** : rapports périodiques sur les traces JSONL, comparant
   une fenêtre de référence à la fenêtre courante.

## Contrat des métriques (à implémenter en phase 1)

| Métrique | Type | Labels |
|---|---|---|
| `smartops_requests_total` | compteur | `status` |
| `smartops_request_latency_seconds` | histogramme | |
| `smartops_tool_calls_total` | compteur | `tool`, `status` |
| `smartops_iterations_per_request` | histogramme | |
| `smartops_escalations_total` | compteur | `reason` |
| `smartops_unconfirmed_risky_actions_total` | compteur | |
| `smartops_llm_tokens_total` | compteur | `model`, `direction` |
| `smartops_llm_cost_usd_total` | compteur | `model` |

## Rapports Evidently (phase 3)

- Dérive de la distribution des outils utilisés
- Dérive de la longueur et de la langue des requêtes
- Évolution du taux d'escalade et de refus
- Évolution de la latence et du coût

Sortie : `reports/monitoring/*.html`, commande `make monitor`.
