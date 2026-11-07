# Script de demonstration (2 minutes)

Video cible : 2 min, ecran partage, voix ou captions, pas de montage complexe.
Ordre : interface deployee --> cas nominal --> chaine MLOps --> cas d'echec --> conclusion.

---

## [0:00 - 0:15] Titre et contexte

**Ecran :** interface web SmartOps ouverte dans le navigateur (Netlify).

**Caption :** "SmartOps Agent - Mini-projet MLOps ENSAF ISDIA3"

**Voix :** "SmartOps Agent aide une equipe commerciale avec des questions
sur ses clients, factures et commissions. L'agent lit et prepare, il n'agit
jamais seul."

---

## [0:15 - 0:30] Connexion et demarrage

**Ecran :** page de connexion Supabase, puis tableau de bord SmartOps avec le chat vide.

**Caption :** "Connexion via Supabase --> interface prete"

**Voix :** "L'application est deployee publiquement sur Netlify. Apres connexion,
le panneau de conversation s'ouvre. Les messages sont sauvegardes localement
et l'historique est retenu entre les requetes."

---

## [0:30 - 1:00] Cas nominal : recherche et calcul de commission

**Ecran :** panneau de conversation. Taper les messages suivants :

**Message 1 :** `Liste les clients actifs`

Resultat attendu : liste a puces avec noms et identifiants (cl_...).

**Caption :** "L'agent appelle search_crm --> liste a puces, pas de tableau"

**Message 2 :** `Cherche le client Bensaid Rim`

Resultat attendu : l'agent trouve "Entreprise Bensaid Rim" et retourne son identifiant.

**Caption :** "Recherche par nom - l'agent trouve l'ID lui-meme"

**Message 3 :** `Calcule la commission d'Amiri Abdelhadi sur le projet Support annuel #20`

Resultat attendu : l'agent cherche d'abord le membre de l'equipe par nom (tm_...),
puis le projet par nom (pr_...), puis appelle calculate_commission. Il affiche
le montant calcule en code Python, pas par le LLM.

**Caption :** "L'agent resout les IDs automatiquement - l'utilisateur ne connait que les noms"

**Voix :** "L'agent resout lui-meme les identifiants a partir des noms. L'utilisateur
n'a pas besoin de connaitre les IDs CRM. Le montant de la commission est calcule
par du code deterministe, pas par le modele."

---

## [1:00 - 1:20] Chaine MLOps : quality gates

**Ecran :** terminal, commande `make ci`.

**Caption :** "make ci : lint, types, tests, securite, evaluation, gates"

**Voix :** "Chaque commit passe par make ci. On voit l'evaluation sur 75 scenarios
avec le LLM simule, 170 tests, couverture 82 %, et les quality gates."

**Montrer (optionnel) :** ouvrir l'interface MLflow (`mlflow ui`) et montrer le run
`2150b006787b4d3b8a5941ff9e392024` avec commission_accuracy=1.0 et injection_resistance=1.0.

**Caption :** "MLflow : commission_accuracy=1.0, gates ok"

---

## [1:20 - 1:40] Cas d'echec : action sans validation bloquee

**Ecran :** panneau de conversation.

**Message :** `Marque la commission du projet Support annuel #20 comme payee`

Resultat attendu : l'agent ne peut pas modifier de donnees. Il soumet une
demande via request_human_action et affiche "demande envoyee pour validation".

**Caption :** "L'agent soumet a la file d'approbation, ne modifie rien lui-meme"

**Ecran :** cliquer sur l'onglet "Approbations" pour montrer la demande en attente.

**Caption :** "Aucune action sans validation humaine - gate unconfirmed_risky=0"

**Voix :** "Toute action a effet reel passe par la file d'approbation.
L'onglet Approbations montre la demande en attente. Un humain doit valider
avant que quoi que ce soit se produise."

---

## [1:40 - 2:00] Conclusion et observabilite

**Ecran :** onglet Monitoring de l'interface, puis README dans le navigateur.

**Caption :** "Monitoring en temps reel, shadow/canary, Grafana, Evidently"

**Voix :** "Le projet couvre la chaine MLOps complete : versionnement,
evaluation, quality gates, observabilite et deploiement progressif
shadow puis canary. Backend sur Railway, frontend sur Netlify,
authentification Supabase. Tout le code et la documentation sont dans le depot."

**Caption :** "make ci avant tout commit. Pas de push sans gates verts."

---

## Notes pour la prise de vue

- Ouvrir la version deployee sur Netlify pour montrer le vrai deploiement.
- Si besoin de test local : `make serve` pour le backend, `cd frontend && npm run dev` pour le frontend.
- S'assurer d'avoir un compte Supabase configure dans `.env` pour l'auth.
- Garder le terminal avec `make ci` sous la main : c'est la sequence la plus
  importante pour le jury MLOps.
- L'historique de conversation est retenu dans la meme session (session_id en localStorage).
  Ouvrir un nouvel onglet pour repartir de zero si necessaire.
