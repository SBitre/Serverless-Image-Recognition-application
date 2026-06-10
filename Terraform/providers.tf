terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Local state for now. Remote state (S3 + DynamoDB lock table) noted
  # as future work in the report.
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Owner       = var.team_name
      Environment = "dev"
      ManagedBy   = "terraform"
      CostCenter  = "class-itc6450"
    }
  }
}