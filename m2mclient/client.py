import weakref
import logging
from threading import Event
from threading import Thread

from lomond import WebSocket

from .dispatcher import Dispatcher
from .dispatcher import PacketFormatError
from .dispatcher import expose
from .packets import M2MPacket
from .packets import PacketType
from . import errors


log = logging.getLogger('m2m')



class WebSocketThread(Thread):
    """Websocket thread."""

    def __init__(self, url, client, on_startup=None):
        super().__init__()
        self.ws = WebSocket(url)
        self._client = weakref.ref(client)
        self.on_startup = on_startup or (lambda: None)
        self.running = False
        self.ready_event = Event()
        self.error = None
        self.daemon = True

    @property
    def client(self):
        return self._client()

    def run(self):
        """Main thread loop."""
        try:
            for event in self.ws:
                if event.name == 'rejected':
                    self.error = event.reason
                elif event.name == 'disconnected':
                    if not event.graceful:
                        self.error = event.reason
                elif event.name == 'ready':
                    self.running = True
                    self.on_startup()
                    self.ready_event.set()
                elif event.name == 'binary':
                    self.on_binary(event.data)
        finally:
            self.running = False
            self.ready_event.set()

    def on_binary(self, data):
        """Called with a binary message."""
        if not self.client:
            log.warning('ws message %r ignored', data)
            return
        try:
            packet = M2MPacket.from_bytes(data)
        except PacketFormatError as packet_error:
            # We received a badly formatted packet from the server
            # Inconceivable!
            log.warning('bad packet (%s)', packet_error)
        else:
            log.debug(' <- %r', packet)
            self.client.dispatcher.dispatch_packet(packet)

    def send(self, data):
        """Send binary message (low level interface)."""
        self.ws.send_binary(data)

    def close(self):
        """Close the websocket."""
        self.ws.close()


class CommandResult(object):
    """
    A pending result that may block until a response is received from
    the server.

    """

    def __init__(self, name):
        self.name = name
        self._result = None
        self._event = Event()

    def __repr__(self):
        return "CommandResult({!r})".format(self.name)

    def set(self, result):
        """Set the result from another thread."""
        log.debug('command result %r', result)
        self._result = result
        self._event.set()

    def get(self, timeout=5):
        """Get the result or throw a CommandTimeout error.

        In normal operation this should return in less than a second.
        Timeouts could occur if the m2m server is down, overloaded, or
        otherwise fubar.
        """
        # The default timeout of 5 seconds is probably unrealistically
        # high Even under load the server response time should be
        # measured in milliseconds
        if not self._event.wait(timeout):
            raise errors.CommandTimeout('command timed out')
        if self._result is None:
            raise errors.CommandError(
                'invalid response'
            )
        if not isinstance(self._result, dict):
            raise errors.CommandFail('invalid response')
        status = self._result.get('status', 'fail')
        if status != 'ok':
            msg = self._result.get('msg', '')
            raise errors.CommandFail("{}; {}".format(status, msg))
        return self._result


class M2MClient:
    """A client for the M2M protocol."""

    def __init__(self, url, username, password, connect_wait=5):
        self.url = url
        self.username = username
        self.password = password
        self.connect_wait = connect_wait
        self._identity = None
        self.dispatcher = Dispatcher(M2MPacket, instance=self)
        self.command_id = 0
        self.command_events = {}
        self.ws = None
        self.identity_event = Event()
        self.create_ws()

    def create_ws(self):
        self.ws = WebSocketThread(
            self.url,
            self,
            on_startup=self.on_startup
        )

    def __enter__(self):
        log.debug('connecting to %s', self.url)
        self.ws.start()
        self.ws.ready_event.wait(self.connect_wait)
        if not self.ws.running:
            raise errors.ConnectionError(
                self.ws.error or 'unable to connect'
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            # Close the websocket
            self.close()
        finally:
            self.ws = None
            self.dispatcher.close()

            while self.command_events:
                command_id, result = self.command_events.popitem()
                result.set(None)

    def get_identity(self, timeout=10):
        """
        Get the client's identity.

        This may block if we haven't received a set_identity packet.
        Sending the identity is one of the first things the server does,
        so it's unlikely to block for any significant amount of time.
        The timeout is there as a precaution; we don't want to wait
        indefinitely if the server is fubar.

        """
        if not self.identity_event.wait(timeout):
            raise errors.NoIdentity(
                "the server didn't send use an identity in time"
            )
        return self._identity

    def close(self):
        """A graceful close."""
        # If everything is working, the server will kick us in a few
        # milliseconds.
        self.ws.close()

    def send(self, packet_type, *args, **kwargs):
        """Send a packet."""
        packet = M2MPacket.create(packet_type, *args, **kwargs)
        if self.ws.running:
            self.ws.send(packet.as_bytes)
            log.debug(' -> %r', packet)
        else:
            log.warning(' -> %r (server gone)', packet)

    def command(self, command_packet, *args, **kwargs):
        """
        Send a command to the server.

        Return a CommandResult object that may be waited on.
        """
        command_id = self.command_id = self.command_id + 1
        result = self.command_events[command_id] = CommandResult(command_packet)
        self.send(command_packet, command_id, *args, **kwargs)
        return result

    def on_startup(self):
        """Called on startup."""
        self.send('request_join')
        self.send(
            'request_login',
            username=self.username,
            password=self.password
        )

    def log(self, text):
        """Broadcast a log message."""
        text_bytes = text.encode()
        return self.command('command_broadcast_log', text=text_bytes)

    def add_route(self, node1, node2):
        """Create a single route."""
        identity = self.get_identity()
        result = self.command(
            "command_add_route",
            node1=node1,
            port1=-1,
            node2=node2,
            port2=-1,
            requester=identity,
            forwarded=0
        )
        return result

    def send_instruction(self, node, **params):
        """Send an instruction to the client."""
        result = self.command('command_send_instruction',
                              node=node,
                              data=params)
        return result

    def name_node(self, node, name):
        """Associate a node (UUID) with a name."""
        return self.command("command_set_name",
                            node=node,
                            name=name)

    def get_identities(self, nodes):
        """Get identities of online nodes."""
        return self.command("command_get_identities", nodes=nodes)

    def set_meta(self, device_id, key, value):
        """Set meta information associated with a device."""
        identity = self.get_identity()
        result = self.command("command_set_meta",
                              requester=identity,
                              node=device_id,
                              key=key,
                              value=value)
        return result

    def get_meta(self, device_id):
        """Get a meta dictionary associated with the device."""
        identity = self.get_identity()
        result = self.command("command_get_meta",
                              requester=identity,
                              node=device_id)
        return result

    @expose(PacketType.response)
    def on_command(self, command_id, result):
        """Handle a response to a command."""
        try:
            command_result = self.command_events.pop(command_id)
        except KeyError:
            log.error('received a response to an unknown event')
            command_result.set(None)
        else:
            command_result.set(result)

    @expose(PacketType.set_identity)
    def handle_set_identitiy(self, identity):
        """The server is informing us of our identity on the network."""
        self._identity = identity
        self.identity_event.set()

    @expose(PacketType.welcome)
    def handle_welcome(self):
        """We can now open channels."""

    @expose(PacketType.notify_login_success)
    def handle_notify_login_success(self, user: bytes.decode):
        """Logged in ok."""

    @expose(PacketType.notify_login_fail)
    def handle_notify_login_fail(self, message: bytes.decode):
        """Username or password was wrong."""
        raise errors.M2MAuthFailed(message)

    @expose(PacketType.log)
    def handle_log(self, text: bytes.decode):
        log.info('[log] %s', text)
