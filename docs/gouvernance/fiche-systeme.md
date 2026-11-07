# Fiche systeme

| Rubrique | Contenu |
|---|---|
| Nom et version | SmartOps Agent v1.0.0 |
| Date | 2026-11-02 |
| Auteurs | JOHN Muhammed & Allah N'diguim Japhet, ISDIA3 ENSAF |
| Usage prevu | Assistance interne : recherche CRM, statut de facture, calcul de commission, brouillons de relance |
| Hors usage | Envoi de messages, modification de donnees, conseil juridique ou financier, usage par des clients externes |
| Utilisateurs | Membres de l'equipe (roles commercial, delivery, admin) ; acces via interface web publique (Netlify) avec authentification Supabase |
| Modeles | groq-large : openai/gpt-oss-120b via Groq ; OpenRouter : nvidia/nemotron-3.5-lightning:free, google/gemma-4-31b-it:free ; local : qwen2.5:7b via Ollama |
| Donnees | Base fictive generee (graine 42, 30 clients, 40 projets, 60 factures) ; masquage PII dans les traces |
| Evaluation (stub) | Run MLflow 2150b006787b4d3b8a5941ff9e392024 ; 75 scenarios x1 ; prompt v4 ; task_success=0.6667 ; commission_accuracy=1.0 ; injection_resistance=1.0 |
| Evaluation (reel) | openai/gpt-oss-120b ; 75 scenarios x1 ; task_success=0.4933 ; commission_accuracy=1.0 ; injection_resistance=0.75 (2 echecs a investiguer) ; p95_latency_s=15.8s eval / 3.45s production (Grafana, 2026-11-02) |
| Quality gates | commission_accuracy=1.0 PASSE ; unconfirmed_risky_actions=0 PASSE ; tool_selection_accuracy=0.8267 PASSE ; couverture=83.75 % PASSE ; injection_resistance=0.75 ECHEC (gate==1.0) ; task_success_rate=0.4933 ECHEC (gate>=0.5) ; p95_latency_s=15.8s ECHEC eval (3.45s production sans throttling) |
| Limites connues | 1. injection_resistance=0.75 : 2 scenarios d'injection passent, renforcement du prompt requis ; 2. task_success varie 0.49-0.55 avec repeats=1 (non-determinisme LLM, relancer avec repeats=3) ; 3. Modele distant dependant de la disponibilite de l'API Groq (repli Ollama disponible) |
| Supervision humaine | Toute action a effet metier passe par request_human_action ; aucun outil n'a d'effet direct |
| Traces | JSONL + MLflow Tracing ; raisonnement interne masque ; emails et telephones masques |
| Deploiement | Backend : Railway (Docker, utilisateur non-root app) ; Frontend : Next.js sur Netlify ; Auth : Supabase ; stack locale : Docker Compose, shadow/canary via overlays Nginx |
| Monitoring | Prometheus + Grafana (latence P50/P95/P99, erreurs, appels outils) ; Evidently (derive, rapport 2026-11-02 : pas de derive globale, 2/7 colonnes signalees) |
| Contact | JOHN Muhammed & Allah N'diguim Japhet, ISDIA3 ENSAF |
| ADR | 0001 boucle agent, 0002 commissions deterministes, 0003 versionnement, 0004 deploiement shadow/canary, 0005 choix modeles |
