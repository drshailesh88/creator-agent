# Life OS - IAM Configuration
# IAM roles。and policies for EC2, S3, EFS, and VM Import

# IAM Role for EC2 Instance
resource "aws_iam_role" "life_os" {
  name = "${local.name_prefix}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-ec2-role"
  }
}

# IAM Instance Profile
resource "aws_iam_instance_profile" "life_os" {
  name = "${local.name_prefix}-instance-profile"
  role = aws_iam_role.life_os.name

  tags = {
    Name = "${local.name_prefix}-instance-profile"
  }
}

# S3 Access Policy
resource "aws_iam_policy" "s3_access" {
  name        = "${local.name_prefix}-s3-access"
  description = "Policy for S3 access from Life OS instance"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ListBuckets"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.nixos_images.arn,
          aws_s3_bucket.bootstrap.arn
        ]
      },
      {
        Sid    = "ReadNixOSImages"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ]
        Resource = "${aws_s3_bucket.nixos_images.arn}/*"
      },
      {
        Sid    = "ReadWriteBootstrap"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.bootstrap.arn}/*"
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-s3-policy"
  }
}

resource "aws_iam_role_policy_attachment" "life_os_s3" {
  role       = aws_iam_role.life_os.name
  policy_arn = aws_iam_policy.s3_access.arn
}

# EFS Access Policy
resource "aws_iam_policy" "efs_access" {
  count = var.enable_efs ? 1 : 0

  name        = "${local.name_prefix}-efs-access"
  description = "Policy for EFS access from Life OS instance"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EFSAccess"
        Effect = "Allow"
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:ClientRootAccess",
          "elasticfilesystem:DescribeMountTargets",
          "elasticfilesystem:DescribeFileSystems"
        ]
        Resource = aws_efs_file_system.life_os[0].arn
      },
      {
        Sid    = "EFSAccessPoints"
        Effect = "Allow"
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite"
        ]
        Resource = [
          aws_efs_access_point.app_data[0].arn,
          aws_efs_access_point.shared_memory[0].arn,
          aws_efs_access_point.logs[0].arn
        ]
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-efs-policy"
  }
}

resource "aws_iam_role_policy_attachment" "life_os_efs" {
  count = var.enable_efs ? 1 : 0

  role       = aws_iam_role.life_os.name
  policy_arn = aws_iam_policy.efs_access[0].arn
}

# SSM Access Policy (for Session Manager and Parameter Store)
resource "aws_iam_policy" "ssm_access" {
  name        = "${local.name_prefix}-ssm-access"
  description = "Policy for SSM access from Life OS instance"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SSMCore"
        Effect = "Allow"
        Action = [
          "ssm:UpdateInstanceInformation",
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel"
        ]
        Resource = "*"
      },
      {
        Sid    = "SSMParameters"
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${local.name_prefix}/*"
      },
      {
        Sid    = "EC2Messages"
        Effect = "Allow"
        Action = [
          "ec2messages:AcknowledgeMessage",
          "ec2messages:DeleteMessage",
          "ec2messages:FailMessage",
          "ec2messages:GetEndpoint",
          "ec2messages:GetMessages",
          "ec2messages:SendReply"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-ssm-policy"
  }
}

resource "aws_iam_role_policy_attachment" "life_os_ssm" {
  role       = aws_iam_role.life_os.name
  policy_arn = aws_iam_policy.ssm_access.arn
}

# CloudWatch Logs Policy
resource "aws_iam_policy" "cloudwatch_logs" {
  name        = "${local.name_prefix}-cloudwatch-logs"
  description = "Policy for CloudWatch Logs from Life OS instance"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/life-os/*"
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-cloudwatch-policy"
  }
}

resource "aws_iam_role_policy_attachment" "life_os_cloudwatch" {
  role       = aws_iam_role.life_os.name
  policy_arn = aws_iam_policy.cloudwatch_logs.arn
}

# VM Import Role for AMI Creation
resource "aws_iam_role" "vmimport" {
  name = "${local.name_prefix}-vmimport"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "vmie.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "sts:ExternalId" = "vmimport"
          }
        }
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-vmimport-role"
  }
}

# VM Import Policy
resource "aws_iam_policy" "vmimport" {
  name        = "${local.name_prefix}-vmimport-policy"
  description = "Policy for VM Import/Export service"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3Access"
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:GetObject",
          "s3:ListBucket",
          "s3:PutObject",
          "s3:GetBucketAcl"
        ]
        Resource = [
          aws_s3_bucket.nixos_images.arn,
          "${aws_s3_bucket.nixos_images.arn}/*"
        ]
      },
      {
        Sid    = "EC2Access"
        Effect = "Allow"
        Action = [
          "ec2:ModifySnapshotAttribute",
          "ec2:CopySnapshot",
          "ec2:RegisterImage",
          "ec2:Describe*"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-vmimport-policy"
  }
}

resource "aws_iam_role_policy_attachment" "vmimport" {
  role       = aws_iam_role.vmimport.name
  policy_arn = aws_iam_policy.vmimport.arn
}

# KMS Key for encryption (optional, for enhanced security)
resource "aws_kms_key" "life_os" {
  count = var.environment == "prod" ? 1 : 0

  description             = "KMS key for Life OS encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableRootAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowEC2Role"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.life_os.arn
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-kms-key"
  }
}

resource "aws_kms_alias" "life_os" {
  count = var.environment == "prod" ? 1 : 0

  name          = "alias/${local.name_prefix}"
  target_key_id = aws_kms_key.life_os[0].key_id
}
