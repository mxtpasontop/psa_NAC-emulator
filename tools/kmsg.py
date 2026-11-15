"""Recover Linux 3.10 printk records from a local guest RAM diagnostic dump."""
import struct


def extract(data):
    pos = data.find(b'Booting Linux on physical CPU')-16
    lines = []
    while pos >= 0 and pos+16 <= len(data):
        timestamp, length, textlen, dictlen, _, _ = struct.unpack_from('<QHHHBB', data, pos)
        if length < 16 or length > 8192 or textlen+dictlen+16 > length:
            break
        text = data[pos+16:pos+16+textlen].decode(errors='replace')
        lines.append(f'[{timestamp/1e9:10.6f}] {text}')
        pos += length
    return '\n'.join(lines)+'\n' if lines else ''
