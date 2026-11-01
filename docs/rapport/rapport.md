# SmartOps Agent : rapport de projet

**ENSAF ISDIA3 - Mini-projet MLOps, 2026-2027**
Binome : JOHN Muhammed & Allah N'diguim Japhet
Date : 2026-11-01

---

## 1. Probleme et perimetre

### 1.1 Contexte

Dans une petite entreprise de services (Smartara, donnees fictives), l'equipe
perd du temps sur des taches repetitives : retrouver un client, verifier une
facture, calculer une commission, preparer une relance. Ces operations demandent
de naviguer dans plusieurs interfaces et d'appliquer des regles metier que l'on
peut oublier.

### 1.2 Objectif

Fournir un agent conversationnel interne qui repond a ces demandes en langage
naturel, cite ses sources, et soumet toute action a effet reel a une validation
humaine.

### 1.3 Perimetre

**Dans le perimetre :** recherche CRM, statut de facture, calcul de commission,
brouillon de relance, demande de validation humaine.

**Hors perimetre :** envoi de messages, modification de donnees, conseil
juridique ou financier, usage par des clients externes, questions generales sans
lien avec l'entreprise.

### 1.4 Risques prioritaires

Trois risques guides toutes les decisions de conception (detail : `docs/gouvernance/registre-des-risques.md`) :

1. **R1** : une action reelle sans validation humaine (zero tolerance, gate dedie).
2. **R2** : injection d'instructions cachees dans les donnees (zero tolerance, gate dedie).
3. **R3** : montant invente par le modele (zero tolerance : calcul en code, ADR 0002).

---

## 2. Architecture

### 2.1 Vue d'ensemble

```
Utilisateur --> API FastAPI
                  |
                  +-- Garde-fous entree (role, injection, limites de debit)
                  |
                  +-- Boucle agent (loop.py)
                  |       |
                  |       +-- LLMClient (Groq ou Ollama)
                  |       |
                  |       +-- Validation Pydantic des arguments
                  |       |
                  |       +-- Outils (5 fonctions Python)
                  |               |
                  |               +-- CRM SQLite (lecture seule)
                  |               +-- File d'approbation humaine
                  |
                  +-- Traces JSONL + MLflow Tracing
                  +-- Metriques Prometheus --> Grafana
```

### 2.2 Boucle agent (ADR 0001)

Nous avons ecrit une boucle courte en Python plutot que d'utiliser LangGraph
ou CrewAI. Raison : un framework supplementaire ajoute des dependances et des
comportements difficiles a tracer. Notre boucle est lisible, testable et
auditable en quelques centaines de lignes.

La boucle execute au maximum 6 iterations. Au-dela, elle escalade vers l'equipe.
Chaque appel LLM et chaque appel outil est trace avec sa latence.

### 2.3 Les cinq outils

| Outil | Role | Effet metier |
|---|---|---|
| search_crm | Cherche un client ou un projet | Aucun (lecture) |
| get_invoice_status | Statut d'une facture | Aucun (lecture) |
| calculate_commission | Calcule une commission | Aucun (calcul en code) |
| draft_followup | Prepare un brouillon de relance | Aucun (brouillon) |
| request_human_action | Soumet une action a validation | Ecriture en file d'attente |

Aucun outil n'a d'effet definitif : seul `request_human_action` insere une
entree dans la file d'approbation, qui necessite une decision humaine explicite
avant tout effet metier.

### 2.4 Commissions (ADR 0002)

Les regles de commission sont implementees en Python deterministe :

- 20 % pour l'apporteur, 40 % pour le realisateur, 60 % si c'est la meme personne.
- Au minimum 40 % de la marge reste a l'entreprise.
- Paiement conditionne au paiement du client, calcule apres les couts directs.

Le modele LLM n'intervient pas dans le calcul : il ne fait que reformuler le
resultat retourne par la fonction Python. Gate `commission_accuracy == 1.0`.

---

## 3. Donnees

### 3.1 Base fictive

La base CRM est entierement fictive, generee par `data/seed/seed.py` avec la
graine 42. Elle contient des clients, projets, factures et membres d'equipe avec
des noms, entreprises et montants inventes.

Commande : `uv run python -m smartops_agent.data.seed`
Reproductibilite : toujours le meme resultat avec la meme graine.

### 3.2 Scenarios d'evaluation

75 scenarios JSONL ecrits par le binome, repartis en 7 categories :

| Categorie | Scenarios | Ce qu'on teste |
|---|---|---|
| nominal | 18 | Cas d'utilisation courants |
| error | 10 | Comportement face a des erreurs metier (introuvable...) |
| ambiguous | 10 | Demande de clarification face a l'ambiguite |
| out_of_scope | 11 | Refus propre des demandes hors perimetre |
| risky | 8 | Blocage des actions a effet sans validation |
| injection | 8 | Resistance aux injections dans les donnees |
| permission | 10 | Respect des droits par role |

### 3.3 Versionnement des donnees

La base fictive est geree par DVC (pipeline `seed_data`). Les scenarios
sont dans Git. Chaque run MLflow enregistre le hash du fichier de scenarios
pour garantir la traçabilite.

---

## 4. Choix techniques

### 4.1 LLM

Modele par defaut : **llama-3.3-70b-versatile** via l'API Groq (gratuit en TP,
appel natif a la fonction-outil). Repli local : **qwen2.5:7b** via Ollama.

Les deux modeles sont compares dans MLflow. Identifiant exact figure dans
`configs/models.yaml` et enregistre dans chaque run.

### 4.2 Traçabilite

Deux niveaux :

1. **Traces JSONL** locales (masquage PII avant ecriture) pour le monitoring et Evidently.
2. **MLflow Tracing** : chaque appel LLM et chaque appel outil est enregistre avec
   sa latence, ses arguments et son resultat (sans raisonnement interne).

Regles de masquage : emails --> `[EMAIL]`, numeros de telephone --> `[PHONE]`.

### 4.3 Qualite du code

- ruff (lint + format), mypy strict, pre-commit a chaque commit.
- Commits conventionnels, branches + pull requests relues par le binome.
- Coverage >= 80 % (atteint : 89 % avec les tests d'evaluation).

### 4.4 Securite

- gitleaks : aucun secret dans le depot.
- bandit : analyse statique du code source.
- pip-audit : audit des dependances (une vulnerabilite transitive PYSEC-2026-2447
  ignoree car sans correctif dans la version compatible de diskcache).
- Trivy et Dependabot : audit de l'image Docker et alertes automatiques.
- Injection Prometheus : labels valides avant utilisation (frozenset des noms connus).

---

## 5. Experiences et resultats

### 5.1 Runs de reference

Deux runs enregistres dans MLflow :

| Run | Modele | Stub | task_success | commission | injection |
|---|---|---|---|---|---|
| 2150b006787b4d3b8a5941ff9e392024 | groq-large (stub) | oui | 0.6667 | 1.0 | 1.0 |
| d1ecc86a0a2446ac9518db7e2c4a1680 | openai/gpt-oss-120b | non | 0.5467 | 1.0 | 0.875 |

Les deux runs utilisent les 75 scenarios avec la graine 42, x1 repetition, le 2026-11-01.

### 5.2 Resultats par categorie (LLM reel, run d1ecc86a0a2446ac9518db7e2c4a1680)

| Categorie | Scenarios | Reussite | Selection outils |
|---|---|---|---|
| nominal | 18 | 88.9 % | 94.4 % |
| error | 10 | 50.0 % | 80.0 % |
| ambiguous | 10 | 40.0 % | 100 % |
| out_of_scope | 11 | 27.3 % | 100 % |
| risky | 8 | 50.0 % | 50.0 % |
| injection | 8 | 87.5 % | 100 % |
| permission | 10 | 20.0 % | 70.0 % |
| **Total** | **75** | **54.7 %** | **86.7 %** |

### 5.3 Analyse des resultats du LLM reel

**Categorie nominal (88.9 %)** : forte amelioration par rapport au stub (55.6 %).
Le vrai LLM extrait les informations du message et inclut les resultats d'outils
dans sa reponse, ce qui correspond aux checks `contains_any`.

**Categorie error (50 %)** : amelioration majeure par rapport au stub (0 %).
5 scenarios echouent encore : le LLM repond parfois de facon generique sans
inclure explicitement le message d'erreur metier.

**Categorie ambiguous (40 %) et out_of_scope (27.3 %)** : les checks attendaient
des formulations specifiques de demande de clarification ou de refus. Le modele
repond correctement du point de vue utilisateur mais dans un style different.

**Categorie risky (50 %)** : 4 scenarios echouent car le modele tente d'agir
directement au lieu d'appeler `request_human_action`. Cela indique un risque
metier reel sur ces scenarios specifiques.

**Categorie injection (87.5 %, 1 echec)** : 1 scenario d'injection a passe la
detection. Le guardrail detecte les patterns connus mais le modele peut etre
influence par des injections formulees differemment. Ce point requiert une
investigation et potentiellement de nouveaux scenarios de test.

**Categorie permission (20 %)** : le modele respecte les guardrails au niveau
technique (ToolError FORBIDDEN) mais la reponse n'inclut pas toujours les mots
attendus par les checks. Les tests d'integration couvrent ces chemins correctement.

### 5.4 Run avec vrai LLM

| Modele | Run MLflow | task_success | injection | p95_latency |
|---|---|---|---|---|
| openai/gpt-oss-120b (groq-large) | d1ecc86a0a2446ac9518db7e2c4a1680 | 0.5467 | 0.875 | 16.3s* |
| openai/gpt-oss-20b (groq-small) | b247be0c129b4204975f57c3d797ea7e | 0.4533 | 0.75 | 23.9s* |

*P95 gonfle par les delais de reeessai API (429 Too Many Requests pendant l'evaluation).
Le modele large est superieur sur toutes les metriques ; il reste le modele par defaut.

**Remarque importante sur les modeles :** les modeles llama-3.3-70b-versatile et
llama-3.1-8b-instant n'etaient plus disponibles sur ce compte Groq. Le run a ete
effectue avec openai/gpt-oss-120b (prompt v2). Voir ADR 0005 pour le detail du
changement de modele.

---

## 6. Observabilite

### 6.1 Metriques Prometheus

10 metriques instrumentees dans `monitoring/metrics.py` :

- `smartops_requests_total` (role, status)
- `smartops_request_latency_seconds` (role)
- `smartops_llm_calls_total` (model, status)
- `smartops_tool_calls_total` (tool, status)
- `smartops_agent_iterations` (role)
- `smartops_escalations_total` (reason)
- `smartops_approval_queue_size`
- `smartops_llm_daily_calls_total`
- `smartops_unconfirmed_risky_actions_total`

### 6.2 Tableau de bord Grafana

Fichier : `monitoring/grafana/dashboards/smartops.json`
10 panneaux en 3 lignes : Requetes, Latence, Outils et escalades.
Metriques cles : P50/P95/P99, taux d'erreur, file d'approbation, appels LLM journaliers.

### 6.3 Rapport de derive Evidently

Script : `src/smartops_agent/monitoring/report.py`
Compare la premiere moitie des traces (reference) a la deuxieme (courante).
Detecte les derives de distribution sur : iterations, longueur des reponses,
nombre d'appels outils, latence, taux d'escalade.

---

## 7. Deploiement

### 7.1 Stack Docker Compose

`docker-compose.yml` : API, MLflow, Prometheus, Grafana.
Commande : `make serve` (API seule) ou `docker compose up` (stack complete).

### 7.2 Strategie shadow/canary (ADR 0004)

Avant toute promotion en production :

1. **Shadow** : la version candidate recoit une copie des requetes via Nginx
   (`mirror` directive). Sa reponse n'est jamais montree. On compare les traces.
2. **Canary** : si les gates passent, 10 % du trafic est redirige vers la candidate
   (`split_clients` Nginx). Les metriques sont surveillees 24-48 h.
3. **Promotion** : `make promote CANDIDATE_IMAGE=<image>` bascule le stable.
4. **Retour arriere** : `make rollback` revient a la version precedente.

### 7.3 CI/CD

GitHub Actions (`.github/workflows/`) :
- ci.yaml : lint, types, tests, securite, evaluation stub, gates.
- docker.yaml : build et push de l'image sur GHCR a chaque tag.

---

## 8. Limites et perspectives

### 8.1 Limites connues

1. **Taux de reussite sous-estime avec le LLM simule** : les categories
   `error` et `permission` ne peuvent pas etre evaluees fidelement sans un
   vrai LLM. Les seuils `baseline` restent provisoires.

2. **Latences du stub non representatives** : le P95 stub est 0 s.
   Le P95 reel est attendu entre 4 et 8 s (Groq, 2-4 iterations x 1-3 s/appel).
   Le seuil de 8 s est fixe par analyse, pas par mesure reelle.

3. **Dependance a l'API Groq** : en cas de panne ou de changement de prix,
   le repli sur Ollama (qwen2.5:7b) est documente mais non benchmark.

4. **Base fictive limitee** : 40 clients, 20 projets, 30 factures.
   Comportement sur une vraie base de production non valide.

5. **Interface utilisateur** : seule une API REST est fournie.
   Une interface web ou Slack est hors perimetre de ce mini-projet.

### 8.2 Perspectives

- Evaluer avec GROQ_API_KEY et mettre a jour les seuils baseline.
- Comparer groq-large vs groq-small sur cout et qualite.
- Ajouter un outil de modification supervisee (avec double validation).
- Etendre la base fictive et diversifier les scenarios.

---

## 9. Risques et gouvernance

Registre complet : `docs/gouvernance/registre-des-risques.md`
Fiche systeme : `docs/gouvernance/fiche-systeme.md`
Decisions d'architecture : `docs/adr/`

### 9.1 Resume des mesures par risque critique

| Risque | Mesure | Verification |
|---|---|---|
| Action sans validation (R1) | request_human_action seul outil a effet | Gate unconfirmed_risky=0, scenarios risky |
| Injection (R2) | Donnees traites comme donnees, jamais comme ordres | Gate injection_resistance=1.0 |
| Montant invente (R3) | Calcul en code, ADR 0002 | Gate commission_accuracy=1.0 |
| Donnees personnelles dans traces (R4) | Masquage email/telephone avant ecriture | Test unitaire |
| Boucle sans fin (R6) | 6 iterations max | Test integration |

### 9.2 Supervision humaine

- Toute action a effet metier passe par la file d'approbation.
- Aucun outil n'envoie de message, ne modifie ni ne supprime de donnee.
- Les traces permettent de reconstruire chaque interaction.
- Le raisonnement interne du modele n'est pas enregistre.

---

## Annexes

- Architecture detaillee : voir README.md (diagramme Mermaid)
- Specifications des outils : `docs/specs/outils.md`
- Resultats complets : `docs/evaluation.md` et `reports/eval/`
- Changelog : `CHANGELOG.md`
- Instructions de reproduction : `docs/reproductibilite.md`
