"""
Custom exceptions for MiniTel-Lite protocol implementation.
"""


class MiniTelError(Exception):
    """Base exception for all MiniTel-Lite related errors."""
    pass


class ProtocolError(MiniTelError):
    """Raised when protocol violations occur."""
    pass


class ConnectionError(MiniTelError):
    """Raised when connection issues occur."""
    pass


class AuthenticationError(MiniTelError):
    """Raised when authentication fails."""
    pass


class NonceError(ProtocolError):
    """Raised when nonce sequence validation fails."""
    pass


class HashValidationError(ProtocolError):
    """Raised when frame hash validation fails."""
    pass


class FrameDecodingError(ProtocolError):
    """Raised when frame decoding fails."""
    pass


class ServerDisconnectionError(ConnectionError):
    """Raised when server disconnects unexpectedly."""
    pass


class TimeoutError(ConnectionError):
    """Raised when connection or operation times out."""
    pass
