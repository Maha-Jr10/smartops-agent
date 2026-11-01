variable "image_tag" {
  description = "Tag de l'image de l'API"
  type        = string
  default     = "local"
}

variable "app_env" {
  description = "Environnement d'exécution"
  type        = string
  default     = "staging"
}

variable "api_port" {
  description = "Port exposé de l'API"
  type        = number
  default     = 8000
}

variable "mlflow_port" {
  description = "Port exposé de MLflow"
  type        = number
  default     = 5000
}

variable "groq_api_key" {
  description = "Clé API Groq (fournie via TF_VAR_groq_api_key, jamais dans un fichier versionné)"
  type        = string
  sensitive   = true
  default     = ""
}
