{
  description = "secure app launcher, inspired by QubesOS and appvm";
  nixConfig.bash-prompt = "\[vixos\]$ ";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
  };

  outputs = { self, nixpkgs, flake-utils }:
    let
      notDarwin = s: !(nixpkgs.lib.strings.hasInfix "darwin" s);
      systems = nixpkgs.lib.filter notDarwin flake-utils.lib.defaultSystems;
    in
    flake-utils.lib.eachSystem systems
      (system:
        let
	  pkgs = nixpkgs.legacyPackages.${system};
	  pname = "vixos";
        in
        {
          packages.${pname} = pkgs.python311.pkgs.buildPythonApplication rec {
	    inherit pname;
            version = "0.0.0";
            src = ./.;

            propagatedBuildInputs = with pkgs; [
              python311Packages.libvirt
              python311Packages.pycryptodome
              python311Packages.paramiko
              python311Packages.click
              waypipe
            ];
          };
          packages.default = self.packages.${system}.${pname};
          devShell = pkgs.mkShell {
            packages = with pkgs; [
              python311Packages.libvirt
              python311Packages.pycryptodome
              python311Packages.paramiko
              python311Packages.click
              waypipe
              ((import ./virt-viewer-without-menu) pkgs)
            ];
          };
        }
      );
}
