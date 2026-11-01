# Script de demonstration (2 minutes)

Video cible : 2 min, ecran partage, voix ou captions, pas de montage complexe.
Ordre : systeme en marche --> chaine MLOps --> un cas d'echec.

---

## [0:00 - 0:15] Titre et contexte

**Ecran :** README ouvert dans le navigateur, section architecture.

**Caption :** "SmartOps Agent - Mini-projet MLOps ENSAF ISDIA3"

**Voix :** "SmartOps Agent aide une equipe commerciale avec des questions
sur ses clients, factures et commissions. L'agent lit et prepare, il n'agit
jamais seul."

---

## [0:15 - 0:30] Demarrage du systeme

**Ecran :** terminal, commande `make serve`, puis `curl http://localhost:8000/health`.

**Caption :** "make serve --> API prete en quelques secondes"

Resultat attendu dans le terminal :
```json
{"status": "ok", "version": "1.0.0"}
```

**Voix :** "Le systeme demarre en une commande. La route /health confirme
que l'API tourne."

---

## [0:30 - 1:00] Cas nominal : recherche CRM et calcul de commission

**Ecran :** terminal ou Swagger UI (`http://localhost:8000/docs`).

**Requete :**
```json
POST /chat
{
  "message": "Quel est le statut de la facture du projet Alpha de Diallo ?",
  "role": "commercial",
  "user_id": "alice"
}
```

**Caption :** "L'agent appelle get_invoice_status via l'API Groq"

**Voix :** "L'agent appelle l'outil get_invoice_status avec les bons
arguments, recoit le resultat de la base fictive, et repond en citant
les donnees. Il n'invente rien."

**Montrer :** la trace JSONL dans `data/traces/` ou dans l'interface MLflow,
avec le masquage PII visible.

**Caption :** "Traces JSONL : les emails sont masques --> [EMAIL]"

---

## [1:00 - 1:20] Chaine MLOps : quality gates

**Ecran :** terminal, commande `make ci`.

**Caption :** "make ci : lint, types, tests, securite, evaluation, gates"

**Voix :** "Chaque commit passe par make ci. Ici on voit l'evaluation
sur 75 scenarios avec le LLM simule, et les quality gates."

**Montrer :** la sortie de `make ci` avec les gates en vert.
Optionnel : ouvrir l'interface MLflow (`mlflow ui`) et montrer le run
`2150b006787b4d3b8a5941ff9e392024` avec ses metriques.

**Caption :** "MLflow : run 2150b00... - commission_accuracy=1.0, gates ok"

---

## [1:20 - 1:40] Cas d'echec : action sans validation bloquee

**Ecran :** terminal ou Swagger UI.

**Requete :**
```json
POST /chat
{
  "message": "Marque la commission du projet Alpha comme payee",
  "role": "commercial",
  "user_id": "alice"
}
```

**Caption :** "L'agent ne peut pas modifier de donnees directement"

**Voix :** "L'agent repond qu'il ne peut pas modifier les donnees.
Il propose de soumettre une demande de validation."

**Montrer :** la reponse de l'agent et eventuellement la file d'approbation
vide (`GET /approvals`).

**Caption :** "Aucune action sans validation humaine - gate unconfirmed_risky=0"

---

## [1:40 - 2:00] Conclusion et deploiement

**Ecran :** README, section "Chaine MLOps" avec le tableau des outils.

**Caption :** "Shadow/canary, Grafana, Evidently - tout est observable"

**Voix :** "Le projet couvre la chaine MLOps complete : versionnement,
evaluation, quality gates, observabilite, et deploiement progressif
shadow puis canary. Tout le code et la documentation sont dans le depot."

**Caption :** "make ci avant tout commit. Pas de push sans gates verts."

---

## Notes pour la prise de vue

- Resoudre les variables d'environnement avant la video : copier `.env.example`
  en `.env`, renseigner ou non GROQ_API_KEY (le mode stub marche sans).
- Lancer `make serve` dans un premier terminal, garder un second pour les requetes.
- Si la latence Groq est visible a l'ecran, c'est un plus pour montrer le P95 reel.
- Garder le terminal avec `make ci` sous la main : c'est la sequence la plus
  importante pour le jury MLOps.
