"""Build ARM diagnostic helpers against the original firmware's libc ABI."""
from pathlib import Path
import os
import subprocess

BASE = Path(__file__).resolve().parents[1]


def main():
    zig = BASE/'tools/zig/zig-x86_64-windows-0.14.1/zig.exe'
    if not zig.is_file():
        raise SystemExit('The pinned Zig 0.14.1 Windows toolchain is required under tools/zig')
    flags = [str(zig), 'cc', '-target', 'arm-linux.3.10.0-gnueabihf.2.18',
             '-mcpu=cortex_a9', '-Os', '-fno-stack-protector', '-nostdlib',
             '-fno-unwind-tables', '-fno-asynchronous-unwind-tables', '-fPIC', '-c']
    guest = BASE/'guest'
    (guest/'logger').mkdir(exist_ok=True)
    objects = BASE/'tools/build'
    objects.mkdir(exist_ok=True)
    for source in ['console_logger', 'qt_probe']:
        subprocess.run(flags+['-o', str(objects/(source+'.o')),
                             str(BASE/'guest-src'/(source+'.c'))], check=True)
    linker = BASE/'tools/binutils/ucrt64/bin/arm-none-eabi-ld.exe'
    env = dict(os.environ)
    env['PATH'] = str(BASE/'tools/qemu')+os.pathsep+env.get('PATH', '')
    link = [str(linker), '--hash-style=both', '--allow-shlib-undefined', '-z', 'now', '-s']
    subprocess.run(link+['-shared', '-o', str(guest/'logger/libConsoleBackend.so'),
                         str(objects/'console_logger.o')], check=True, env=env)
    libs = BASE/'inspection/graphics/lib'
    subprocess.run([*link, '-e', '_start', '-Ttext-segment=0x10000',
                    '--dynamic-linker', '/lib/ld-linux-armhf.so.3',
                    '-o', str(guest/'qt-probe'), str(objects/'qt_probe.o'),
                    str(libs/'libc-2.18.so'), str(libs/'libdl-2.18.so')], check=True, env=env)
    print('Built the console logger and Qt ABI probe against firmware libc')


if __name__ == '__main__':
    main()
