"""
MiniTel-Lite Protocol v3.0 implementation.

This module handles the encoding and decoding of MiniTel-Lite protocol frames
according to the v3.0 specification.
"""

import base64
import hashlib
import struct
from typing import Tuple, Optional
from .exceptions import FrameDecodingError, HashValidationError


# Protocol Commands
class Commands:
    HELLO = 0x01
    DUMP = 0x02
    STOP_CMD = 0x04
    
    # Response commands
    HELLO_ACK = 0x81
    DUMP_FAILED = 0x82
    DUMP_OK = 0x83
    STOP_OK = 0x84


class ProtocolFrame:
    """
    Represents a MiniTel-Lite protocol frame.
    
    Frame Format:
    LEN (2 bytes, big-endian) | DATA_B64 (Base64 encoded)
    
    Binary Frame (after Base64 decoding):
    CMD (1 byte) | NONCE (4 bytes, big-endian) | PAYLOAD (variable) | HASH (32 bytes SHA-256)
    """
    
    def __init__(self, cmd: int, nonce: int, payload: bytes = b""):
        self.cmd = cmd
        self.nonce = nonce
        self.payload = payload
        self.hash = self._calculate_hash()
    
    def _calculate_hash(self) -> bytes:
        """Calculate SHA-256 hash of CMD + NONCE + PAYLOAD."""
        data = struct.pack(">BI", self.cmd, self.nonce) + self.payload
        return hashlib.sha256(data).digest()
    
    def encode(self) -> bytes:
        """
        Encode the frame according to MiniTel-Lite v3.0 specification.
        
        Returns:
            bytes: Encoded frame ready for transmission
        """
        # Build binary frame: CMD + NONCE + PAYLOAD + HASH
        binary_frame = (
            struct.pack(">BI", self.cmd, self.nonce) +
            self.payload +
            self.hash
        )
        
        # Base64 encode the binary frame
        b64_data = base64.b64encode(binary_frame)
        
        # Prepend length (2 bytes, big-endian)
        length = len(b64_data)
        return struct.pack(">H", length) + b64_data
    
    @classmethod
    def decode(cls, data: bytes) -> "ProtocolFrame":
        """
        Decode a frame from wire format.
        
        Args:
            data: Raw bytes from network
            
        Returns:
            ProtocolFrame: Decoded frame
            
        Raises:
            FrameDecodingError: If frame is malformed
            HashValidationError: If hash validation fails
        """
        try:
            # Read length prefix (2 bytes, big-endian)
            if len(data) < 2:
                raise FrameDecodingError("Frame too short for length prefix")
            
            length = struct.unpack(">H", data[:2])[0]
            
            # Read Base64 data
            if len(data) < 2 + length:
                raise FrameDecodingError("Frame shorter than declared length")
            
            b64_data = data[2:2 + length]
            
            # Base64 decode
            try:
                binary_frame = base64.b64decode(b64_data)
            except Exception as e:
                raise FrameDecodingError(f"Invalid Base64 data: {e}")
            
            # Parse binary frame
            if len(binary_frame) < 37:  # 1 + 4 + 32 minimum
                raise FrameDecodingError("Binary frame too short")
            
            # Extract components
            cmd = binary_frame[0]
            nonce = struct.unpack(">I", binary_frame[1:5])[0]
            payload = binary_frame[5:-32]
            received_hash = binary_frame[-32:]
            
            # Create frame and validate hash
            frame = cls(cmd, nonce, payload)
            if frame.hash != received_hash:
                raise HashValidationError("Frame hash validation failed")
            
            return frame
            
        except (struct.error, IndexError) as e:
            raise FrameDecodingError(f"Frame parsing error: {e}")
    
    def __repr__(self) -> str:
        return f"ProtocolFrame(cmd=0x{self.cmd:02x}, nonce={self.nonce}, payload_len={len(self.payload)})"


class ProtocolHandler:
    """
    Handles MiniTel-Lite protocol operations and nonce management.
    """
    
    def __init__(self):
        self.client_nonce = 0
        self.server_nonce = 1
    
    def create_hello_frame(self) -> ProtocolFrame:
        """Create a HELLO command frame."""
        frame = ProtocolFrame(Commands.HELLO, self.client_nonce)
        self.client_nonce += 2  # Client increments by 2 for next message
        return frame
    
    def create_dump_frame(self) -> ProtocolFrame:
        """Create a DUMP command frame."""
        frame = ProtocolFrame(Commands.DUMP, self.client_nonce)
        self.client_nonce += 2  # Client increments by 2 for next message
        return frame
    
    def create_stop_frame(self) -> ProtocolFrame:
        """Create a STOP_CMD frame."""
        frame = ProtocolFrame(Commands.STOP_CMD, self.client_nonce)
        self.client_nonce += 2  # Client increments by 2 for next message
        return frame
    
    def validate_response_nonce(self, frame: ProtocolFrame) -> bool:
        """
        Validate that the response nonce is correct.
        
        Args:
            frame: Received frame from server
            
        Returns:
            bool: True if nonce is valid
        """
        expected_nonce = self.server_nonce
        if frame.nonce == expected_nonce:
            self.server_nonce += 2  # Server increments by 2 for next response
            return True
        return False
    
    def reset_nonces(self):
        """Reset nonce counters for new connection."""
        self.client_nonce = 0
        self.server_nonce = 1
    
    def get_command_name(self, cmd: int) -> str:
        """Get human-readable command name."""
        command_names = {
            Commands.HELLO: "HELLO",
            Commands.DUMP: "DUMP",
            Commands.STOP_CMD: "STOP_CMD",
            Commands.HELLO_ACK: "HELLO_ACK",
            Commands.DUMP_FAILED: "DUMP_FAILED",
            Commands.DUMP_OK: "DUMP_OK",
            Commands.STOP_OK: "STOP_OK",
        }
        return command_names.get(cmd, f"UNKNOWN_0x{cmd:02x}")
