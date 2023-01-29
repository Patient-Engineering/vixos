# Shamelessly stolen from https://github.com/jollheef/appvm/blob/master/xml.go
# To be updated in future versions

# TODO: rewrite this to proper python structures.


def generate_xml(
    vmname: str,
    network: str,
    gui: bool,
    vm_path: str,
    reginfo: str,
    image_path: str,
    shared_dir: str,
) -> str:
    devices = gui_devices if gui else ""

    qemuParams = qemu_params_default
    if network == "qemu":
        qemuParams = qemu_params_with_network
    elif network == "libvirt":
        devices += net_devices

    return xml_template % (
        vmname,
        vm_path,
        vm_path,
        vm_path,
        reginfo,
        image_path,
        shared_dir,
        shared_dir,
        shared_dir,
        devices,
        qemuParams,
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
      <model type='qxl' primary='yes'/>
    </video>
"""

xml_template = """
<domain type='kvm' xmlns:qemu='http://libvirt.org/schemas/domain/qemu/1.0'>
  <name>%s</name>
  <memory unit='GiB'>4</memory>
  <currentMemory unit='GiB'>1</currentMemory>
  <vcpu>4</vcpu>
  <os>
    <type arch='x86_64'>hvm</type>
    <kernel>%s/kernel</kernel>
    <initrd>%s/initrd</initrd>
    <cmdline>loglevel=4 init=%s/init %s</cmdline>
  </os>
  <features>
    <acpi></acpi>
  </features>
  <clock offset='utc'/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <devices>
    <!-- Fake (because -snapshot) writeback image -->
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2' cache='writeback' error_policy='report'/>
      <source file='%s'/>
      <target dev='vda' bus='virtio'/>
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
      <source dir='%s'/>
      <target dir='xchg'/> <!-- workaround for nixpkgs/nixos/modules/virtualisation/qemu-vm.nix -->
    </filesystem>
    <filesystem type='mount' accessmode='mapped'>
      <source dir='%s'/>
      <target dir='shared'/> <!-- workaround for nixpkgs/nixos/modules/virtualisation/qemu-vm.nix -->
    </filesystem>
    <filesystem type='mount' accessmode='mapped'>
      <source dir='%s'/>
      <target dir='home'/>
    </filesystem>
    %s
  </devices>
  %s
</domain>
"""
