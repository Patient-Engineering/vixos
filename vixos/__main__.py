import re
import os
import argparse
import subprocess
import libvirt
import time
import tempfile
from xml.dom import minidom
from pathlib import Path
from .template_xml import generate_xml, generate_mount_xml
from .template_nix import generate_managed_nix, generate_default_nix, generate_local_nix, generate_global_nix
from .libvirt_utils import libvirt_connection
from typing import Tuple, Optional
from .ssh import SshManager


class AppVM:
    def __init__(self, name: str) -> None:
        self.name = name
        self.vixos_root = Path.home() / "vixos"
        self.vixos_path = self.vixos_root / name
        self.shared_path = self.vixos_path / "home"

        # TODO: maybe move non-pure init actions to another functions?
        self.vixos_path.mkdir(exist_ok=True, parents=True)
        self.shared_path.mkdir(exist_ok=True)
        self.ssh = SshManager(self.vixos_root)

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
        self, vm_path: Path, is_gui: bool, reginfo: str, image_path: Path
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
        managed_config = self.vixos_path / "managed.nix"
        managed_config.write_text(generate_managed_nix(self.name, self.ssh.pubkey_text))

        globalf = self.vixos_root / "global.nix"
        if not globalf.exists():
            globalf.write_text(generate_global_nix())

        localf = self.vixos_path / "local.nix"
        if not localf.exists():
            localf.write_text(generate_local_nix())

        configpath = self.vixos_path / "default.nix"
        if not configpath.exists():
            config = generate_default_nix(self.name, executable)
            configpath.write_text(config)

    def generate_vm(self) -> Tuple[Path, str, Path]:
        subprocess.check_call(
            [
                "nix-build",
                "<nixpkgs/nixos>",
                "-A",
                "config.system.build.vm",
                "-I",
                f"nixos-config={self.vixos_path}/default.nix",
                "-I",
                self.vixos_path,
            ]
        )

        with open(f"result/bin/run-{self.name}-vm", "r") as configf:
            config = configf.read()

        reginfo = re.findall("regInfo=.*/registration", config)[0]

        realpath = Path(os.readlink("result/system"))
        os.unlink("result")

        # TODO: find a way to share the rootfs more cleanly
        qcow2 = self.vixos_path / f"{self.name}.qcow2"
        if not qcow2.exists():
            # This file is tiny on disk, because it's sparse.
            # And because of copy-on-write and --snapshot it never grows. The 4096M
            # here is basically just a restriction on maximum non-persistent data size.
            subprocess.check_call(["qemu-img", "create", "-f", "qcow2", qcow2, "4096M"])

        return (realpath, reginfo, qcow2)

    def ssh_attach_user(self, dom, wait: bool) -> None:
        retries = 20 if wait else 1
        ip = self.get_ip_address(dom, retries)
        self.ssh.interactive_session("user", ip)

    def ssh_shell_exec_as_root(self, dom, command: str) -> None:
        ip = self.get_ip_address(dom, 1)
        session = self.ssh.ssh_session("root", ip)
        # TODO: better error handling?
        session.exec_command(command)
        session.close()

    # TODO extremely ugly, refactor later (duplicated with get_ip_address)s
    def get_ip_address_from_conn(self, conn) -> str:
        dom = conn.lookupByName(self.vm_name)
        ip = self.try_get_ip_address(dom)
        assert ip is not None  # TODO handle more gracefully
        return ip

    def get(self, conn, vm_path: str, local_path: str) -> None:
        self.ssh.get_from_remote(
            "user",
            self.get_ip_address_from_conn(conn),
            vm_path,
            local_path,
        )

    def put(self, conn, local_path: str, vm_path: str) -> None:
        self.ssh.put_in_remote(
            "user",
            self.get_ip_address_from_conn(conn),
            local_path,
            vm_path,
        )

    def start(self, conn, is_gui: bool, executable: str) -> None:
        self.make_nix_config_file(executable)
        vm_path, reginfo, qcow2 = self.generate_vm()
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

    def has_filesystem(self, conn, mount_tag) -> bool:
        dom = conn.lookupByName(self.vm_name)
        xml = dom.XMLDesc()
        dom = minidom.parseString(xml)
        for diskType in dom.getElementsByTagName("filesystem"):
            target_obj = diskType.getElementsByTagName("target")[0]
            target_dir = target_obj.attributes["dir"].value
            if target_dir == mount_tag:
                return True
        return False

    def attach_filesystem(self, conn, source: str, mount_tag: str) -> None:
        dom = conn.lookupByName(self.vm_name)
        mount_xml = generate_mount_xml(source, mount_tag)
        dom.attachDevice(mount_xml)

    def mount_filesystem(self, conn, mount_tag: str, destination: str) -> None:
        dom = conn.lookupByName(self.vm_name)
        # TODO: refactor by escaping the shell (ideally abstract over this)
        cmd = f"""
            mkdir -p {destination}
            mount -t virtiofs {mount_tag} {destination}
        """
        self.ssh_shell_exec_as_root(dom, cmd)


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


def parse_file_specification(spec: str) -> Tuple[Optional[str], str]:
    if ":" not in spec:
        # local file spec, like `vmname`
        return (None, spec)
    if spec.count(":") > 1:
        raise RuntimeError("More than one `:` in specification found")
    vm_name, path = spec.split(":")
    return (vm_name, path)


def copy(args) -> None:
    source_vm, source_path = parse_file_specification(args.source)
    dest_vm, dest_path = parse_file_specification(args.destination)

    with libvirt_connection("qemu:///system") as conn:
        if source_vm is None and dest_vm is None:
            print("Just use `cp`...")
            return
        if source_vm is not None and dest_vm is not None:
            source = AppVM(source_vm)
            dest = AppVM(dest_vm)
            with tempfile.NamedTemporaryFile() as tempf:
                source.get(conn, source_path, tempf.name)
                dest.put(conn, tempf.name, dest_path)
                return
        if source_vm is not None:
            source = AppVM(source_vm)
            source.get(conn, source_path, dest_path)
        if dest_vm is not None:
            dest = AppVM(dest_vm)
            dest.put(conn, source_path, dest_path)


def mount(args) -> None:
    # If destination parameter is omitted, use source.
    destination = args.destination or args.source

    appvm = AppVM(args.package)

    with libvirt_connection("qemu:///system") as conn:
        mount_name = destination
        if not appvm.has_filesystem(conn, mount_name):
            appvm.attach_filesystem(conn, args.source, mount_name)
        appvm.mount_filesystem(conn, mount_name, destination)


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

    cp_parser = subparsers.add_parser(
        "cp",
        help="Copy from/to VMs",
    )
    cp_parser.add_argument(
        "source",
        help="Source specification, like `vmname:/etc/passwd` or `mylocalfile`.",
    )
    cp_parser.add_argument(
        "destination",
        help="Destination specification, like `vmname:/tmp/file` or `mylocalfile`.",
    )
    cp_parser.set_defaults(func=copy)

    mount_parser = subparsers.add_parser(
        "mount", help="Mount a directory into a running VM"
    )
    mount_parser.set_defaults(func=mount)
    mount_parser.add_argument(
        "package",
        help="Profile (package) name.",
    )
    mount_parser.add_argument(
        "source",
        nargs="?",
        default=os.getcwd(),
        help="Source directory (on the host). Uses current workign directory by default.",
    )
    mount_parser.add_argument(
        "destination",
        nargs="?",
        default=None,
        help="Destination directory (in the VM). Same as source directory by default.",
    )

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
