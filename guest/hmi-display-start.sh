#!/bin/sh
# Load native services first, with their original libraries and an offscreen QPA.
. /tmp/nac/hmi-start.sh
start_native surface /usr/bin/ovip/UIFramework/ZoneManagement/SurfaceManager
. /tmp/nac/software-display.sh
if ! start_software_display; then
    echo NAC_HMI_DISPLAY_XVFB_FAILED
    cat /tmp/nac-xvfb.log
    exit 1
fi

# The Internet group crashes during QML initialization when the corresponding
# service is absent. Keep the rest of the native groups in this offline probe.
mkdir -p /tmp/nac-disabled-groups || exit 1
for plugin in /usr/lib/ovip/GroupsPlugins/libInternetHMIGroupPlugin.so*; do
    [ -e "$plugin" ] || [ -L "$plugin" ] || continue
    mv "$plugin" /tmp/nac-disabled-groups/ || exit 1
done

# Let the serial shell return while the master is still starting. The host
# owns the observation deadline and shuts down the whole guest afterward.
(
    for attempt in $(seq 1 1200); do
        if dbus-send --system --print-reply --reply-timeout=2000 --dest=org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus.NameHasOwner string:org.ovip.uifwk | grep -q 'boolean true'; then
            echo NAC_HMI_DISPLAY_LAUNCH
            software_display /bin/busybox env QT_QPA_PLATFORM=minimalegl QSG_RENDER_LOOP=basic OVIP_UIFWK_WELCOME_ANIMATION=0 \
                NAC_EGL_CAPTURE=/tmp/nac-hmi-display.ppm NAC_QT_NATIVE_INTERFACE_FALLBACK=1 \
                LD_PRELOAD=/tmp/nac/libNacEglBridge.so \
                /usr/bin/ovip/HMIInternalApplication/HMIInternalApplication -platform minimalegl
            echo "NAC_HMI_DISPLAY_EXIT=$?"
            exit
        fi
        sleep 1
    done
    echo NAC_HMI_DISPLAY_MASTER_TIMEOUT
) >/tmp/nac-hmi-display.log 2>&1 &
echo NAC_HMI_DISPLAY_START_END
