{
  description = "secure app launcher, inspired by QubesOS and appvm";
  nixConfig.bash-prompt = "\[vixos\]$ ";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem
      (system:
        let pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          devShell = pkgs.mkShell {
            packages = with pkgs; [
              python39Packages.libvirt
              python39Packages.pycryptodome
              python39Packages.libvirt
              ((import ./virt-viewer-without-menu) pkgs)
            ];
          };
        }
      );
}
