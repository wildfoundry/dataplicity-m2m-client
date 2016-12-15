"""
Manages packet structures.

Packets are encoded as a bencode list as follows:

[<int type>, <payload>]

Where type is an integer that identifies the type of the packet, and
payload is anything that may be encoded in bencode. The payload will
be extracted and used as parameters to the handler method.

"""

from .import bencode

class PacketError(Exception):
    """A packet format error."""


class PacketFormatError(PacketError):
    """Packet is badly formatted."""


class UnknownPacketError(PacketError):
    """A packet we don't know how to handle."""


class PacketMeta(type):
    """Maintains a registry of packet classes."""

    def __new__(mcs, name, bases, attrs):
        packet_cls = super(PacketMeta, mcs).__new__(mcs, name, bases, attrs)
        if bases and packet_cls.type >= 0:
            is_registered = packet_cls.type in packet_cls.registry
            assert not is_registered,\
                "packet type {!r} has been registered".format(packet_cls)
            packet_cls.registry[packet_cls.type] = packet_cls
        return packet_cls


class PacketBase(metaclass=PacketMeta):
    """Metaclass to register packet type."""

    registry = {}
    attributes = []

    # Packet type
    type = -1  # Indicates it is a base packet class

    # Named attributes, if using default init_data
    def __init__(self, *args, **kwargs):
        params = {
            name: arg
            for arg, (name, _type) in zip(args, self.attributes)
        }
        params.update(kwargs)

        for name, _type in self.attributes:
            if name not in params:
                raise PacketFormatError(
                    "missing attribute '{}', in {!r}".format(name, self)
                )
            value = params[name]
            if isinstance(value, str):
                params[name] = value = value.encode('utf-8', 'xmlcharreplace')
            if not isinstance(value, _type):
                _fmt = "{} parameter '{}' should be a {!r} (not {!r})"
                raise PacketFormatError(
                    _fmt.format(self, name, _type, value)
                )
        self.__dict__.update(params)

    def __repr__(self):
        data = {}
        for attrib_name, _ in self.attributes:
            try:
                data[attrib_name] = getattr(self, attrib_name)
            except AttributeError:
                continue
        params = ', '.join(
            "{}={!r}".format(k, v if k != 'password' else '********')
            for k, v in data.items()
        )
        return "{}({})".format(self.__class__.__name__, params)

    @classmethod
    def process_packet_type(cls, packet_type):
        """
        Convert packet type value in to an integer.

        Allows derived classes to use packet types in other formats.

        """
        return packet_type

    @classmethod
    def create(cls, packet_type, *args, **kwargs):
        """Dynamically create a packet from its type and parameters."""
        packet_cls = cls.registry.get(cls.process_packet_type(packet_type))
        if packet_cls is None:
            raise ValueError('no packet type {}'.format(packet_type))
        return packet_cls(*args, **kwargs)

    @classmethod
    def from_bytes(cls, packet_bytes):
        """Return a packet from a bytes string."""
        if not packet_bytes.startswith(b'l'):
            raise PacketFormatError('packet must be a list')

        try:
            packet_data = bencode.decode(packet_bytes)
        except bencode.DecodeError as error:
            raise PacketFormatError(
                'packet is badly formatted ({})'.format(error)
            )

        packet_type, *packet_body = packet_data
        if not isinstance(packet_type, int):
            raise PacketFormatError('first value must be an integer')
        try:
            packet_cls = cls.registry[packet_type]
        except KeyError:
            raise UnknownPacketError(
                "unknown packet ({!r})".format(packet_type)
            )
        return packet_cls(*packet_body)

    @property
    def kwargs(self):
        """Keyword args to be used to invoke handler."""
        return {
            name: getattr(self, name)
            for name, _ in self.attributes
        }

    @property
    def as_bytes(self):
        """Encode the packet as bytes."""
        packet_bytes = bencode.encode(
            [int(self.type)] +
            [getattr(self, name) for name, _type in self.attributes]
        )
        return packet_bytes
