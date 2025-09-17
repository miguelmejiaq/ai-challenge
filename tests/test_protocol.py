"""
Tests for MiniTel-Lite protocol implementation.
"""

import pytest
import struct
import base64
import hashlib
from src.minitel.protocol import ProtocolFrame, ProtocolHandler, Commands
from src.minitel.exceptions import FrameDecodingError, HashValidationError


class TestProtocolFrame:
    """Test cases for ProtocolFrame class."""
    
    def test_frame_creation(self):
        """Test basic frame creation."""
        frame = ProtocolFrame(Commands.HELLO, 0)
        assert frame.cmd == Commands.HELLO
        assert frame.nonce == 0
        assert frame.payload == b""
        assert len(frame.hash) == 32  # SHA-256 hash length
    
    def test_frame_with_payload(self):
        """Test frame creation with payload."""
        payload = b"test payload"
        frame = ProtocolFrame(Commands.DUMP, 42, payload)
        assert frame.cmd == Commands.DUMP
        assert frame.nonce == 42
        assert frame.payload == payload
    
    def test_hash_calculation(self):
        """Test that hash is calculated correctly."""
        frame = ProtocolFrame(Commands.HELLO, 0)
        
        # Manually calculate expected hash
        data = struct.pack(">BI", Commands.HELLO, 0)
        expected_hash = hashlib.sha256(data).digest()
        
        assert frame.hash == expected_hash
    
    def test_frame_encoding(self):
        """Test frame encoding to wire format."""
        frame = ProtocolFrame(Commands.HELLO, 0)
        encoded = frame.encode()
        
        # Check that we have length prefix
        assert len(encoded) >= 2
        
        # Extract length
        length = struct.unpack(">H", encoded[:2])[0]
        
        # Check that the rest is Base64 encoded data
        b64_data = encoded[2:2 + length]
        assert len(b64_data) == length
        
        # Should be valid Base64
        try:
            base64.b64decode(b64_data)
        except Exception:
            pytest.fail("Encoded data is not valid Base64")
    
    def test_frame_decode_roundtrip(self):
        """Test that encoding and decoding produces the same frame."""
        original = ProtocolFrame(Commands.DUMP, 123, b"test data")
        encoded = original.encode()
        decoded = ProtocolFrame.decode(encoded)
        
        assert decoded.cmd == original.cmd
        assert decoded.nonce == original.nonce
        assert decoded.payload == original.payload
        assert decoded.hash == original.hash
    
    def test_decode_invalid_length(self):
        """Test decoding with invalid length prefix."""
        # Too short for length prefix
        with pytest.raises(FrameDecodingError):
            ProtocolFrame.decode(b"x")
        
        # Length longer than available data
        invalid_data = struct.pack(">H", 1000) + b"short"
        with pytest.raises(FrameDecodingError):
            ProtocolFrame.decode(invalid_data)
    
    def test_decode_invalid_base64(self):
        """Test decoding with invalid Base64 data."""
        # Valid length prefix but invalid Base64
        invalid_data = struct.pack(">H", 4) + b"!@#$"
        with pytest.raises(FrameDecodingError):
            ProtocolFrame.decode(invalid_data)
    
    def test_decode_too_short_binary(self):
        """Test decoding with binary frame too short."""
        # Valid Base64 but too short binary frame
        short_binary = b"x" * 10  # Less than minimum 37 bytes
        b64_data = base64.b64encode(short_binary)
        data = struct.pack(">H", len(b64_data)) + b64_data
        
        with pytest.raises(FrameDecodingError):
            ProtocolFrame.decode(data)
    
    def test_decode_invalid_hash(self):
        """Test decoding with invalid hash."""
        # Create a valid frame
        frame = ProtocolFrame(Commands.HELLO, 0)
        encoded = frame.encode()
        
        # Decode to get the binary frame
        length = struct.unpack(">H", encoded[:2])[0]
        b64_data = encoded[2:2 + length]
        binary_frame = base64.b64decode(b64_data)
        
        # Corrupt the hash (last 32 bytes)
        corrupted_binary = binary_frame[:-32] + b"x" * 32
        corrupted_b64 = base64.b64encode(corrupted_binary)
        corrupted_data = struct.pack(">H", len(corrupted_b64)) + corrupted_b64
        
        with pytest.raises(HashValidationError):
            ProtocolFrame.decode(corrupted_data)
    
    def test_frame_repr(self):
        """Test frame string representation."""
        frame = ProtocolFrame(Commands.HELLO, 42, b"test")
        repr_str = repr(frame)
        
        assert "ProtocolFrame" in repr_str
        assert "0x01" in repr_str  # HELLO command
        assert "42" in repr_str    # nonce
        assert "4" in repr_str     # payload length


class TestProtocolHandler:
    """Test cases for ProtocolHandler class."""
    
    def test_handler_initialization(self):
        """Test handler initialization."""
        handler = ProtocolHandler()
        assert handler.client_nonce == 0
        assert handler.server_nonce == 1
    
    def test_create_hello_frame(self):
        """Test HELLO frame creation."""
        handler = ProtocolHandler()
        frame = handler.create_hello_frame()
        
        assert frame.cmd == Commands.HELLO
        assert frame.nonce == 0
        assert frame.payload == b""
        assert handler.client_nonce == 2  # Should increment
    
    def test_create_dump_frame(self):
        """Test DUMP frame creation."""
        handler = ProtocolHandler()
        # First call to advance nonce
        handler.create_hello_frame()
        
        frame = handler.create_dump_frame()
        assert frame.cmd == Commands.DUMP
        assert frame.nonce == 2
        assert handler.client_nonce == 4
    
    def test_create_stop_frame(self):
        """Test STOP_CMD frame creation."""
        handler = ProtocolHandler()
        frame = handler.create_stop_frame()
        
        assert frame.cmd == Commands.STOP_CMD
        assert frame.nonce == 0
        assert handler.client_nonce == 2
    
    def test_nonce_sequence(self):
        """Test nonce sequence management."""
        handler = ProtocolHandler()
        
        # Client nonces should increment by 2
        frame1 = handler.create_hello_frame()
        frame2 = handler.create_dump_frame()
        frame3 = handler.create_stop_frame()
        
        assert frame1.nonce == 0
        assert frame2.nonce == 2
        assert frame3.nonce == 4
    
    def test_validate_response_nonce_valid(self):
        """Test valid response nonce validation."""
        handler = ProtocolHandler()
        
        # Server should respond with nonce 1
        response = ProtocolFrame(Commands.HELLO_ACK, 1)
        assert handler.validate_response_nonce(response) is True
        assert handler.server_nonce == 3  # Should increment by 2
    
    def test_validate_response_nonce_invalid(self):
        """Test invalid response nonce validation."""
        handler = ProtocolHandler()
        
        # Wrong nonce
        response = ProtocolFrame(Commands.HELLO_ACK, 5)
        assert handler.validate_response_nonce(response) is False
        assert handler.server_nonce == 1  # Should not change
    
    def test_reset_nonces(self):
        """Test nonce reset functionality."""
        handler = ProtocolHandler()
        
        # Advance nonces
        handler.create_hello_frame()
        handler.create_dump_frame()
        
        # Reset
        handler.reset_nonces()
        assert handler.client_nonce == 0
        assert handler.server_nonce == 1
    
    def test_get_command_name(self):
        """Test command name lookup."""
        handler = ProtocolHandler()
        
        assert handler.get_command_name(Commands.HELLO) == "HELLO"
        assert handler.get_command_name(Commands.DUMP) == "DUMP"
        assert handler.get_command_name(Commands.STOP_CMD) == "STOP_CMD"
        assert handler.get_command_name(Commands.HELLO_ACK) == "HELLO_ACK"
        assert handler.get_command_name(Commands.DUMP_FAILED) == "DUMP_FAILED"
        assert handler.get_command_name(Commands.DUMP_OK) == "DUMP_OK"
        assert handler.get_command_name(Commands.STOP_OK) == "STOP_OK"
        
        # Unknown command
        assert "UNKNOWN_0xff" in handler.get_command_name(0xFF)


class TestCommands:
    """Test command constants."""
    
    def test_command_values(self):
        """Test that command values match specification."""
        assert Commands.HELLO == 0x01
        assert Commands.DUMP == 0x02
        assert Commands.STOP_CMD == 0x04
        
        assert Commands.HELLO_ACK == 0x81
        assert Commands.DUMP_FAILED == 0x82
        assert Commands.DUMP_OK == 0x83
        assert Commands.STOP_OK == 0x84


class TestProtocolIntegration:
    """Integration tests for protocol components."""
    
    def test_full_protocol_sequence(self):
        """Test a complete protocol sequence."""
        handler = ProtocolHandler()
        
        # Client sends HELLO
        hello_frame = handler.create_hello_frame()
        hello_encoded = hello_frame.encode()
        hello_decoded = ProtocolFrame.decode(hello_encoded)
        
        assert hello_decoded.cmd == Commands.HELLO
        assert hello_decoded.nonce == 0
        
        # Server responds with HELLO_ACK
        hello_ack = ProtocolFrame(Commands.HELLO_ACK, 1)
        assert handler.validate_response_nonce(hello_ack)
        
        # Client sends first DUMP
        dump1_frame = handler.create_dump_frame()
        assert dump1_frame.nonce == 2
        
        # Server responds with DUMP_FAILED
        dump1_response = ProtocolFrame(Commands.DUMP_FAILED, 3)
        assert handler.validate_response_nonce(dump1_response)
        
        # Client sends second DUMP
        dump2_frame = handler.create_dump_frame()
        assert dump2_frame.nonce == 4
        
        # Server responds with DUMP_OK and override code
        override_code = b"JOSHUA_OVERRIDE_1983"
        dump2_response = ProtocolFrame(Commands.DUMP_OK, 5, override_code)
        assert handler.validate_response_nonce(dump2_response)
        assert dump2_response.payload == override_code
        
        # Client sends STOP
        stop_frame = handler.create_stop_frame()
        assert stop_frame.nonce == 6
        
        # Server responds with STOP_OK
        stop_response = ProtocolFrame(Commands.STOP_OK, 7)
        assert handler.validate_response_nonce(stop_response)
    
    def test_protocol_with_large_payload(self):
        """Test protocol with large payload."""
        large_payload = b"x" * 1000
        frame = ProtocolFrame(Commands.DUMP_OK, 42, large_payload)
        
        encoded = frame.encode()
        decoded = ProtocolFrame.decode(encoded)
        
        assert decoded.payload == large_payload
        assert decoded.cmd == Commands.DUMP_OK
        assert decoded.nonce == 42
    
    def test_protocol_with_unicode_payload(self):
        """Test protocol with Unicode payload."""
        unicode_text = "JOSHUA_OVERRIDE_1983_🚀"
        payload = unicode_text.encode('utf-8')
        
        frame = ProtocolFrame(Commands.DUMP_OK, 42, payload)
        encoded = frame.encode()
        decoded = ProtocolFrame.decode(encoded)
        
        assert decoded.payload == payload
        assert decoded.payload.decode('utf-8') == unicode_text
