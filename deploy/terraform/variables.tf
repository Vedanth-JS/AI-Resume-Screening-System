variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "us-central1-a"
}

variable "node_count" {
  description = "Initial number of GKE nodes"
  type        = number
  default     = 3
}

variable "min_nodes" {
  description = "Minimum GKE nodes (autoscaling)"
  type        = number
  default     = 2
}

variable "max_nodes" {
  description = "Maximum GKE nodes (autoscaling)"
  type        = number
  default     = 10
}
