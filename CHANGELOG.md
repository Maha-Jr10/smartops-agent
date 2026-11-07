# Changelog

Toutes les modifications notables sont documentees ici.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).
Versionnement : [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Ajouts
- Interface web Next.js (Netlify) avec panneau de conversation, file d'approbation et monitoring
- Authentification Supabase (tokens JWT verifies cote backend)
- Fournisseur OpenRouter configure (nvidia/nemotron-3.5-lightning:free, google/gemma-4-31b-it:free, gratuits)
- Noms marocains / classmates comme donnees fictives CRM (round-robin deterministe, tous les noms apparaissent)
- Equipe fictive de 7 membres : Bihkak Asmae (commercial), Japhet Allah-n'diguim (admin) ajoutes
- search_crm supporte l'entite team_member (table team_members, champ role retourne comme status)
- Memoire de session : frontend envoie session_id (UUID, localStorage), l'historique backend est active par tour
- Persistance des messages dans localStorage, survive au rechargement de page
- Systeme de prompt v4 : interdiction des tableaux markdown, retention des IDs de recherche, l'agent ne demande jamais d'ID a l'utilisateur (il cherche par nom lui-meme)

### Corrections
- Piege CRM : nom trap mis a jour "Societe Marocaine de Services" (etait "Societe Generale Africaine")
- Boucle agent : insertion du message assistant manquant avant le message outil orphelin lors d'un mauvais appel (evitait HTTP 500)
- search_crm : pas de detection AMBIGUOUS sur les requetes de listage (query vide)
- Interface : rendu markdown dans les bulles de l'agent (gras, listes)
- Disposition mobile responsive pour le header et les suggestions

## [1.0.0] - 2026-11-01

### Ajouts
- Agent conversationnel SmartOps avec boucle LLM (Groq llama-3.3-70b / Ollama)
- Cinq outils : search_crm, get_invoice_status, calculate_commission,
  draft_followup, request_human_action
- Masquage PII dans les traces (emails, telephones)
- File d'approbation humaine pour les actions a effet metier (policies.yaml)
- Evaluation sur 75 scenarios (7 categories) avec LLM simule pour la CI
- Quality gates : couverture 80 %, commission_accuracy = 1.0,
  injection_resistance = 1.0, unconfirmed_risky = 0, P95 latence <= 8 s
- Tableau de bord Grafana : latence P50/P95/P99, taux d'erreur, appels outils,
  escalades, file d'approbation, appels LLM journaliers
- Rapport de derive Evidently (reference vs fenetre courante)
- Pipeline DVC : seed_data, evaluate, gates
- Stack Docker Compose : API, MLflow, Prometheus, Grafana
- Deploiement shadow/canary via overlays Docker Compose + proxy Nginx
- Infrastructure Terraform pour l'environnement local

### Securite
- Ports Terraform lies a 127.0.0.1 (pas d'exposition reseau)
- Labels Prometheus valides avant injection (pas d'injection via le champ role)
- PII masque dans les traces et les erreurs LLM
- pip-audit integre a la CI (PYSEC-2026-2447 supprime, dep transitive sans fix)

## Instructions de tag v1.0.0

Ces commandes sont a executer par le binome apres validation finale :

```bash
# Verifier que la CI est verte
git log --oneline -5

# Creer le tag signe
git tag -s v1.0.0 -m "feat: version 1.0.0 - SmartOps Agent MLOps"

# Pousser le tag (le binome decide quand)
# git push origin v1.0.0
```

[Unreleased]: https://github.com/example/smartops-agent/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/example/smartops-agent/releases/tag/v1.0.0
