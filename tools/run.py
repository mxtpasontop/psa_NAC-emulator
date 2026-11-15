"""Run a bounded NAC boot diagnostic using QEMU TCG software emulation."""
from pathlib import Path
import argparse
import json
import re
import select
import socket
import subprocess
import time

BASE = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=int, default=20)
    parser.add_argument('--dtb', type=Path, default=BASE/'images/board-headless.dtb')
    parser.add_argument('--name', default='boot')
    parser.add_argument('--dump-ram', action='store_true')
    parser.add_argument('--rootfs', action='store_true', help='Attach the eMMC filesystem through a disposable SD snapshot')
    parser.add_argument('--commands', type=Path, help='Run this shell script inside the guest diagnostic shell')
    parser.add_argument('--initrd', type=Path, default=BASE/'images/earlyaudio.cpio')
    parser.add_argument('--command-timeout', type=int, default=10)
    parser.add_argument('--ui-probe', action='store_true', help='Probe the native Qt and HMI processes using the prepared diagnostic initramfs')
    args = parser.parse_args()
    if args.ui_probe:
        args.rootfs = True
        args.initrd = BASE/'images/diagnostic.cpio.gz'
        args.commands = BASE/'tools/enter-guest.sh'
        args.command_timeout = 60
        if not args.initrd.exists():
            parser.error('Run tools/prepare_ui.py first')
    if not 1 <= args.seconds <= 300:
        parser.error('seconds must be between 1 and 300')
    if not 1 <= args.command_timeout <= 60:
        parser.error('command-timeout must be between 1 and 60')
    if not args.name.replace('-', '').replace('_', '').isalnum():
        parser.error('name may contain letters, digits, hyphens and underscores')
    logs = BASE/'logs'
    logs.mkdir(exist_ok=True)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
        with socket.socket() as console_sock:
            console_sock.bind(('127.0.0.1', 0))
            console_port = console_sock.getsockname()[1]
    serial = logs/f'{args.name}-serial.log'
    command = [str(BASE/'tools/qemu/qemu-system-arm.exe'),
        '-M', 'sabrelite', '-accel', 'tcg,thread=multi', '-smp', '1', '-m', '1G',
        '-device', 'loader,addr=0x02098000,data=0x349,data-len=4',
        '-display', 'none', '-monitor', 'none', '-S',
        '-qmp', f'tcp:127.0.0.1:{port},server=on,wait=off',
        '-chardev', f'socket,id=console,host=127.0.0.1,port={console_port},server=on,wait=off',
        '-serial', 'chardev:console', '-nic', 'none',
        '-kernel', str(BASE/'images/zImage'), '-dtb', str(args.dtb.resolve()),
        '-initrd', str(args.initrd.resolve()),
        '-append', 'console=ttymxc0,115200 earlyprintk debug ignore_loglevel clk_ignore_unused nowatchdog rdinit=/bin/sh']
    if args.rootfs:
        card = BASE/'images/rootfs-sd.img'
        if not card.exists():
            parser.error('Run prepare.py --rootfs to create images/rootfs-sd.img')
        command.extend(['-drive', f'file={card},if=none,id=nacroot,format=raw,snapshot=on',
                        '-device', 'sd-card,drive=nacroot,bus=sd-bus'])
    report = {'command':command, 'software_emulation':True}
    with (logs/f'{args.name}-qemu.log').open('wb') as out:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT)
        try:
            for _ in range(40):
                try:
                    sock = socket.create_connection(('127.0.0.1', port), timeout=2)
                    break
                except OSError:
                    if process.poll() is not None:
                        raise RuntimeError('QEMU exited; inspect the QEMU log')
                    time.sleep(.25)
            else:
                raise RuntimeError('QMP did not become ready')
            with sock, sock.makefile('rwb') as stream, socket.create_connection(('127.0.0.1', console_port), timeout=2) as terminal:
                report['qmp'] = json.loads(stream.readline())
                def qmp(execute, arguments=None):
                    msg = {'execute':execute}
                    if arguments is not None:
                        msg['arguments'] = arguments
                    stream.write(json.dumps(msg).encode()+b'\n'); stream.flush()
                    while True:
                        response = json.loads(stream.readline())
                        if 'return' in response:
                            return response['return']
                        if 'error' in response:
                            raise RuntimeError(response['error'])
                qmp('qmp_capabilities')
                qmp('cont')
                print(f'Running ARM guest with TCG software emulation for {args.seconds} seconds.', flush=True)
                console = ''
                serial.write_text('')
                def receive():
                    chunks = []
                    while select.select([terminal], [], [], 0)[0]:
                        data = terminal.recv(65536)
                        if not data:
                            break
                        chunks.append(data)
                    text = b''.join(chunks).decode(errors='replace')
                    with serial.open('a') as transcript:
                        transcript.write(text.replace('\r\n', '\n').replace('\r', ''))
                    return text
                deadline = time.monotonic()+args.seconds
                while time.monotonic() < deadline:
                    console += receive()
                    if console.rstrip().endswith('#'):
                        break
                    time.sleep(.25)
                # Feed characters at terminal speed so the emulated UART FIFO
                # does not discard the end of long command lines.
                commands = 'echo NAC_TCG_SHELL_OK\n'
                if args.commands:
                    commands += args.commands.read_text().replace('\r', '')+'\n'
                for line in commands.splitlines():
                    if not line.strip():
                        continue
                    for char in line+'\n':
                        terminal.sendall(char.encode())
                        time.sleep(.01)
                    response = ''
                    deadline = time.monotonic()+args.command_timeout
                    while time.monotonic() < deadline:
                        response += receive()
                        if re.search(r'(?:^|\n)#(?: |$)', response):
                            break
                        time.sleep(.1)
                    console += response
                qmp('stop')
                console += receive()
                serial.write_text(console.replace('\r\n', '\n').replace('\r', ''))
                report['shell_verified'] = '\nNAC_TCG_SHELL_OK\n' in console.replace('\r', '')
                report['rootfs_verified'] = '\nNAC_ROOTFS_OK\n' in console.replace('\r', '')
                if args.ui_probe:
                    report['qt_offscreen_verified'] = '\nQT_PROBE_OK\n' in console.replace('\r', '')
                    report['hmi_master_started'] = 'UIFwkMasterProcess::main Starting' in console
                    report['graphics_probe_complete'] = '\nNAC_GRAPHICS_DIAG_END\n' in console.replace('\r', '')
                    report['rendered_frame_verified'] = False
                report['registers'] = qmp('human-monitor-command', {'command-line':'info registers'})
                if args.dump_ram:
                    path = str(logs/f'{args.name}-ram.bin').replace('\\', '/')
                    qmp('human-monitor-command', {'command-line':f'pmemsave 0x10400000 0x1000000 "{path}"'})
                    from kmsg import extract
                    dump = logs/f'{args.name}-ram.bin'
                    if dump.exists():
                        (logs/f'{args.name}-kernel.log').write_text(extract(dump.read_bytes()))
                qmp('quit')
        finally:
            if process.poll() is None:
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=5)
            report['exit_code'] = process.returncode
            (logs/f'{args.name}.json').write_text(json.dumps(report, indent=2)+'\n')
    print(serial.read_text(errors='replace')[-1800:])
    print(f'Diagnostics saved to {logs/args.name}.json')
    if not report.get('shell_verified'):
        raise SystemExit('Shell verification failed; inspect the diagnostic logs')
    if args.ui_probe and not (report.get('qt_offscreen_verified') and report.get('hmi_master_started') and report.get('graphics_probe_complete')):
        raise SystemExit('Native UI diagnostic did not complete successfully; inspect the logs')


if __name__ == '__main__':
    main()
