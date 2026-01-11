{
  description = "Life OS - Multi-Agent Content & Life Management System";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    agenix = {
      url = "github:ryantm/agenix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    nixos-generators = {
      url = "github:nix-community/nixos-generators";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, agenix, nixos-generators, ... }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" ];

      # Python environment with all dependencies
      mkPythonEnv = pkgs: pkgs.python311.withPackages (ps: with ps; [
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
        # Agno and AI dependencies
        openai
        anthropic
        langchain
        langchain-community
        chromadb
        # Additional tools
        beautifulsoup4
        requests
        aiohttp
        pillow
      ]);

    in
    flake-utils.lib.eachSystem supportedSystems (system:
      let
        pkgs = import nixpkgs { inherit system; };
        pythonEnv = mkPythonEnv pkgs;
      in
      {
        # Development shell
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            pythonEnv
            opentofu
            awscli2
            age
            agenix.packages.${system}.default
            redis
            postgresql
          ];

          shellHook = ''
            echo "Life OS Development Environment"
            echo "================================"
            echo "Available commands:"
            echo "  tofu        - OpenTofu for AWS infrastructure"
            echo "  agenix      - Secrets management"
            echo "  python      - Python with all dependencies"
            echo ""
          '';
        };

        # Packages
        packages = {
          # Life OS application package
          life-os = pkgs.stdenv.mkDerivation {
            pname = "life-os";
            version = "0.1.0";
            src = ./src;

            buildInputs = [ pythonEnv ];

            installPhase = ''
              mkdir -p $out/lib/life-os
              cp -r . $out/lib/life-os/

              mkdir -p $out/bin
              cat > $out/bin/life-os-router << 'EOF'
              #!/bin/sh
              exec ${pythonEnv}/bin/python -m master-router.main "$@"
              EOF
              chmod +x $out/bin/life-os-router
            '';
          };

          # AWS AMI image
          life-os-image = nixos-generators.nixosGenerate {
            inherit system;
            modules = [
              ./nix/hosts/life-os-primary.nix
              agenix.nixosModules.default
            ];
            format = "amazon";
          };
        };

        # Default package
        defaultPackage = self.packages.${system}.life-os;
      }
    ) // {
      # NixOS modules
      nixosModules = {
        life-os = import ./nix/modules/life-os.nix;
        master-router = import ./nix/modules/master-router.nix;
        orchestrator = import ./nix/modules/orchestrator.nix;
        content = import ./nix/modules/content.nix;
        business = import ./nix/modules/business.nix;
        personal = import ./nix/modules/personal.nix;
      };

      # NixOS configurations
      nixosConfigurations = {
        life-os-primary = nixpkgs.lib.nixosSystem {
          system = "x86_64-linux";
          modules = [
            ./nix/hosts/life-os-primary.nix
            agenix.nixosModules.default
            self.nixosModules.life-os
          ];
        };
      };
    };
}
