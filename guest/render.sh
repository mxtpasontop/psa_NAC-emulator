#!/bin/sh
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
export XDG_RUNTIME_DIR=/tmp
. /tmp/nac/software-display.sh
echo NAC_RENDER_DIAG_BEGIN
if ! start_software_display; then
    cat /tmp/nac-xvfb.log
    exit 1
fi
trap 'kill "$xvfb_pid" 2>/dev/null' EXIT
software_display /tmp/nac/egl-probe
result=$?
cat /tmp/nac-xvfb.log
echo EGL_PROBE_STATUS=$result
if [ "$result" -eq 0 ]; then
    echo NAC_FRAME_BEGIN
    base64 /tmp/nac-render.ppm
    echo NAC_FRAME_END
    echo NAC_SWAP_CAPTURE_PROBE
    software_display /bin/busybox env NAC_EGL_CAPTURE=/tmp/nac-swap-render.ppm LD_PRELOAD=/tmp/nac/libNacEglBridge.so /tmp/nac/qt-render-probe -platform minimalegl
    qt_result=$?
    echo QT_RENDER_PROBE_STATUS=$qt_result
    if [ "$qt_result" -eq 0 ]; then
        echo NAC_QT_FRAME_BEGIN
        gzip -c /tmp/nac-qt-render.ppm | base64
        echo NAC_QT_FRAME_END
        if [ -f /tmp/nac-swap-render.ppm ]; then
            echo NAC_SWAP_FRAME_BEGIN
            gzip -c /tmp/nac-swap-render.ppm | base64
            echo NAC_SWAP_FRAME_END
        fi
    fi
fi
echo NAC_RENDER_DIAG_END
