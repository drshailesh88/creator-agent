# Master Router NixOS Module
# Routes requests to appropriate orchestrators

{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.life-os.master-router;
  lifeCfg = config.services.life-os;
in {
  options.services.life-os.master-router = {
    enable = mkEnableOption "Life OS Master Router";

    port = mkOption {
      type = types.int;
      default = 8000;
      description = "Port for Master Router";
    };

    domains = mkOption {
      type = types.attrsOf (types.submodule {
        options = {
          endpoint = mkOption {
            type = types.str;
            description = "Internal endpoint for this domain";
          };
          keywords = mkOption {
            type = types.listOf types.str;
            description = "Keywords that trigger routing to this domain";
          };
          description = mkOption {
            type = types.str;
            default = "";
            description = "Description of what this domain handles";
          };
        };
      });
      default = {
        content = {
          endpoint = "http://localhost:8001";
          keywords = [ "write" "blog" "twitter" "content" "article" "research" "paper" ];
          description = "Content creation and research";
        };
        business = {
          endpoint = "http://localhost:8002";
          keywords = [ "hr" "finance" "loan" "invoice" "employee" "payroll" "budget" ];
          description = "Business operations management";
        };
        personal = {
          endpoint = "http://localhost:8003";
          keywords = [ "health" "family" "schedule" "reminder" "fitness" "learning" ];
          description = "Personal life management";
        };
      };
      description = "Domain routing configuration";
    };
  };

  config = mkIf cfg.enable {
    systemd.services.life-os-router = {
      description = "Life OS Master Router";
      wantedBy = [ "multi-user.target" ];
      after = [ "network.target" "redis-life-os.service" ];
      requires = [ "redis-life-os.service" ];

      environment = {
        ROUTER_PORT = toString cfg.port;
        ROUTER_HOST = lifeCfg.apiHost;
        DEFAULT_MODEL = lifeCfg.defaultModel;
        FALLBACK_MODEL = lifeCfg.fallbackModel;
        PERSONALITY = lifeCfg.personality;
        DATA_DIR = lifeCfg.dataDir;
        REDIS_URL = "redis://localhost:6379";
      };

      serviceConfig = {
        Type = "simple";
        User = "life-os";
        Group = "life-os";
        WorkingDirectory = lifeCfg.dataDir;
        ExecStart = "${pkgs.python311}/bin/python -m uvicorn master_router.main:app --host $ROUTER_HOST --port $ROUTER_PORT";
        Restart = "always";
        RestartSec = 5;

        # Security hardening
        NoNewPrivileges = true;
        ProtectSystem = "strict";
        ProtectHome = true;
        PrivateTmp = true;
        ReadWritePaths = [ lifeCfg.dataDir ];

        # Secrets from agenix
        LoadCredential = [
          "glm-api-key:/run/agenix/glm-api-key"
          "claude-api-key:/run/agenix/claude-api-key"
          "api-secret:/run/agenix/life-os-api-secret"
        ];
      };
    };
  };
}
