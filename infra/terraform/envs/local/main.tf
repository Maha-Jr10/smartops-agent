# Environnement "staging" local, décrit en Infrastructure as Code.
# Même image que la CI : ce qui est testé est ce qui est déployé.

locals {
  repo_root = abspath("${path.module}/../../../..")
}

resource "docker_network" "smartops" {
  name = "smartops-${var.app_env}"
}

resource "docker_image" "api" {
  name = "smartops-agent:${var.image_tag}"
  build {
    context    = local.repo_root
    dockerfile = "docker/Dockerfile"
  }
}

resource "docker_image" "mlflow" {
  name = "ghcr.io/mlflow/mlflow:v2.16.2"
}

resource "docker_volume" "mlflow" {
  name = "smartops-mlflow-${var.app_env}"
}

resource "docker_container" "mlflow" {
  name    = "smartops-mlflow-${var.app_env}"
  image   = docker_image.mlflow.image_id
  restart = "unless-stopped"
  command = [
    "mlflow", "server", "--host", "0.0.0.0", "--port", "5000",
    "--backend-store-uri", "sqlite:////mlflow/mlflow.db",
    "--artifacts-destination", "/mlflow/artifacts",
  ]
  networks_advanced {
    name = docker_network.smartops.name
  }
  ports {
    internal = 5000
    external = var.mlflow_port
    ip       = "127.0.0.1"
  }
  volumes {
    volume_name    = docker_volume.mlflow.name
    container_path = "/mlflow"
  }
}

resource "docker_container" "api" {
  name    = "smartops-api-${var.app_env}"
  image   = docker_image.api.image_id
  restart = "unless-stopped"
  env = [
    "APP_ENV=${var.app_env}",
    "GROQ_API_KEY=${var.groq_api_key}",
    "MLFLOW_TRACKING_URI=http://${docker_container.mlflow.name}:5000",
  ]
  networks_advanced {
    name = docker_network.smartops.name
  }
  ports {
    internal = 8000
    external = var.api_port
    ip       = "127.0.0.1"
  }
  healthcheck {
    test     = ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
    interval = "30s"
    timeout  = "5s"
    retries  = 3
  }
}
