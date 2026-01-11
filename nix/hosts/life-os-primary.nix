# Life OS Primary Host Configuration
#
# This is the main NixOS configuration for the Life OS server.
# It imports all modules and configures the complete system.
#
# Build AMI: nix build .#life-os-image
# Deploy: nixos-rebuild switch --flake .#life-os-primary

{ config, lib, pkgs, modulesPath, ... }:

{
  imports = [
    # AWS/EC2 base configuration
    "${modulesPath}/virtualisation/amazon-image.nix"

    # Life OS modules (imported via flake.nix nixosConfigurations)
    ../modules/life-os.nix
    ../modules/master-router.nix
    ../modules/orchestrator.nix
    ../modules/content.nix
    ../modules/business.nix
    ../modules/personal.nix
  ];

  # =============================================================================
  # SYSTEM BASICS
  # =============================================================================

  system.stateVersion = "24.05";

  networking = {
    hostName = "life-os-primary";
    domain = "life-os.local";

    # Enable firewall
    firewall = {
      enable = true;

      # Public ports
      allowedTCPPorts = [
        22    # SSH
        80    # HTTP (redirect to HTTPS)
        443   # HTTPS
        8000  # Master Router API (consider restricting in production)
      ];

      # Internal ports (only localhost)
      # These are handled by services binding to 127.0.0.1
      # 6379  - Redis
      # 5432  - PostgreSQL
      # 8001  - Content Orchestrator
      # 8002  - Business Orchestrator
      # 8003  - Personal Orchestrator
    };

    # Use systemd-resolved for DNS
    useNetworkd = true;
  };

  # Enable systemd-networkd for cloud environments
  systemd.network.enable = true;

  # =============================================================================
  # AWS/CLOUD-INIT CONFIGURATION
  # =============================================================================

  # EC2 instance settings
  ec2.hvm = true;

  # Cloud-init for AWS metadata
  services.cloud-init = {
    enable = true;
    network.enable = true;
  };

  # Amazon SSM Agent for management
  services.amazon-ssm-agent.enable = true;

  # =============================================================================
  # TIME AND LOCALE
  # =============================================================================

  time.timeZone = "UTC";

  i18n = {
    defaultLocale = "en_US.UTF-8";
    supportedLocales = [ "en_US.UTF-8/UTF-8" ];
  };

  # =============================================================================
  # USERS
  # =============================================================================

  # Admin user for SSH access
  users.users.admin = {
    isNormalUser = true;
    extraGroups = [ "wheel" "systemd-journal" ];
    openssh.authorizedKeys.keys = [
      # Add your SSH public key here
      # "ssh-ed25519 AAAA... your-key@your-machine"
    ];
  };

  # Allow admin to use sudo without password (for automation)
  security.sudo.wheelNeedsPassword = false;

  # =============================================================================
  # SSH CONFIGURATION
  # =============================================================================

  services.openssh = {
    enable = true;
    settings = {
      PermitRootLogin = "no";
      PasswordAuthentication = false;
      KbdInteractiveAuthentication = false;
    };
    # Generate ed25519 host key (needed for agenix)
    hostKeys = [
      {
        path = "/etc/ssh/ssh_host_ed25519_key";
        type = "ed25519";
      }
    ];
  };

  # =============================================================================
  # AGENIX SECRETS
  # =============================================================================

  age.secrets = {
    # LLM API Keys
    glm-api-key = {
      file = ../../secrets/glm-api-key.age;
      owner = "life-os";
      group = "life-os";
      mode = "0400";
    };

    claude-api-key = {
      file = ../../secrets/claude-api-key.age;
      owner = "life-os";
      group = "life-os";
      mode = "0400";
    };

    # Research API Keys
    pubmed-api-key = {
      file = ../../secrets/pubmed-api-key.age;
      owner = "life-os";
      group = "life-os";
      mode = "0400";
    };

    serper-api-key = {
      file = ../../secrets/serper-api-key.age;
      owner = "life-os";
      group = "life-os";
      mode = "0400";
    };

    # System Secrets
    life-os-api-secret = {
      file = ../../secrets/life-os-api-secret.age;
      owner = "life-os";
      group = "life-os";
      mode = "0400";
    };

    # Business Secrets
    business-db-key = {
      file = ../../secrets/business-db-key.age;
      owner = "life-os";
      group = "life-os";
      mode = "0400";
    };

    # Personal Secrets
    personal-encryption-key = {
      file = ../../secrets/personal-encryption-key.age;
      owner = "life-os";
      group = "life-os";
      mode = "0400";
    };
  };

  # Ensure agenix decrypts before services start
  age.identityPaths = [ "/etc/ssh/ssh_host_ed25519_key" ];

  # =============================================================================
  # LIFE OS SERVICES
  # =============================================================================

  services.life-os = {
    enable = true;

    # API Configuration
    apiHost = "0.0.0.0";
    apiPort = 8000;

    # LLM Configuration
    defaultModel = "glm-4";
    fallbackModel = "claude-3-5-haiku-20241022";

    # Security - restrict API access (empty = all, set IPs for production)
    allowedIPs = [];

    # Data directory
    dataDir = "/var/lib/life-os";

    # Clawdbot personality
    personality = ''
      You are a helpful, efficient Life OS assistant.
      You manage content creation, business operations, and personal organization.
      Be concise but thorough. Always aim to accomplish tasks, not just answer questions.
      When uncertain, ask clarifying questions.
    '';
  };

  # Master Router
  services.life-os.master-router = {
    enable = true;
    port = 8000;

    domains = {
      content = {
        endpoint = "http://127.0.0.1:8001";
        keywords = [ "write" "blog" "twitter" "content" "article" "research" "paper" "newsletter" ];
        description = "Content creation, research, and publishing";
      };
      business = {
        endpoint = "http://127.0.0.1:8002";
        keywords = [ "hr" "finance" "loan" "invoice" "employee" "payroll" "budget" "legal" "contract" ];
        description = "Business operations and management";
      };
      personal = {
        endpoint = "http://127.0.0.1:8003";
        keywords = [ "health" "family" "schedule" "reminder" "fitness" "learning" "habit" "goal" ];
        description = "Personal life management";
      };
    };
  };

  # Content Orchestrator
  services.life-os.orchestrators.content = {
    enable = true;
    port = 8001;
    agents = [ "researcher" "writer" "graphics" "social" ];

    research = {
      enablePubmed = true;
      enableWebSearch = true;
      enableRAG = true;
    };

    writer = {
      formats = [ "blog" "twitter" "newsletter" "academic" "linkedin" ];
      defaultTone = "professional";
    };

    graphics = {
      enableInfographics = true;
      enableCharts = true;
    };
  };

  # Business Orchestrator
  services.life-os.orchestrators.business = {
    enable = true;
    port = 8002;
    agents = [ "hr" "finance" "loans" "legal" ];

    hr = {
      enable = true;
      features = [ "recruitment" "onboarding" "performance" "scheduling" ];
    };

    finance = {
      enable = true;
      features = [ "invoicing" "expenses" "budgeting" "reporting" ];
    };

    loans.enable = true;

    legal = {
      enable = true;
      features = [ "contracts" "compliance" "documents" ];
    };

    securityLevel = "high";
  };

  # Personal Orchestrator
  services.life-os.orchestrators.personal = {
    enable = true;
    port = 8003;
    agents = [ "health" "family" "learning" "productivity" ];

    health = {
      enable = true;
      features = [ "fitness" "nutrition" "wellness" "medical" ];
      encryptData = true;
    };

    family = {
      enable = true;
      features = [ "calendar" "reminders" "events" "communication" ];
    };

    learning = {
      enable = true;
      features = [ "courses" "books" "skills" "goals" ];
    };

    productivity = {
      enable = true;
      features = [ "tasks" "habits" "focus" "reviews" ];
    };
  };

  # =============================================================================
  # NGINX REVERSE PROXY (Optional - for HTTPS)
  # =============================================================================

  services.nginx = {
    enable = true;

    recommendedGzipSettings = true;
    recommendedOptimisation = true;
    recommendedProxySettings = true;
    recommendedTlsSettings = true;

    virtualHosts = {
      # Default host - redirect to API
      "_" = {
        default = true;
        locations."/" = {
          proxyPass = "http://127.0.0.1:8000";
          proxyWebsockets = true;
        };
      };

      # Add HTTPS configuration when you have a domain
      # "api.yourdomain.com" = {
      #   forceSSL = true;
      #   enableACME = true;
      #   locations."/" = {
      #     proxyPass = "http://127.0.0.1:8000";
      #     proxyWebsockets = true;
      #   };
      # };
    };
  };

  # =============================================================================
  # SYSTEM PACKAGES
  # =============================================================================

  environment.systemPackages = with pkgs; [
    # System utilities
    vim
    git
    htop
    tmux
    curl
    wget
    jq

    # Networking
    dig
    netcat
    tcpdump

    # Python environment (for Life OS)
    (python311.withPackages (ps: with ps; [
      fastapi
      uvicorn
      httpx
      pydantic
      redis
      sqlalchemy
      asyncpg
      python-dotenv
      structlog
      tenacity
      openai
      anthropic
      langchain
      langchain-community
      chromadb
      beautifulsoup4
      requests
      aiohttp
      pillow
    ]))

    # Database tools
    postgresql
    redis
  ];

  # =============================================================================
  # MONITORING AND LOGGING
  # =============================================================================

  # Journal configuration
  services.journald = {
    extraConfig = ''
      SystemMaxUse=1G
      SystemMaxFileSize=100M
      MaxRetentionSec=1week
    '';
  };

  # Enable persistent journal
  services.journald.storage = "persistent";

  # =============================================================================
  # AUTOMATIC UPDATES (Optional)
  # =============================================================================

  # Uncomment to enable automatic security updates
  # system.autoUpgrade = {
  #   enable = true;
  #   flake = "github:your-org/life-os";
  #   flags = [ "--update-input" "nixpkgs" ];
  #   dates = "04:00";
  #   randomizedDelaySec = "45min";
  # };

  # =============================================================================
  # GARBAGE COLLECTION
  # =============================================================================

  nix = {
    settings = {
      auto-optimise-store = true;
      experimental-features = [ "nix-command" "flakes" ];
    };

    gc = {
      automatic = true;
      dates = "weekly";
      options = "--delete-older-than 30d";
    };
  };
}
