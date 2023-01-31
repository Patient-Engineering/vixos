# VixOS

VixOS is a secure app launcher, inspired by QubesOS and jollheef/appvm.

VixOS is in an early development stage, and should not be used in production (obviously).

## Goals and non-goals

The goal of the project is to create a practical virtualisation tool. I want to move most of my workloads into VMs, but I want this to be mostly seamless (no manual VM management). Nixos sounds like a perfect tool for that job.

## Usage

Enter development shell:

```
$ nix develop
[vixos]$
```

Top-level:

```
[vixos]$ python3 -m vixos --help
usage: __main__.py [-h] {run,list,shell} ...

VixOS is a secure application launcher.

optional arguments:
  -h, --help        show this help message and exit

subcommands:
  {run,list,shell}
    run             Run a nixpkgs program
    list            List available vixos VMs
    shell           Run a shell in a running VM
```

Run:

```
usage: __main__.py run [-h] [--gui] [--background] [--executable EXECUTABLE] package
```

Example:

```
[vixos]$ python3 -m vixos run firefox --gui
OK, running firefox...
```

List:

```
[vixos]$ python3 -m vixos list
vixos_firefox
```

Shell:

```
python3 -m vixos shell firefox
```

## Dev plan

* [x] P0: GUI wayland + sway (host)
* [x] P1: File share - (/nix/store)
* [x] P1: Net sharing - host ethernet
* [ ] P1: RO VMs, mountable folders RO/RW
* [ ] P2: Clipboard sharing, additional command
* [ ] P2: Networking later NAT/bridge / without
* [ ] P2: NixOS flake
* [ ] P2: Add/passthrough USB devices (especially yubikey) (P2 because this is a blocker for me)
* [ ] P3: Integrate with https://github.com/talex5/wayland-proxy-virtwl
* [ ] P3: Randomized shared folders per run
* [ ] P3: Automatically manage VM memory (autobaloon)
* [ ] P4: Add stuff to VM at runtime (like nix-shell -p)
* [ ] P4: Workspaces?
* [ ] P4: "docker cp"
* [ ] P4: Check linux kernel is new enough (5.16+)
* [ ] P5: Nixos hardening

## Docs

Currently there is no real user-facing documentation, but developers sometimes share useful
information in [the docs](./docs) directory.

