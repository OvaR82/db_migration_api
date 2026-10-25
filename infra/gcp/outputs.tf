output "service_url" {
  value = google_cloud_run_v2_service.api.uri
}

output "image" {
  description = "Push the API image to this path"
  value       = local.image
}

output "cloud_sql_connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}
