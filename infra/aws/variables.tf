variable "region" {
  type        = string
  description = "AWS region where resources will be deployed"
}

variable "project" {
  type        = string
  description = "Project identifier used for naming resources"
}

variable "db_user" {
  type        = string
  description = "Username for the PostgreSQL RDS instance"
}

variable "db_password" {
  type        = string
  description = "Password for the PostgreSQL RDS instance"
  sensitive   = true
}

variable "db_name" {
  type        = string
  description = "Database name for the RDS instance"
}

variable "image_tag" {
  type        = string
  description = "Docker image tag to deploy to ECS"
}
