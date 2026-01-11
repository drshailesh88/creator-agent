# Agenix Secrets Configuration for Life OS
#
# This file defines which secrets exist and which public keys can decrypt them.
# The actual encrypted secret files (.age) are stored alongside this file.
#
# SETUP INSTRUCTIONS:
# 1. Generate an SSH key for each host that needs to decrypt secrets:
#    ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_life_os -C "life-os-host"
#
# 2. Copy the public key from ~/.ssh/id_ed25519_life_os.pub
#
# 3. Replace the placeholder public keys below with your actual keys
#
# 4. Encrypt a secret:
#    echo "my-secret-value" | agenix -e glm-api-key.age
#
# IMPORTANT: Never commit unencrypted secrets! Only .age files should be tracked.

let
  # =============================================================================
  # PUBLIC KEYS - Replace these with your actual public keys!
  # =============================================================================

  # Host keys - These are the SSH host keys from your servers
  # Get them with: ssh-keyscan <hostname> | grep ed25519
  # Or from the server: cat /etc/ssh/ssh_host_ed25519_key.pub

  # Primary Life OS server (AWS EC2 instance)
  life-os-primary = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAEXAMPLE_REPLACE_WITH_ACTUAL_HOST_KEY";

  # Additional hosts (add more as needed)
  # life-os-secondary = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAEXAMPLE_SECONDARY_HOST_KEY";

  # User keys - These are your personal SSH keys for administering secrets
  # Get yours with: cat ~/.ssh/id_ed25519.pub

  admin-user = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAEXAMPLE_REPLACE_WITH_YOUR_KEY admin@life-os";

  # You can add multiple admin users
  # admin-user-2 = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAEXAMPLE_ANOTHER_ADMIN";

  # =============================================================================
  # KEY GROUPS - Combine keys for different access levels
  # =============================================================================

  # All systems that should be able to decrypt all secrets
  allSystems = [ life-os-primary ];

  # All admin users who can edit secrets
  allAdmins = [ admin-user ];

  # Combined: all keys that should access common secrets
  allKeys = allSystems ++ allAdmins;

  # Business-only secrets (more restricted)
  businessKeys = allSystems ++ allAdmins;

  # Personal secrets (most restricted - only primary host and admin)
  personalKeys = [ life-os-primary admin-user ];

in {
  # =============================================================================
  # LLM API KEYS
  # =============================================================================

  # GLM (Zhipu AI) API key - Primary LLM for most tasks
  # Encrypt: echo "your-glm-api-key" | agenix -e glm-api-key.age
  "glm-api-key.age".publicKeys = allKeys;

  # Claude (Anthropic) API key - Fallback for complex reasoning
  # Encrypt: echo "your-claude-api-key" | agenix -e claude-api-key.age
  "claude-api-key.age".publicKeys = allKeys;

  # =============================================================================
  # RESEARCH API KEYS
  # =============================================================================

  # PubMed API key - For medical/scientific research
  # Get one at: https://www.ncbi.nlm.nih.gov/account/
  # Encrypt: echo "your-pubmed-api-key" | agenix -e pubmed-api-key.age
  "pubmed-api-key.age".publicKeys = allKeys;

  # Serper API key - For web search
  # Get one at: https://serper.dev/
  # Encrypt: echo "your-serper-api-key" | agenix -e serper-api-key.age
  "serper-api-key.age".publicKeys = allKeys;

  # =============================================================================
  # SYSTEM SECRETS
  # =============================================================================

  # Life OS API secret - JWT signing key for API authentication
  # Generate: openssl rand -base64 32 | agenix -e life-os-api-secret.age
  "life-os-api-secret.age".publicKeys = allKeys;

  # =============================================================================
  # BUSINESS SECRETS
  # =============================================================================

  # Business database encryption key - For encrypting sensitive business data
  # Generate: openssl rand -base64 32 | agenix -e business-db-key.age
  "business-db-key.age".publicKeys = businessKeys;

  # =============================================================================
  # PERSONAL SECRETS
  # =============================================================================

  # Personal data encryption key - For health, family, and personal data
  # Generate: openssl rand -base64 32 | agenix -e personal-encryption-key.age
  "personal-encryption-key.age".publicKeys = personalKeys;
}
