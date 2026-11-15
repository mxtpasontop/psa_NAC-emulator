#!/bin/sh
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
export XDG_RUNTIME_DIR=/tmp
export LD_LIBRARY_PATH=/tmp/nac/mesa/lib
export LIBGL_DRIVERS_PATH=/tmp/nac/mesa/dri
export EGL_PLATFORM=x11
export DISPLAY=:0
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=softpipe
echo NAC_RENDER_DIAG_BEGIN
# Only the disposable QEMU snapshot is writable; its backing image stays intact.
ln -sf /tmp/nac/mesa/bin/xkbcomp /usr/bin/xkbcomp
mkdir -p /usr/share/X11/xkb
mount --bind /tmp/nac/mesa/share/X11/xkb /usr/share/X11/xkb
/tmp/nac/mesa/bin/Xvfb :0 -screen 0 800x480x24 -nolisten tcp -ac >/tmp/nac-xvfb.log 2>&1 &
xvfb_pid=$!
trap 'kill "$xvfb_pid" 2>/dev/null' EXIT
count=0
while [ ! -S /tmp/.X11-unix/X0 ] && [ "$count" -lt 30 ]; do
    kill -0 "$xvfb_pid" 2>/dev/null || break
    sleep 1
    count=$((count+1))
done
sleep 2
/tmp/nac/egl-probe
result=$?
cat /tmp/nac-xvfb.log
echo EGL_PROBE_STATUS=$result
if [ "$result" -eq 0 ]; then
    echo NAC_FRAME_BEGIN
    base64 /tmp/nac-render.ppm
    echo NAC_FRAME_END
    LD_PRELOAD=/tmp/nac/libNacEglBridge.so /tmp/nac/qt-render-probe -platform minimalegl
    qt_result=$?
    echo QT_RENDER_PROBE_STATUS=$qt_result
    if [ "$qt_result" -eq 0 ]; then
        echo NAC_QT_FRAME_BEGIN
        gzip -c /tmp/nac-qt-render.ppm | base64
        echo NAC_QT_FRAME_END
    fi
fi
echo NAC_RENDER_DIAG_END
