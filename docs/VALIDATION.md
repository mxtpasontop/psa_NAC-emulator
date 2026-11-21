# Validated checkpoint

The local firmware integration was exercised on Windows x64 on 2026-11-15
with Python 3.15.1 and QEMU 11.1.0. The firmware was Continental NAC Wave 4
`44.07.33.32_NAC-r0`, update ID `001315031692686757`.

QEMU used its `sabrelite` board, one emulated Cortex-A9 core, 1 GiB of RAM and
`-accel tcg,thread=multi`. No hardware virtualization was used.

## Observed results

- The original Linux 3.10.53 kernel and initramfs reached a serial shell.
- A guest command returned `NAC_TCG_SHELL_OK`.
- The merged eMMC filesystem mounted as ext4 through a disposable SD snapshot.
- The original filesystem's BusyBox executed successfully inside the guest.
- A helper constructed and destroyed a real `QGuiApplication` using the
  firmware's Qt 5.5 offscreen plugin and returned `QT_PROBE_OK`.
- The unmodified `UIFwkMasterProcess` started with a diagnostic console-logging
  backend and logged that it was creating its master object.

The successful UI diagnostic reported:

```json
{
  "software_emulation": true,
  "shell_verified": true,
  "rootfs_verified": true,
  "qt_offscreen_verified": true,
  "hmi_master_started": true,
  "graphics_probe_complete": true,
  "rendered_frame_verified": false,
  "exit_code": 0
}
```

The user independently repeated the UI probe and observed the same startup
checkpoint. Raw transcripts, addresses, extracted binaries and analysis
databases remain local and are excluded from Git.

## Software graphics checkpoint

The optional `--render-probe` was also exercised under the same TCG-only VM.
Debian's checksum-pinned Mesa 13.0.6 overlay loaded against the firmware's
original glibc 2.18. A private Xvfb server supplied an X11 display because this
Debian Mesa build does not enable its surfaceless platform.

Observed output included:

```text
EGL_INITIALIZED=1.4
GL_RENDERER=Gallium 0.4 on softpipe
GL_VERSION=OpenGL ES 3.0 Mesa 13.0.6
GL_PIXEL=32,128,223,255 ERROR=0x0
NAC_SOFTWARE_GLES_OK
NAC_QT_PBUFFER_CREATED=800x480
NAC_QT_GL_CONTEXT_CURRENT
QT_GL_RENDERER=Gallium 0.4 on softpipe
QT_GL_ERROR=0x0 QT_RED=255,0,0 QT_GREEN=0,255,0
NAC_QT_SOFTWARE_PAINT_OK
```

The second part used the firmware's original Qt 5.5 `minimalegl` platform and
OpenGL paint engine. The opt-in EGL adapter translated its null native window
into a genuine Mesa pbuffer. `QPainter` drew a dark blue background, cyan bar,
red rectangle and green rectangle. Guest-side GL readback verified sample
pixels in all four regions before exporting the complete framebuffer.
The host validated the compressed PPM transfer and wrote an 800×480 PNG, which
was visually inspected. This was a project-authored diagnostic scene.

The successful render report had `software_gles_verified`,
`qt_software_paint_verified` and `rendered_frame_verified` set to `true`,
`frame_kind` set to `qt_paint_test_scene`, and `hmi_frame_verified` set to `false`.
No Peugeot HMI frame or Qt Quick scene has been validated.

The render probe's root filesystem is writable only inside QEMU's disposable
snapshot; the backing image stays unchanged. The previous offscreen/HMI probe
continues to use a read-only root filesystem and a separate initramfs.

The final device tree also disables the original bus-frequency device after
an intermittent boot hang was observed during its DDR low-power transition.
Both the original Qt/HMI startup probe and the new renderer probe passed with
that adaptation. The backing SD image's SHA-256 still matched its preparation
manifest after the writable-snapshot graphics checks.

## Native service startup checkpoint

The longer `--hmi-probe --observe-seconds 90` mode was exercised with the same
firmware, original kernel and TCG-only VM. Unlike the quick UI smoke test, it
continues beyond the master-creation message. It uses the original framework
plugin paths and starts the original DLT daemon, Node State Manager,
`ApplicationFwkCore` and HMI master against a private guest D-Bus daemon.
The eMMC root filesystem remains mounted read-only. `/var`, `/Data`, `/media`,
`/tmp`, `/run` and `/dev/shm` are temporary filesystems.

Observed results included:

- The original Qt offscreen application probe completed.
- The master created `shared.hmicommon.syshmi.ovip` settings shared memory.
- The original NSM registered `org.genivi.NodeStateManager`.
- The original application framework registered its execution-control,
  content-broker and profile-management services.
- The original HMI master registered `org.ovip.uifwk` and its lifecycle service.
- The master remained alive at collection time.
- The registered HMI service answered a D-Bus peer ping.

The service registrations were read from D-Bus's live name inventory, not
inferred from a startup log. Some native constructor and initialization messages
were absent; report fields with `message_observed` describe log capture only.
The read-only D-Bus ping returned successfully and is reported separately as
`hmi_bus_ping_verified`.
No HMI screen was rendered by this mode.

A repeated quick UI probe exceeded the old 60-second command budget during
cold Qt library loading. Firmware probes now default to a 180-second command
budget, and an explicit `--command-timeout` is respected. The initial shell
timeout and the subsequent host observation window remain separate controls.
The quick UI probe passed when repeated with the larger command budget.

Starting the OEM DLT daemon without a watchdog interval produced repeated
`Failed to read timer_wd; Bad file descriptor` warnings. Supplying
`WATCHDOG_USEC=20000000` removed those warnings in the repeated run. This matches
the watchdog timer setup in the [upstream DLT source](https://github.com/COVESA/dlt-daemon/blob/v2.17.0/src/daemon/dlt-daemon.c).
The probe supplies the interval only; it does not implement or acknowledge a
systemd watchdog.

Missing vehicle persistence data and zone-monitor state remain visible in the
master's native logs. Public service registration is a startup milestone, not
proof that the complete HMI, its applications or vehicle functions are ready.

## Display capture under TCG

The render probe reads the presentation surface during `eglSwapBuffers`.
Its 800×480 capture matched the firmware Qt paint test's direct readback
byte for byte. The test also verified restoration of the GL framebuffer and
pixel pack settings after capture.

In the native display probe, the firmware Surface Manager supplied zone shared
memory and the HMI master attached to it. The native
`HMIInternalApplication` loaded Qt Quick groups and presented a solid black
surface before crashing in its Internet group plugin. Omitting that plugin
from the disposable snapshot advanced startup to text layout.

The firmware's fontconfig code dereferenced a null native interface in the
`minimalegl` platform. The display probe supplies the firmware Qt library's
default native interface when that platform returns null. With this fallback
the application passed text construction and continued into time and settings
QML. The capture in that run was still solid black.

A local run with the shared Pixel theme assets gave the same black capture.
It verified that the original display application created its EGL surface,
used the native-interface fallback and selected the Pixel theme. The logs
still report missing vehicle configuration and DateTimeService. The capture
is an individual application's surface. The full display depends on the
firmware's compositor and lifecycle.

## Limits of these results

The quick UI probe stops the HMI process at an early initialization checkpoint.
The longer probe observes native service startup. These tests
do not demonstrate a fully initialized HMI, Qt Quick rendering, complete
systemd startup, navigation, audio, vehicle communication or real hardware
compatibility. Winston's Vivante output plugin still requires `/dev/galcore`.
Missing persistence keys and vehicle services remain unresolved.

The source-only tests in `tests/` validate parser and packaging behavior. They
do not substitute for these firmware integration checks.
