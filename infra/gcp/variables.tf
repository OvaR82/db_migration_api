variable "project_id" {
  description = "GCP project to deploy into (billing must be enabled)"
  type        = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "name" {
  description = "Prefix for resource names"
  type        = string
  default     = "db-migration"
}

variable "image_tag" {
  description = "Tag of the API image pushed to Artifact Registry"
  type        = string
  default     = "v1"
}

variable "db_tier" {
  description = "Cloud SQL machine type"
  type        = string
  default     = "db-f1-micro"
}

variable "allow_unauthenticated" {
  description = "Make the Cloud Run URL public. The API has no auth of its own."
  type        = bool
  default     = true
}
