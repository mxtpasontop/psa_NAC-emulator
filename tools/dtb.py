"""Small flattened device tree reader/writer for local rehosting experiments."""
import struct


def modify(blob, transform, additions=None):
    if len(blob) < 40:
        raise ValueError('Truncated FDT header')
    header = struct.unpack_from('>10I', blob)
    if header[0] != 0xd00dfeed or header[5] != 17:
        raise ValueError('Expected a version 17 FDT')
    total = header[1]
    struct_end = header[2]+header[9]
    if not (40 <= total <= len(blob) and 40 <= header[2] <= struct_end <= total
            and 40 <= header[3] <= header[3]+header[8] <= total
            and 40 <= header[4] < total):
        raise ValueError('FDT block lies outside the declared image')
    blob = blob[:total]
    strings = bytearray(blob[header[3]:header[3]+header[8]])
    pos = header[2]
    stack = []
    output = bytearray()
    def word(value):
        output.extend(struct.pack('>I', value))
    def padded(value):
        output.extend(value)
        output.extend(b'\0' * (-len(value) % 4))
    while True:
        if pos+4 > struct_end:
            raise ValueError('Truncated FDT structure')
        token = struct.unpack_from('>I', blob, pos)[0]
        pos += 4
        if token == 1:
            end = blob.index(0, pos, struct_end)
            name = blob[pos:end].decode()
            stack.append(name)
            word(1); padded(blob[pos:end+1])
            pos = (end+4)&~3
        elif token == 2:
            if not stack:
                raise ValueError('Unbalanced FDT node')
            for key, value in (additions or {}).get('/'.join(stack), {}).items():
                encoded = key.encode()+b'\0'
                offset = strings.find(encoded)
                if offset < 0:
                    offset = len(strings)
                    strings.extend(encoded)
                word(3); word(len(value)); word(offset); padded(value)
            stack.pop(); word(2)
        elif token == 3:
            if not stack or pos+8 > struct_end:
                raise ValueError('Invalid FDT property header')
            size, name_offset = struct.unpack_from('>II', blob, pos)
            pos += 8
            if pos+size > struct_end or name_offset >= len(strings):
                raise ValueError('FDT property lies outside its block')
            name = strings[name_offset:strings.index(0, name_offset)].decode()
            value = transform('/'.join(stack), name, blob[pos:pos+size])
            pos = (pos+size+3)&~3
            if value is not None:
                word(3); word(len(value)); word(name_offset); padded(value)
        elif token == 4:
            word(4)
        elif token == 9:
            if stack:
                raise ValueError('Unclosed FDT node')
            word(9); break
        else:
            raise ValueError(f'Unknown FDT token {token}')
    pos = header[4]
    while True:
        if pos+16 > total:
            raise ValueError('Unterminated FDT reservation map')
        if blob[pos:pos+16] == b'\0'*16:
            break
        pos += 16
    reserve = blob[header[4]:pos+16]
    struct_offset = 40+len(reserve)
    string_offset = struct_offset+len(output)
    new_header = struct.pack('>10I', header[0], string_offset+len(strings),
                             struct_offset, string_offset, 40, 17, 16,
                             header[7], len(strings), len(output))
    return new_header+reserve+output+strings


def headless(blob):
    """Disable devices absent from QEMU; retain the original firmware separately."""
    def patch(path, name, value):
        if path == '' and name == 'compatible':
            return b'fsl,imx6q\0'
        if '/usdhc@' in path and name == 'status':
            return b'okay\0' if path.endswith('usdhc@0219c000') else b'disabled\0'
        if '/usdhc@' in path and name == 'bus-width':
            return struct.pack('>I', 4)
        absent = any(part in path for part in
                     ('/ipu@', '/gpu@', '/ldb@', '/pre@', '/prg@', '/fb@',
                      '/lvds_display_driver', '/v4l2_', '/contiwdog', '/vlowhandler', '/busfreq'))
        if absent and name == 'status':
            return b'disabled\0'
        if absent and name == 'compatible':
            return b'nac-emulator,unimplemented\0'
        return value
    return modify(blob, patch, {
        '/soc/busfreq': {'status': b'disabled\0'},
        '/soc/aips-bus@02100000/usdhc@0219c000': {
            'pinctrl-names': b'default\0', 'pinctrl-0': b'', 'non-removable': b''
        }
    })


if __name__ == '__main__':
    from pathlib import Path
    import argparse
    parser = argparse.ArgumentParser(description='Make a headless experimental NAC device tree')
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error('Keep the original DTB: source and output must differ')
    args.output.write_bytes(headless(args.source.read_bytes()))
