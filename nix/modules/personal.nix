# Personal Orchestrator NixOS Module
# Handles personal life: Health, Family, Learning, etc.

{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.life-os.orchestrators.personal;
  lifeCfg = config.services.life-os;
in {
  options.services.life-os.orchestrators.personal = {
    enable = mkEnableOption "Personal Life Orchestrator";

    port = mkOption {
      type = types.int;
      default = 8003;
      description = "Port for Personal Orchestrator";
    };

    agents = mkOption {
      type = types.listOf types.str;
      default = [ "health" "family" "learning" "productivity" ];
      description = "Enabled personal agents";
    };

    # Health Agent configuration
    health = {
      enable = mkOption {
        type = types.bool;
        default = true;
        description = "Enable Health agent";
      };

      features = mkOption {
        type = types.listOf types.str;
        default = [ "fitness" "nutrition" "wellness" "medical" ];
        description = "Enabled health features";
      };

      # HIPAA-like protections for health data
      encryptData = mkOption {
        type = types.bool;
        default = true;
        description = "Encrypt health data at rest";
      };
    };

    # Family Agent configuration
    family = {
      enable = mkOption {
        type = types.bool;
        default = true;
        description = "Enable Family agent";
      };

      features = mkOption {
        type = types.listOf types.str;
        default = [ "calendar" "reminders" "events" "communication" ];
        description = "Enabled family features";
      };
    };

    # Learning Agent configuration
    learning = {
      enable = mkOption {
        type = types.bool;
        default = true;
        description = "Enable Learning agent";
      };

      features = mkOption {
        type = types.listOf types.str;
        default = [ "courses" "books" "skills" "goals" ];
        description = "Enabled learning features";
      };
    };

    # Productivity Agent configuration
    productivity = {
      enable = mkOption {
        type = types.bool;
        default = true;
        description = "Enable Productivity agent";
      };

      features = mkOption {
        type = types.listOf types.str;
        default = [ "tasks" "habits" "focus" "reviews" ];
        description = "Enabled productivity features";
      };
    };
  };

  config = mkIf cfg.enable {
    services.life-os.orchestrators.personal = {
      enable = true;
      port = cfg.port;
      agents = cfg.agents;
      extraSecrets = [
        "personal-encryption-key:/run/agenix/personal-encryption-key"
      ];
      extraEnv = {
        HEALTH_ENABLED = boolToString cfg.health.enable;
        HEALTH_FEATURES = concatStringsSep "," cfg.health.features;
        HEALTH_ENCRYPT = boolToString cfg.health.encryptData;
        FAMILY_ENABLED = boolToString cfg.family.enable;
        FAMILY_FEATURES = concatStringsSep "," cfg.family.features;
        LEARNING_ENABLED = boolToString cfg.learning.enable;
        LEARNING_FEATURES = concatStringsSep "," cfg.learning.features;
        PRODUCTIVITY_ENABLED = boolToString cfg.productivity.enable;
        PRODUCTIVITY_FEATURES = concatStringsSep "," cfg.productivity.features;
      };
    };

    # Personal directories
    systemd.tmpfiles.rules = [
      "d ${lifeCfg.dataDir}/personal 0700 life-os life-os -"
      "d ${lifeCfg.dataDir}/personal/health 0700 life-os life-os -"
      "d ${lifeCfg.dataDir}/personal/family 0700 life-os life-os -"
      "d ${lifeCfg.dataDir}/personal/learning 0700 life-os life-os -"
      "d ${lifeCfg.dataDir}/personal/productivity 0700 life-os life-os -"
    ];
  };
}
