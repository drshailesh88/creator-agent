#!/usr/bin/env bash
# Life OS - EC2 Bootstrap Script
# This script runs on first boot to configure the instance

set -euo pipefail

# Configuration from Terraform
ENVIRONMENT="${environment}"
EFS_ID="${efs_id}"
S3_BOOTSTRAP_BUCKET="${s3_bootstrap_bucket}"
AWS_REGION="${aws_region}"
DOMAIN_NAME="${domain_name}"

# Logging
exec > >(tee /var/log/life-os-bootstrap.log) 2>&1
echo "=== Life OS Bootstrap Started at $(date) ==="
echo "Environment: $ENVIRONMENT"

# Wait for network to be available
echo "Waiting for network..."
for i in {1..30}; do
    if ping -c 1 8.8.8.8 &> /dev/null; then
        echo "Network is available"
        break
    fi
    sleep 2
done

# Configure AWS region
export AWS_DEFAULT_REGION="$AWS_REGION"

# Create required directories
echo "Creating directories..."
mkdir -p /var/lib/life-os
mkdir -p /var/log/life-os
mkdir -p /etc/life-os

# Format and mount data volume if present
DATA_DEVICE="/dev/xvdf"
DATA_MOUNT="/var/lib/life-os/data"

if [ -b "$DATA_DEVICE" ]; then
    echo "Configuring data volume..."

    # Check if already formatted
    if ! blkid "$DATA_DEVICE" &> /dev/null; then
        echo "Formatting data volume..."
        mkfs.ext4 -L life-os-data "$DATA_DEVICE"
    fi

    # Create mount point and mount
    mkdir -p "$DATA_MOUNT"

    # Add to fstab if not already present
    if ! grep -q "$DATA_DEVICE" /etc/fstab; then
        echo "$DATA_DEVICE $DATA_MOUNT ext4 defaults,nofail 0 2" >> /etc/fstab
    fi

    mount "$DATA_MOUNT" || true
    echo "Data volume mounted at $DATA_MOUNT"
fi

# Mount EFS if configured
if [ -n "$EFS_ID" ]; then
    echo "Configuring EFS mount..."
    EFS_MOUNT="/mnt/efs"
    mkdir -p "$EFS_MOUNT"

    # Install EFS utilities if not present (NixOS specific)
    # Note: On NixOS, this should be configured in the NixOS configuration

    # Add to fstab
    if ! grep -q "$EFS_ID" /etc/fstab; then
        echo "$EFS_ID:/ $EFS_MOUNT efs _netdev,tls,iam 0 0" >> /etc/fstab
    fi

    # Attempt mount (may fail if EFS utils not installed yet)
    mount "$EFS_MOUNT" 2>/dev/null || echo "EFS mount deferred to system configuration"

    # Create subdirectories
    mkdir -p "$EFS_MOUNT/app-data" 2>/dev/null || true
    mkdir -p "$EFS_MOUNT/shared-memory" 2>/dev/null || true
    mkdir -p "$EFS_MOUNT/logs" 2>/dev/null || true
fi

# Download bootstrap configuration from S3
echo "Downloading bootstrap configuration..."
if command -v aws &> /dev/null; then
    aws s3 cp "s3://$S3_BOOTSTRAP_BUCKET/config/bootstrap.json" /etc/life-os/bootstrap.json || true
else
    echo "AWS CLI not available, skipping S3 download"
fi

# Configure hostname
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id || echo "unknown")
hostnamectl set-hostname "life-os-$ENVIRONMENT-$INSTANCE_ID" || true

# Write environment configuration
cat > /etc/life-os/environment << EOF
LIFE_OS_ENVIRONMENT=$ENVIRONMENT
LIFE_OS_INSTANCE_ID=$INSTANCE_ID
LIFE_OS_REGION=$AWS_REGION
LIFE_OS_DOMAIN=$DOMAIN_NAME
LIFE_OS_DATA_DIR=$DATA_MOUNT
LIFE_OS_EFS_DIR=/mnt/efs
EOF

# Set permissions
chown -R root:root /etc/life-os
chmod 600 /etc/life-os/environment

# Configure firewall (if iptables available)
if command -v iptables &> /dev/null; then
    echo "Configuring firewall rules..."

    # Allow loopback
    iptables -A INPUT -i lo -j ACCEPT

    # Allow established connections
    iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

    # Allow SSH
    iptables -A INPUT -p tcp --dport 22 -j ACCEPT

    # Allow HTTP/HTTPS
    iptables -A INPUT -p tcp --dport 80 -j ACCEPT
    iptables -A INPUT -p tcp --dport 443 -j ACCEPT

    # Allow NFS for EFS
    iptables -A INPUT -p tcp --dport 2049 -j ACCEPT

    # Drop everything else (commented out for safety during bootstrap)
    # iptables -A INPUT -j DROP
fi

# Signal completion
echo "=== Life OS Bootstrap Completed at $(date) ==="

# Write completion marker
touch /var/lib/life-os/.bootstrap-complete
echo "$ENVIRONMENT" > /var/lib/life-os/.environment

# Optional: Trigger NixOS rebuild if configuration changed
# nixos-rebuild switch || true

exit 0
