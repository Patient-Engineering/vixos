# How to: hotplug a directory

In the future this will be handled more transparently.
Currently as a user you must:

1. Create a XML file called `kot.xml` with a following content:

```
<filesystem type='mount' accessmode='passthrough'>
  <binary path='/run/current-system/sw/bin/virtiofsd' xattr='on' />
  <driver type='virtiofs' queue='1024'/>
  <source dir='/home/msm/Projects/ctf'/>
  <target dir='ctf'/>
</filesystem>
```

`<binary>` tag is a nixos workaround for nixos: https://github.com/NixOS/nixpkgs/issues/187078
`<source>` should be of course changed by you to the host path
`<target>` is a tag name for a directory

2. Attach it to your VM

```
$ virsh -c qemu:///system attach-device vixos_firefox kot.xml
```

Remember to replace the VM name

3. Mount it in your VM

Run the following in the VM (as root):
```
$ mount -t virtiofs ctf /home/user/ctf
```

`ctf` is a tag name from `<target>`, and the path is of course the mount path.
