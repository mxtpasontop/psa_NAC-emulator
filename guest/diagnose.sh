#!/bin/sh
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
export XDG_RUNTIME_DIR=/tmp
echo NAC_GRAPHICS_DIAG_BEGIN
mount -t tmpfs tmpfs /var
mount -t tmpfs tmpfs /Data
mount -t tmpfs tmpfs /media
tar -xzf /tmp/nac/assets/readwrite-data.tar.gz -C / ./var
tar -xzf /tmp/nac/assets/ui-app-data-resource.tar.gz -C / ./media
echo NAC_UI_ASSETS_READY
mkdir -p /run/dbus /tmp/dltoffline /run/systemd/system
/lib/ld-linux-armhf.so.3 /tmp/nac/strace -V
WL_COMPOSITOR_CONFIG=0 timeout -t 2 /usr/bin/winston -P ivi -P screenshooter -l 3
echo COMPOSITOR_STATUS=$?
dbus-daemon --session --fork --address=unix:path=/run/dbus/system_bus_socket
echo DBUS_STATUS=$?
QT_DEBUG_PLUGINS=0 /tmp/nac/qt-probe -platform offscreen
echo QT_PROBE_STATUS=$?
mount --bind /tmp/nac/logger /usr/lib/ovip/OVIPLogger/backends
QT_DEBUG_PLUGINS=0 /usr/bin/ovip/UIFwkMasterProcess/UIFwkMasterProcess -platform offscreen > /tmp/hmi.log 2>&1 &
hmi_pid=$!
for attempt in $(seq 1 1000); do
    if grep -q 'CUIFwkMasterProcess::run Creating Master' /tmp/hmi.log; then
        echo HMI_MASTER_STARTED
        break
    fi
    kill -0 "$hmi_pid" 2>/dev/null || break
    sleep 1
done
kill -KILL "$hmi_pid" 2>/dev/null
wait "$hmi_pid"
echo HMI_DIAGNOSTIC_EXIT=$?
grep -m 1 'UIFwkMasterProcess::main Starting' /tmp/hmi.log
echo NAC_HMI_LOG_TAIL
tail -n 55 /tmp/hmi.log
echo NAC_GRAPHICS_DIAG_END
