mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
modprobe mmc_block
modprobe sdhci-esdhc-imx
modprobe ext4
for disk in /dev/mmcblk[0-9]; do mount -t ext4 -o ro "$disk" /mnt/root && break; done
/mnt/root/bin/busybox uname -a
/mnt/root/bin/busybox ls /mnt/root/usr/bin/ovip/UIFwkMasterProcess
/mnt/root/bin/busybox test -r /mnt/root/usr/bin/ovip/UIFwkMasterProcess/UIFwkMasterProcess && echo NAC_ROOTFS_OK
