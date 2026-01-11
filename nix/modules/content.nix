# Content Orchestrator NixOS Module
# Handles content creation: research, writing, graphics

{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.life-os.orchestrators.content;
  lifeCfg = config.services.life-os;
in {
  options.services.life-os.orchestrators.content = {
    enable = mkEnableOption "Content Orchestrator";

    port = mkOption {
      type = types.int;
      default = 8001;
      description = "Port for Content Orchestrator";
    };

    agents = mkOption {
      type = types.listOf types.str;
      default = [ "researcher" "writer" "graphics" "social" ];
      description = "Enabled content agents";
    };

    # Research configuration
    research = {
      enablePubmed = mkOption {
        type = types.bool;
        default = true;
        description = "Enable PubMed research";
      };

      enableWebSearch = mkOption {
        type = types.bool;
        default = true;
        description = "Enable web search";
      };

      enableRAG = mkOption {
        type = types.bool;
        default = true;
        description = "Enable RAG from knowledge base";
      };
    };

    # Writer configuration
    writer = {
      formats = mkOption {
        type = types.listOf types.str;
        default = [ "blog" "twitter" "newsletter" "academic" "linkedin" ];
        description = "Enabled content formats";
      };

      defaultTone = mkOption {
        type = types.str;
        default = "professional";
        description = "Default writing tone";
      };
    };

    # Graphics configuration
    graphics = {
      enableInfographics = mkOption {
        type = types.bool;
        default = true;
        description = "Enable infographic generation";
      };

      enableCharts = mkOption {
        type = types.bool;
        default = true;
        description = "Enable chart generation";
      };
    };
  };

  config = mkIf cfg.enable {
    # Register with main orchestrator config
    services.life-os.orchestrators.content = {
      enable = true;
      port = cfg.port;
      agents = cfg.agents;
      extraSecrets = [
        "pubmed-api-key:/run/agenix/pubmed-api-key"
        "serper-api-key:/run/agenix/serper-api-key"
      ];
      extraEnv = {
        ENABLE_PUBMED = boolToString cfg.research.enablePubmed;
        ENABLE_WEB_SEARCH = boolToString cfg.research.enableWebSearch;
        ENABLE_RAG = boolToString cfg.research.enableRAG;
        WRITER_FORMATS = concatStringsSep "," cfg.writer.formats;
        DEFAULT_TONE = cfg.writer.defaultTone;
        ENABLE_INFOGRAPHICS = boolToString cfg.graphics.enableInfographics;
        ENABLE_CHARTS = boolToString cfg.graphics.enableCharts;
      };
    };

    # Content-specific tmpfiles
    systemd.tmpfiles.rules = [
      "d ${lifeCfg.dataDir}/content/outputs 0750 life-os life-os -"
      "d ${lifeCfg.dataDir}/content/knowledge 0750 life-os life-os -"
      "d ${lifeCfg.dataDir}/content/templates 0750 life-os life-os -"
    ];
  };
}
