"""M2M Exceptions and error conditions."""

class ConnectionError(Exception):
    """Unable to connect to M2M server."""


class CommandError(Exception):
    """M2M command error base exception."""


class M2MAuthFailed(CommandError):
    """Bad username or password."""


class CommandTimeout(CommandError):
    """The M2M server didn't respond in a timely manner."""


class CommandFail(CommandError):
    """The M2M servers responded with an explicit error to a command."""


class NoIdentity(CommandError):
    """The server didn't send us the identity in time."""
