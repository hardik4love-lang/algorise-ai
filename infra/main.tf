// Algorise AI - Production infrastructure bootstrap.
//
// This root module provisions the shared platform substrate: networking,
// container registry, secrets, observability and IAM federation. Workload
// specific resources (PostgreSQL, Redis, Kubernetes) live in ./modules.
//
// Usage:
//   terraform -chdir=infra/environments/production init
//   terraform -chdir=infra/environments/production plan
//   terraform -chdir=infra/environments/production apply

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.13"
    }
  }

  backend "s3" {
    bucket         = "algorise-ai-terraform-state"
    key            = "algorise-ai/production/terraform.tfstate"
    region         = "ap-south-1"
    encrypt        = true
    dynamodb_table = "algorise-ai-terraform-locks"
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "algorise-ai"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

module "network" {
  source = "../../modules/network"

  environment         = var.environment
  region              = var.region
  vpc_cidr            = var.vpc_cidr
  availability_zones  = var.availability_zones
  enable_nat_gateway  = true
  single_nat_gateway  = false
}

module "container_registry" {
  source = "../../modules/container-registry"

  environment    = var.environment
  region         = var.region
  repository_url = "ghcr.io/hardik4love-lang/algorise-ai"
  image_retention_days = 90
}

module "secrets_manager" {
  source = "../../modules/secrets-manager"

  environment   = var.environment
  region        = var.region
  secret_prefix = "algorise-ai"
}

module "observability" {
  source = "../../modules/observability"

  environment    = var.environment
  region         = var.region
  retention_days = 30
  enable_alerts  = true
}

module "iam_workload_identity" {
  source = "../../modules/iam-workload-identity"

  environment     = var.environment
  region          = var.region
  github_owner    = "hardik4love-lang"
  github_repos    = ["algorise-ai"]
  oidc_provider   = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
}

module "backup_dr" {
  source = "../../modules/backup-disaster-recovery"

  environment      = var.environment
  region           = var.region
  backup_retention_days = 30
  cross_region_backup     = true
  dr_region              = "us-east-1"
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}
