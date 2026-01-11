# Business Orchestrator NixOS Module
# Handles business operations: HR, Finance, Loans, Legal

{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.life-os.orchestrators.business;
  lifeCfg = config.services.life-os;
in {
  options.services.life-os.orchestrators.business = {
    enable = mkEnableOption "Business Orchestrator";

    port = mkOption {
      type = types.int;
      default = 8002;
      description = "Port for Business Orchestrator";
    };

    agents = mkOption {
      type = types.listOf types.str;
      default = [ "hr" "finance" "loans" "legal" ];
      description = "Enabled business agents";
    };

    # HR Agent configuration
    hr = {
      enable = mkOption {
        type = types.bool;
        default = true;
        description = "Enable HR agent";
      };

      features = mkOption {
        type = types.listOf types.str;
        default = [ "recruitment" "onboarding" "performance" "scheduling" ];
        description = "Enabled HR features";
      };
    };

    # Finance Agent configuration
    finance = {
      enable = mkOption {
        type = types.bool;
        default = true;
        description = "Enable Finance agent";
      };

      features = mkOption {
        type = types.listOf types.str;
        default = [ "invoicing" "expenses" "budgeting" "reporting" ];
        description = "Enabled finance features";
      };
    };

    # Loans Agent configuration
    loans = {
      enable = mkOption {
        type = types.bool;
        default = true;
        description = "Enable Loans tracking agent";
      };
    };

    # Legal Agent configuration
    legal = {
      enable = mkOption {
        type = types.bool;
        default = true;
        description = "Enable Legal agent";
      };

      features = mkOption {
        type = types.listOf types.str;
        default = [ "contracts" "compliance" "documents" ];
        description = "Enabled legal features";
      };
    };

    # Security level (business data is sensitive)
    securityLevel = mkOption {
      type = types.enum [ "standard" "high" "maximum" ];
      default = "high";
      description = "Security level for business data";
    };
  };

  config = mkIf cfg.enable {
    services.life-os.orchestrators.business = {
      enable = true;
      port = cfg.port;
      agents = cfg.agents;
      extraSecrets = [
        "business-db-key:/run/agenix/business-db-key"
      ];
      extraEnv = {
        HR_ENABLED = boolToString cfg.hr.enable;
        HR_FEATURES = concatStringsSep "," cfg.hr.features;
        FINANCE_ENABLED = boolToString cfg.finance.enable;
        FINANCE_FEATURES = concatStringsSep "," cfg.finance.features;
        LOANS_ENABLED = boolToString cfg.loans.enable;
        LEGAL_ENABLED = boolToString cfg.legal.enable;
        LEGAL_FEATURES = concatStringsSep "," cfg.legal.features;
        SECURITY_LEVEL = cfg.securityLevel;
      };
    };

    # Business-specific directories with tighter permissions
    systemd.tmpfiles.rules = [
      "d ${lifeCfg.dataDir}/business 0700 life-os life-os -"
      "d ${lifeCfg.dataDir}/business/hr 0700 life-os life-os -"
      "d ${lifeCfg.dataDir}/business/finance 0700 life-os life-os -"
      "d ${lifeCfg.dataDir}/business/loans 0700 life-os life-os -"
      "d ${lifeCfg.dataDir}/business/legal 0700 life-os life-os -"
    ];
  };
}
