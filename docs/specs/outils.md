# Spécification des outils

Cinq outils, tous simulés sur une base fictive. Chaque appel est validé (Pydantic) avant
exécution, limité dans le temps et tracé. Les permissions sont définies dans
`configs/policies.yaml`.

| Outil | Effet | Rôles autorisés |
|---|---|---|
| `search_crm` | lecture | commercial, delivery, admin |
| `get_invoice_status` | lecture | commercial, admin |
| `calculate_commission` | lecture (calcul) | tous, limité à ses propres commissions sauf admin |
| `draft_followup` | brouillon (rien n'est envoyé) | commercial, admin |
| `request_human_action` | escalade | tous |

## search_crm

- **Entrées :** `query` (texte, 2 à 100 caractères), `entity` (`lead` | `client` | `project`)
- **Sorties :** liste de fiches (identifiant, nom, statut), au plus 10
- **Erreurs :** `NOT_FOUND`, `AMBIGUOUS` (plusieurs résultats proches : l'agent doit demander une précision)

## get_invoice_status

- **Entrées :** `invoice_id` ou `project_id`
- **Sorties :** montant, devise (GMD, MAD ou USD, jamais convertie), statut payé/non payé, date
- **Erreurs :** `NOT_FOUND`, `FORBIDDEN`

## calculate_commission

- **Entrées :** `project_id`, `person_id`
- **Sorties :** montant, devise, règle appliquée, détail du calcul
- **Règles (code déterministe) :** base = total du projet moins les coûts directs ;
  20 % apporteur, 40 % réalisation, 60 % si la même personne fait les deux ;
  l'entreprise garde au moins 40 % ; si plusieurs personnes réalisent, les 40 % sont partagés.
- **Erreurs :** `CLIENT_NOT_PAID` (aucune commission avant le paiement du client),
  `FORBIDDEN` (commission d'un collègue), `NOT_FOUND`

## draft_followup

- **Entrées :** `lead_id`, `tone` (`neutral` | `friendly` | `formal`)
- **Sorties :** objet et texte du brouillon, marqué « brouillon, non envoyé »
- **Erreurs :** `OPTED_OUT` (le prospect a refusé les messages), `NOT_FOUND`

## request_human_action

- **Entrées :** `action` (une des actions de `human_approval_required`), `reason`, `payload`
- **Sorties :** identifiant de demande, statut `pending`
- **Erreurs :** `UNKNOWN_ACTION`
- **Rôle :** seule voie vers une action réelle. L'agent ne voit jamais la décision finale
  comme acquise : il répond « demande envoyée pour validation ».

## Limites communes

- 6 itérations maximum par requête, puis arrêt propre et escalade
- délai maximal par outil : 5 s ; par appel au LLM : 20 s
- une seule nouvelle tentative si le modèle renvoie un appel mal formé
