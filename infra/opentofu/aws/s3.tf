# Life OS - S3 Storage Configuration
# S3 buckets for NixOS images and bootstrap data

# S3 Bucket for NixOS Images
resource "aws_s3_bucket" "nixos_images" {
  bucket = local.s3_images_bucket

  tags = {
    Name    = local.s3_images_bucket
    Purpose = "NixOS AMI images and system artifacts"
  }
}

resource "aws_s3_bucket_versioning" "nixos_images" {
  bucket = aws_s3_bucket.nixos_images.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "nixos_images" {
  bucket = aws_s3_bucket.nixos_images.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "nixos_images" {
  bucket = aws_s3_bucket.nixos_images.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "nixos_images" {
  bucket = aws_s3_bucket.nixos_images.id

  rule {
    id     = "cleanup-old-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  rule {
    id     = "archive-old-images"
    status = "Enabled"

    filter {
      prefix = "archived/"
    }

    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

# S3 Bucket for Bootstrap Data
resource "aws_s3_bucket" "bootstrap" {
  bucket = local.s3_bootstrap_bucket

  tags = {
    Name    = local.s3_bootstrap_bucket
    Purpose = "Bootstrap configuration and secrets"
  }
}

resource "aws_s3_bucket_versioning" "bootstrap" {
  bucket = aws_s3_bucket.bootstrap.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "bootstrap" {
  bucket = aws_s3_bucket.bootstrap.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "bootstrap" {
  bucket = aws_s3_bucket.bootstrap.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "bootstrap" {
  bucket = aws_s3_bucket.bootstrap.id

  rule {
    id     = "cleanup-old-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 7
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# Bucket Policy for NixOS Images - Allow EC2 and VM Import access
resource "aws_s3_bucket_policy" "nixos_images" {
  bucket = aws_s3_bucket.nixos_images.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEC2Access"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.life_os.arn
        }
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.nixos_images.arn,
          "${aws_s3_bucket.nixos_images.arn}/*"
        ]
      },
      {
        Sid    = "AllowVMImportAccess"
        Effect = "Allow"
        Principal = {
          Service = "vmie.amazonaws.com"
        }
        Action = [
          "s3:GetObject",
          "s3:GetBucketLocation",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.nixos_images.arn,
          "${aws_s3_bucket.nixos_images.arn}/*"
        ]
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      },
      {
        Sid    = "DenyInsecureTransport"
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.nixos_images.arn,
          "${aws_s3_bucket.nixos_images.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# Bucket Policy for Bootstrap - EC2 access only
resource "aws_s3_bucket_policy" "bootstrap" {
  bucket = aws_s3_bucket.bootstrap.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEC2Access"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.life_os.arn
        }
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.bootstrap.arn,
          "${aws_s3_bucket.bootstrap.arn}/*"
        ]
      },
      {
        Sid    = "DenyInsecureTransport"
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.bootstrap.arn,
          "${aws_s3_bucket.bootstrap.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}

# Upload initial bootstrap configuration
resource "aws_s3_object" "bootstrap_config" {
  bucket  = aws_s3_bucket.bootstrap.id
  key     = "config/bootstrap.json"
  content = jsonencode({
    version     = "1.0"
    environment = var.environment
    created_at  = timestamp()
    settings = {
      domain_name = var.domain_name
      efs_enabled = var.enable_efs
    }
  })
  content_type = "application/json"

  tags = {
    Name = "bootstrap-config"
  }

  lifecycle {
    ignore_changes = [content]
  }
}
