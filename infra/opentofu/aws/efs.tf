# Life OS - EFS Configuration
# Elastic File System for shared memory between services

# EFS File System
resource "aws_efs_file_system" "life_os" {
  count = var.enable_efs ? 1 : 0

  creation_token   = "${local.name_prefix}-efs"
  encrypted        = true
  performance_mode = "generalPurpose"
  throughput_mode  = var.efs_throughput_mode

  # Provisioned throughput (only applicable when throughput_mode is "provisioned")
  provisioned_throughput_in_mibps = var.efs_throughput_mode == "provisioned" ? 50 : null

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  lifecycle_policy {
    transition_to_primary_storage_class = "AFTER_1_ACCESS"
  }

  tags = {
    Name    = local.efs_name
    Purpose = "Shared memory for Life OS services"
  }
}

# EFS Mount Target
resource "aws_efs_mount_target" "life_os" {
  count = var.enable_efs ? 1 : 0

  file_system_id  = aws_efs_file_system.life_os[0].id
  subnet_id       = aws_subnet.public.id
  security_groups = [aws_security_group.efs[0].id]
}

# Security Group for EFS
resource "aws_security_group" "efs" {
  count = var.enable_efs ? 1 : 0

  name        = "${local.name_prefix}-efs-sg"
  description = "Security group for EFS mount targets"
  vpc_id      = aws_vpc.life_os.id

  # Allow NFS traffic from Life OS instance
  ingress {
    description     = "NFS from Life OS instance"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.life_os.id]
  }

  # Allow all outbound traffic
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-efs-sg"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# EFS Access Point for application data
resource "aws_efs_access_point" "app_data" {
  count = var.enable_efs ? 1 : 0

  file_system_id = aws_efs_file_system.life_os[0].id

  posix_user {
    gid = 1000
    uid = 1000
  }

  root_directory {
    path = "/app-data"

    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "0755"
    }
  }

  tags = {
    Name    = "${local.name_prefix}-ap-app-data"
    Purpose = "Application data access point"
  }
}

# EFS Access Point for shared memory
resource "aws_efs_access_point" "shared_memory" {
  count = var.enable_efs ? 1 : 0

  file_system_id = aws_efs_file_system.life_os[0].id

  posix_user {
    gid = 1000
    uid = 1000
  }

  root_directory {
    path = "/shared-memory"

    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "0755"
    }
  }

  tags = {
    Name    = "${local.name_prefix}-ap-shared-memory"
    Purpose = "Inter-service shared memory"
  }
}

# EFS Access Point for logs
resource "aws_efs_access_point" "logs" {
  count = var.enable_efs ? 1 : 0

  file_system_id = aws_efs_file_system.life_os[0].id

  posix_user {
    gid = 1000
    uid = 1000
  }

  root_directory {
    path = "/logs"

    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "0755"
    }
  }

  tags = {
    Name    = "${local.name_prefix}-ap-logs"
    Purpose = "Centralized logging"
  }
}

# EFS Backup Policy
resource "aws_efs_backup_policy" "life_os" {
  count = var.enable_efs ? 1 : 0

  file_system_id = aws_efs_file_system.life_os[0].id

  backup_policy {
    status = var.environment == "prod" ? "ENABLED" : "DISABLED"
  }
}

# CloudWatch Alarms for EFS
resource "aws_cloudwatch_metric_alarm" "efs_burst_credits" {
  count = var.enable_efs && var.efs_throughput_mode == "bursting" ? 1 : 0

  alarm_name          = "${local.name_prefix}-efs-burst-credits"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "BurstCreditBalance"
  namespace           = "AWS/EFS"
  period              = 300
  statistic           = "Average"
  threshold           = 1000000000000 # 1 TB
  alarm_description   = "EFS burst credits running low"
  alarm_actions       = []

  dimensions = {
    FileSystemId = aws_efs_file_system.life_os[0].id
  }

  tags = {
    Name = "${local.name_prefix}-efs-credits-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "efs_percent_io_limit" {
  count = var.enable_efs ? 1 : 0

  alarm_name          = "${local.name_prefix}-efs-io-limit"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "PercentIOLimit"
  namespace           = "AWS/EFS"
  period              = 300
  statistic           = "Average"
  threshold           = 90
  alarm_description   = "EFS approaching IO limit"
  alarm_actions       = []

  dimensions = {
    FileSystemId = aws_efs_file_system.life_os[0].id
  }

  tags = {
    Name = "${local.name_prefix}-efs-io-alarm"
  }
}
