from __future__ import print_function
from __future__ import unicode_literals

"""
Encode / Decode Bencode (http://en.wikipedia.org/wiki/Bencode)

"""

import io

from six import (PY3,
                 integer_types,
                 text_type)


class EncodeError(ValueError):
    """Failed to encode value in to bencode."""


class DecodeError(ValueError):
    """Error raised when decoding invalid bencode."""


def encode(obj):
    """Encode to Bencode, return byte."""
    binary = []
    append = binary.append

    if PY3:
        def int2ascii(n):
            """Encode an integer as decimal in to bytes."""
            return str(n).encode('ascii')
    else:
        def int2ascii(n):
            """Encode an integer as decimal in to bytes."""
            return bytes(n)

    def add_encode(obj):
        if isinstance(obj, bytes):
            append(int2ascii(len(obj)))
            append(b':')
            append(obj)
        elif isinstance(obj, text_type):
            obj = obj.encode('utf-8')
            append(int2ascii(len(obj)))
            append(b':')
            append(obj)
        elif isinstance(obj, integer_types):
            append(b'i')
            append(int2ascii(obj))
            append(b'e')
        elif isinstance(obj, (list, tuple)):
            append(b"l")
            for item in obj:
                add_encode(item)
            append(b'e')
        elif isinstance(obj, dict):
            append(b'd')
            keys = sorted(obj.keys())
            for k in keys:
                if not isinstance(k, bytes):
                    raise EncodeError("dict keys must be bytes")
                add_encode(k)
                add_encode(obj[k])
            append(b'e')
        else:
            raise EncodeError(
                'value {!r} can not be encoded in Bencode'.format(obj)
            )

    add_encode(obj)
    return b''.join(binary)


def decode(data):
    """Decode Bencode, return an object."""
    assert isinstance(data, bytes), "decode takes bytes"
    return _decode(io.BytesIO(data).read)


def _decode(read):
    """Decode bencode.

    The `read` parameter should be a callable that returns number of
    bytes.
    """
    obj_type = read(1)
    if obj_type == b'e':
        return None
    if obj_type == b'i':
        number_bytes = b''
        while 1:
            c = read(1)
            if not c.isdigit():
                if c != b'e':
                    raise DecodeError('illegal digit in size')
                break
            number_bytes += c
        number = int(number_bytes)
        return number
    elif obj_type == b'l':
        l = []
        while 1:
            i = _decode(read)
            if i is None:
                break
            l.append(i)
        return l
    elif obj_type == b'd':
        kv = []
        while 1:
            k = _decode(read)
            if k is None:
                break
            v = _decode(read)
            kv.append((k, v))
        return dict(kv)
    else:
        size_bytes = obj_type
        while 1:
            c = read(1)
            if c == b':':
                break
            size_bytes += c
        size = int(size_bytes)
        return read(size)


if __name__ == '__main__':

    import unittest

    class Testbenstring(unittest.TestCase):

        TESTS = [
            (
                b"benstring module by Will McGugan".split(b' '),
                b"l9:benstring6:module2:by4:Will7:McGugane"
            ),
            (
                b'',
                b'0:'
            ),
            (
                5,
                b'i5e'
            ),
            (
                b'bytes',
                b'5:bytes'
            ),
            (
                "unicode",
                b"7:unicode"
            ),
            (
                {b'foo': b'bar'},
                b'd3:foo3:bare'
            ),
        ]

        def test_decoder(self):
            for plain, encoded in self.TESTS:
                self.assertEqual(encode(plain), encoded)

        def test_encoder(self):
            for plain, encoded in self.TESTS:
                if isinstance(plain, text_type):
                    plain = plain.encode('utf-8')
                self.assertEqual(decode(encoded), plain)

    unittest.main()
