# Life OS - Input Variables
# Variables for configuring the AWS infrastructure

variable "aws_region" {
  description = "AWS region for deploying resources"
  type        = string
  default     = "us-east-1"

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]+$", var.aws_region))
    error_message = "AWS region must be a valid region identifier (e.g., us-east-1, eu-west-1)."
  }
}

variable "instance_type" {
  description = "EC2 instance type for Life OS"
  type        = string
  default     = "t3.medium"

  validation {
    condition     = can(regex("^[a-z][0-9]+[a-z]?\\.[a-z0-9]+$", var.instance_type))
    error_message = "Instance type must be a valid EC2 instance type (e.g., t3.medium, m5.large)."
  }
}

variable "ami_id" {
  description = "AMI ID for NixOS (leave empty to use latest NixOS AMI from AWS Marketplace)"
  type        = string
  default     = ""
}

variable "allowed_ips" {
  description = "List of IP addresses allowed to access Life OS (HTTPS and SSH)"
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for ip in var.allowed_ips : can(regex("^([0-9]{1,3}\\.){3}[0-9]{1,3}$", ip))
    ])
    error_message = "All IPs must be valid IPv4 addresses (e.g., 203.0.113.50)."
  }
}

variable "domain_name" {
  description = "Optional domain name for Life OS (requires Route53 hosted zone)"
  type        = string
  default     = ""
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "enable_ebs_encryption" {
  description = "Enable EBS volume encryption"
  type        = bool
  default     = true
}

variable "root_volume_size" {
  description = "Size of the root EBS volume in GB"
  type        = number
  default     = 50

  validation {
    condition     = var.root_volume_size >= 20 && var.root_volume_size <= 1000
    error_message = "Root volume size must be between 20 and 1000 GB."
  }
}

variable "data_volume_size" {
  description = "Size of the data EBS volume in GB"
  type        = number
  default     = 100

  validation {
    condition     = var.data_volume_size >= 20 && var.data_volume_size <= 2000
    error_message = "Data volume size must be between 20 and 2000 GB."
  }
}

variable "ssh_public_key" {
  description = "SSH public key for EC2 instance access (leave empty to generate new key pair)"
  type        = string
  default     = ""
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed CloudWatch monitoring for EC2 instance"
  type        = bool
  default     = false
}

variable "backup_retention_days" {
  description = "Number of days to retain automated backups"
  type        = number
  default     = 7

  validation {
    condition     = var.backup_retention_days >= 1 && var.backup_retention_days <= 35
    error_message = "Backup retention must be between 1 and 35 days."
  }
}

variable "enable_efs" {
  description = "Enable EFS for shared memory between services"
  type        = bool
  default     = true
}

variable "efs_throughput_mode" {
  description = "EFS throughput mode (bursting or provisioned)"
  type        = string
  default     = "bursting"

  validation {
    condition     = contains(["bursting", "provisioned", "elastic"], var.efs_throughput_mode)
    error_message = "EFS throughput mode must be one of: bursting, provisioned, elastic."
  }
}
