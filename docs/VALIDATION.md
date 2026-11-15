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

## Limits of this result

The HMI process is stopped at an early initialization checkpoint. The test
does not demonstrate a fully initialized HMI, Qt Quick rendering, complete
systemd startup, navigation, audio, vehicle communication or real hardware
compatibility. Winston's Vivante output plugin still requires `/dev/galcore`.
Missing persistence keys and vehicle services remain unresolved.

The source-only tests in `tests/` validate parser and packaging behavior. They
do not substitute for these firmware integration checks.
