"""
Dispatches incoming packets.

"""

import logging


class PacketFormatError(Exception):
    """The packet didn't conform to spec."""


def expose(packet_type):
    """Mark a method as a handler for a given packet type."""
    def deco(func):
        """Mark a method as a packet handler."""
        func._dispatcher_exposed = True
        func._dispatcher_packet_type = packet_type
        return func
    return deco


class Dispatcher:
    """
    Base class to dispatch to handlers for a packet.

    May also be used to dispatch to methods of another object, rather
    than a base class.

    """

    def __init__(self, packet_cls, instance=None, log=None):
        super(Dispatcher, self).__init__()
        self.log = log or logging.getLogger('dispatcher')
        self._packet_cls = packet_cls
        self._packet_handlers = {}
        self._init_dispatcher(instance or self)

    def _init_dispatcher(self, handler_instance):
        """
        Finds the methods decorated with @expose, and creates a dict
        that maps packet type on to the method.

        """
        for method_name in dir(handler_instance):
            if method_name.startswith('_'):
                continue
            method = getattr(handler_instance, method_name, None)
            if getattr(method, '_dispatcher_exposed', False):
                packet_type = method._dispatcher_packet_type
                self._packet_handlers[packet_type] = method

    def close(self):
        """Close the dispatcher (will be unusable after this call).."""
        self._packet_handlers.clear()

    def dispatch(self, packet_type, packet_body):
        """Dispatch a packet to appropriate handler."""
        if not isinstance(packet_type, int):
            raise PacketFormatError('packet type should be an int')
        packet = self._packet_cls.create(packet_type, *packet_body)
        return self.dispatch_packet(packet)

    def dispatch_packet(self, packet):
        """Dispatches an incoming packet to its handler."""
        method = self._packet_handlers.get(int(packet.type), None)

        if method is None:
            return self.on_missing_handler(packet)

        kwargs = packet.kwargs
        try:
            for name, param_callable in method.__annotations__.items():
                kwargs[name] = param_callable(kwargs[name])
        except Exception as error:
            self.log.warning('packet failed to validate')
            raise PacketFormatError(str(error))
        try:
            return method(**kwargs)
        except Exception:
            self.log.exception('error calling handler')
            raise

    def on_missing_handler(self, packet):
        """Called when no handler is available to handle `packet`."""
        self.log.warning('no handler for %r', packet.type)
