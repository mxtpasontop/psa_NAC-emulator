#!/bin/sh
# Observe native service startup without stopping at the master constructor.
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
export HOME=/home/root XDG_RUNTIME_DIR=/tmp QT_QPA_PLATFORM=offscreen
export QT_PLUGIN_PATH=/usr/lib/ovip/AppFwk/Core:/usr/lib/ovip/AppFwk/Domains:/usr/lib/ovip/UIFramework
export DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket
echo NAC_HMI_START_BEGIN
mount -t tmpfs tmpfs /var
mount -t tmpfs tmpfs /Data
mount -t tmpfs tmpfs /media
tar -xzf /tmp/nac/assets/readwrite-data.tar.gz -C / ./var
tar -xzf /tmp/nac/assets/ui-app-data-resource.tar.gz -C / ./media
mkdir -p /run/dbus /tmp/dltoffline /run/systemd/system /dev/shm
mount -t tmpfs tmpfs /dev/shm
mount --bind /tmp/nac/logger /usr/lib/ovip/OVIPLogger/backends
dbus-daemon --session --fork --address="$DBUS_SYSTEM_BUS_ADDRESS"
/tmp/nac/qt-probe -platform offscreen
echo HMI_QT_PROBE_STATUS=$?
start_native() {
    name=$1
    shift
    "$@" >"/tmp/nac-hmi-$name.log" 2>&1 &
    echo $! >"/tmp/nac-hmi-$name.pid"
}
# The OEM daemon expects a systemd watchdog period; without one its timer fd
# remains invalid and it spins while flooding the log. No watchdog reply is faked.
start_native dlt /bin/busybox env WATCHDOG_USEC=20000000 /usr/bin/dlt-daemon
start_native nsm /usr/bin/NodeStateManager
start_native framework /usr/bin/ovip/AppFwk/ApplicationFwkCore
start_native master /usr/bin/ovip/UIFwkMasterProcess/UIFwkMasterProcess -platform offscreen
# Stream the native log during the host's observation window.
tail -n +1 -f /tmp/nac-hmi-master.log &
echo $! >/tmp/nac-hmi-tail.pid
echo NAC_HMI_START_END
