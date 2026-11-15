"""Prepare an isolated, checksum-pinned Mesa software renderer for ARM."""
from pathlib import Path
import io
import json
import posixpath
import tarfile

from prepare_ui import BASE, fetch, run
import sys


def data_archive(package):
    if not package.startswith(b'!<arch>\n'):
        raise ValueError('Invalid Debian ar archive')
    pos = 8
    while pos+60 <= len(package):
        header = package[pos:pos+60]
        size = int(header[48:58])
        if header[58:60] != b'`\n' or size < 0:
            raise ValueError('Invalid Debian archive member header')
        name = header[:16].decode().strip().rstrip('/')
        if pos+60+size > len(package):
            raise ValueError('Truncated Debian archive member')
        if name.startswith('data.tar'):
            return tarfile.open(fileobj=io.BytesIO(package[pos+60:pos+60+size]))
        pos += 60+size+(size%2)
    raise ValueError('Debian package has no data archive')


def main():
    if not (BASE/'guest/qt-probe').is_file():
        raise SystemExit('Run tools/prepare_ui.py first to prepare the toolchain and native diagnostics')
    packages = json.loads((BASE/'tools/render-packages.json').read_text())
    entries = {}
    copyrights = {}
    doc_links = {}
    notices = BASE/'guest/mesa/licenses'
    notices.mkdir(parents=True, exist_ok=True)
    for package in packages:
        file = fetch('https://archive.debian.org/debian/'+package['Filename'],
                     Path(package['Filename']).name, package['SHA256'])
        print('Preparing', package['Package'], package['Version'], flush=True)
        with data_archive(file.read_bytes()) as archive:
            for member in archive:
                name = member.name.removeprefix('./')
                if name.startswith('/') or '..' in name.split('/'):
                    raise ValueError('Unexpected package path')
                if name.endswith('/copyright') and (member.isfile() or member.islnk()):
                    copyrights[name] = archive.extractfile(member).read()
                if name.startswith('usr/share/doc/') and member.issym():
                    doc_links[name] = (member.linkname.lstrip('/') if member.linkname.startswith('/') else
                                       posixpath.normpath(posixpath.join(posixpath.dirname(name),member.linkname)))
                if member.isfile() and (name in ('usr/bin/Xvfb', 'usr/bin/xkbcomp') or
                                        name.startswith('usr/share/X11/xkb/')):
                    target = BASE/'guest/mesa'/name.removeprefix('usr/')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.extractfile(member).read())
                if '.so' not in posixpath.basename(name):
                    continue
                if member.isfile() or member.islnk():
                    entries[name] = archive.extractfile(member).read()
                elif member.issym():
                    target = member.linkname
                    entries[name] = (target.lstrip('/') if target.startswith('/') else
                                     posixpath.normpath(posixpath.join(posixpath.dirname(name), target)))
    for package in packages:
        name = 'usr/share/doc/'+package['Package']+'/copyright'
        for _ in range(32):
            if name in copyrights:
                (notices/(package['Package']+'.txt')).write_bytes(copyrights[name])
                break
            for prefix, target in doc_links.items():
                if name == prefix or name.startswith(prefix+'/'):
                    name = target+name[len(prefix):]
                    break
            else:
                raise ValueError('Missing package copyright notice: '+package['Package'])
        else:
            raise ValueError('Cyclic package documentation link')
    def resolve(name, seen=None):
        seen = set() if seen is None else seen
        if name in seen or name not in entries:
            raise ValueError('Unresolved package library link: '+name)
        seen.add(name)
        value = entries[name]
        return value if isinstance(value, bytes) else resolve(value, seen)
    count = 0
    for name in entries:
        filename = posixpath.basename(name)
        if filename.endswith('_dri.so') and filename != 'swrast_dri.so':
            continue
        directory = BASE/'guest/mesa'/('dri' if filename.endswith('_dri.so') else 'lib')
        directory.mkdir(exist_ok=True)
        data = resolve(name)
        target = directory/filename
        if target.exists() and target.read_bytes() != data:
            raise ValueError('Conflicting library basename: '+filename)
        target.write_bytes(data)
        count += 1
    print(f'Prepared {count} library names; OEM libc remains in use')
    run(sys.executable, BASE/'tools/dtb.py', BASE/'images/board-245f4.dtb', BASE/'images/board-headless.dtb')
    run(sys.executable, BASE/'tools/build_guest.py')
    run(sys.executable, BASE/'tools/pack_initrd.py', BASE/'guest', BASE/'images/render.cpio.gz')


if __name__ == '__main__':
    main()
