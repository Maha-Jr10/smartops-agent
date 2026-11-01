output "api_url" {
  value = "http://localhost:${var.api_port}"
}

output "api_health_url" {
  value = "http://localhost:${var.api_port}/health"
}

output "mlflow_url" {
  value = "http://localhost:${var.mlflow_port}"
}
