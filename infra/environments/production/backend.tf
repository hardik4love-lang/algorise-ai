# Production environment wiring.
#
# Copy to .tfvars and fill in the account-specific values. Never commit
# the populated file.

terraform {
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
}
