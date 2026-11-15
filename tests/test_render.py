"""Archive and serial transfer checks using synthetic data only."""
from pathlib import Path
import base64
import gzip
import io
import struct
import sys
import tarfile
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from frames import read_frame, png_bytes
from prepare_render import data_archive


class FrameTests(unittest.TestCase):
    ppm = b'P6\n2 1\n255\n'+bytes([255,0,0,0,255,0])

    def transfer(self, data):
        encoded = base64.b64encode(data).decode()
        return 'log\r\nFRAME_BEGIN\r\n'+encoded[:8]+'\r\n'+encoded[8:]+'\r\nFRAME_END\r\n'

    def test_reads_serial_frame_with_wrapped_crlf(self):
        self.assertEqual(read_frame(self.transfer(self.ppm),'FRAME',2,1),self.ppm)

    def test_reads_gzip_frame_and_rejects_excess_pixels(self):
        self.assertEqual(read_frame(self.transfer(gzip.compress(self.ppm)),'FRAME',2,1,True),self.ppm)
        with self.assertRaises(ValueError):
            read_frame(self.transfer(gzip.compress(self.ppm+b'extra')),'FRAME',2,1,True)

    def test_rejects_truncated_wrong_size_and_missing_transfers(self):
        for console in [self.transfer(self.ppm[:-1]), self.transfer(b'P6\n1 2\n255\n'+self.ppm[-6:]),
                        'FRAME_BEGIN\n!!!!\nFRAME_END\n','no frame']:
            with self.subTest(console=console), self.assertRaises(ValueError):
                read_frame(console,'FRAME',2,1)

    def test_rejects_corrupt_gzip_transfer(self):
        corrupt = bytearray(gzip.compress(self.ppm))
        corrupt[-8] ^= 1  # Corrupt the gzip CRC, retaining a valid image payload.
        with self.assertRaises(ValueError):
            read_frame(self.transfer(corrupt),'FRAME',2,1,True)

    def test_png_has_rgb_dimensions_valid_crc_and_expected_scanline(self):
        png = png_bytes(self.ppm,2,1)
        self.assertEqual(png[:8],b'\x89PNG\r\n\x1a\n')
        chunks = {}
        pos = 8
        while pos < len(png):
            size = struct.unpack_from('>I',png,pos)[0]
            kind = png[pos+4:pos+8]
            data = png[pos+8:pos+8+size]
            self.assertEqual(struct.unpack_from('>I',png,pos+8+size)[0],zlib.crc32(kind+data))
            chunks[kind] = data
            pos += size+12
        self.assertEqual(chunks[b'IHDR'],struct.pack('>IIBBBBB',2,1,8,2,0,0,0))
        self.assertEqual(zlib.decompress(chunks[b'IDAT']),b'\0'+bytes([255,0,0,0,255,0]))


class DebianArchiveTests(unittest.TestCase):
    def package(self):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream,mode='w:gz') as archive:
            member = tarfile.TarInfo('./usr/lib/test.so')
            member.size = 3
            archive.addfile(member,io.BytesIO(b'ELF'))
        data = stream.getvalue()
        header = f'{"data.tar.gz/":<16}{0:<12}{0:<6}{0:<6}{"100644":<8}{len(data):<10}`\n'.encode()
        return b'!<arch>\n'+header+data

    def test_reads_data_member_without_extracting_host_paths(self):
        with data_archive(self.package()) as archive:
            self.assertEqual(archive.extractfile('./usr/lib/test.so').read(),b'ELF')

    def test_rejects_bad_magic_header_and_truncated_member(self):
        package = self.package()
        for bad in [b'no archive',package[:-10],package[:66]+b'xx'+package[68:]]:
            with self.subTest(length=len(bad)), self.assertRaises(ValueError):
                data_archive(bad)


if __name__ == '__main__':
    unittest.main()
