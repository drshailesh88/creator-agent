# Life OS - AWS Infrastructure
# OpenTofu/Terraform configuration for deploying Life OS on AWS

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  # Uncomment to use remote state
  # backend "s3" {
  #   bucket         = "life-os-terraform-state"
  #   key            = "infrastructure/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "life-os-terraform-locks"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

# Random suffix for globally unique resource names
resource "random_id" "suffix" {
  byte_length = 4
}

# Local variables
locals {
  name_prefix = "life-os-${var.environment}"

  common_tags = {
    Project     = "Life OS"
    Environment = var.environment
    ManagedBy   = "OpenTofu"
    Repository  = "creator-agent"
  }

  # Resource naming
  vpc_name              = "${local.name_prefix}-vpc"
  instance_name         = "${local.name_prefix}-instance"
  s3_images_bucket      = "${local.name_prefix}-nixos-images-${random_id.suffix.hex}"
  s3_bootstrap_bucket   = "${local.name_prefix}-bootstrap-${random_id.suffix.hex}"
  efs_name              = "${local.name_prefix}-shared-memory"

  # Network configuration
  vpc_cidr              = "10.0.0.0/16"
  public_subnet_cidr    = "10.0.1.0/24"
  availability_zone     = "${var.aws_region}a"

  # Security configuration
  allowed_ssh_cidrs     = [for ip in var.allowed_ips : "${ip}/32"]
  allowed_https_cidrs   = [for ip in var.allowed_ips : "${ip}/32"]
}
