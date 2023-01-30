import re
import os
import argparse
import subprocess
import libvirt
from pathlib import Path
from .template_xml import generate_xml
from .template_nix import generate_base_nix, generate_nix, generate_local_nix
from .libvirt_utils import libvirt_connection
from typing import Tuple


class AppVM:
    def __init__(self, name: str, gui: bool) -> None:
        self.name = name
        self.is_gui = gui
        self.vixos_path = os.path.expanduser("~/vixos")
        Path(self.vixos_path).mkdir(exist_ok=True)
        self.shared_path = self.vixos_path + "/shared"
        Path(self.shared_path).mkdir(exist_ok=True)

    @property
    def vmname(self):
        return f"vixos_{self.name}"

    def xml_config(self, vm_path: str, reginfo: str, image_path: str) -> str:
        return generate_xml(
            vmname=self.vmname,
            network="libvirt",
            gui=self.is_gui,
            vm_path=vm_path,
            reginfo=reginfo,
            image_path=image_path,
            shared_dir=self.shared_path,
        )

    def make_nix_config_file(self, executable: str) -> str:
        with open(f"{self.vixos_path}/base.nix", "w") as configf:
            configf.write(generate_base_nix())

        localf = Path(self.vixos_path) / "local.nix"
        if not localf.exists():
            localf.write_text(generate_local_nix())

        configfile = f"{self.name}.nix"
        configpath = Path(f"{self.vixos_path}/{configfile}")
        if not configpath.exists():
            configpath.write_text(generate_nix(self.name, executable))
        return configfile

    def generate_vm(self, name: str) -> Tuple[str, str, str]:
        subprocess.check_call(
            [
                "nix-build",
                "<nixpkgs/nixos>",
                "-A",
                "config.system.build.vm",
                "-I",
                f"nixos-config={self.vixos_path}/{name}",
                "-I",
                self.vixos_path,
            ]
        )

        with open("result/bin/run-nixos-vm", "r") as configf:
            config = configf.read()

        reginfo = re.findall("regInfo=.*/registration", config)[0]

        realpath = os.readlink("result/system")
        os.unlink("result")

        qcow2 = f"{self.vixos_path}/{name}.fake.qcow2"
        if not Path(qcow2).exists():
            subprocess.check_call(["qemu-img", "create", "-f", "qcow2", qcow2, "40M"])

        return (realpath, reginfo, qcow2)

    def start(self, conn, executable: str) -> None:
        config_file = self.make_nix_config_file(executable)
        vm_path, reginfo, qcow2 = self.generate_vm(config_file)
        config = self.xml_config(vm_path, reginfo, qcow2)
        dom = conn.createXML(config)
        if not dom:
            raise SystemExit("Failed to create a domain from an XML definition")

        print(f"Guest {dom.name()} has booted")
        if self.is_gui:
            subprocess.check_call(["virt-viewer", "-c", conn.getURI(), self.vmname])
        else:
            subprocess.check_call(
                ["virsh", "-c", conn.getURI(), "console", self.vmname]
            )

    def destroy(self, conn):
        try:
            dom = conn.lookupByName(self.vmname)
            print(f"Destroying {dom.name()}")
            dom.destroy()
        except libvirt.libvirtError:
            print(f"Destroying failed (probably domain already destroyed).")


def run(args):
    print(f"OK, running {args.package}...")

    appvm = AppVM(args.package, args.gui)

    executable = args.executable or args.package

    with libvirt_connection("qemu:///system") as conn:
        try:
            appvm.start(conn, executable)
        finally:
            if not args.background:
                appvm.destroy(conn)


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
        "-g",
        help="If specified, add graphical devices to the VM.",
        action="store_true",
    )
    run_parser.add_argument(
        "--background",
        "-b",
        help="If specified, run in the background (and don't kill the VM on exit).",
        action="store_true",
    )
    run_parser.add_argument(
        "--executable",
        "-e",
        help="Set the executable name to run (by default uses the package name)",
    )

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
