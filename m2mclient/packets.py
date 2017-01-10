"""
Packets defined in the M2M protocol.

"""

from enum import IntEnum, unique

from .packetbase import PacketBase


@unique
class PacketType(IntEnum):
    """The top level packet type."""

    # Null packet, does nothing
    null = 0

    # Client sends this to join the server
    request_join = 1

    # Client sends this to re-connect
    request_identify = 2

    # Sent by the server if request_join or request_identity was
    # successful
    welcome = 3

    # Textual information for developer
    log = 4

    # Send a packet to another node
    request_send = 5

    # Incoming data from the server
    route = 6

    # Send the packet back
    ping = 7

    # A ping return
    pong = 8

    # Set the clients identity
    set_identity = 9

    # Open a channel
    request_open = 10

    # Close a channel
    request_close = 11

    # Close all channels
    request_close_all = 12

    # Keep alive packet
    keep_alive = 13

    # Sent by the server to notify a client that a port has been opened
    notify_open = 14

    # Request login for privileged accounts
    request_login = 15

    instruction = 16

    notify_login_success = 17

    notify_login_fail = 18

    # Notify the client that a port has closed
    notify_close = 19

    # Client wishes to disconnect
    request_leave = 20

    # An out of band route control packet
    route_control = 21

    # Send a route_control packet
    request_send_control = 22

    # Notify client of name # ADDDED 15/11/16
    notify_name = 23

    response = 100
    command_add_route = 101
    command_send_instruction = 102
    command_log = 103
    command_broadcast_log = 104
    #command_forward = 105
    command_set_name = 106
    command_check_nodes = 107
    command_get_identities = 108
    command_set_auth = 109

    # Associate meta info with a node
    command_set_meta = 110

    # Get Meta info
    command_get_meta = 111

    # Deprecated peer packets 200-299
    #peer_add_route = 200
    #peer_forward = 201
    #peer_notify_disconnect = 202
    #peer_notify_name = 203
    #peer_close_port = 204


# ------------------------------------------------------------
# Packet classes
# ------------------------------------------------------------

class M2MPacket(PacketBase):
    """Base class, not a real packet."""

    @classmethod
    def process_packet_type(self, packet_type):
        """Enable the use of strings to identify packets."""
        if isinstance(packet_type, str):
            return PacketType[packet_type].value
        return int(packet_type)

    @classmethod
    def peek_type(cls, packet_bytes):
        """
        Get the packet type, without fully decoding the entire packet.

        Return None if the packet was invalid.

        """
        if packet_bytes.startswith(b'li'):
            packet_type, terminator, _remainder = packet_bytes[2:8].partition(b'e')
            if terminator and packet_type.isdigit():
                return int(packet_type)

    @classmethod
    def summarize(cls, data):
        """Abbreviate large bytes attributes."""
        if isinstance(data, bytes) and len(data) > 32:
            return "<{} bytes>".format(len(data))
        return repr(data)


class Null(M2MPacket):
    """Probably never sent, this may be used as a sentinel at some point."""

    type = PacketType.null
    as_bytes = b'li0ee'


class RequestJoin(M2MPacket):
    """Client requests joining the server."""

    type = PacketType.request_join


class RequestIdentify(M2MPacket):
    """Client requests joining the server with a particular identity."""

    type = PacketType.request_identify
    attributes = [('uuid', bytes)]


class Welcome(M2MPacket):
    """Send to the client when an identity has been recorded."""

    type = PacketType.welcome
    as_bytes = b'li3ee'


class Log(M2MPacket):
    """Log information, client may ignore."""

    type = PacketType.log
    attributes = [
        ('text', bytes)
    ]

    @property
    def as_bytes(self):
        return b'li4e%i:%se' % (len(self.text), self.text)


class KeepAlive(M2MPacket):
    """Keep alive packet."""

    type = PacketType.keep_alive


class RequestSend(M2MPacket):
    """Request to send data to a connection."""

    type = PacketType.request_send
    attributes = [
        ('port', int),
        ('data', bytes)
    ]

    def __repr__(self):
        """Avoid logging large packets."""
        fmt = "{}(port={}, data={})"
        return fmt.format(
            self.__class__.__name__,
            self.port,
            self.summarize(self.data)
        )


class NotifyName(M2MPacket):
    """Notify a client of their name."""

    type = PacketType.notify_name
    attributes = [
        ('name', bytes)
    ]

class Route(M2MPacket):
    """Route data."""

    type = PacketType.route
    attributes = [
        ('port', int),
        ('data', bytes)
    ]

    def __repr__(self):
        """Avoid logging large packets."""
        fmt = "{}(port={}, data={})"
        return fmt.format(
            self.__class__.__name__,
            self.port,
            self.summarize(self.data)
        )

    @property
    def as_bytes(self):
        """Shortcut encoding for frequently used packet."""
        # Save a few nano-seconds here and there, and soon you have a millisecond!
        return b"li6ei%ie%i:%se" % (self.port, len(self.data), self.data)


class RouteControl(M2MPacket):
    """Out of band data."""

    type = PacketType.route_control
    attributes = [
        ('port', int),
        ('data', bytes)
    ]


class RequestSendControl(M2MPacket):
    """Request to send data to a connection."""

    type = PacketType.request_send_control
    attributes = [
        ('port', int),
        ('data', bytes)
    ]


class Ping(M2MPacket):
    """Ping packet to check connection."""

    type = PacketType.ping
    attributes = [
        ('data', bytes)
    ]

    @property
    def as_bytes(self):
        """Shortcut encoding."""
        return b'li7e%i:%se' % (len(self.data), self.data)


class Pong(M2MPacket):
    """Response to Ping packet."""

    type = PacketType.pong
    attributes = [
        ('data', bytes)
    ]


class SetIdentity(M2MPacket):
    """Inform a client of their identity."""

    type = PacketType.set_identity
    attributes = [
        ('identity', bytes)
    ]

    @property
    def as_bytes(self):
        """
        Shortcut encode.
        """
        return b'li9e%i:%se' % (len(self.identity), self.identity)


class NotifyOpen(M2MPacket):
    """Let the client know a channel was opened."""

    type = PacketType.notify_open
    attributes = [('port', int)]

    @property
    def as_bytes(self):
        """
        Encoding shortcut because we can send a lot of these in quick
        succession.
        """
        return b'li14ei%iee' % self.port


class RequestLogin(M2MPacket):
    """Login for extra privileges."""

    type = PacketType.request_login
    attributes = [
        ('username', bytes),
        ('password', bytes)
    ]


class NotifyLoginSuccess(M2MPacket):
    """Login success."""

    type = PacketType.notify_login_success
    attributes = [
        ('user', bytes)
    ]


class NotifyLoginFail(M2MPacket):
    """Login failed."""

    type = PacketType.notify_login_fail
    attributes = [
        ('message', bytes)
    ]


class NotifyClose(M2MPacket):
    """channel was closed."""

    type = PacketType.notify_close
    attributes = [
        ('port', int)
    ]

    @property
    def as_bytes(self):
        """
        Encoding shortcut because we can send a lot of these in quick
        succession.
        """
        return b'li19ei%iee' % self.port


class RequestClose(M2MPacket):
    """Ask server to close a port."""

    type = PacketType.request_close
    attributes = [
        ('port', int)
    ]


class RequestLeave(M2MPacket):
    """Polite way of disconnecting from the server."""

    type = PacketType.request_leave


class Instruction(M2MPacket):
    """
    Send an 'instruction' which is an application define packet not send
    through a channel.
    """

    type = PacketType.instruction
    attributes = [
        ('sender', bytes),
        ('data', dict)
    ]


class CommandResponse(M2MPacket):
    """Sent in response to a command."""

    type = PacketType.response
    attributes = [
        ('command_id', int),
        ('result', dict)
    ]


class CommandAddRoute(M2MPacket):
    """Command the server to generate a route from uuid1 to uuid2."""

    type = PacketType.command_add_route
    attributes = [
        ('command_id', int),
        ('node1', bytes),
        ('port1', int),
        ('node2', bytes),
        ('port2', int),
        ('requester', bytes),
        ('forwarded', int)
    ]


class CommandSendInstruction(M2MPacket):
    """Send an instruction to a client."""

    type = PacketType.command_send_instruction
    attributes = [
        ('command_id', int),
        ('node', bytes),
        ('data', dict)
    ]


class CommandLog(M2MPacket):
    """Send a message to be written to the logs."""

    type = PacketType.command_log
    attributes = [
        ('command_id', int),
        ('node', bytes),
        ('text', bytes)
    ]


class CommandBroadcastLog(M2MPacket):
    """Send a message to all clients."""

    # Probably just for debug. Not sure what would happen with 1000s of clients
    type = PacketType.command_broadcast_log
    attributes = [
        ('command_id', int),
        ('text', bytes)
    ]


class CommandSetName(M2MPacket):
    """Set an alternative name of a node."""

    type = PacketType.command_set_name
    attributes = [
        ('command_id', int),
        ('node', bytes),
        ('name', bytes)
    ]


class CommandCheckNodes(M2MPacket):
    """Get identities from a list of names."""

    type = PacketType.command_check_nodes
    attributes = [
        ('command_id', int),
        ('nodes', list)
    ]


class CommandGetIdentities(M2MPacket):
    """Get identities from a list of names."""

    type = PacketType.command_get_identities
    attributes = [
        ('command_id', int),
        ('nodes', list)
    ]


class CommandSetAuth(M2MPacket):
    """Set auth information."""

    type = PacketType.command_set_auth
    attributes = [
        ('command_id', int),
        ('expire', int),
        ('value', bytes)
    ]


class CommandSetMeta(M2MPacket):
    """Set a meta key/value associated with a node."""

    type = PacketType.command_set_meta
    attributes = [
        ('command_id', int),
        ('requester', bytes),
        ('node', bytes),
        ('key', bytes),
        ('value', bytes)
    ]


class CommandGetMeta(M2MPacket):
    """Get a dictionary of meta values associated with a node."""

    type = PacketType.command_get_meta
    attributes = [
        ('command_id', int),
        ('requester', bytes),
        ('node', bytes)
    ]


if __name__ == "__main__":
    ping_packet = PingPacket(data=b'test')
    print(ping_packet)
    print(ping_packet.as_bytes)
    print(PingPacket.from_bytes(ping_packet.as_bytes))
    print(M2MPacket.create('ping', data=b"test2"))
    print(PingPacket.from_bytes(ping_packet.as_bytes))
