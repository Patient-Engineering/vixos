# Shamelessly stolen from https://github.com/jollheef/appvm/blob/master/xml.go
# To be updated in future versions

# TODO: rewrite this to proper python structures.
from pathlib import Path


def generate_xml(
    vm_name: str,
    network: str,
    gui: bool,
    vm_path: str,
    reginfo: str,
    image_path: str,
    shared_path: str,
    ro_rootfs: bool,
    rw_paths: list[str],
) -> str:
    devices = gui_devices if gui else ""

    qemu_params = qemu_params_default
    if network == "qemu":
        qemu_params = qemu_params_with_network
    elif network == "libvirt":
        devices += net_devices

    filesystems = default_filesystems.format(shared_path=shared_path)

    for guest_path in rw_paths:
        # TODO: dirty hack to avoid appending absolute path
        host_path = Path(shared_path) / guest_path[1:]
        host_path.mkdir(exist_ok=True, parents=True)
        entry = mountable_dir.format(
            src_path=host_path,
            dst_path=guest_path,
        )
        filesystems += entry

    # create dirs
    (Path(shared_path) / "home").mkdir(exist_ok=True)
    (Path(shared_path) / "tmp").mkdir(exist_ok=True)

    return xml_template.format(
        vm_name=vm_name,
        vm_path=vm_path,
        reginfo=reginfo,
        image_path=image_path,
        ro_rootfs="<readonly/>" if ro_rootfs else "",
        filesystems=filesystems,
        extra_devices=devices,
        extra_params=qemu_params,
    )


qemu_params_default = """
  <qemu:commandline>
    <qemu:arg value='-snapshot'/>
  </qemu:commandline>
"""

qemu_params_with_network = """
  <qemu:commandline>
    <qemu:arg value='-device'/>
    <qemu:arg value='e1000,netdev=net0,bus=pci.0,addr=0x10'/>
    <qemu:arg value='-netdev'/>
    <qemu:arg value='user,id=net0'/>
    <qemu:arg value='-snapshot'/>
  </qemu:commandline>
"""

net_devices = """
    <interface type='network'>
      <source network='default'/>
    </interface>
"""

gui_devices = """
    <!-- Graphical console -->
    <graphics type='spice' autoport='yes'>
      <listen type='address'/>
      <image compression='off'/>
    </graphics>
    <!-- Guest additionals support -->
    <channel type='spicevmc'>
      <target type='virtio' name='com.redhat.spice.0'/>
    </channel>
    <video>
      <model type='virtio' heads='1' primary='yes'/>
    </video>
"""

default_filesystems = """
    <filesystem type='mount' accessmode='passthrough'>
      <source dir='/nix/store'/>
      <target dir='nix-store'/>
      <readonly/>
    </filesystem>
    <filesystem type='mount' accessmode='mapped'>
      <source dir='{shared_path}/tmp'/>
      <target dir='xchg'/> <!-- workaround for nixpkgs/nixos/modules/virtualisation/qemu-vm.nix -->
    </filesystem>
    <filesystem type='mount' accessmode='mapped'>
      <source dir='{shared_path}/tmp'/>
      <target dir='shared'/> <!-- workaround for nixpkgs/nixos/modules/virtualisation/qemu-vm.nix -->
    </filesystem>
    <filesystem type='mount' accessmode='mapped'>
      <source dir='{shared_path}/home'/>
      <target dir='home'/>
    </filesystem>
"""

mountable_dir = """
    <filesystem type='mount' accessmode='passthrough'>
      <binary path='/run/current-system/sw/bin/virtiofsd' xattr='on' />
      <driver type='virtiofs' queue='1024'/>
      <source dir='{src_path}'/>
      <target dir='{dst_path}'/>
    </filesystem>
"""

xml_template = """
<domain type='kvm' xmlns:qemu='http://libvirt.org/schemas/domain/qemu/1.0'>
  <name>{vm_name}</name>
  <memory unit='GiB'>4</memory>
  <currentMemory unit='GiB'>1</currentMemory>
  <vcpu>4</vcpu>
  <os>
    <type arch='x86_64'>hvm</type>
    <kernel>{vm_path}/kernel</kernel>
    <initrd>{vm_path}/initrd</initrd>
    <cmdline>loglevel=4 init={vm_path}/init {reginfo}</cmdline>
  </os>
  <features>
    <acpi></acpi>
  </features>
  <clock offset='utc'/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <memoryBacking>
    <source type='memfd'/>
    <access mode='shared'/>
  </memoryBacking>
  <devices>
    <!-- Fake (because -snapshot) writeback image -->
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2' cache='writeback' error_policy='report'/>
      <source file='{image_path}'/>
      <target dev='vda' bus='virtio'/>
      {ro_rootfs}
    </disk>
    <serial type='pty'>
      <source path='/dev/pts/0'/>
      <target type='isa-serial' port='0'>
        <model name='isa-serial'/>
      </target>
      <alias name='serial0'/>
    </serial>
    <console type='pty' tty='/dev/pts/0'>
      <source path='/dev/pts/0'/>
      <target type='serial' port='0'/>
      <alias name='serial0'/>
    </console>
    {filesystems}
    {extra_devices}
  </devices>
  {extra_params}
</domain>
"""
