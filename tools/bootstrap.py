"""Fetch project-local dependencies; does not install services or change Windows."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import sys
import urllib.request

BASE = Path(__file__).resolve().parents[1]
QEMU_URL = 'https://qemu.weilnetz.de/w64/qemu-w64-setup-20260811.exe'
QEMU_SHA512 = '5bcf9eed634e8575a37b74f445af41a2fe4106da512d0c30c368301d4c105037fdfab40a5287367a28a957624cddebbc8c07e16c88ab6634f554cdf3d16bf543'
UPSTREAM = 'https://github.com/ludwig-v/psa-nac-firmware-reverse-engineering.git'
COMMIT = '4ce14d0ff528cf4127dcf141463c3a946d6c8997'


def run(*command):
    subprocess.run([str(item) for item in command], check=True)


def main():
    git = shutil.which('git')
    sevenzip = shutil.which('7z') or 'C:/Program Files/7-Zip/7z.exe'
    if not git or not Path(sevenzip).is_file():
        raise SystemExit('Git and 7-Zip are required. Install them, then run this script again.')
    upstream = BASE/'upstream/psa-nac-firmware-reverse-engineering'
    if not upstream.exists():
        run(git, '-c', 'http.sslBackend=openssl', 'clone', UPSTREAM, upstream)
        run(git, '-C', upstream, 'checkout', '--detach', COMMIT)
    actual = subprocess.check_output([git, '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != COMMIT:
        raise SystemExit(f'Upstream checkout differs from the tested revision: {actual}')
    deps = BASE/'tools/deps'
    if not (deps/'dissect/util/compression/lzo.py').exists():
        run(sys.executable, '-m', 'pip', 'install', '--target', deps, 'dissect.util==3.24')
    installer = BASE/'tools/downloads/qemu-w64-setup-20260811.exe'
    installer.parent.mkdir(exist_ok=True)
    if not installer.exists():
        partial = installer.with_suffix('.partial')
        print('Downloading QEMU (about 197 MiB)', flush=True)
        urllib.request.urlretrieve(QEMU_URL, partial)
        with partial.open('rb') as f:
            digest = hashlib.file_digest(f, 'sha512').hexdigest()
        if digest != QEMU_SHA512:
            raise SystemExit('QEMU checksum mismatch; partial download kept for inspection')
        partial.replace(installer)
    with installer.open('rb') as f:
        if hashlib.file_digest(f, 'sha512').hexdigest() != QEMU_SHA512:
            raise SystemExit('QEMU checksum mismatch')
    qemu = BASE/'tools/qemu'
    if not (qemu/'qemu-system-arm.exe').exists():
        run(sevenzip, 'x', installer, '-o'+str(qemu), '-y', '-bso0', '-bsp0')
    run(qemu/'qemu-system-arm.exe', '--version')
    print('Dependencies ready. Run tools/prepare.py --rootfs next.')


if __name__ == '__main__':
    main()
