# Registre des risques

| ID | Risque | Impact | Mesure | Preuve (test ou métrique) |
|---|---|---|---|---|
| R1 | L'agent exécute une action réelle sans validation | Élevé | Aucun outil n'a cet effet ; seule voie : `request_human_action` | Gate `unconfirmed_risky_actions = 0`, scénarios `risky` |
| R2 | Instructions cachées dans les données (injection) | Élevé | Résultats d'outils traités comme des données ; consignes système strictes | Gate `injection_resistance = 1.0`, scénarios `injection` |
| R3 | Montant inventé par le modèle | Élevé | Calcul en code (ADR 0002) ; vérification du montant affiché | Gate `commission_accuracy = 1.0` |
| R4 | Données personnelles dans les traces | Moyen | Masquage des emails et téléphones avant écriture | Test unitaire de masquage |
| R5 | Accès à la commission d'un collègue | Moyen | Permissions par rôle, portée « ses propres commissions » | Scénarios `permission` |
| R6 | Boucle sans fin ou appels répétés | Moyen | 6 itérations maximum, délais par outil | Test d'intégration, métrique d'itérations |
| R7 | Dépendance au fournisseur LLM (panne, prix, modèle retiré) | Moyen | Repli Ollama, identifiant de modèle figé | Comparaison MLflow |
| R8 | Coût de la démo publique | Moyen | Limite de débit, plafond quotidien d'appels | Métrique de coût, alerte |
| R9 | Confiance excessive des utilisateurs | Moyen | L'agent cite l'outil et les données utilisés ; brouillons seulement | Revue qualitative |
| R10 | Dérive des requêtes après déploiement | Faible | Rapports Evidently, alertes | Rapport de dérive |
| R11 | Relance au ton inadapté envoyée à un client | Faible | Brouillon uniquement, relu par un humain | Scénarios `draft_followup` |

## Supervision humaine

- Toute action listée dans `human_approval_required` exige une validation explicite.
- L'agent demande une précision quand une demande est ambiguë au lieu de deviner.
- Les traces permettent de reconstruire chaque interaction sans enregistrer le
  raisonnement interne du modèle.
