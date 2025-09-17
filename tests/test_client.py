"""
Tests for MiniTel-Lite client implementation.
"""

import pytest
import socket
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from src.minitel.client import MiniTelClient
from src.minitel.protocol import ProtocolFrame, Commands
from src.minitel.exceptions import (
    ConnectionError, AuthenticationError, NonceError, 
    ServerDisconnectionError, TimeoutError, MiniTelError
)


class MockSocket:
    """Mock socket for testing."""
    
    def __init__(self):
        self.sent_data = []
        self.receive_data = []
        self.receive_index = 0
        self.connected = False
        self.timeout = None
        self.should_raise_on_connect = None
        self.should_raise_on_send = None
        self.should_raise_on_recv = None
    
    def connect(self, address):
        if self.should_raise_on_connect:
            raise self.should_raise_on_connect
        self.connected = True
    
    def settimeout(self, timeout):
        self.timeout = timeout
    
    def sendall(self, data):
        if self.should_raise_on_send:
            raise self.should_raise_on_send
        self.sent_data.append(data)
    
    def recv(self, size):
        if self.should_raise_on_recv:
            raise self.should_raise_on_recv
        
        if self.receive_index >= len(self.receive_data):
            return socket.timeout("No more data")  # Simulate disconnection
        
        data = self.receive_data[self.receive_index]
        self.receive_index += 1
        
        if isinstance(data, Exception):
            raise data
        
        return data[:size]  # Return up to requested size
    
    def close(self):
        self.connected = False
    
    def add_response(self, frame_or_data):
        """Add a response frame or raw data to be returned by recv."""
        if isinstance(frame_or_data, ProtocolFrame):
            encoded = frame_or_data.encode()
            length_bytes = encoded[:2]
            frame_data = encoded[2:]
            self.receive_data.append(length_bytes)
            self.receive_data.append(frame_data)
        else:
            self.receive_data.append(frame_or_data)


class TestMiniTelClient:
    """Test cases for MiniTelClient class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_socket = MockSocket()
        self.client = MiniTelClient("test.example.com", 1234, timeout=1.0)
    
    @patch('socket.socket')
    def test_client_initialization(self, mock_socket_class):
        """Test client initialization."""
        client = MiniTelClient("localhost", 8080, timeout=5.0, record_session=True)
        
        assert client.host == "localhost"
        assert client.port == 8080
        assert client.timeout == 5.0
        assert client.session_recorder is not None
        assert client.socket is None
        assert client.override_code is None
    
    @patch('socket.socket')
    def test_connect_success(self, mock_socket_class):
        """Test successful connection."""
        mock_socket_class.return_value = self.mock_socket
        
        self.client.connect()
        
        assert self.mock_socket.connected
        assert self.mock_socket.timeout == 1.0
        assert self.client.socket == self.mock_socket
    
    @patch('socket.socket')
    def test_connect_failure(self, mock_socket_class):
        """Test connection failure."""
        self.mock_socket.should_raise_on_connect = socket.error("Connection refused")
        mock_socket_class.return_value = self.mock_socket
        
        with pytest.raises(ConnectionError):
            self.client.connect()
    
    def test_disconnect(self):
        """Test disconnection."""
        self.client.socket = self.mock_socket
        self.mock_socket.connected = True
        
        self.client.disconnect()
        
        assert not self.mock_socket.connected
        assert self.client.socket is None
    
    @patch('socket.socket')
    def test_send_frame_success(self, mock_socket_class):
        """Test successful frame sending."""
        mock_socket_class.return_value = self.mock_socket
        self.client.connect()
        
        frame = ProtocolFrame(Commands.HELLO, 0)
        self.client._send_frame(frame)
        
        assert len(self.mock_socket.sent_data) == 1
        assert self.mock_socket.sent_data[0] == frame.encode()
    
    def test_send_frame_not_connected(self):
        """Test sending frame when not connected."""
        frame = ProtocolFrame(Commands.HELLO, 0)
        
        with pytest.raises(ConnectionError, match="Not connected"):
            self.client._send_frame(frame)
    
    @patch('socket.socket')
    def test_send_frame_socket_error(self, mock_socket_class):
        """Test sending frame with socket error."""
        mock_socket_class.return_value = self.mock_socket
        self.client.connect()
        
        self.mock_socket.should_raise_on_send = socket.error("Send failed")
        frame = ProtocolFrame(Commands.HELLO, 0)
        
        with pytest.raises(ConnectionError):
            self.client._send_frame(frame)
    
    @patch('socket.socket')
    def test_receive_frame_success(self, mock_socket_class):
        """Test successful frame receiving."""
        mock_socket_class.return_value = self.mock_socket
        self.client.connect()
        
        # Prepare response
        response_frame = ProtocolFrame(Commands.HELLO_ACK, 1)
        self.mock_socket.add_response(response_frame)
        
        received = self.client._receive_frame()
        
        assert received.cmd == Commands.HELLO_ACK
        assert received.nonce == 1
    
    def test_receive_frame_not_connected(self):
        """Test receiving frame when not connected."""
        with pytest.raises(ConnectionError, match="Not connected"):
            self.client._receive_frame()
    
    @patch('socket.socket')
    def test_receive_frame_timeout(self, mock_socket_class):
        """Test receiving frame with timeout."""
        mock_socket_class.return_value = self.mock_socket
        self.client.connect()
        
        self.mock_socket.should_raise_on_recv = socket.timeout()
        
        with pytest.raises(TimeoutError):
            self.client._receive_frame()
    
    @patch('socket.socket')
    def test_receive_frame_disconnection(self, mock_socket_class):
        """Test receiving frame when server disconnects."""
        mock_socket_class.return_value = self.mock_socket
        self.client.connect()
        
        # Empty response simulates disconnection
        self.mock_socket.add_response(b"")
        
        with pytest.raises(ServerDisconnectionError):
            self.client._receive_frame()
    
    @patch('socket.socket')
    def test_authenticate_success(self, mock_socket_class):
        """Test successful authentication."""
        mock_socket_class.return_value = self.mock_socket
        self.client.connect()
        
        # Prepare HELLO_ACK response
        hello_ack = ProtocolFrame(Commands.HELLO_ACK, 1)
        self.mock_socket.add_response(hello_ack)
        
        result = self.client.authenticate()
        
        assert result is True
        assert len(self.mock_socket.sent_data) == 1
        
        # Verify HELLO was sent
        sent_frame = ProtocolFrame.decode(self.mock_socket.sent_data[0])
        assert sent_frame.cmd == Commands.HELLO
        assert sent_frame.nonce == 0
    
    @patch('socket.socket')
    def test_authenticate_wrong_response(self, mock_socket_class):
        """Test authentication with wrong response."""
        mock_socket_class.return_value = self.mock_socket
        self.client.connect()
        
        # Send wrong response
        wrong_response = ProtocolFrame(Commands.DUMP_OK, 1)
        self.mock_socket.add_response(wrong_response)
        
        with pytest.raises(AuthenticationError):
            self.client.authenticate()
    
    @patch('socket.socket')
    def test_authenticate_wrong_nonce(self, mock_socket_class):
        """Test authentication with wrong nonce."""
        mock_socket_class.return_value = self.mock_socket
        self.client.connect()
        
        # Send response with wrong nonce
        wrong_nonce_response = ProtocolFrame(Commands.HELLO_ACK, 5)
        self.mock_socket.add_response(wrong_nonce_response)
        
        with pytest.raises(NonceError):
            self.client.authenticate()
    
    @patch('socket.socket')
    def test_execute_dump_sequence_success(self, mock_socket_class):
        """Test successful DUMP sequence execution."""
        mock_socket_class.return_value = self.mock_socket
        self.client.connect()
        
        # Prepare responses
        dump_failed = ProtocolFrame(Commands.DUMP_FAILED, 1)
        override_code = b"JOSHUA_OVERRIDE_1983"
        dump_ok = ProtocolFrame(Commands.DUMP_OK, 3, override_code)
        
        self.mock_socket.add_response(dump_failed)
        self.mock_socket.add_response(dump_ok)
        
        result = self.client.execute_dump_sequence()
        
        assert result == "JOSHUA_OVERRIDE_1983"
        assert self.client.override_code == "JOSHUA_OVERRIDE_1983"
        assert len(self.mock_socket.sent_data) == 2  # Two DUMP commands
    
    @patch('socket.socket')
    def test_execute_dump_sequence_second_dump_fails(self, mock_socket_class):
        """Test DUMP sequence when second DUMP fails."""
        mock_socket_class.return_value = self.mock_socket
        self.client.connect()
        
        # Prepare responses
        dump_failed1 = ProtocolFrame(Commands.DUMP_FAILED, 1)
        dump_failed2 = ProtocolFrame(Commands.DUMP_FAILED, 3)
        
        self.mock_socket.add_response(dump_failed1)
        self.mock_socket.add_response(dump_failed2)
        
        with pytest.raises(MiniTelError, match="Second DUMP command failed"):
            self.client.execute_dump_sequence()
    
    @patch('socket.socket')
    def test_execute_dump_sequence_nonce_error(self, mock_socket_class):
        """Test DUMP sequence with nonce error."""
        mock_socket_class.return_value = self.mock_socket
        self.client.connect()
        
        # Prepare response with wrong nonce
        dump_failed = ProtocolFrame(Commands.DUMP_FAILED, 5)  # Wrong nonce
        self.mock_socket.add_response(dump_failed)
        
        with pytest.raises(NonceError):
            self.client.execute_dump_sequence()
    
    @patch('socket.socket')
    def test_send_stop_command_success(self, mock_socket_class):
        """Test successful STOP command."""
        mock_socket_class.return_value = self.mock_socket
        self.client.connect()
        
        # Prepare STOP_OK response
        stop_ok = ProtocolFrame(Commands.STOP_OK, 1)
        self.mock_socket.add_response(stop_ok)
        
        self.client.send_stop_command()
        
        assert len(self.mock_socket.sent_data) == 1
        sent_frame = ProtocolFrame.decode(self.mock_socket.sent_data[0])
        assert sent_frame.cmd == Commands.STOP_CMD
    
    @patch('socket.socket')
    def test_send_stop_command_error_handling(self, mock_socket_class):
        """Test STOP command error handling."""
        mock_socket_class.return_value = self.mock_socket
        self.client.connect()
        
        self.mock_socket.should_raise_on_send = socket.error("Send failed")
        
        # Should not raise exception, just log warning
        self.client.send_stop_command()
    
    @patch('socket.socket')
    def test_execute_mission_success(self, mock_socket_class):
        """Test successful mission execution."""
        mock_socket_class.return_value = self.mock_socket
        
        # Prepare all responses
        hello_ack = ProtocolFrame(Commands.HELLO_ACK, 1)
        dump_failed = ProtocolFrame(Commands.DUMP_FAILED, 3)
        override_code = b"JOSHUA_OVERRIDE_1983"
        dump_ok = ProtocolFrame(Commands.DUMP_OK, 5, override_code)
        stop_ok = ProtocolFrame(Commands.STOP_OK, 7)
        
        self.mock_socket.add_response(hello_ack)
        self.mock_socket.add_response(dump_failed)
        self.mock_socket.add_response(dump_ok)
        self.mock_socket.add_response(stop_ok)
        
        result = self.client.execute_mission()
        
        assert result == "JOSHUA_OVERRIDE_1983"
        assert not self.mock_socket.connected  # Should disconnect
    
    @patch('socket.socket')
    def test_execute_mission_with_session_recording(self, mock_socket_class):
        """Test mission execution with session recording."""
        client = MiniTelClient("test.example.com", 1234, record_session=True)
        mock_socket_class.return_value = self.mock_socket
        
        # Prepare responses
        hello_ack = ProtocolFrame(Commands.HELLO_ACK, 1)
        dump_failed = ProtocolFrame(Commands.DUMP_FAILED, 3)
        override_code = b"JOSHUA_OVERRIDE_1983"
        dump_ok = ProtocolFrame(Commands.DUMP_OK, 5, override_code)
        stop_ok = ProtocolFrame(Commands.STOP_OK, 7)
        
        self.mock_socket.add_response(hello_ack)
        self.mock_socket.add_response(dump_failed)
        self.mock_socket.add_response(dump_ok)
        self.mock_socket.add_response(stop_ok)
        
        with patch.object(client.session_recorder, 'save_session', return_value='test_session.json'):
            result = client.execute_mission()
        
        assert result == "JOSHUA_OVERRIDE_1983"
        assert client.session_recorder is not None
        assert len(client.session_recorder.interactions) > 0
    
    @patch('socket.socket')
    def test_execute_mission_connection_failure(self, mock_socket_class):
        """Test mission execution with connection failure."""
        self.mock_socket.should_raise_on_connect = socket.error("Connection refused")
        mock_socket_class.return_value = self.mock_socket
        
        with pytest.raises(ConnectionError):
            self.client.execute_mission()
        
        # Should still disconnect
        assert not self.mock_socket.connected
    
    @patch('socket.socket')
    def test_execute_mission_authentication_failure(self, mock_socket_class):
        """Test mission execution with authentication failure."""
        mock_socket_class.return_value = self.mock_socket
        
        # Send wrong response to HELLO
        wrong_response = ProtocolFrame(Commands.DUMP_OK, 1)
        self.mock_socket.add_response(wrong_response)
        
        with pytest.raises(AuthenticationError):
            self.client.execute_mission()
        
        # Should still disconnect
        assert not self.mock_socket.connected


class TestClientEdgeCases:
    """Test edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_socket = MockSocket()
        self.client = MiniTelClient("test.example.com", 1234, timeout=1.0)
    
    @patch('socket.socket')
    def test_receive_exact_partial_data(self, mock_socket_class):
        """Test _receive_exact with partial data."""
        mock_socket_class.return_value = self.mock_socket
        self.client.connect()
        
        # Simulate partial reads
        self.mock_socket.receive_data = [b"hel", b"lo", b""]
        
        result = self.client._receive_exact(5)
        assert result == b"hello"
    
    @patch('socket.socket')
    def test_receive_exact_disconnection(self, mock_socket_class):
        """Test _receive_exact when connection drops."""
        mock_socket_class.return_value = self.mock_socket
        self.client.connect()
        
        # Simulate disconnection
        self.mock_socket.receive_data = [b"hel", b""]
        
        result = self.client._receive_exact(5)
        assert result == b"hel"  # Partial data before disconnection
    
    @patch('socket.socket')
    def test_client_with_session_recording_disabled(self, mock_socket_class):
        """Test client behavior with session recording disabled."""
        client = MiniTelClient("test.example.com", 1234, record_session=False)
        assert client.session_recorder is None
        
        mock_socket_class.return_value = self.mock_socket
        
        # Should work normally without session recording
        client.connect()
        frame = ProtocolFrame(Commands.HELLO, 0)
        client._send_frame(frame)
        
        assert len(self.mock_socket.sent_data) == 1
    
    def test_client_logging_setup(self):
        """Test that client sets up logging correctly."""
        client = MiniTelClient("test.example.com", 1234)
        assert client.logger is not None
        assert client.logger.name == "src.minitel.client"

    def test_client_main_function(self):
        """Test main CLI function."""
        with patch('sys.argv', ['client.py', '--host', 'localhost', '--port', '8080']):
            with patch('src.minitel.client.MiniTelClient.execute_mission') as mock_execute:
                mock_execute.return_value = "TEST_CODE"
                
                from src.minitel.client import main
                result = main()
                assert result == 0

    def test_client_main_keyboard_interrupt(self):
        """Test main function with keyboard interrupt."""
        with patch('sys.argv', ['client.py', '--host', 'localhost', '--port', '8080']):
            with patch('src.minitel.client.MiniTelClient.execute_mission') as mock_execute:
                mock_execute.side_effect = KeyboardInterrupt()
                
                from src.minitel.client import main
                result = main()
                assert result == 1

    def test_client_main_exception(self):
        """Test main function with exception."""
        with patch('sys.argv', ['client.py', '--host', 'localhost', '--port', '8080']):
            with patch('src.minitel.client.MiniTelClient.execute_mission') as mock_execute:
                mock_execute.side_effect = Exception("Test error")
                
                from src.minitel.client import main
                result = main()
                assert result == 1

    def test_execute_mission_finally_block(self):
        """Test that execute_mission always disconnects."""
        with patch.object(self.client, 'connect') as mock_connect:
            with patch.object(self.client, 'authenticate') as mock_auth:
                with patch.object(self.client, 'disconnect') as mock_disconnect:
                    mock_auth.side_effect = Exception("Test error")
                    
                    with pytest.raises(Exception):
                        self.client.execute_mission()
                    
                    # Should still call disconnect
                    mock_disconnect.assert_called_once()

    
    @patch('socket.socket')
    def test_disconnect_with_exception(self, mock_socket_class):
        """Test disconnect when close() raises exception."""
        mock_socket_class.return_value = self.mock_socket
        self.client.connect()
        
        # Mock close to raise exception
        def raise_exception():
            raise socket.error("Close failed")
        
        self.mock_socket.close = raise_exception
        
        # Should not raise exception, just log warning
        self.client.disconnect()
        assert self.client.socket is None
