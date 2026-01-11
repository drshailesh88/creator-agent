# Life OS - EC2 Compute Configuration
# EC2 instance and related resources for Life OS

# Data source to find NixOS AMI if not specified
data "aws_ami" "nixos" {
  count = var.ami_id == "" ? 1 : 0

  most_recent = true
  owners      = ["427812963091"] # NixOS Foundation

  filter {
    name   = "name"
    values = ["NixOS-*-x86_64-linux"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }
}

# SSH Key Pair
resource "tls_private_key" "life_os" {
  count = var.ssh_public_key == "" ? 1 : 0

  algorithm = "ED25519"
}

resource "aws_key_pair" "life_os" {
  key_name   = "${local.name_prefix}-key"
  public_key = var.ssh_public_key != "" ? var.ssh_public_key : tls_private_key.life_os[0].public_key_openssh

  tags = {
    Name = "${local.name_prefix}-key"
  }
}

# Store private key in SSM Parameter Store (if generated)
resource "aws_ssm_parameter" "ssh_private_key" {
  count = var.ssh_public_key == "" ? 1 : 0

  name        = "/${local.name_prefix}/ssh-private-key"
  description = "SSH private key for Life OS instance"
  type        = "SecureString"
  value       = tls_private_key.life_os[0].private_key_openssh

  tags = {
    Name = "${local.name_prefix}-ssh-key"
  }
}

# EC2 Instance
resource "aws_instance" "life_os" {
  ami                    = var.ami_id != "" ? var.ami_id : data.aws_ami.nixos[0].id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.life_os.key_name
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.life_os.id]
  iam_instance_profile   = aws_iam_instance_profile.life_os.name
  monitoring             = var.enable_detailed_monitoring

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size
    encrypted             = var.enable_ebs_encryption
    delete_on_termination = true
    iops                  = 3000
    throughput            = 125

    tags = {
      Name = "${local.name_prefix}-root-volume"
    }
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # Enforce IMDSv2
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "enabled"
  }

  user_data = base64encode(templatefile("${path.module}/templates/user_data.sh", {
    environment          = var.environment
    efs_id               = var.enable_efs ? aws_efs_file_system.life_os[0].id : ""
    s3_bootstrap_bucket  = aws_s3_bucket.bootstrap.id
    aws_region           = var.aws_region
    domain_name          = var.domain_name
  }))

  tags = {
    Name = local.instance_name
  }

  lifecycle {
    ignore_changes = [ami, user_data]
  }

  depends_on = [
    aws_internet_gateway.life_os,
    aws_iam_role_policy_attachment.life_os_s3,
    aws_iam_role_policy_attachment.life_os_efs,
  ]
}

# Data Volume (separate from root for data persistence)
resource "aws_ebs_volume" "data" {
  availability_zone = local.availability_zone
  size              = var.data_volume_size
  type              = "gp3"
  encrypted         = var.enable_ebs_encryption
  iops              = 3000
  throughput        = 125

  tags = {
    Name        = "${local.name_prefix}-data-volume"
    Backup      = "true"
    Environment = var.environment
  }
}

resource "aws_volume_attachment" "data" {
  device_name = "/dev/xvdf"
  volume_id   = aws_ebs_volume.data.id
  instance_id = aws_instance.life_os.id
}

# Elastic IP
resource "aws_eip" "life_os" {
  domain = "vpc"

  tags = {
    Name = "${local.name_prefix}-eip"
  }
}

resource "aws_eip_association" "life_os" {
  instance_id   = aws_instance.life_os.id
  allocation_id = aws_eip.life_os.id
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "${local.name_prefix}-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "This alarm monitors EC2 CPU utilization"
  alarm_actions       = []

  dimensions = {
    InstanceId = aws_instance.life_os.id
  }

  tags = {
    Name = "${local.name_prefix}-cpu-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "status_check" {
  alarm_name          = "${local.name_prefix}-status-check"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Maximum"
  threshold           = 0
  alarm_description   = "This alarm monitors EC2 status checks"
  alarm_actions       = []

  dimensions = {
    InstanceId = aws_instance.life_os.id
  }

  tags = {
    Name = "${local.name_prefix}-status-alarm"
  }
}

# EBS Snapshot Lifecycle Policy
resource "aws_dlm_lifecycle_policy" "data_backup" {
  description        = "Life OS data volume backup policy"
  execution_role_arn = aws_iam_role.dlm_lifecycle.arn
  state              = "ENABLED"

  policy_details {
    resource_types = ["VOLUME"]

    schedule {
      name = "Daily snapshots"

      create_rule {
        interval      = 24
        interval_unit = "HOURS"
        times         = ["03:00"]
      }

      retain_rule {
        count = var.backup_retention_days
      }

      tags_to_add = {
        SnapshotCreator = "DLM"
        Environment     = var.environment
      }

      copy_tags = true
    }

    target_tags = {
      Backup = "true"
    }
  }

  tags = {
    Name = "${local.name_prefix}-backup-policy"
  }
}

# IAM Role for DLM
resource "aws_iam_role" "dlm_lifecycle" {
  name = "${local.name_prefix}-dlm-lifecycle-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "dlm.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-dlm-role"
  }
}

resource "aws_iam_role_policy_attachment" "dlm_lifecycle" {
  role       = aws_iam_role.dlm_lifecycle.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSDataLifecycleManagerServiceRole"
}
