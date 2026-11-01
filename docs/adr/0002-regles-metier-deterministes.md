# ADR 0002 : Les calculs d'argent sont faits par du code, pas par le LLM

**Statut :** accepté

## Contexte
Un LLM peut se tromper sur un pourcentage ou une soustraction, et le fait avec assurance.
Une commission fausse crée un conflit réel dans l'équipe.

## Décision
`calculate_commission` applique les règles en code déterministe. Le modèle choisit l'outil
et reformule le résultat, il ne calcule rien.

## Conséquences
- Gate à 100 % d'exactitude, testable par des tests unitaires.
- Le LLM ne peut pas « inventer » un montant ; un test vérifie que le montant affiché
  est identique à celui renvoyé par l'outil.
