# Base Orchestrator NixOS Module
# Shared configuration for all orchestrators

{ config, lib, pkgs, ... }:

with lib;

let
  lifeCfg = config.services.life-os;

  # Helper to create orchestrator service
  mkOrchestratorService = name: cfg: {
    description = "Life OS ${name} Orchestrator";
    wantedBy = [ "multi-user.target" ];
    after = [ "network.target" "life-os-router.service" "redis-life-os.service" ];
    requires = [ "redis-life-os.service" ];

    environment = {
      ORCHESTRATOR_NAME = name;
      ORCHESTRATOR_PORT = toString cfg.port;
      DEFAULT_MODEL = lifeCfg.defaultModel;
      FALLBACK_MODEL = lifeCfg.fallbackModel;
      PERSONALITY = lifeCfg.personality;
      DATA_DIR = "${lifeCfg.dataDir}/${name}";
      REDIS_URL = "redis://localhost:6379";
    };

    serviceConfig = {
      Type = "simple";
      User = "life-os";
      Group = "life-os";
      WorkingDirectory = "${lifeCfg.dataDir}/${name}";
      ExecStart = "${pkgs.python311}/bin/python -m uvicorn orchestrators.${name}.main:app --host 127.0.0.1 --port ${toString cfg.port}";
      Restart = "always";
      RestartSec = 5;

      # Security hardening
      NoNewPrivileges = true;
      ProtectSystem = "strict";
      ProtectHome = true;
      PrivateTmp = true;
      ReadWritePaths = [ "${lifeCfg.dataDir}/${name}" ];

      # Secrets
      LoadCredential = [
        "glm-api-key:/run/agenix/glm-api-key"
        "claude-api-key:/run/agenix/claude-api-key"
      ];
    };
  };

in {
  options.services.life-os.orchestrators = mkOption {
    type = types.attrsOf (types.submodule ({ name, ... }: {
      options = {
        enable = mkEnableOption "Enable ${name} orchestrator";

        port = mkOption {
          type = types.int;
          description = "Port for this orchestrator";
        };

        agents = mkOption {
          type = types.listOf types.str;
          default = [];
          description = "List of agents to enable";
        };

        extraSecrets = mkOption {
          type = types.listOf types.str;
          default = [];
          description = "Additional secrets to load";
        };

        extraEnv = mkOption {
          type = types.attrsOf types.str;
          default = {};
          description = "Additional environment variables";
        };
      };
    }));
    default = {};
    description = "Orchestrator configurations";
  };

  config = {
    # Create directories for each orchestrator
    systemd.tmpfiles.rules = mapAttrsToList
      (name: cfg: "d ${lifeCfg.dataDir}/${name} 0750 life-os life-os -")
      (filterAttrs (n: v: v.enable) config.services.life-os.orchestrators);

    # Create systemd services for each enabled orchestrator
    systemd.services = mapAttrs'
      (name: cfg: nameValuePair "life-os-${name}" (mkOrchestratorService name cfg))
      (filterAttrs (n: v: v.enable) config.services.life-os.orchestrators);
  };
}
