{ pkgs ? import <nixpkgs> {} }:
with pkgs;
mkShell {
  packages = [
    python39Packages.libvirt
    ((import ./virt-viewer-without-menu/default.nix) pkgs)
  ];
}
