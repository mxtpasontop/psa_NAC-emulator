"""Prepare reproducible native UI diagnostics without modifying OEM images."""
from pathlib import Path
import hashlib
import io
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

BASE = Path(__file__).resolve().parents[1]
DOWNLOADS = BASE/'tools/downloads'
ZIG_URL = 'https://ziglang.org/download/0.14.1/zig-x86_64-windows-0.14.1.zip'
ZIG_SHA = '554f5378228923ffd558eac35e21af020c73789d87afeabf4bfd16f2e6feed2c'
LD_URL = 'https://mirror.msys2.org/mingw/ucrt64/mingw-w64-ucrt-x86_64-arm-none-eabi-binutils-2.47-1-any.pkg.tar.zst'
LD_SHA = 'b6bd237b4905f693fbe3995237f6e38dc69946fbcc867f2b9c20d0dfdeb8b7cf'
STRACE_URL = 'https://archive.debian.org/debian/pool/main/s/strace/strace_4.5.20-2.3_armhf.deb'
STRACE_SHA = 'f2a68ae1bfd60f82e8d89804b043568661e36f6e066bfc4a6bb416fbdef1f6b1'


def fetch(url, name, digest):
    path = DOWNLOADS/name
    if not path.exists():
        print(f'Downloading {name}', flush=True)
        temp = path.with_name(path.name+'.partial')
        urllib.request.urlretrieve(url, temp)
        with temp.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != digest:
            raise ValueError(f'Checksum mismatch: {name}')
        temp.replace(path)
    with path.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
            raise ValueError(f'Checksum mismatch: {name}')
    return path


def run(*command):
    subprocess.run([str(x) for x in command], check=True)


def main():
    DOWNLOADS.mkdir(exist_ok=True)
    seven = shutil.which('7z') or 'C:/Program Files/7-Zip/7z.exe'
    openssl = shutil.which('openssl') or 'C:/Program Files/Git/usr/bin/openssl.exe'
    zig_archive = fetch(ZIG_URL, 'zig-0.14.1.zip', ZIG_SHA)
    zig_dir = BASE/'tools/zig'
    if not (zig_dir/'zig-x86_64-windows-0.14.1/zig.exe').exists():
        with zipfile.ZipFile(zig_archive) as archive:
            archive.extractall(zig_dir)
    ld_archive = fetch(LD_URL, 'arm-binutils.pkg.tar.zst', LD_SHA)
    ld_dir = BASE/'tools/binutils'
    if not (ld_dir/'ucrt64/bin/arm-none-eabi-ld.exe').exists():
        run(seven, 'x', ld_archive, '-o'+str(ld_dir), '-y', '-bso0', '-bsp0')
        for archive in ld_dir.glob('*.tar'):
            run(seven, 'x', archive, '-o'+str(ld_dir), '-y', '-bso0', '-bsp0')
    package = fetch(STRACE_URL, 'strace_4.5.20-2.3_armhf.deb', STRACE_SHA).read_bytes()
    if not package.startswith(b'!<arch>\n'):
        raise ValueError('Invalid Debian ar archive')
    guest = BASE/'guest'
    guest.mkdir(exist_ok=True)
    pos = 8
    found = False
    while pos < len(package):
        header = package[pos:pos+60]
        size = int(header[48:58])
        name = header[:16].decode().strip().rstrip('/')
        data = package[pos+60:pos+60+size]
        pos += 60+size+(size%2)
        if name.startswith('data.tar'):
            with tarfile.open(fileobj=io.BytesIO(data)) as archive:
                for member in archive:
                    if member.name.lstrip('./') == 'usr/bin/strace':
                        (guest/'strace').write_bytes(archive.extractfile(member).read())
                        found = True
                    if member.name.lstrip('./') == 'usr/share/doc/strace/copyright':
                        (DOWNLOADS/'strace-copyright.txt').write_bytes(archive.extractfile(member).read())
    if not found:
        raise ValueError('strace was not found in its package')
    # Use the exact firmware ABI, rather than a modern C runtime.
    libs = BASE/'inspection/graphics'
    run(seven, 'x', BASE/'images/earlyaudio.cpio', '-o'+str(libs),
        '-ir!lib/libc-2.18.so', '-ir!lib/libdl-2.18.so', '-y', '-bso0', '-bsp0')
    firmware = BASE.parent/'SWL/001315031692686757/Firmware/AUTO'
    key = BASE/'upstream/psa-nac-firmware-reverse-engineering/Firmware_Keys/WAVE4/44.07.33-32-r0.key'
    assets = guest/'assets'
    assets.mkdir(exist_ok=True)
    for folder, name in [('1010110/NAC_B2/OVIP','readwrite-data.tar.gz'),
                         ('Universes','ui-app-data-resource.tar.gz')]:
        run(openssl, 'smime', '-decrypt', '-in', firmware/folder/name,
            '-inkey', key, '-out', assets/name)
    run(sys.executable, BASE/'tools/dtb.py', BASE/'images/board-245f4.dtb', BASE/'images/board-headless.dtb')
    run(sys.executable, BASE/'tools/build_guest.py')
    run(sys.executable, BASE/'tools/pack_initrd.py', guest, BASE/'images/diagnostic.cpio.gz',
        '--exclude', 'mesa', '--exclude', 'egl-probe', '--exclude', 'render.sh',
        '--exclude', 'libNacEglBridge.so', '--exclude', 'qt-render-probe')
    print('Native UI diagnostics ready. Run tools/run.py --ui-probe --seconds 45')


if __name__ == '__main__':
    main()
