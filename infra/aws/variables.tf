variable "region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "db-migration"
}

variable "db_user" {
  type    = string
  default = "postgres"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "db_name" {
  type    = string
  default = "hr"
}

variable "image_tag" {
  type    = string
  default = "v1" # debe coincidir con la imagen que empujes a ECR
}
