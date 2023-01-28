import re
import os
import argparse
import subprocess
from pathlib import Path
from .template_xml import generate_xml
from .template_nix import generate_base_nix, generate_nix
from .libvirt_utils import libvirt_connection
from typing import Tuple


class AppVM:
    def __init__(self, name: str) -> None:
        self.name = name

    def xml_config(
        self, vmname: str, vm_path: str, reginfo: str, image_path: str, shared_path: str
    ) -> str:
        return generate_xml(
            vmname=vmname,
            network="libvirt",
            gui=True,
            vm_path=vm_path,
            reginfo=reginfo,
            image_path=image_path,
            shared_dir=shared_path,
        )

    def make_nix_config_file(self, vixos_path: str) -> str:
        with open(f"{vixos_path}/base.nix", "w") as configf:
            configf.write(generate_base_nix())

        configfile = f"{self.name}.nix"
        configpath = f"{vixos_path}/{configfile}"
        with open(configpath, "w") as configf:
            configf.write(generate_nix(self.name))
        return configfile

    def generate_vm(self, vixos_path: str, name: str) -> Tuple[str, str, str]:
        subprocess.check_call(
            [
                "nix-build",
                "<nixpkgs/nixos>",
                "-A",
                "config.system.build.vm",
                "-I",
                f"nixos-config={vixos_path}/{name}",
                "-I",
                vixos_path,
            ]
        )

        with open("result/bin/run-nixos-vm", "r") as configf:
            config = configf.read()

        reginfo = re.findall("regInfo=.*/registration", config)[0]
        print("reginfo=", reginfo)

        realpath = os.readlink("result/system")
        print("realpath=", realpath)
        os.unlink("result")

        qcow2 = f"{vixos_path}/{name}.fake.qcow2"
        if not Path(qcow2).exists():
            subprocess.check_call(["qemu-img", "create", "-f", "qcow2", qcow2, "40M"])

        return (realpath, reginfo, qcow2)

    def start(self, conn) -> None:
        vixos_path = os.path.expanduser("~/vixos")
        Path(vixos_path).mkdir(exist_ok=True)

        shared_path = vixos_path + "/shared"
        Path(shared_path).mkdir(exist_ok=True)

        vmname = f"vixos_{self.name}"

        config_file = self.make_nix_config_file(vixos_path)
        vm_path, reginfo, qcow2 = self.generate_vm(vixos_path, config_file)
        config = self.xml_config(vmname, vm_path, reginfo, qcow2, shared_path)
        dom = conn.createXML(config)
        if not dom:
            raise SystemExit("Failed to create a domain from an XML definition")

        print("Guest " + dom.name() + " has booted")


def run(args):
    print(f"OK, running {args.package}...")

    appvm = AppVM(args.package)

    with libvirt_connection("qemu:///system") as conn:
        appvm.start(conn)


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
    run_parser.add_argument(
        "--gui",
        help="If specified, add graphical devices to the VM.",
        action="store_true",
    )

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
