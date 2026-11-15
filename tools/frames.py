"""Validate diagnostic frame transfers and write RGB PNGs without extra packages."""
import base64
import io
import gzip
import re
import struct
import zlib


def read_frame(console, marker, width, height, compressed=False):
    pattern = re.escape(marker+'_BEGIN')+r'\r?\n([A-Za-z0-9+/=\s]+)\r?\n'+re.escape(marker+'_END')
    match = re.search(pattern, console)
    if not match:
        raise ValueError('Missing or malformed frame transfer: '+marker)
    data = base64.b64decode(''.join(match[1].split()), validate=True)
    header = f'P6\n{width} {height}\n255\n'.encode()
    expected = len(header)+width*height*3
    if compressed:
        # A corrupt guest transfer cannot expand past this diagnostic's frame size.
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
                data = stream.read(expected+1)
        except (OSError, EOFError, zlib.error) as error:
            raise ValueError('Invalid compressed frame') from error
    if len(data) != expected or not data.startswith(header):
        raise ValueError('Unexpected PPM header or pixel count')
    return data


def png_bytes(ppm, width, height):
    header = f'P6\n{width} {height}\n255\n'.encode()
    if not ppm.startswith(header) or len(ppm) != len(header)+width*height*3:
        raise ValueError('Unexpected PPM header or pixel count')
    def chunk(kind, data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    rgb = ppm[len(header):]
    stride = width*3
    rows = b''.join(b'\0'+rgb[y*stride:(y+1)*stride] for y in range(height))
    return (b'\x89PNG\r\n\x1a\n'+
            chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+
            chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b''))
