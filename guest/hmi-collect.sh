#!/bin/sh
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
export DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket
echo
echo NAC_HMI_STATE_BEGIN
kill "$(cat /tmp/nac-hmi-tail.pid)" 2>/dev/null
for name in dlt nsm framework master; do
    echo "NAC_HMI_PROCESS=$name"
    pid=$(cat "/tmp/nac-hmi-$name.pid" 2>/dev/null)
    if [ -n "$pid" ] && [ -r "/proc/$pid/status" ]; then
        grep -E '^(Name|State|VmRSS|Threads):' "/proc/$pid/status"
        if [ "$name" = master ] && ! grep -q 'State:.*Z' "/proc/$pid/status"; then
            echo NAC_HMI_MASTER_ALIVE
        fi
        cat "/proc/$pid/wchan"
        echo
    else
        echo NAC_HMI_PROCESS_EXITED
    fi
    echo "NAC_HMI_LOG=$name"
    tail -n 40 "/tmp/nac-hmi-$name.log" 2>/dev/null
    echo
done
echo NAC_HMI_MILESTONES
grep -E 'UIFwkMasterProcess::main Starting|HMIMaster::ctor|CUIFwkMasterProcess::run: Before loop|CUIFwkMasterProcess::sltHMIMasterInitialized|SettingsSharedMemory::ctor SHM shared.hmicommon.syshmi.ovip created' /tmp/nac-hmi-master.log
echo NAC_HMI_BUS_NAMES
dbus-send --system --print-reply --dest=org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus.ListNames
echo NAC_HMI_BUS_NAMES_END
echo NAC_HMI_BUS_PING
if dbus-send --system --print-reply --reply-timeout=3000 --dest=org.ovip.uifwk / org.freedesktop.DBus.Peer.Ping; then
    echo NAC_HMI_DBUS_PING_OK
fi
echo NAC_HMI_STATE_END
