#!/bin/sh
. /tmp/nac/hmi-collect.sh surface
echo NAC_HMI_DISPLAY_LOG_BEGIN
cat /tmp/nac-xvfb.log
tail -n 100 /tmp/nac-hmi-display.log 2>/dev/null
grep -E '^NAC_HMI_DISPLAY_(LAUNCH|EXIT=|MASTER_TIMEOUT)|^NAC_QT_(PBUFFER_CREATED=|NATIVE_INTERFACE_FALLBACK)' \
    /tmp/nac-hmi-display.log 2>/dev/null
echo
echo NAC_HMI_DISPLAY_LOG_END
if [ -f /tmp/nac-hmi-display.ppm ]; then
    echo NAC_HMI_DISPLAY_FRAME_BEGIN
    gzip -c /tmp/nac-hmi-display.ppm | base64
    echo NAC_HMI_DISPLAY_FRAME_END
fi
echo NAC_HMI_DISPLAY_END
