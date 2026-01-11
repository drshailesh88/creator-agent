# Life OS - Multi-Agent Content & Life Management System

A scalable, secure multi-orchestrator system for managing different spheres of your life through AI agents.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        YOUR VPS                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                      CLAWDBOT                              │ │
│  │              (Your Interface Layer)                        │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  │ HTTPS
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AWS (Clawdinators)                           │
│              NixOS │ agenix │ Self-healing                      │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    LIFE OS                                 │ │
│  │                                                            │ │
│  │   Master Router → Orchestrators → Agents                  │ │
│  │                                                            │ │
│  │   • Content: Research, Writers, Graphics                  │ │
│  │   • Business: HR, Finance, Loans, Legal                   │ │
│  │   • Personal: Health, Family, Learning                    │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- [Nix](https://nixos.org/download.html) with flakes enabled
- AWS account with appropriate permissions
- [OpenTofu](https://opentofu.org/) installed
- [agenix](https://github.com/ryantm/agenix) for secrets management

### 1. Clone and Configure

```bash
git clone https://github.com/yourusername/life-os.git
cd life-os
```

### 2. Set Up Secrets

```bash
# Generate your SSH key if you don't have one
ssh-keygen -t ed25519 -C "your-email@example.com"

# Add your public key to secrets/secrets.nix
# Then encrypt your secrets:
cd secrets
agenix -e glm-api-key.age
agenix -e claude-api-key.age
# ... add all required secrets
```

### 3. Configure AWS Infrastructure

```bash
cd infra/opentofu/aws
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your settings
tofu init
tofu plan
tofu apply
```

### 4. Build and Deploy

```bash
# Build the NixOS image
nix build .#life-os-image

# Upload to S3 and import as AMI (automated via script)
./scripts/deploy.sh
```

### 5. Connect Clawdbot

Add the Life OS skill to your Clawdbot:

```bash
cp clawdbot-skill/life-os.js /path/to/clawdbot/skills/
# Add LIFE_OS_API_URL and LIFE_OS_API_KEY to Clawdbot's .env
```

## Project Structure

```
life-os/
├── flake.nix                 # Main Nix flake
├── nix/
│   ├── modules/              # NixOS modules
│   │   ├── life-os.nix       # Main module
│   │   ├── master-router.nix
│   │   └── orchestrator.nix
│   └── hosts/                # Host configurations
│       └── life-os-primary.nix
├── infra/
│   └── opentofu/aws/         # AWS infrastructure
├── secrets/                  # Encrypted secrets (agenix)
├── src/
│   ├── master-router/        # Request routing
│   ├── orchestrators/        # Domain orchestrators
│   │   ├── content/
│   │   ├── business/
│   │   └── personal/
│   └── shared/               # Shared utilities
└── clawdbot-skill/           # Clawdbot integration
```

## Adding a New Orchestrator

1. Create orchestrator directory:
   ```bash
   mkdir -p src/orchestrators/new-domain/agents
   ```

2. Create orchestrator config:
   ```yaml
   # src/orchestrators/new-domain/config.yaml
   name: "New Domain Orchestrator"
   port: 8004
   agents:
     - name: "Agent 1"
       tools: [tool1, tool2]
   ```

3. Register in Master Router:
   ```yaml
   # src/master-router/domains.yaml
   new-domain:
     endpoint: "http://localhost:8004"
     keywords: ["keyword1", "keyword2"]
   ```

4. Create NixOS module (optional, for systemd service)

5. Deploy:
   ```bash
   nixos-rebuild switch
   ```

## Security

- **Secrets**: All API keys and sensitive data encrypted with agenix
- **Network**: AWS Security Groups restrict access to your VPS IP
- **Authentication**: API key required for all requests
- **Updates**: Self-healing NixOS, automatic updates via flake

## Cost Estimate

| Resource | Monthly Cost |
|----------|-------------|
| EC2 t3.medium | ~$30 |
| EFS | ~$3 |
| S3 | ~$2 |
| Data transfer | ~$5 |
| **Total** | **~$40** |

## License

MIT
