"""Append a local tools directory to a copy of the NAC early initramfs."""
from pathlib import Path
import argparse
import gzip
import stat


def record(name, data=b'', mode=stat.S_IFREG | 0o755, inode=1):
    name = name.encode()+b'\0'
    fields = [inode, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(name), 0]
    result = b'070701'+''.join(f'{value:08x}' for value in fields).encode()+name
    result += b'\0'*(-len(result)%4)
    result += data+b'\0'*(-len(data)%4)
    return result


def pack(original, directory, excludes=()):
    overlay = bytearray(record('nac', mode=stat.S_IFDIR | 0o755))
    for inode, path in enumerate(sorted(directory.rglob('*')), 2):
        relative = path.relative_to(directory).as_posix()
        if any(relative == item or relative.startswith(item.rstrip('/')+'/') for item in excludes):
            continue
        if path.suffix in ('.idb', '.i64', '.id0', '.id1', '.id2', '.nam', '.til', '.o'):
            continue
        if path.is_symlink():
            raise ValueError(f'Payload symlinks are not supported: {path}')
        name = 'nac/'+path.relative_to(directory).as_posix()
        if path.is_dir():
            overlay.extend(record(name, mode=stat.S_IFDIR | 0o755, inode=inode))
        else:
            data = path.read_bytes()
            if path.suffix in ('.sh', '.conf', '.xml'):
                data = data.replace(b'\r\n', b'\n')
            overlay.extend(record(name, data, inode=inode))
    overlay.extend(record('TRAILER!!!', mode=0))
    # Linux accepts concatenated newc archives, including their alignment pads.
    return gzip.compress(original+overlay, mtime=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--original', type=Path, default=Path(__file__).resolve().parents[1]/'images/earlyaudio.cpio')
    parser.add_argument('--exclude', action='append', default=[], help='Exclude a relative payload path and its children')
    args = parser.parse_args()
    if not args.directory.is_dir() or args.original.resolve() == args.output.resolve():
        parser.error('Supply a payload directory and a separate output file')
    args.output.write_bytes(pack(args.original.read_bytes(), args.directory, args.exclude))
    print(f'Created {args.output}: {args.output.stat().st_size:,} bytes')
