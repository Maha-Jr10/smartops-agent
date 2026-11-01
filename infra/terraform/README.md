# Infrastructure as Code (Terraform)

| Environnement | Rôle | Statut |
|---|---|---|
| `envs/local` | Staging local : API et MLflow dans Docker, décrits en Terraform | prêt |
| `envs/cloud` | Démo publique sur un service de conteneurs managé | extension, phase 4 |

Commandes : `make tf-init`, `make tf-plan`, `make tf-apply`, `make tf-destroy`.
La clé Groq est passée par la variable d'environnement `TF_VAR_groq_api_key`.
