# ADR 0001 : Boucle d'agent simple écrite par nous

**Statut :** accepté

## Contexte
Il existe des frameworks d'agents (LangGraph, CrewAI). Le cahier des charges préfère
« une solution simple, reproductible et bien évaluée » à une architecture complexe non maîtrisée,
et demande de contrôler les limites d'itération, les délais et les traces.

## Décision
Nous écrivons une boucle courte en Python utilisant l'appel d'outils natif du fournisseur.

## Conséquences
- Chaque étape est visible, testable et traçable, et nous pouvons l'expliquer au jury.
- Moins de dépendances, donc moins de risques de sécurité.
- Une comparaison avec LangGraph reste possible comme extension.
