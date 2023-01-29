# VixOS

VixOS is a secure app launcher, inspired by QubesOS and jollheef/appvm.

VixOS is in an early development stage, and should not be used in production (obviously).

## Goals and non-goals

The goal of the project is to create a practical virtualisation tool. I want to move most of my workloads into VMs, but I want this to be mostly seamless (no manual VM management). Nixos sounds like a perfect tool for that job.

## Usage

Top-level:

```
$ python3 -m vixos.main --help
usage: main.py [-h] {run} ...

VixOS is a secure application launcher.

optional arguments:
  -h, --help  show this help message and exit

subcommands:
  {run}
    run       Run a nixpkgs program
```

Run:

```
$ python3 -m vixos.main run --help
usage: main.py run [-h] [--gui] [--background] package

positional arguments:
  package           Name of the nixpkgs package to run.

optional arguments:
  -h, --help        show this help message and exit
  --gui, -g         If specified, add graphical devices to the VM.
  --background, -b  If specified, run in the background (and don't kill the VM on exit).
```

Example:

```
$ python3 -m vixos.main run firefox --gui
OK, running firefox...
```

## Dev plan

* [x] P0: GUI wayland + sway (host)
* [x] P1: file share - (/nix/store)
* [x] P1: net sharing - host ethernet
* [ ] P1: RO VMs, mountable folders RO/RW
* [ ] P2: clipboard sharing, additional command
* [ ] P2: networking later NAT/bridge / without
* [ ] P2: NixOS flake
* [ ] P2: Add/passthrough USB devices (especially yubikey) (P2 because this is a blocker for me)
* [ ] P3: Integrate with https://github.com/talex5/wayland-proxy-virtwl
* [ ] P3: randomized shared folders per run
* [ ] P4: add stuff to VM at runtime (like nix-shell -p)
* [ ] P4: workspaces?
* [ ] P4: "docker cp"
* [ ] P5: nixos hardening
