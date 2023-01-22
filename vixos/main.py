import argparse
from .libvirt_utils import libvirt_connection


def run(args):
    print(f"OK, running {args.package}...")

    with libvirt_connection("qemu:///system") as conn:
        print(conn.getCapabilities())


def main():
    parser = argparse.ArgumentParser(
        description="VixOS is a secure application launcher."
    )

    subparsers = parser.add_subparsers(title="subcommands", required=True)
    run_parser = subparsers.add_parser("run", help="Run a nixpkgs program")
    run_parser.set_defaults(func=run)
    run_parser.add_argument(
        "package",
        help="Name of the nixpkgs package to run.",
    )

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
