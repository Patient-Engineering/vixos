# Shamelessly stolen from https://github.com/jollheef/appvm/blob/master/xml.go
# To be updated in future versions

# TODO: rewrite this to proper python structures.


def generate_xml(
    vm_name: str,
    gui: bool,
    vm_path: str,
    reginfo: str,
    image_path: str,
    shared_path: str,
) -> str:
    devices = gui_devices if gui else ""

    return xml_template.format(
        vm_name=vm_name,
        vm_path=vm_path,
        reginfo=reginfo,
        image_path=image_path,
        shared_path=shared_path,
        extra_devices=devices,
    )


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
    <!-- TODO remove console=ttyS0 by default to speed up boot times -->
    <cmdline>loglevel=4 init={vm_path}/init console=ttyS0 {reginfo}</cmdline>
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
      <transient/>
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
    <!-- filesystems -->
    <filesystem type='mount' accessmode='passthrough'>
      <source dir='/nix/store'/>
      <target dir='nix-store'/>
      <readonly/>
    </filesystem>
    <filesystem type='mount' accessmode='mapped'>
      <source dir='{shared_path}'/>
      <target dir='xchg'/> <!-- workaround for nixpkgs/nixos/modules/virtualisation/qemu-vm.nix -->
    </filesystem>
    <filesystem type='mount' accessmode='mapped'>
      <source dir='{shared_path}'/>
      <target dir='shared'/> <!-- workaround for nixpkgs/nixos/modules/virtualisation/qemu-vm.nix -->
    </filesystem>
    <filesystem type='mount' accessmode='mapped'>
      <source dir='{shared_path}'/>
      <target dir='home'/>
    </filesystem>
    <interface type='network'>
      <source network='default'/>
    </interface>
    {extra_devices}
  </devices>
</domain>
"""

mount_xml_template = """
<filesystem type='mount' accessmode='passthrough'>
  <binary path='/run/current-system/sw/bin/virtiofsd' xattr='on' />
  <driver type='virtiofs' queue='1024'/>
  <source dir='/home/msm/Projects/ctf'/>
  <target dir='ctf'/>
</filesystem>
"""
