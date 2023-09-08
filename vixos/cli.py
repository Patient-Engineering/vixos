import click
import os

from .appvm import AppVM
from .libvirt_utils import libvirt_connection


def parse_file_specification(spec: str) -> tuple[str | None, str]:
    if ":" not in spec:
        # local file spec, like `vmname`
        return (None, spec)
    if spec.count(":") > 1:
        raise RuntimeError("More than one `:` in specification found")
    vm_name, path = spec.split(":")
    return (vm_name, path)



@click.group()
@click.pass_context
def main(ctx):
    pass


@main.command()
@click.argument("package")
@click.option(
    '--gui',
    '-g',
    is_flag=True,
    default=False,
    help='If specified, add graphical devices to the VM.'
)
@click.option(
    '--background',
    '-b',
    is_flag=True,
    default=False,
    help='If specified, run in the background (and don\'t kill the VM on exit).'
)
@click.option(
    '--executable',
    '-e',
    help='Set the executable name to run (by default uses the package name)'
)
def run(package: str, gui: bool, background: bool, executable: str | None) -> None:
    """Run a nixpkgs program

    Starts a VM and executes PACKAGAE (or EXECUTABLE if specified).

    Examples:
    vixos run bash
    vixos run --gui firefox
    """
    print(f"OK, running {package}...")
    appvm = AppVM(package)
    executable = executable or package

    with libvirt_connection("qemu:///system") as conn:
        try:
            appvm.start(conn, gui, executable)
        finally:
            if not background:
                appvm.attach(conn, gui)
                appvm.destroy(conn)


@main.command(name="list")
def list_vms() -> None:
    """List available vixos VMs"""
    with libvirt_connection("qemu:///system") as conn:
        domains = conn.listAllDomains()
        if domains is None:
            print("Failed to get a list of domain IDs")
            return

        for dom in domains:
            if dom.name().startswith("vixos_"):
                print(dom.name())


@main.command()
@click.argument("package")
def shell(package) -> None:
    """Run a shell in a running VM"""
    appvm = AppVM(package)

    with libvirt_connection("qemu:///system") as conn:
        appvm.attach(conn, False)


@main.command()
@click.argument("package")
@click.argument("command", nargs=-1)
def waypipe_exec(package: str, command: str) -> None:
    """Execute shell command using waypipe.

    Execute COMMAND inside running VM specified by PACKAGE.
    TO execute multi-argument command use '--'. Example:

    vixos waypipe-exec bash -- ls -lha
    """
    appvm = AppVM(package)

    with libvirt_connection("qemu:///system") as conn:
        appvm.waypipe_exec(conn, " ".join(command))


@main.command()
@click.argument("source", type=click.Path())
@click.argument("destination", type=click.Path())
def copy(source, destination) -> None:
    """Copy from/to VMs

    SOURCE specification, like `vmname:/etc/passwd` or `mylocalfile`.",
    DESTINATION specification, like `vmname:/tmp/file` or `mylocalfile`.",
    """
    source_vm, source_path = parse_file_specification(source)
    dest_vm, dest_path = parse_file_specification(destination)

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


@main.command()
@click.argument("package")
@click.argument("source", default=os.getcwd())
@click.argument("destination")
def mount(package: str, source: str, destination: str) -> None:
    """Mount a directory into a running VM

    help="Source directory (on the host). Uses current workign directory by default.",
    help="Destination directory (in the VM). Same as source directory by default.",
    """
    appvm = AppVM(package)

    with libvirt_connection("qemu:///system") as conn:
        mount_name = destination
        if not appvm.has_filesystem(conn, mount_name):
            appvm.attach_filesystem(conn, source, mount_name)
        appvm.mount_filesystem(conn, mount_name, destination)
