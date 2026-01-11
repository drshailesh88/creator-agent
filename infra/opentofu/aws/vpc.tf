# Life OS - VPC and Network Configuration
# Network infrastructure for Life OS deployment

# VPC
resource "aws_vpc" "life_os" {
  cidr_block           = local.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = local.vpc_name
  }
}

# Internet Gateway
resource "aws_internet_gateway" "life_os" {
  vpc_id = aws_vpc.life_os.id

  tags = {
    Name = "${local.name_prefix}-igw"
  }
}

# Public Subnet
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.life_os.id
  cidr_block              = local.public_subnet_cidr
  availability_zone       = local.availability_zone
  map_public_ip_on_launch = true

  tags = {
    Name = "${local.name_prefix}-public-subnet"
    Type = "Public"
  }
}

# Route Table for Public Subnet
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.life_os.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.life_os.id
  }

  tags = {
    Name = "${local.name_prefix}-public-rt"
  }
}

# Route Table Association
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Security Group for Life OS Instance
resource "aws_security_group" "life_os" {
  name        = "${local.name_prefix}-sg"
  description = "Security group for Life OS instance"
  vpc_id      = aws_vpc.life_os.id

  # HTTPS access from allowed IPs
  dynamic "ingress" {
    for_each = length(local.allowed_https_cidrs) > 0 ? [1] : []
    content {
      description = "HTTPS from allowed IPs"
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = local.allowed_https_cidrs
    }
  }

  # HTTP access from allowed IPs (for redirect to HTTPS)
  dynamic "ingress" {
    for_each = length(local.allowed_https_cidrs) > 0 ? [1] : []
    content {
      description = "HTTP from allowed IPs (redirect)"
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = local.allowed_https_cidrs
    }
  }

  # SSH access from allowed IPs
  dynamic "ingress" {
    for_each = length(local.allowed_ssh_cidrs) > 0 ? [1] : []
    content {
      description = "SSH from allowed IPs"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = local.allowed_ssh_cidrs
    }
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
    Name = "${local.name_prefix}-sg"
  }

  lifecycle {
    create_before_destroy = true
  }
}

# VPC Flow Logs (optional but recommended for security)
resource "aws_flow_log" "life_os" {
  count = var.environment == "prod" ? 1 : 0

  vpc_id                   = aws_vpc.life_os.id
  traffic_type             = "ALL"
  log_destination_type     = "cloud-watch-logs"
  log_destination          = aws_cloudwatch_log_group.vpc_flow_logs[0].arn
  iam_role_arn             = aws_iam_role.vpc_flow_logs[0].arn
  max_aggregation_interval = 60

  tags = {
    Name = "${local.name_prefix}-flow-logs"
  }
}

# CloudWatch Log Group for VPC Flow Logs
resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  count = var.environment == "prod" ? 1 : 0

  name              = "/aws/vpc/${local.name_prefix}-flow-logs"
  retention_in_days = 30

  tags = {
    Name = "${local.name_prefix}-flow-logs"
  }
}

# IAM Role for VPC Flow Logs
resource "aws_iam_role" "vpc_flow_logs" {
  count = var.environment == "prod" ? 1 : 0

  name = "${local.name_prefix}-vpc-flow-logs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-vpc-flow-logs-role"
  }
}

# IAM Policy for VPC Flow Logs
resource "aws_iam_role_policy" "vpc_flow_logs" {
  count = var.environment == "prod" ? 1 : 0

  name = "${local.name_prefix}-vpc-flow-logs-policy"
  role = aws_iam_role.vpc_flow_logs[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# Network ACL for additional security layer
resource "aws_network_acl" "public" {
  vpc_id     = aws_vpc.life_os.id
  subnet_ids = [aws_subnet.public.id]

  # Allow inbound HTTPS
  ingress {
    protocol   = "tcp"
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 443
    to_port    = 443
  }

  # Allow inbound HTTP
  ingress {
    protocol   = "tcp"
    rule_no    = 110
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 80
    to_port    = 80
  }

  # Allow inbound SSH
  ingress {
    protocol   = "tcp"
    rule_no    = 120
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 22
    to_port    = 22
  }

  # Allow inbound ephemeral ports (for return traffic)
  ingress {
    protocol   = "tcp"
    rule_no    = 200
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 1024
    to_port    = 65535
  }

  # Allow all outbound traffic
  egress {
    protocol   = "-1"
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }

  tags = {
    Name = "${local.name_prefix}-public-nacl"
  }
}
