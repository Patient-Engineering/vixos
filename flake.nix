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
        let pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          devShell = pkgs.mkShell {
            packages = with pkgs; [
              python39Packages.libvirt
              python39Packages.pycryptodome
              python39Packages.paramiko
              waypipe
              ((import ./virt-viewer-without-menu) pkgs)
            ];
          };
        }
      );
}
