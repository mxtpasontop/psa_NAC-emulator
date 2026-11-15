# psa_NAC-emulator

A Windows development environment for running original Peugeot/Continental
NAC firmware in QEMU using **TCG software emulation**. VT-x, AMD-V, Hyper-V and
WSL are not required.

**This is an experimental headless rehosting project. The Peugeot touchscreen
interface does not render yet.**

This project boots the original ARM Linux kernel and early userspace from the
local Peugeot/Continental NAC Wave 4 update, version `44.07.33.32_NAC-r0`, on
Windows using **QEMU TCG software emulation**. Hardware virtualization is not
required. It uses one emulated Cortex-A9 CPU and 1 GiB of guest RAM.

**Current status:** a working diagnostic shell and mounted eMMC filesystem;
the original Qt 5.5 offscreen backend initializes, and the original HMI master
enters its startup code and begins constructing its master object. An optional
Mesa/Xvfb overlay now renders a verified 800×480 test scene through the
firmware's own Qt OpenGL paint engine. The full Peugeot touchscreen interface
is not running and no HMI frame has been rendered.
This is a development environment for rehosting the actual firmware.

| Capability | Status |
| --- | --- |
| Original ARM Linux kernel and early userspace | Boots to a working shell |
| Original eMMC filesystem | Mounts; native programs execute |
| Original Qt 5.5 offscreen platform | Initializes successfully |
| Original HMI master | Begins constructing its master object |
| Software EGL/GLES with Mesa softpipe | Renders and verifies pixels |
| Original Qt OpenGL paint engine | Renders an 800×480 diagnostic scene; exports PNG |
| Complete HMI and rendered touchscreen | Not implemented |
| Vehicle services, CAN, audio, radio and navigation | Not validated |

## Quick start from a fresh clone

Requirements:

- Windows x64 and PowerShell.
- Python 3.11 or newer, Git for Windows, and 7-Zip.
- OpenSSL; the copy bundled with Git for Windows is detected automatically.
- Your own extracted `44.07.33.32_NAC-r0` Wave 4 firmware update.
- Space for the original update, generated images and downloaded toolchains.

Open PowerShell **in the extracted firmware folder**, alongside `SWL` and
`UpdateInfo.xml`, then run:

```powershell
git clone https://github.com/mxtpasontop/psa_NAC-emulator.git nac-emulator
python .\nac-emulator\tools\bootstrap.py
python .\nac-emulator\tools\prepare.py --rootfs
python .\nac-emulator\tools\run.py --seconds 45
```

The expected folder layout is:

```text
extracted-firmware/
├── UpdateInfo.xml
├── SWL/
│   └── 001315031692686757/Firmware/AUTO/...
└── nac-emulator/                  # This Git repository
    ├── guest/                    # Guest diagnostic scripts
    ├── guest-src/                # ARM helper source
    ├── tools/                    # Preparation and launch tools
    ├── tests/                    # Tests using synthetic data
    ├── launch.ps1
    └── README.md
```

All commands below run from `extracted-firmware/`. Preparation downloads tools
into the project and writes generated images under `nac-emulator/images`.
It does not run a QEMU installer or change Windows virtualization settings.
OEM firmware, keys, generated images and downloaded executables are not included
in this repository.

## Run the prepared environment

From the firmware folder:

```powershell
python .\nac-emulator\tools\run.py --seconds 45
```

The bounded diagnostic boots the guest, runs a shell command, saves a transcript
and JSON report under `nac-emulator/logs`, then stops QEMU. A successful report
contains `"shell_verified": true` and the transcript contains the command's
`NAC_TCG_SHELL_OK` output.

To mount and verify the original eMMC filesystem too:

```powershell
python .\nac-emulator\tools\run.py --seconds 45 --rootfs --commands .\nac-emulator\tools\probe-rootfs.sh --name rootfs-check
```

The probe loads the original storage/filesystem modules, mounts the filesystem
at `/mnt/root`, runs its BusyBox, and checks for the HMI executable. Successful
output includes an ARM Linux version and `NAC_ROOTFS_OK`.

## Probe the original UI processes

```powershell
python .\nac-emulator\tools\prepare_ui.py
python .\nac-emulator\tools\run.py --ui-probe --seconds 45 --name ui-check
```

`prepare_ui.py` downloads checksum-pinned Zig 0.14.1, GNU ARM binutils and an
older ARM strace package compatible with this firmware. They stay inside the
project. It builds small diagnostic helpers, decrypts copies of the common UI
resource and initial writable-data archives, and appends a tools payload to a
separate initramfs. The original boot images and update package stay intact.

The UI probe uses temporary filesystems for `/var`, `/Data`, `/media`, `/tmp`
and `/run`. It unpacks the firmware's common UI resources, starts a private
D-Bus daemon inside the guest, initializes the original Qt offscreen platform
plugin, then starts the unmodified `UIFwkMasterProcess` with `-platform offscreen`.
A small console backend replaces DLT logging through a guest-only bind mount.
The backend ABI was established from the local logger library's `dlsym` calls;
its source is `guest-src/console_logger.c`.

The diagnostic deliberately stops the HMI process after it logs that it is
creating its master object. This verifies startup progress, not a fully
initialized application or a rendered interface. A passing JSON report has:

```json
{
  "qt_offscreen_verified": true,
  "hmi_master_started": true,
  "graphics_probe_complete": true,
  "rendered_frame_verified": false
}
```

Reports and serial transcripts are created locally under `logs/`; they are
not committed. See [validation notes](docs/VALIDATION.md) for the tested checkpoint.
For deeper tracing, the payload includes strace at
`/tmp/nac/strace`; invoke it using `/lib/ld-linux-armhf.so.3 /tmp/nac/strace`.
Guest diagnostic sources are in `guest/diagnose.sh` and `guest-src/`.

The C helpers are compiled without modern startup/runtime objects, then linked
with GNU ld against the original firmware libc ABI. This avoids the observed
incompatibility between the modern Zig/LLD output and the old ARM loader. The
Qt probe constructs and destroys a real `QGuiApplication` through the exact
Qt 5.5 ABI; it does not provide a replacement HMI.

## Probe software graphics

After preparing the firmware and UI tools above:

```powershell
python .\nac-emulator\tools\prepare_render.py
python .\nac-emulator\tools\run.py --render-probe --seconds 60 --name render-check
```

The optional preparation downloads checksum-pinned ARM packages from Debian's
Jessie and Jessie backports archives. It places Mesa 13.0.6, Xvfb and their
dependencies in an isolated guest overlay. It keeps the firmware's original
glibc 2.18 and kernel. The full package list, versions and SHA-256 hashes are in
`tools/render-packages.json`; upstream copyright notices are retained locally
under `guest/mesa/licenses`. These old packages are used for ABI compatibility.
The guest has no network interface.

The probe starts a private Xvfb display with TCP listening disabled, forces
Mesa's **softpipe** software renderer, and verifies a real GLES pbuffer by
reading its pixels. It then uses the original Qt 5.5 `minimalegl` platform,
`QOpenGLContext`, `QOpenGLPaintDevice` and `QPainter` to render coloured rectangles.
`guest-src/egl_bridge.c` adapts minimalegl's null native window to a real
800×480 Mesa pbuffer. No fake GPU device or precomputed frame is supplied.

A successful run saves `logs/render-check-frame.png`, the serial transcript
and a report containing:

```json
{
  "software_gles_verified": true,
  "qt_software_paint_verified": true,
  "rendered_frame_verified": true,
  "frame_kind": "qt_paint_test_scene",
  "hmi_frame_verified": false
}
```

The PNG is a diagnostic scene, not the Peugeot interface. This verifies the
software graphics foundation; Qt Quick and the complete HMI are still untested.
The render probe temporarily mounts its **disposable QEMU disk snapshot**
writable to add an XKB compiler link. The backing image and OEM update stay
intact. Other probes continue to mount the root filesystem read-only. Mesa and
the EGL adapter are enabled only in this probe, and its larger initramfs is
separate from the existing UI diagnostic.

## Interactive serial console

For an interactive serial console:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\nac-emulator\launch.ps1 -Rootfs
```

This process-level execution-policy option does not change the machine's saved
policy. Use Ctrl+C to stop QEMU. Run the commands in `tools/probe-rootfs.sh` in
the guest to mount `/mnt/root`. The rootfs uses a disposable QEMU snapshot and
is mounted read-only by the probe.

## Rebuild the prepared images

Python 3.11 or newer, Git, OpenSSL and 7-Zip are needed. The scripts detect the
OpenSSL supplied with Git for Windows and 7-Zip's standard installation path.
All downloaded dependencies stay inside this project.

```powershell
python .\nac-emulator\tools\bootstrap.py
python .\nac-emulator\tools\prepare.py --rootfs
```

`bootstrap.py` obtains the pinned upstream research checkout, the LZO decoder,
and QEMU 11.1.0's Windows package. It verifies a pinned SHA-512 checksum before
extracting QEMU, without running its installer.

`prepare.py` decrypts copies of the kernel, bootloader and eight eMMC filesystem
parts. It validates lzop checksums and ARM zImage lengths, extracts the early
initramfs and kernel configuration, finds the bootloader's device tree, merges
the rootfs and makes an SD image. `images/manifest.json` records image sizes and
SHA-256 digests. The `SWL` directory and `UpdateInfo.xml` are not modified.

## Board adaptations and current limits

The stock QEMU `sabrelite` model supplies part of the i.MX6 hardware. A separate
`board-headless.dtb` disables the unsupported IPU, framebuffer, Vivante GPU,
LVDS, video capture and selected board watchdog devices. The original DTB is
retained as `board-245f4.dtb`. The root compatible becomes `fsl,imx6q`.
The bus-frequency device is also disabled: its DDR low-power transition could
otherwise hang boot intermittently at `Bus freq set to 24000000 start...`.

The experimental DTB enables the SDHC4 controller with an empty pinctrl state,
four-bit SD mode and non-removable media. Other SD controllers are disabled.
The SD image attaches to QEMU's first discoverable `sd-bus` (SDHC4 in this
pinned build); Linux exposes it as `/dev/mmcblk3` in the observed run. The probe
discovers the block-device name instead of hardcoding it.

A generic loader initializes the GPT control register to `0x349`, reflecting
the bootloader state expected by this kernel. `nowatchdog` disables Linux's
soft-lockup watchdog for this software-emulated diagnostic environment.
`clk_ignore_unused` keeps clocks needed during bring-up enabled. No kernel
instruction patches are applied.

The graphical interface depends on Continental's Winston Wayland compositor,
the original Qt applications, graphics drivers and vehicle services. Disabling
the unsupported graphics devices allows the shell to boot but cannot display
the HMI. The optional software renderer now works for a native Qt paint test,
but integrating it with the HMI still requires application/service configuration,
persistence and vehicle message stubs. Audio, radio, navigation/GPS, CAN behavior and normal systemd
startup have not been validated.

The compositor configuration loads `libwlxs-viv-output.so`, which requires
`/dev/galcore` and Vivante's 2D API. The observed failure is `failed to create
wl_viv`. The offscreen Qt path gets past that compositor dependency for startup
testing, but does not supply the OpenGL ES context needed for Qt Quick rendering.
HMI startup also reports missing persistence keys and services. These remain
separate requirements for bringing up the complete interface.

## Understanding the output

The UI probe normally prints many `CPersistence::registerKey` messages, followed
by `CUIFwkMasterProcess::run Creating Master` and `NAC_GRAPHICS_DIAG_END`.
It then closes the VM and returns to PowerShell. This is the intended diagnostic
checkpoint; it is not a fully booted infotainment session.

`--seconds` sets the maximum wait for the initial shell. Guest commands can
extend the total run time. The UI probe deliberately terminates its HMI child
process after the checkpoint, so a termination message can appear in the log.

If a probe fails, inspect both `logs/<name>-serial.log` and
`logs/<name>-qemu.log`. A shell-only run does not need the optional UI toolchains.
Preparation currently targets this exact update layout and hardware generation;
other firmware releases have not been validated.

## Development and tests

From the repository directory:

```powershell
python -m unittest discover -s tests -v
```

The automated tests use synthetic device trees, initramfs payloads, Debian
archives and frame transfers. They
do not require firmware, keys, QEMU or third-party Python packages. GitHub Actions
runs these checks on Linux and Windows. Actual firmware boot and HMI startup
remain integration checks performed locally with the commands above.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the project scope and useful areas
for further work.

## References

- [NAC firmware research and version keys](https://github.com/ludwig-v/psa-nac-firmware-reverse-engineering), pinned revision `4ce14d0ff528cf4127dcf141463c3a946d6c8997`.
- [QEMU SABRE Lite documentation](https://www.qemu.org/docs/master/system/arm/sabrelite.html).
- [Windows QEMU builds](https://qemu.weilnetz.de/w64/), also linked from [QEMU's download page](https://www.qemu.org/download/).
- [Zig downloads](https://ziglang.org/download/) and [GNU ARM binutils package](https://packages.msys2.org/packages/mingw-w64-ucrt-x86_64-arm-none-eabi-binutils).
- [Debian's archived strace package](https://archive.debian.org/debian/pool/main/s/strace/).
- [Debian's Mesa build configuration](https://sources.debian.org/src/mesa/13.0.6-1~bpo8%2B1/debian/rules/) and [archived packages](https://archive.debian.org/debian/).
- [Qt 5.5 minimalegl source](https://github.com/qt/qtbase/tree/v5.5.0/src/plugins/platforms/minimalegl).

OEM images, downloaded tools, research keys and logs are ignored by `.gitignore`.
Upstream components retain their own licenses in their downloaded directories.

## License

Project-authored source is available under the [MIT license](LICENSE).
That license does not cover OEM firmware, keys or downloaded third-party tools.
See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for component sources.
This is an independent project and is not affiliated with Peugeot, Stellantis,
Continental or Qt.
