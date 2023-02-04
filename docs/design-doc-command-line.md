# Design doc: Command Line

### Overview

We need to plan and implement a proper command line interface for the tool.
Ideally we will pick something that is familiar for the users, and at the
same time easy to use and fits the project scope.

### Design

I propose that we stay consistent with docker and kubectl as much as possible -
they may serve a different purpose, but many of the parameters will overlap.

The docker-inspired commands we will initially implement:

- [ ] `vixos build` - create a new profile (or `vixos create`?)
- [ ] `vixos run` - start a new VM (based on a existing profile) 
- [ ] `vixos stop` - stop a running VM
- [ ] `vixos ps` - list running VMs
- [ ] `vixos cp` - copy files between a VM and a local filesystem
- [ ] `vixos attach` - get a shell in the running VM

Other commands:

- [ ] `vixos appvm` - start a new transient AppVM 
- [ ] `vixos mount` - mount the current directory to the same path in the VM
