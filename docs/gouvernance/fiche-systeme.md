# Fiche systeme

| Rubrique | Contenu |
|---|---|
| Nom et version | SmartOps Agent v1.0.0 |
| Date | 2026-11-01 |
| Auteurs | Binome ISDIA3 ENSAF |
| Usage prevu | Assistance interne : recherche CRM, statut de facture, calcul de commission, brouillons de relance |
| Hors usage | Envoi de messages, modification de donnees, conseil juridique ou financier, usage par des clients externes |
| Utilisateurs | Membres de l'equipe (roles commercial, delivery, admin) ; acces local uniquement |
| Modeles | groq-large : llama-3.3-70b-versatile (Groq) ; local : qwen2.5:7b (Ollama) |
| Donnees | Base fictive generee (graine 42, aucune donnee personnelle reelle) ; masquage PII dans les traces |
| Evaluation (stub) | Run MLflow 2150b006787b4d3b8a5941ff9e392024 ; 75 scenarios x1 ; task_success=0.6667 ; commission_accuracy=1.0 ; injection_resistance=1.0 |
| Evaluation (reel) | A completer par le binome apres run avec GROQ_API_KEY (voir docs/evaluation.md) |
| Limites connues | 1. Taux de reussite sur categories error et permission sous-estime avec le LLM simule (voir docs/evaluation.md) ; 2. Stub non representatif des vraies latences (P95 reel attendu 4-8 s) ; 3. Modele distant dependant de la disponibilite de l'API Groq (repli Ollama) |
| Quality gates | couverture >= 80 %, commission_accuracy == 1.0, unconfirmed_risky_actions == 0, injection_resistance == 1.0, p95_latency_s <= 8.0 |
| Supervision humaine | Toute action a effet metier passe par request_human_action ; aucun outil n'a d'effet direct |
| Traces | JSONL + MLflow Tracing ; raisonnement interne masque ; emails et telephones masques |
| Deploiement | Docker Compose (stack locale), shadow/canary via overlays Nginx |
| Monitoring | Prometheus + Grafana (latence P50/P95/P99, erreurs, appels outils) ; Evidently (derive) |
| Contact | JOHN Muhammed & Allah N'diguim Japhet, ISDIA3 ENSAF |
| ADR | 0001 boucle agent, 0002 commissions deterministes, 0003 versionnement, 0004 deploiement shadow/canary, 0005 choix modeles |
