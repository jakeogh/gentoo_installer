#!/usr/bin/env python3

import os
import click
from kcl.fileops import path_is_block_special
from kcl.mountops import block_special_path_is_mounted
from kcl.mountops import path_is_mounted
from kcl.command import run_command
from kcl.printops import eprint
from kcl.deviceops import warn
from kcl.deviceops import destroy_block_device
from kcl.deviceops import destroy_block_device_head_and_tail
from kcl.deviceops import destroy_block_devices_head_and_tail
from kcl.deviceops import luksformat
from kcl.deviceops import create_filesystem
from .install_stage3 import install_stage3
from .create_boot_device import create_boot_device
from .create_root_device import create_root_device
from .write_boot_partition import write_boot_partition

def get_file_size(filename):
    fd = os.open(filename, os.O_RDONLY)
    try:
        return os.lseek(fd, 0, os.SEEK_END)
    finally:
        os.close(fd)

@click.group()
@click.pass_context
def sendgentoo(ctx):
    pass

sendgentoo.add_command(destroy_block_device)
sendgentoo.add_command(destroy_block_device_head_and_tail)
sendgentoo.add_command(luksformat)
sendgentoo.add_command(create_filesystem)

@sendgentoo.command()
@click.argument('root_devices',                required=True, nargs=-1)
@click.option('--boot-device',                 is_flag=False, required=True)
@click.option('--boot-device-partition-table', is_flag=False, required=True, type=click.Choice(['gpt']))
@click.option('--root-device-partition-table', is_flag=False, required=True, type=click.Choice(['gpt']))
@click.option('--boot-filesystem',             is_flag=False, required=True, type=click.Choice(['ext4', 'zfs']))
@click.option('--root-filesystem',             is_flag=False, required=True, type=click.Choice(['ext4', 'zfs']))
@click.option('--c-std-lib',                   is_flag=False, required=True, type=click.Choice(['glibc', 'musl', 'uclibc']))
@click.option('--raid',                        is_flag=False, required=True, type=click.Choice(['disk', 'mirror', 'raidz1', 'raidz2', 'raidz3', 'raidz10', 'raidz50', 'raidz60']))
@click.option('--raid-group-size',             is_flag=False, required=True, type=click.IntRange(1, 2))
@click.option('--march',                       is_flag=False, required=True, type=click.Choice(['native', 'x86-64']))
#@click.option('--pool-name',                   is_flag=False, required=True, type=str)
@click.option('--hostname',                    is_flag=False, required=True)
@click.option('--newpasswd',                   is_flag=False, required=True)
@click.option('--ip',                          is_flag=False, required=True)
@click.option('--force',                       is_flag=True,  required=False)
@click.option('--encrypt',                     is_flag=True,  required=False)
@click.option('--multilib',                    is_flag=True,  required=False)
@click.pass_context
def install(ctx, root_devices, boot_device, boot_device_partition_table, root_device_partition_table, boot_filesystem, root_filesystem, c_std_lib, raid, raid_group_size, march, hostname, newpasswd, ip, force, encrypt, multilib):
    assert isinstance(root_devices, tuple)
    assert hostname.lower() == hostname
    if not os.path.isdir('/usr/portage/distfiles'):
        os.makedirs('/usr/portage/distfiles')
    if not os.path.isdir('/usr/portage/sys-kernel'):
        eprint("run emerge--sync first")
        quit(1)
    if encrypt:
        eprint("encryption not yet supported")
        #quit(1)
    if c_std_lib == 'musl':
        eprint("musl not supported yet")
        quit(1)
    if c_std_lib == 'uclibc':
        eprint("uclibc fails with efi grub because efivar fails to compile. See Note.")
        quit(1)

    if len(root_devices) > 1:
        assert root_filesystem == 'zfs'
    elif len(root_devices) == 1:
        if root_filesystem == 'zfs':
            assert raid == 'disk'

    if root_filesystem == 'zfs':
        assert root_device_partition_table == 'gpt'

    assert not boot_device[-1].isdigit()
    for device in root_devices:
        assert not device[-1].isdigit()

    #if raid:
    #    assert root_filesystem == 'zfs'

    eprint("installing gentoo on boot device:", boot_device, '(' + boot_device_partition_table + ')', '(' + boot_filesystem + ')')
    assert path_is_block_special(boot_device)
    assert not block_special_path_is_mounted(boot_device)
    eprint("installing gentoo on root device(s):", root_devices, '(' + root_device_partition_table + ')', '(' + root_filesystem + ')')
    for device in root_devices:
        assert path_is_block_special(device)
        assert not block_special_path_is_mounted(device)

    eprint("using C library:", c_std_lib)
    eprint("hostname:", hostname)

    for device in root_devices:
        eprint("boot_device:", boot_device)
        eprint("device:", device)
        eprint("get_file_size(boot_device):", get_file_size(boot_device))
        eprint("get_file_size(device):     ", get_file_size(device))
        assert get_file_size(boot_device) <= get_file_size(device)

    first_root_device_size = get_file_size(root_devices[0])
    for device in root_devices:
        assert get_file_size(device) == first_root_device_size

    if not force:
        warn((boot_device,))
        warn(root_devices)

    try:
        os.mkdir('/mnt/gentoo')
    except FileExistsError:
        pass

    if boot_device == root_devices[0]:
        assert boot_filesystem == root_filesystem
        assert boot_device_partition_table == root_device_partition_table
        if boot_filesystem == 'zfs':
            destroy_block_devices_head_and_tail(root_devices, force=True, no_backup=True, size=(1024*1024*128), note=False)
            # if this is zfs, it will make a gpt table, / and EFI partition
            create_root_device(devices=root_devices, exclusive=True, filesystem=root_filesystem, partition_table=root_device_partition_table, force=True, raid=raid, raid_group_size=raid_group_size, pool_name=hostname)
            create_boot_device(device=boot_device, partition_table='none', filesystem=boot_filesystem, force=True) # dont want to delete the gpt that zfs made
            boot_mount_command = False
            root_mount_command = False

        elif boot_filesystem == 'ext4':
            ctx.invoke(destroy_block_device_head_and_tail, device=device, force=True)
            create_boot_device(ctx, device=boot_device, partition_table=boot_device_partition_table, filesystem=boot_filesystem, force=True) # writes gurb_bios from 48s to 1023s then writes EFI partition from 1024s to 18047s
            create_root_device(ctx, devices=root_devices, exclusive=False, filesystem=root_filesystem, partition_table=root_device_partition_table, force=True, raid=raid, raid_group_size=raid_group_size, pool_name=hostname)
            root_mount_command = "mount " + root_devices[0] + "3 /mnt/gentoo"
            boot_mount_command = False
        else:  # unknown case
            assert False
    else:
        eprint("differing root and boot devices: (exclusive) root_devices[0]:", root_devices[0], "boot_device:", boot_device)
        create_boot_device(device=boot_device, partition_table=boot_device_partition_table, filesystem=boot_filesystem, force=True)
        write_boot_partition(device=boot_device, force=True)
        create_root_device(devices=root_devices, exclusive=True, filesystem=root_filesystem, partition_table=root_device_partition_table, force=True, raid=raid)
        if root_filesystem == 'zfs':
            root_mount_command = False
        elif root_filesystem == 'ext4':
            root_mount_command = "mount " + root_devices[0] + "1 /mnt/gentoo"
        boot_mount_command = "mount " + boot_device + "3 /mnt/gentoo/boot"

    if root_mount_command:
        run_command(root_mount_command)

    assert path_is_mounted('/mnt/gentoo')

    try:
        os.mkdir('/mnt/gentoo/boot')
    except FileExistsError:
        pass

    if boot_mount_command:
        run_command(boot_mount_command)
        assert path_is_mounted('/mnt/gentoo/boot')
    else:
        assert not path_is_mounted('/mnt/gentoo/boot')

    try:
        os.mkdir('/mnt/gentoo/boot/efi')
    except FileExistsError:
        pass

    if boot_filesystem == 'zfs':
        efi_mount_command = "mount " + boot_device + "9 /mnt/gentoo/boot/efi"
    else:
        efi_mount_command = "mount " + boot_device + "2 /mnt/gentoo/boot/efi"

    run_command(efi_mount_command)
    install_stage3(c_std_lib=c_std_lib, multilib=multilib)

    #if march == 'native':
    chroot_gentoo_command = "/home/cfg/_myapps/sendgentoo/sendgentoo/chroot_gentoo.sh " + c_std_lib + " " + boot_device + " " + hostname + ' ' + march + ' ' + root_filesystem + ' ' + newpasswd + ' ' + ip
    eprint("now run:", chroot_gentoo_command)
    return


if __name__ == '__main__':
    sendgentoo()
