{ pkgs ? import <nixpkgs> {}, ... }:
pkgs.virt-viewer.overrideAttrs(x: {
  patches = [
    ./patches/0001-Remove-menu-bar.patch
    ./patches/0002-Do-not-grab-keyboard-mouse.patch
    ./patches/0003-Use-name-of-appvm-applications-as-a-title.patch
    ./patches/0004-Use-title-application-name-as-subtitle.patch
  ] ++ pkgs.virt-viewer.patches;
})
