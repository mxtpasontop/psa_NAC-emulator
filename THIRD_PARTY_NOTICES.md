# Third-party components

The repository contains project-authored source and documentation. Preparation
scripts obtain these components separately for local use:

| Component | Source | Use |
| --- | --- | --- |
| NAC firmware research checkout | [ludwig-v/psa-nac-firmware-reverse-engineering](https://github.com/ludwig-v/psa-nac-firmware-reverse-engineering) | Local firmware preparation; pinned revision in `bootstrap.py` |
| QEMU Windows build | [qemu.weilnetz.de](https://qemu.weilnetz.de/w64/) | ARM system emulation |
| Dissect utilities | [fox-it/dissect.util](https://github.com/fox-it/dissect.util) | LZO decompression |
| Zig | [ziglang.org](https://ziglang.org/download/) | ARM C compilation |
| GNU ARM binutils | [MSYS2 package](https://packages.msys2.org/packages/mingw-w64-ucrt-x86_64-arm-none-eabi-binutils) | Linking diagnostic helpers |
| strace | [Debian archive](https://archive.debian.org/debian/pool/main/s/strace/) | Optional guest syscall tracing |
| Mesa, Xvfb, XKB data and ARM dependencies | [Debian archive](https://archive.debian.org/debian/) | Optional software rendering; package versions and SHA-256 hashes in `tools/render-packages.json` |

These components retain their upstream licenses; the project's MIT license
does not replace them. The Debian strace copyright notice is extracted into
`tools/downloads/strace-copyright.txt` by `prepare_ui.py`. Downloaded components
and their license material are excluded from Git.
`prepare_render.py` also retains each selected Debian package's copyright
notice under `guest/mesa/licenses`. The renderer overlay is downloaded locally;
its binaries and notices are not redistributed in this repository.

OEM firmware and Qt/Vivante/Continental binaries must be supplied locally.
They are not distributed by this repository. No third-party firmware source,
decompiled pseudocode, executable, cryptographic key or UI artwork is included
in the committed project files.
