import re
import os
import argparse
import subprocess
import libvirt
import time
from pathlib import Path
from .template_xml import generate_xml
from .template_nix import generate_base_nix, generate_nix, generate_local_nix
from .libvirt_utils import libvirt_connection
from typing import Tuple, Optional
from .ssh import SshManager


class AppVM:
    def __init__(self, name: str) -> None:
        self.name = name
        # TODO: use pathlib consistently in the project
        self.vixos_path = os.path.expanduser("~/vixos")
        self.shared_path = self.vixos_path + "/shared"

        # TODO: maybe move non-pure init actions to another functions?
        Path(self.vixos_path).mkdir(exist_ok=True)
        Path(self.shared_path).mkdir(exist_ok=True)
        self.ssh = SshManager(Path(self.vixos_path))

    @property
    def vm_name(self) -> str:
        return f"vixos_{self.name}"

    def try_get_ip_address(self, dom) -> Optional[str]:
        try:
            ifaces = dom.interfaceAddresses(
                libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE, 0
            )
        except:
            return None

        ipv4_addrs = []
        for val in ifaces.values():
            for ipaddr in val.get("addrs", []):
                if ipaddr["type"] == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                    ipv4_addrs.append(ipaddr["addr"])

        if len(ipv4_addrs) > 1:
            raise ValueError("Domain has more than one IPv4 address")
        if len(ipv4_addrs) < 1:
            return None
        return ipv4_addrs[0]

    def get_ip_address(self, dom, retries: int = 25) -> str:
        for _ in range(retries):
            addr = self.try_get_ip_address(dom)
            if addr is not None:
                return addr
            time.sleep(1)
        raise ValueError(f"Couldn't get ip address in {retries} tries.")

    def xml_config(
        self, vm_path: str, is_gui: bool, reginfo: str, image_path: str
    ) -> str:
        return generate_xml(
            vm_name=self.vm_name,
            gui=is_gui,
            vm_path=vm_path,
            reginfo=reginfo,
            image_path=image_path,
            shared_path=self.shared_path,
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
            config = generate_nix(self.name, executable, self.ssh.pubkey_text)
            configpath.write_text(config)
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

        qcow2 = f"{self.vixos_path}/empty_rootfs.qcow2"
        if not Path(qcow2).exists():
            subprocess.check_call(["qemu-img", "create", "-f", "qcow2", qcow2, "40M"])

        return (realpath, reginfo, qcow2)

    def ssh_attach_user(self, dom, wait: bool) -> None:
        retries = 20 if wait else 1
        ip = self.get_ip_address(dom, retries)
        assert ip is not None
        # TODO: use a hardcoded known host key here instead?
        subprocess.check_call(
            [
                "ssh",
                f"user@{ip}",
                "-i",
                str(self.ssh.privkey_path),
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
            ]
        )

    def start(self, conn, is_gui: bool, executable: str) -> None:
        config_file = self.make_nix_config_file(executable)
        vm_path, reginfo, qcow2 = self.generate_vm(config_file)
        config = self.xml_config(vm_path, is_gui, reginfo, qcow2)
        dom = conn.createXML(config)
        if not dom:
            raise SystemExit("Failed to create a domain from an XML definition")
        print(f"Guest {dom.name()} has booted")

    def attach(self, conn, is_gui: bool) -> None:
        if is_gui:
            subprocess.check_call(["virt-viewer", "-c", conn.getURI(), self.vm_name])
        else:
            dom = conn.lookupByName(self.vm_name)
            self.ssh_attach_user(dom, True)

    def destroy(self, conn):
        try:
            dom = conn.lookupByName(self.vm_name)
            print(f"Destroying {dom.name()}")
            dom.destroy()
        except libvirt.libvirtError:
            print(f"Destroying failed (probably domain already destroyed).")


def run(args) -> None:
    print(f"OK, running {args.package}...")
    appvm = AppVM(args.package)
    executable = args.executable or args.package

    with libvirt_connection("qemu:///system") as conn:
        try:
            appvm.start(conn, args.gui, executable)
        finally:
            if not args.background:
                appvm.attach(conn, args.gui)
                appvm.destroy(conn)


def shell(args) -> None:
    appvm = AppVM(args.package)

    with libvirt_connection("qemu:///system") as conn:
        appvm.attach(conn, False)


def list_vms(args) -> None:
    with libvirt_connection("qemu:///system") as conn:
        domains = conn.listAllDomains()
        if domains is None:
            print("Failed to get a list of domain IDs")
            return

        for dom in domains:
            if dom.name().startswith("vixos_"):
                print(dom.name())


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

    list_parser = subparsers.add_parser("list", help="List available vixos VMs")
    list_parser.set_defaults(func=list_vms)

    shell_parser = subparsers.add_parser("shell", help="Run a shell in a running VM")
    shell_parser.set_defaults(func=shell)
    shell_parser.add_argument(
        "package",
        # Yes, this parameter is basically a "workspace" and not a package.
        help="Attach to a VM responsible for this package.",
    )

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
