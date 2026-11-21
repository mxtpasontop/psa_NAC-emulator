# Source from a guest script. Keep Mesa's libraries out of unrelated services.
software_display() (
    export LD_LIBRARY_PATH=/tmp/nac-mesa-client
    export LIBGL_DRIVERS_PATH=/tmp/nac/mesa/dri
    export EGL_PLATFORM=x11 DISPLAY=:0 LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=softpipe
    exec "$@"
)

start_software_display() {
    # Xvfb needs Debian's FreeType. Keep the firmware's FreeType for Qt clients.
    mkdir -p /tmp/nac-mesa-client || return
    for library in /tmp/nac/mesa/lib/*; do
        case "${library##*/}" in
            libfreetype.so*) continue ;;
        esac
        ln -sf "$library" /tmp/nac-mesa-client/ || return
    done
    # These paths exist only in the disposable writable QEMU snapshot.
    ln -sf /tmp/nac/mesa/bin/xkbcomp /usr/bin/xkbcomp || return
    mkdir -p /usr/share/X11/xkb || return
    mount --bind /tmp/nac/mesa/share/X11/xkb /usr/share/X11/xkb || return
    LD_LIBRARY_PATH=/tmp/nac/mesa/lib /tmp/nac/mesa/bin/Xvfb :0 -screen 0 800x480x24 -nolisten tcp -ac >/tmp/nac-xvfb.log 2>&1 &
    xvfb_pid=$!
    count=0
    while [ ! -S /tmp/.X11-unix/X0 ] && [ "$count" -lt 30 ]; do
        kill -0 "$xvfb_pid" 2>/dev/null || return 1
        sleep 1
        count=$((count+1))
    done
    [ -S /tmp/.X11-unix/X0 ] || return 1
    sleep 2
}
