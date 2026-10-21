variable "environment" {
  type        = string
  description = "Deployment environment name."
}

variable "region" {
  type    = string
  default = "ap-south-1"
}

variable "vpc_cidr" {
  type    = string
  default = "10.42.0.0/16"
}

variable "availability_zones" {
  type    = list(string)
  default = ["ap-south-1a", "ap-south-1b", "ap-south-1c"]
}

variable "certificate_arn" {
  type        = string
  description = "ACM certificate ARN for the public API endpoint."
}

variable "hosted_zone_id" {
  type        = string
  description = "Route53 hosted zone ID for the Algorise domain."
}
