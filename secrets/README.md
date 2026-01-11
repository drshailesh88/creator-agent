# Life OS Secrets Management with Agenix

This directory contains encrypted secrets for the Life OS multi-agent system using [agenix](https://github.com/ryantm/agenix).

## Overview

Agenix uses age encryption with SSH keys to manage secrets. Secrets are encrypted with public keys and can only be decrypted by the corresponding private keys present on authorized hosts.

## Directory Structure

```
secrets/
├── secrets.nix          # Defines secrets and their authorized keys
├── README.md            # This file
├── .gitignore           # Ensures only encrypted files are tracked
├── glm-api-key.age      # Encrypted GLM API key
├── claude-api-key.age   # Encrypted Claude API key
├── pubmed-api-key.age   # Encrypted PubMed API key
├── serper-api-key.age   # Encrypted Serper API key
├── life-os-api-secret.age    # Encrypted API JWT secret
├── business-db-key.age       # Encrypted business database key
└── personal-encryption-key.age  # Encrypted personal data key
```

## Initial Setup

### 1. Generate SSH Keys

First, generate an SSH key pair for administering secrets:

```bash
# Generate admin key (do this on your local machine)
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_life_os -C "life-os-admin"

# View your public key
cat ~/.ssh/id_ed25519_life_os.pub
```

### 2. Get Host Keys

For each NixOS host that needs to decrypt secrets, get its SSH host key:

```bash
# Option A: From local machine (if host is accessible)
ssh-keyscan -t ed25519 <hostname-or-ip>

# Option B: On the host itself
cat /etc/ssh/ssh_host_ed25519_key.pub
```

### 3. Configure secrets.nix

Edit `secrets.nix` and replace the placeholder keys:

```nix
let
  # Your admin public key
  admin-user = "ssh-ed25519 AAAA... your-key-here";

  # Your server's host key
  life-os-primary = "ssh-ed25519 AAAA... host-key-here";
in {
  # ...
}
```

## Encrypting Secrets

### Using agenix CLI

```bash
# Enter the nix development shell (includes agenix)
nix develop

# Encrypt a secret (will open $EDITOR)
agenix -e glm-api-key.age

# Or pipe directly (useful for scripts)
echo "sk-your-api-key-here" | agenix -e glm-api-key.age

# Re-encrypt after adding new keys to secrets.nix
agenix -r
```

### Generating Random Secrets

For secrets that need to be randomly generated:

```bash
# Generate a 32-byte base64 secret
openssl rand -base64 32 | agenix -e life-os-api-secret.age

# Generate a hex secret
openssl rand -hex 32 | agenix -e business-db-key.age
```

## Adding New Secrets

1. **Define the secret in `secrets.nix`:**

```nix
{
  # ... existing secrets ...

  # New secret
  "my-new-secret.age".publicKeys = allKeys;
}
```

2. **Create the encrypted file:**

```bash
agenix -e my-new-secret.age
```

3. **Reference it in your NixOS configuration:**

```nix
# In your host configuration or module
age.secrets.my-new-secret = {
  file = ../secrets/my-new-secret.age;
  owner = "service-user";
  group = "service-group";
  mode = "0400";
};

# The decrypted secret will be at /run/agenix/my-new-secret
```

## Accessing Secrets in Services

Secrets are decrypted at boot and placed in `/run/agenix/`. Reference them in systemd services:

```nix
systemd.services.my-service = {
  serviceConfig = {
    # Method 1: Load as credential (recommended)
    LoadCredential = [ "api-key:/run/agenix/glm-api-key" ];

    # Method 2: Environment file
    EnvironmentFile = "/run/agenix/my-env-file";
  };

  # Method 3: Pass as environment variable (less secure)
  script = ''
    export API_KEY=$(cat /run/agenix/glm-api-key)
    exec my-service
  '';
};
```

## Re-encrypting Secrets

When you add new hosts or admins to `secrets.nix`, re-encrypt all secrets:

```bash
# Re-encrypt all secrets with updated keys
agenix -r

# This reads each .age file, decrypts it with your key,
# and re-encrypts it with all authorized keys
```

## Rotating Secrets

To rotate a secret:

```bash
# Generate new value and re-encrypt
openssl rand -base64 32 | agenix -e life-os-api-secret.age

# Rebuild and deploy
nixos-rebuild switch
```

## Security Best Practices

1. **Never commit unencrypted secrets** - The `.gitignore` helps prevent this
2. **Use separate keys for different environments** - Don't share keys between prod/dev
3. **Rotate secrets regularly** - Especially API keys
4. **Use minimal permissions** - Only give hosts the secrets they need
5. **Backup your admin private key securely** - You need it to manage secrets
6. **Review authorized keys regularly** - Remove old hosts/admins

## Troubleshooting

### "No matching host key found"

Your host's SSH key doesn't match what's in `secrets.nix`. Update the key and run `agenix -r`.

### "Permission denied"

- Check that your private key is at `~/.ssh/id_ed25519` or specify with `-i`
- Ensure your public key is in `secrets.nix`

### Secrets not decrypting on host

1. Verify the host key in `secrets.nix` matches `/etc/ssh/ssh_host_ed25519_key.pub`
2. Run `agenix -r` to re-encrypt with the correct key
3. Rebuild with `nixos-rebuild switch`

### Viewing encrypted secret info

```bash
# See which keys can decrypt a secret
age-keygen -y ~/.ssh/id_ed25519

# Check age file recipients
age --decrypt -i ~/.ssh/id_ed25519 secret.age
```

## Required Secrets for Life OS

| Secret | Purpose | How to Get |
|--------|---------|------------|
| `glm-api-key` | Zhipu GLM-4 API | https://open.bigmodel.cn/ |
| `claude-api-key` | Anthropic Claude API | https://console.anthropic.com/ |
| `pubmed-api-key` | NCBI PubMed API | https://www.ncbi.nlm.nih.gov/account/ |
| `serper-api-key` | Serper web search | https://serper.dev/ |
| `life-os-api-secret` | JWT signing key | `openssl rand -base64 32` |
| `business-db-key` | Business data encryption | `openssl rand -base64 32` |
| `personal-encryption-key` | Personal data encryption | `openssl rand -base64 32` |
