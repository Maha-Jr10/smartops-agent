# Plan du projet

## Pourquoi ce projet dépasse le minimum demandé

Le cahier des charges demande une base solide. Comme nous sommes en binôme, nous ajoutons
des éléments qui montrent une vraie maîtrise, sans perdre la simplicité demandée
(« une solution simple, reproductible et bien évaluée est préférable »).

| Ajout | Lien avec le cours |
|---|---|
| Stratégies de déploiement : mode shadow puis canary entre deux versions de l'agent | Titre du module : « stratégies de déploiement » |
| Permissions par rôle et file de validation humaine | 5.5 : permissions minimales, confirmation humaine |
| Scénarios d'attaque (injection dans les données) intégrés aux gates | Section 8 : entrées non fiables |
| Chaque scénario répété 3 fois, résultats avec écart | Évaluation honnête d'un système non déterministe |
| Comparaison Groq / modèle local Ollama : qualité, latence, coût | Compromis qualité, latence, coût (chapitre 2) |
| Infrastructure as Code (Terraform) et image publiée par CD | Chapitre 5 : promotion d'une version |
| Monitoring en deux niveaux : Prometheus/Grafana et Evidently | Section 9 et extension « observabilité avancée » |
| Sécurité de la chaîne : gitleaks, bandit, pip-audit, Trivy, Dependabot | Section 8 : niveau sécurité |
| Test de charge (Locust) pour justifier le seuil de latence P95 | Section 8 : seuils non arbitraires |
| Décisions documentées (ADR) | Reproductibilité et gouvernance |

Règle : aucune extension avant que le périmètre obligatoire soit terminé et évalué.

## Phases

| Phase | Contenu | Terminé quand |
|---|---|---|
| 0. Mise en place | Dépôt, outillage, CI, configs, documents de cadrage | `make ci` passe, CI verte |
| 1. Cœur de l'agent | Base fictive, 5 outils, boucle agent, garde-fous, traces, route `/chat` | Tests unitaires et d'intégration verts |
| 2. Évaluation | ~80 scénarios, harnais d'évaluation, MLflow, baseline, gates, eval gate en CI | Baseline enregistrée, seuils figés et justifiés |
| 3. Observabilité | Métriques Prometheus, tableau Grafana, rapports Evidently, test de charge | Tableau de bord et un rapport de dérive |
| 4. Déploiement | Shadow et canary, Terraform staging, release v1.0.0, démo publique (extension) | Version promue par les gates |
| 5. Livrables | Rapport 8 à 12 pages, dossier de reproductibilité, vidéo 2 minutes | Tout est remis |

## Répartition du binôme

| JOHN Muhammed | Allah N'diguim Japhet |
|---|---|
| Boucle agent, outils, garde-fous | Base fictive et jeu de scénarios |
| API, traces, métriques Prometheus | Harnais d'évaluation, MLflow, quality gates |
| Docker, Terraform, CD, stratégies de déploiement | Grafana, Evidently, test de charge |

**Ensemble :** registre des risques, rapport, vidéo.

**Règles de travail :**
- chaque pull request est relue par l'autre membre avant fusion ;
- chacun doit pouvoir expliquer tout le système, pas seulement sa partie, car le jury
  peut interroger n'importe qui sur n'importe quel point ;
- lors de la présentation, chacun présente une partie qu'il n'a pas codée.
