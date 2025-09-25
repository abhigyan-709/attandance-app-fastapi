terraform {
  required_version = ">= 1.5.0, < 2.0.0"

  # Remote state + locking
  backend "s3" {
    bucket         = "projectdevops-terraform-state"                # <- created by workflow if missing
    key            = "attandance-app-fastapi/s3/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "terraform-locks"                               # <- created by workflow if missing
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }
}

provider "aws" {
  region = var.aws_region
}
