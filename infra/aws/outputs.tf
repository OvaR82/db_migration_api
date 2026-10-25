output "ecr_repo" {
  value = aws_ecr_repository.api.repository_url
}

output "rds_endpoint" {
  value = aws_db_instance.postgres.address
}

output "alb_dns_name" {
  value = aws_lb.api.dns_name
}
