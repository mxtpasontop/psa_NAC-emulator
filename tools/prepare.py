"""Prepare local NAC Wave 4 images without changing the SWL update package."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import sys
import zlib

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'tools/deps'))


def lzop(data):
    """Read lzop streams produced by this firmware, checking block checksums."""
    from dissect.util.compression import lzo
    if not data.startswith(bytes.fromhex('894c5a4f000d0a1a0a')):
        raise ValueError('Not an lzop stream')
    pos = 9
    def number(n):
        nonlocal pos
        value = int.from_bytes(data[pos:pos+n], 'big')
        if pos+n > len(data):
            raise ValueError('Truncated lzop stream')
        pos += n
        return value
    version = number(2)
    number(2); number(2)
    method = number(1)
    if method not in (1, 2, 3):
        raise ValueError(f'Unsupported lzop method {method}')
    if version >= 0x940:
        number(1)
    flags = number(4)
    if flags & 0x800:
        number(4)
    number(4); number(4)
    if version >= 0x940:
        number(4)
    name_len = number(1)
    pos += name_len
    header_end = pos
    checksum = number(4)
    check = zlib.crc32 if flags & 0x1000 else zlib.adler32
    if check(data[9:header_end]) & 0xffffffff != checksum:
        raise ValueError('lzop header checksum mismatch')
    if flags & 0x40:
        extra_len = number(4)
        pos += extra_len
        number(4)
    output = bytearray()
    while (size := number(4)):
        packed = number(4)
        if not 0 < packed <= size <= 64 * 1024 * 1024:
            raise ValueError('Invalid lzop block size')
        sums = {}
        for mask, name in [(1, 'adler_data'), (0x100, 'crc_data')]:
            if flags & mask:
                sums[name] = number(4)
        if packed < size:
            for mask, name in [(2, 'adler_packed'), (0x200, 'crc_packed')]:
                if flags & mask:
                    sums[name] = number(4)
        chunk = data[pos:pos+packed]
        pos += packed
        dec = lzo.decompress(chunk, header=False, buflen=size) if packed < size else chunk
        if len(dec) != size:
            raise ValueError('lzop output length mismatch')
        for name, expected in sums.items():
            value = chunk if name.endswith('packed') else dec
            check = zlib.adler32 if name.startswith('adler') else zlib.crc32
            if check(value) & 0xffffffff != expected:
                raise ValueError(f'lzop {name} checksum mismatch')
        output.extend(dec)
    return bytes(output)


def decrypt(source, output, key, openssl):
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(output.name + '.partial')
    with source.open('rb') as f:
        encrypted = b'smime.p7m' in f.read(256)
    try:
        if encrypted:
            subprocess.run([str(openssl), 'smime', '-decrypt', '-in', str(source),
                            '-inkey', str(key), '-out', str(temp)], check=True)
        else:
            shutil.copyfile(source, temp)
        temp.replace(output)
    finally:
        temp.unlink(missing_ok=True)
    print(f'Prepared {output.name}: {output.stat().st_size:,} bytes', flush=True)


def unpack_kernel(path, output):
    data = path.read_bytes()
    # This NBX has a 64-byte header followed by two 64-byte descriptors.
    # Each descriptor contains load/end addresses, a file offset and a name.
    entries = []
    for at in (0x40, 0x80):
        load, end, offset = struct.unpack_from('<QQQ', data, at)
        name = data[at+24:at+56].split(b'\0')[0].decode('ascii')
        size = end-load
        if not 0 < size <= len(data) or offset+size > len(data):
            raise ValueError('Unrecognized NBX descriptor; refusing to guess')
        payload = data[offset:offset+size]
        entries.append(dict(name=name, offset=offset, size=size, load_address=hex(load)))
        if name.startswith('earlyaudio'):
            (output/'earlyaudio.cpio.lzo').write_bytes(payload)
            (output/'earlyaudio.cpio').write_bytes(lzop(payload))
        elif name == 'kernel (compressed)':
            if payload[0x24:0x28] != bytes.fromhex('18286f01'):
                raise ValueError('NBX kernel is not an ARM zImage')
            start, end = struct.unpack_from('<II', payload, 0x28)
            if end-start != len(payload):
                raise ValueError('zImage length mismatch')
            (output/'zImage').write_bytes(payload)
            magic = bytes.fromhex('894c5a4f000d0a1a0a')
            at = 0
            while (at := payload.find(magic, at)) >= 0:
                try:
                    kernel = lzop(payload[at:])
                except (ValueError, IndexError, struct.error):
                    at += 1
                    continue
                (output/'kernel.bin').write_bytes(kernel)
                at = kernel.find(b'IKCFG_ST')
                if at >= 0:
                    dec = zlib.decompressobj(31)
                    (output/'kernel.config').write_bytes(dec.decompress(kernel[at+8:]))
                break
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rootfs', action='store_true', help='Also decrypt/merge the eMMC root filesystem')
    parser.add_argument('--firmware', type=Path, default=BASE.parent/'SWL/001315031692686757/Firmware/AUTO')
    parser.add_argument('--key', type=Path, default=BASE/'upstream/psa-nac-firmware-reverse-engineering/Firmware_Keys/WAVE4/44.07.33-32-r0.key')
    parser.add_argument('--openssl', default=shutil.which('openssl') or 'C:/Program Files/Git/usr/bin/openssl.exe')
    args = parser.parse_args()
    images = BASE/'images'
    images.mkdir(exist_ok=True)
    source = args.firmware/'1010102/NAC_EU/EMMC/kernel-emmc.nbx'
    decrypt(source, images/'kernel-emmc.nbx', args.key, args.openssl)
    entries = unpack_kernel(images/'kernel-emmc.nbx', images)
    boot_source = args.firmware/'1010107/NAC/HW2021_HD/bl-ovip-hd-2021-601.nbx'
    decrypt(boot_source, images/'bootloader.nbx', args.key, args.openssl)
    boot = (images/'bootloader.nbx').read_bytes()
    at = 0
    boards = []
    while (at := boot.find(bytes.fromhex('d00dfeed'), at)) >= 0:
        if at+40 <= len(boot):
            header = struct.unpack_from('>10I', boot, at)
            if 40 < header[1] <= len(boot)-at and header[5] == 17:
                board = boot[at:at+header[1]]
                from dtb import modify, headless
                # Parse the complete structure to reject incidental magic bytes.
                modify(board, lambda path,name,value:value)
                boards.append((at, board))
        at += 1
    if len(boards) != 1:
        raise ValueError(f'Expected one bootloader DTB, found {len(boards)}')
    at, board = boards[0]
    (images/f'board-{at:x}.dtb').write_bytes(board)
    (images/'board-headless.dtb').write_bytes(headless(board))
    if args.rootfs:
        source = args.firmware/'1010103/NAC_EU/EMMC/rootfs-emmc.fsn'
        parts = [source, *sorted(source.parent.glob(source.name+'[0-9][0-9]'))]
        if [p.name for p in parts] != [source.name] + [source.name+f'{i:02}' for i in range(1,len(parts))]:
            raise ValueError('Missing or out-of-order rootfs part')
        temp = images/'rootfs-emmc.fsn.partial'
        try:
            with temp.open('wb') as out:
                for part in parts:
                    chunk = images/'rootfs-part.tmp'
                    decrypt(part, chunk, args.key, args.openssl)
                    with chunk.open('rb') as f:
                        shutil.copyfileobj(f, out)
                    chunk.unlink()
            temp.replace(images/'rootfs-emmc.fsn')
        finally:
            temp.unlink(missing_ok=True)
            (images/'rootfs-part.tmp').unlink(missing_ok=True)
        # QEMU SD cards require a power-of-two capacity. Work on a new copy.
        card = images/'rootfs-sd.img'
        card_temp = card.with_name(card.name+'.partial')
        try:
            with (images/'rootfs-emmc.fsn').open('rb') as source, card_temp.open('wb') as target:
                shutil.copyfileobj(source, target)
                target.truncate(1 << (target.tell()-1).bit_length())
            card_temp.replace(card)
        finally:
            card_temp.unlink(missing_ok=True)
    report = {'firmware':'44.07.33.32_NAC-r0', 'nbx_entries':entries, 'images':{}}
    for p in sorted(images.iterdir()):
        if p.is_file() and p.name != 'manifest.json' and p.suffix not in ('.idb', '.i64', '.id0', '.id1', '.id2', '.nam', '.til'):
            with p.open('rb') as f:
                digest = hashlib.file_digest(f, 'sha256').hexdigest()
            report['images'][p.name] = {'bytes':p.stat().st_size, 'sha256':digest}
    (BASE/'images/manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(entries, indent=2))


if __name__ == '__main__':
    main()
