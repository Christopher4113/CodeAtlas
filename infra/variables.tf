variable "aws_region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "codeatlas"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "pinecone_api_key" {
  description = "Pinecone API key for vector database access"
  type        = string
  sensitive   = true
  default     = "pcsk_6vNSfX_BwYSbu4ZZWynYeyTEP8tTE44Q5ox4hMu99Wvqd9v5SAQgk5BMs8AhZ4CfSaQxhv"
}
