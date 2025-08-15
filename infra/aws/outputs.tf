# ECR repository URL to push the Docker image
output "ecr_repo" {
  value = aws_ecr_repository.api.repository_url
}

# RDS endpoint (used in DATABASE_URL for the app)
output "rds_endpoint" {
  value = aws_db_instance.postgres.address
}

# Public DNS name of the Application Load Balancer (ALB)
output "alb_dns_name" {
  value = aws_lb.api.dns_name
}
