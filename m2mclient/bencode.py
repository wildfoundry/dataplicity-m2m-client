"""
Bencode codec.

Somewhat optimized over original in m2md

"""

import io
import time

from operator import itemgetter

from .lrucache import LRUCache


class EncodeError(Exception):
    """An error occurred when encoding bencode."""


class DecodeError(Exception):
    """An error occurred when decoding bencode."""


def encode(obj):
    """
    Encode data in to bencode, return bytes.

    The following objects may be encoded: int, bytes, list, dicts.

    Dict keys must be bytes, and unicode strings will be encoded in to
    utf-8.

    """
    binary = []
    append = binary.append

    def add_encode(obj):
        """Encode an object, appending bytes to `binary` list."""
        if isinstance(obj, bytes):
            append(b'%i:%b' % (len(obj), obj))
        elif isinstance(obj, str):
            obj_bytes = obj.encode('utf-8')
            append(b"%i:%b" % (len(obj_bytes), obj_bytes))
        elif isinstance(obj, int):
            append(b"i%ie" % obj)
        elif isinstance(obj, (list, tuple)):
            append(b"l")
            for item in obj:
                add_encode(item)
            append(b'e')
        elif isinstance(obj, dict):
            append(b'd')
            try:
                for key, value in sorted(obj.items(), key=itemgetter(0)):
                    append(b"%i:%b" % (len(key), key))
                    add_encode(value)
            except TypeError:
                raise EncodeError('dict keys must be bytes')
            append(b'e')
        else:
            raise EncodeError(
                'value {!r} can not be encoded in Bencode'.format(obj)
            )
    add_encode(obj)
    return b''.join(binary)


def decode(data, _cache=LRUCache(1000), make_string=bytes.decode):
    """
    Decode bencode `data` which should be a bytes object.

    Small packets are cached in an LRU cache

    """
    if data in _cache:
        return _cache[data]

    data_file = io.BytesIO(data)
    read = data_file.read

    def peek(count):
        """Read count bytes, and put the file pointer back."""
        pos = data_file.tell()
        try:
            return read(count)
        finally:
            data_file.seek(pos)
    # A byte iterator.
    iter_bytes = iter(lambda: read(1), b'')

    def _decode():
        obj_type = next(iter_bytes)
        if obj_type.isdigit():
            try:
                # Max 999,999 bytes in a bencode string
                size_bytes = obj_type + read(peek(6).index(b':'))
                if not size_bytes.isdigit():
                    raise DecodeError('illegal digits in size')
                read(1)
                return make_string(read(int(size_bytes)))
            except ValueError:
                raise DecodeError('illegal size')
        elif obj_type == b'e':
            return None
        elif obj_type == b'i':
            try:
                # Arbitrary integer (including negative)
                # max size -10**15-1 to 10**16-1
                return int(read(peek(16).index(b'e')))
            except ValueError:
                raise DecodeError('invalid integer')
            finally:
                read(1)
        elif obj_type == b'l':
            return list(iter(_decode, None))
        elif obj_type == b'd':
            return {k: _decode() for k in iter(_decode, None)}
        raise DecodeError('invalid digit')

    obj = _decode()
    if len(data) < 100:
        _cache[data] = obj
    return obj


if __name__ == '__main__':
    _data = [[1, 3, 'hello'], {b'foo': 'bar'}, b'test', 'test']
    print(repr(_data))
    b_data = encode(_data)
    print(repr(b_data))
    decoded_data = decode(b_data)
    print(repr(decoded_data))

    start = time.time()
    repeats = 100000
    for i in range(repeats):
        decoded_data = decode(b_data)
    elapsed = time.time() - start
    print("{:,.0f}ns per loop".format(elapsed / repeats * 1000000000.0))

    #decode(b'i12')
