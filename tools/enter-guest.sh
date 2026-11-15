mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
modprobe mmc_block
modprobe sdhci-esdhc-imx
modprobe ext4
for disk in /dev/mmcblk[0-9]; do mount -t ext4 -o ro "$disk" /mnt/root && break; done
/mnt/root/bin/busybox test -r /mnt/root/usr/bin/ovip/UIFwkMasterProcess/UIFwkMasterProcess && echo NAC_ROOTFS_OK
mount --bind /dev /mnt/root/dev
mount --bind /proc /mnt/root/proc
mount --bind /sys /mnt/root/sys
mount -t tmpfs tmpfs /mnt/root/tmp
mount -t tmpfs tmpfs /mnt/root/run
/mnt/root/bin/busybox cp -r /nac /mnt/root/tmp/nac
/mnt/root/bin/busybox chroot /mnt/root /bin/sh /tmp/nac/diagnose.sh
