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

## Limits of this result

The HMI process is stopped at an early initialization checkpoint. The test
does not demonstrate a fully initialized HMI, Qt Quick rendering, complete
systemd startup, navigation, audio, vehicle communication or real hardware
compatibility. Winston's Vivante output plugin still requires `/dev/galcore`.
Missing persistence keys and vehicle services remain unresolved.

The source-only tests in `tests/` validate parser and packaging behavior. They
do not substitute for these firmware integration checks.
