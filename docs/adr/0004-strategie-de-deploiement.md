# ADR 0004 : Shadow puis canary pour promouvoir une nouvelle version

**Statut :** accepté

## Contexte
Une nouvelle version de l'agent (nouveau prompt ou nouveau modèle) peut passer les tests
hors ligne et se comporter moins bien sur les vraies requêtes.

## Décision
1. **Shadow :** la version candidate reçoit une copie des requêtes, sa réponse est tracée
   mais jamais montrée ni exécutée. On compare les deux versions sur les mêmes requêtes.
2. **Canary :** si les gates passent, la candidate reçoit 10 % du trafic.
3. **Promotion ou retour arrière** selon les métriques, avec une commande documentée.

## Conséquences
Le passage en production devient une décision mesurée, pas un pari.
