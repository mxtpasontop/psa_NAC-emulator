"""Source-only regression tests; no OEM firmware or downloaded tools required."""
from pathlib import Path
import gzip
import stat
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from dtb import modify, headless
from pack_initrd import pack


def synthetic_dtb():
    """A small FDT v17 fixture using the standard big-endian token format."""
    strings = b'compatible\0status\0bus-width\0'
    def pad(value):
        return value+b'\0'*(-len(value)%4)
    def node(name):
        return struct.pack('>I', 1)+pad(name.encode()+b'\0')
    def prop(name, value):
        return struct.pack('>III', 3, len(value), strings.index(name.encode()+b'\0'))+pad(value)
    end = struct.pack('>I', 2)
    body = node('')+prop('compatible', b'fsl,imx6q-wave2\0')
    body += node('fb@0')+prop('status', b'okay\0')+end
    body += node('soc')+node('aips-bus@02100000')+node('usdhc@0219c000')
    body += prop('status', b'disabled\0')+prop('bus-width', struct.pack('>I', 8))
    body += end*4+struct.pack('>I', 9)
    strings_offset = 56+len(body)
    header = struct.pack('>10I', 0xd00dfeed, strings_offset+len(strings), 56,
                         strings_offset, 40, 17, 16, 0, len(strings), len(body))
    return header+b'\0'*16+body+strings


def read_newc(data):
    """Decode records for assertions independently of the payload writer."""
    pos = 0
    files = {}
    while True:
        if data[pos:pos+6] != b'070701':
            raise AssertionError('Invalid newc magic')
        fields = [int(data[pos+6+i*8:pos+14+i*8], 16) for i in range(13)]
        pos += 110
        name = data[pos:pos+fields[11]-1].decode()
        pos = (pos+fields[11]+3)&~3
        content = data[pos:pos+fields[6]]
        pos = (pos+fields[6]+3)&~3
        if name == 'TRAILER!!!':
            return files
        files[name] = (fields[1], content)


class DeviceTreeTests(unittest.TestCase):
    def test_round_trip_preserves_fixture(self):
        original = synthetic_dtb()
        self.assertEqual(modify(original, lambda p,k,v:v), original)

    def test_headless_keeps_console_board_and_adapts_display_and_storage(self):
        properties = {}
        def collect(path, name, value):
            self.assertNotIn((path, name), properties)
            properties[path, name] = bytes(value)
            return value
        modify(headless(synthetic_dtb()), collect)
        self.assertEqual(properties['', 'compatible'], b'fsl,imx6q\0')
        self.assertEqual(properties['/fb@0', 'status'], b'disabled\0')
        sd = '/soc/aips-bus@02100000/usdhc@0219c000'
        self.assertEqual(properties[sd, 'status'], b'okay\0')
        self.assertEqual(properties[sd, 'bus-width'], struct.pack('>I', 4))
        self.assertEqual(properties[sd, 'pinctrl-0'], b'')

    def test_rejects_truncated_and_out_of_bounds_images(self):
        original = synthetic_dtb()
        with self.assertRaises(ValueError):
            modify(original[:32], lambda p,k,v:v)
        with self.assertRaises(ValueError):
            modify(original[:-1], lambda p,k,v:v)
        malformed = bytearray(original)
        struct.pack_into('>I', malformed, 8, len(original)+4)
        with self.assertRaises(ValueError):
            modify(malformed, lambda p,k,v:v)

    def test_rejects_unterminated_reservation_map(self):
        malformed = bytearray(synthetic_dtb())
        malformed[40:56] = b'X'*16
        with self.assertRaises(ValueError):
            modify(malformed, lambda p,k,v:v)


class PayloadTests(unittest.TestCase):
    def test_payload_is_deterministic_executable_and_filters_analysis_files(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            (directory/'start.sh').write_bytes(b'echo ready\r\n')
            (directory/'analysis.i64').write_bytes(b'not for the guest')
            (directory/'analysis.id2').write_bytes(b'not for the guest')
            (directory/'helper.o').write_bytes(b'not for the guest')
            (directory/'binary').write_bytes(b'\x00\r\n\xff')
            first = pack(b'', directory)
            self.assertEqual(first, pack(b'', directory))
            files = read_newc(gzip.decompress(first))
            self.assertEqual(files['nac/start.sh'][1], b'echo ready\n')
            self.assertEqual(files['nac/binary'][1], b'\x00\r\n\xff')
            self.assertEqual(stat.S_IMODE(files['nac/start.sh'][0]), 0o755)
            self.assertNotIn('nac/analysis.i64', files)
            self.assertNotIn('nac/analysis.id2', files)
            self.assertNotIn('nac/helper.o', files)

    def test_rejects_payload_symlink_outside_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            target = directory/'original'
            target.write_bytes(b'not followed')
            try:
                (directory/'link').symlink_to(target)
            except OSError:
                self.skipTest('Creating symlinks is unavailable on this host')
            with self.assertRaises(ValueError):
                pack(b'', directory)


if __name__ == '__main__':
    unittest.main()
