# Cadrage du projet

Réponses aux 7 questions de la section 11 du cahier des charges, avant tout développement.

## 1. Quel problème précis le système cherche-t-il à résoudre ?

Dans une petite entreprise de services, l'équipe perd du temps sur des tâches répétitives :
retrouver un client ou un prospect, vérifier si une facture est payée, calculer une commission,
préparer une relance. Ces tâches demandent de chercher dans plusieurs écrans et d'appliquer
des règles qu'on oublie facilement.

L'agent répond à ces demandes en langage naturel. Il **lit** et **prépare**, mais il
**n'exécute jamais seul** une action qui a un effet réel (envoyer un email, marquer une
commission comme payée, donner un prix à un client). Ces actions passent par une demande
de validation humaine.

**Hors périmètre :** questions générales sans lien avec l'entreprise, conseils juridiques
ou financiers, modification de données, envoi de messages.

**Conséquences d'une erreur :** une commission mal calculée crée un conflit dans l'équipe ;
un email envoyé à tort abîme la relation avec un client ; une fuite d'information sur la
commission d'un collègue pose un problème de confidentialité. Ces trois risques guident
les garde-fous et les quality gates.

## 2. Quelles données ou quels documents sont utilisés, et avec quels droits ?

- **Base CRM fictive** (clients, prospects, projets, factures) générée par un script avec une
  graine fixe. Aucune donnée réelle ni personnelle.
- **Jeu de scénarios** écrit par le binôme.
- **Règles de commission** : règles réelles de l'entreprise (20 % apporteur, 40 % réalisation,
  60 % si la même personne fait les deux, au moins 40 % pour l'entreprise, paiement seulement
  après le paiement du client, calcul après les coûts directs). Utilisées avec l'accord de
  l'entreprise ; ce ne sont pas des données personnelles.
- **Modèles** : Groq (API autorisée, vue en TP) et un modèle local via Ollama.

Aucun secret ni donnée personnelle n'est déposé dans Git. Un fichier `.env.example` sans
valeur secrète est fourni.

## 3. Quel est le résultat attendu et comment sera-t-il évalué ?

Résultat attendu : une réponse correcte, ou une demande de précision, ou un refus, ou une
escalade vers un humain, selon le cas.

Évaluation sur environ 80 scénarios répartis en 7 catégories (normaux, erreurs, ambigus,
hors périmètre, risqués, injection, permissions), chacun répété 3 fois car un LLM n'est pas
déterministe. Indicateurs :

- taux de réussite des tâches ;
- pertinence de la sélection des outils ;
- taux d'appels invalides ou échoués ;
- latence (moyenne et P95) et nombre moyen d'appels par tâche ;
- comportement face aux demandes ambiguës ou non autorisées ;
- capacité à refuser une action risquée ou à demander une validation ;
- coût estimé par requête.

## 4. Quelles versions doivent être conservées ?

| Élément | Comment |
|---|---|
| Code | Git, tags de version sémantique (v0.1.0, v0.2.0...) |
| Scénarios | Git (fichiers JSONL versionnés, hash enregistré dans MLflow) |
| Données générées | DVC (pipeline `seed_data`, graine dans `params.yaml`) |
| Prompts | version dans `configs/agent.yaml`, enregistrée dans chaque run |
| Modèles | identifiant exact du fournisseur dans `configs/models.yaml` |
| Configurations | Git (`configs/`, `params.yaml`) |
| Résultats | MLflow (paramètres, métriques, artefacts) et DVC (`reports/eval`) |
| Image déployée | GHCR, une image par tag |

## 5. Quels tests empêchent une régression ?

- **Unitaires :** règles de commission, validation des arguments, permissions par rôle,
  masquage des données personnelles, chargement des configurations.
- **Intégration :** boucle agent avec un LLM simulé (réponses invalides, délais dépassés,
  limite d'itérations).
- **Bout en bout :** scénarios complets via l'API.
- **Eval gate :** évaluation avec le vrai LLM ; une version moins bonne que la version stable
  est bloquée.
- **Sécurité :** secrets, analyse statique, vulnérabilités des dépendances et de l'image.

## 6. Quels événements et indicateurs seront observés après le déploiement ?

- Disponibilité et erreurs : taux d'erreur, requêtes échouées.
- Performance : latence moyenne et P95, itérations par requête.
- Qualité : taux d'escalade, taux de refus, appels d'outils invalides.
- Coût : tokens et coût estimé par requête et par jour.
- Dérive : distribution des outils utilisés, longueur et langue des requêtes (Evidently).
- Sécurité : toute action risquée sans validation déclenche une alerte critique.

## 7. Quels sont les risques principaux et les mesures ?

Détail complet dans le [registre des risques](gouvernance/registre-des-risques.md).
Les trois principaux :

1. **Action réelle sans validation** → aucun outil n'a ce pouvoir ; seule voie : la demande de
   validation humaine. Gate à zéro tolérance.
2. **Injection d'instructions cachées dans les données** → les résultats d'outils sont traités
   comme des données, jamais comme des ordres. Scénarios d'attaque dans le jeu de test.
3. **Chiffres inventés par le modèle** → la commission est calculée par du code déterministe,
   le modèle ne fait que reformuler le résultat.
