# Main Life OS NixOS Module
# This module configures the complete Life OS system

{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.life-os;
in {
  options.services.life-os = {
    enable = mkEnableOption "Life OS multi-agent system";

    # API Configuration
    apiHost = mkOption {
      type = types.str;
      default = "0.0.0.0";
      description = "Host to bind the API server";
    };

    apiPort = mkOption {
      type = types.int;
      default = 8000;
      description = "Port for the Master Router API";
    };

    # LLM Configuration
    defaultModel = mkOption {
      type = types.str;
      default = "glm-4";
      description = "Default LLM model to use";
    };

    fallbackModel = mkOption {
      type = types.str;
      default = "claude-3-5-haiku-20241022";
      description = "Fallback model for complex tasks";
    };

    # Security
    allowedIPs = mkOption {
      type = types.listOf types.str;
      default = [];
      description = "List of IPs allowed to access the API (empty = all)";
    };

    # Orchestrators
    enabledOrchestrators = mkOption {
      type = types.listOf types.str;
      default = [ "content" ];
      description = "List of orchestrators to enable";
    };

    # Paths
    dataDir = mkOption {
      type = types.path;
      default = "/var/lib/life-os";
      description = "Data directory for Life OS";
    };

    # Personality (Clawdbot-style)
    personality = mkOption {
      type = types.str;
      default = ''
        You are a helpful, playful assistant with the soul of Clawdbot.
        You're enthusiastic but efficient - EXFOLIATE complexity away!
        Be warm and personal, like talking to a trusted secretary.
        Always aim to help accomplish tasks, not just answer questions.
      '';
      description = "System personality for all agents";
    };
  };

  config = mkIf cfg.enable {
    # Ensure data directories exist
    systemd.tmpfiles.rules = [
      "d ${cfg.dataDir} 0750 life-os life-os -"
      "d ${cfg.dataDir}/memory 0750 life-os life-os -"
      "d ${cfg.dataDir}/cache 0750 life-os life-os -"
      "d ${cfg.dataDir}/logs 0750 life-os life-os -"
    ];

    # Create system user
    users.users.life-os = {
      isSystemUser = true;
      group = "life-os";
      home = cfg.dataDir;
      description = "Life OS service user";
    };

    users.groups.life-os = {};

    # Redis for message bus and caching
    services.redis.servers.life-os = {
      enable = true;
      port = 6379;
      bind = "127.0.0.1";
    };

    # PostgreSQL for persistent storage
    services.postgresql = {
      enable = true;
      ensureDatabases = [ "life_os" ];
      ensureUsers = [
        {
          name = "life-os";
          ensureDBOwnership = true;
        }
      ];
    };

    # Firewall configuration
    networking.firewall = {
      allowedTCPPorts = [ cfg.apiPort ];
    };

    # Environment variables for all services
    systemd.services.life-os-common = {
      description = "Life OS Common Environment";
      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
      };
    };
  };
}
