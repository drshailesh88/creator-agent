# Life OS - Outputs
# Output values for the deployed infrastructure

# Instance Information
output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.life_os.id
}

output "instance_ip" {
  description = "Elastic IP address of the Life OS instance"
  value       = aws_eip.life_os.public_ip
}

output "instance_private_ip" {
  description = "Private IP address of the Life OS instance"
  value       = aws_instance.life_os.private_ip
}

output "instance_dns" {
  description = "Public DNS name of the Life OS instance"
  value       = aws_eip.life_os.public_dns
}

# API Endpoint
output "api_endpoint" {
  description = "HTTPS endpoint for Life OS API"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "https://${aws_eip.life_os.public_ip}"
}

output "ssh_connection" {
  description = "SSH connection command"
  value       = "ssh -i <private-key> root@${aws_eip.life_os.public_ip}"
}

# S3 Bucket Information
output "s3_bucket_names" {
  description = "Names of created S3 buckets"
  value = {
    nixos_images = aws_s3_bucket.nixos_images.id
    bootstrap    = aws_s3_bucket.bootstrap.id
  }
}

output "s3_bucket_arns" {
  description = "ARNs of created S3 buckets"
  value = {
    nixos_images = aws_s3_bucket.nixos_images.arn
    bootstrap    = aws_s3_bucket.bootstrap.arn
  }
}

# EFS Information
output "efs_id" {
  description = "EFS file system ID"
  value       = var.enable_efs ? aws_efs_file_system.life_os[0].id : null
}

output "efs_dns_name" {
  description = "EFS DNS name for mounting"
  value       = var.enable_efs ? aws_efs_file_system.life_os[0].dns_name : null
}

output "efs_access_points" {
  description = "EFS access point IDs"
  value = var.enable_efs ? {
    app_data      = aws_efs_access_point.app_data[0].id
    shared_memory = aws_efs_access_point.shared_memory[0].id
    logs          = aws_efs_access_point.logs[0].id
  } : null
}

# VPC Information
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.life_os.id
}

output "subnet_id" {
  description = "Public subnet ID"
  value       = aws_subnet.public.id
}

output "security_group_id" {
  description = "Security group ID for Life OS instance"
  value       = aws_security_group.life_os.id
}

# IAM Information
output "instance_role_arn" {
  description = "ARN of the EC2 instance IAM role"
  value       = aws_iam_role.life_os.arn
}

output "vmimport_role_arn" {
  description = "ARN of the VM Import role"
  value       = aws_iam_role.vmimport.arn
}

# SSH Key Information
output "ssh_key_name" {
  description = "Name of the SSH key pair"
  value       = aws_key_pair.life_os.key_name
}

output "ssh_private_key_ssm_parameter" {
  description = "SSM Parameter Store path for SSH private key (if auto-generated)"
  value       = var.ssh_public_key == "" ? aws_ssm_parameter.ssh_private_key[0].name : null
  sensitive   = true
}

# Environment Information
output "environment" {
  description = "Deployment environment"
  value       = var.environment
}

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

# KMS Key (if created)
output "kms_key_arn" {
  description = "ARN of the KMS key (prod only)"
  value       = var.environment == "prod" ? aws_kms_key.life_os[0].arn : null
}

# Mount Commands (for reference)
output "efs_mount_command" {
  description = "Command to mount EFS on the instance"
  value       = var.enable_efs ? "sudo mount -t efs -o tls ${aws_efs_file_system.life_os[0].id}:/ /mnt/efs" : null
}

# Summary
output "deployment_summary" {
  description = "Summary of the deployed infrastructure"
  value = {
    instance = {
      id         = aws_instance.life_os.id
      type       = var.instance_type
      public_ip  = aws_eip.life_os.public_ip
      private_ip = aws_instance.life_os.private_ip
    }
    storage = {
      root_volume_size = var.root_volume_size
      data_volume_size = var.data_volume_size
      efs_enabled      = var.enable_efs
    }
    network = {
      vpc_cidr = local.vpc_cidr
      subnet   = local.public_subnet_cidr
    }
    security = {
      allowed_ips = var.allowed_ips
    }
  }
}
