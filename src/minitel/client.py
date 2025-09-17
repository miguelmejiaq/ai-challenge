"""
MiniTel-Lite Emergency Protocol Client

This module implements the main client for connecting to the MiniTel-Lite server
and executing the JOSHUA override mission.
"""

import argparse
import logging
import socket
import sys
import time
from typing import Optional, Tuple
from .protocol import ProtocolFrame, ProtocolHandler, Commands
from .session import SessionRecorder
from .exceptions import (
    MiniTelError, ConnectionError, AuthenticationError, 
    NonceError, ServerDisconnectionError, TimeoutError
)


class MiniTelClient:
    """
    MiniTel-Lite protocol client for NORAD JOSHUA override mission.
    """
    
    def __init__(self, host: str, port: int, timeout: float = 2.0, record_session: bool = False):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket: Optional[socket.socket] = None
        self.protocol_handler = ProtocolHandler()
        self.session_recorder = SessionRecorder() if record_session else None
        self.logger = self._setup_logging()
        self.override_code: Optional[str] = None
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def connect(self) -> None:
        """
        Establish connection to the MiniTel-Lite server.
        
        Raises:
            ConnectionError: If connection fails
        """
        try:
            self.logger.info(f"Connecting to {self.host}:{self.port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            
            if self.session_recorder:
                self.session_recorder.record_event(
                    "connection", 
                    f"Connected to {self.host}:{self.port}",
                    {"host": self.host, "port": self.port, "timeout": self.timeout}
                )
            
            self.logger.info("Connection established")
            
        except socket.error as e:
            error_msg = f"Failed to connect to {self.host}:{self.port}: {e}"
            self.logger.error(error_msg)
            if self.session_recorder:
                self.session_recorder.record_event("error", error_msg, {"error_type": "connection_failed"})
            raise ConnectionError(error_msg)
    
    def disconnect(self) -> None:
        """Close the connection to the server."""
        if self.socket:
            try:
                self.socket.close()
                self.logger.info("Disconnected from server")
                if self.session_recorder:
                    self.session_recorder.record_event("disconnection", "Client disconnected")
            except Exception as e:
                self.logger.warning(f"Error during disconnect: {e}")
            finally:
                self.socket = None
    
    def _send_frame(self, frame: ProtocolFrame) -> None:
        """
        Send a protocol frame to the server.
        
        Args:
            frame: The frame to send
            
        Raises:
            ConnectionError: If sending fails
        """
        if not self.socket:
            raise ConnectionError("Not connected to server")
        
        try:
            encoded_frame = frame.encode()
            self.socket.sendall(encoded_frame)
            
            command_name = self.protocol_handler.get_command_name(frame.cmd)
            self.logger.info(f"Sent {command_name} (nonce={frame.nonce})")
            
            if self.session_recorder:
                self.session_recorder.record_request(frame, f"Sent {command_name}")
                
        except socket.error as e:
            error_msg = f"Failed to send frame: {e}"
            self.logger.error(error_msg)
            if self.session_recorder:
                self.session_recorder.record_event("error", error_msg, {"error_type": "send_failed"})
            raise ConnectionError(error_msg)
    
    def _receive_frame(self) -> ProtocolFrame:
        """
        Receive a protocol frame from the server.
        
        Returns:
            ProtocolFrame: The received frame
            
        Raises:
            ConnectionError: If receiving fails
            ServerDisconnectionError: If server disconnects
        """
        if not self.socket:
            raise ConnectionError("Not connected to server")
        
        try:
            # Read length prefix (2 bytes)
            length_data = self._receive_exact(2)
            if not length_data:
                raise ServerDisconnectionError("Server disconnected during length read")
            
            # Read the frame data
            import struct
            length = struct.unpack(">H", length_data)[0]
            frame_data = self._receive_exact(length)
            if not frame_data:
                raise ServerDisconnectionError("Server disconnected during frame read")
            
            # Decode the frame
            full_data = length_data + frame_data
            frame = ProtocolFrame.decode(full_data)
            
            command_name = self.protocol_handler.get_command_name(frame.cmd)
            self.logger.info(f"Received {command_name} (nonce={frame.nonce})")
            
            if self.session_recorder:
                self.session_recorder.record_response(frame, f"Received {command_name}")
            
            return frame
            
        except socket.timeout:
            error_msg = "Timeout while receiving frame"
            self.logger.error(error_msg)
            if self.session_recorder:
                self.session_recorder.record_event("error", error_msg, {"error_type": "receive_timeout"})
            raise TimeoutError(error_msg)
        except socket.error as e:
            error_msg = f"Failed to receive frame: {e}"
            self.logger.error(error_msg)
            if self.session_recorder:
                self.session_recorder.record_event("error", error_msg, {"error_type": "receive_failed"})
            raise ConnectionError(error_msg)
    
    def _receive_exact(self, num_bytes: int) -> bytes:
        """
        Receive exactly num_bytes from the socket.
        
        Args:
            num_bytes: Number of bytes to receive
            
        Returns:
            bytes: The received data
        """
        data = b""
        while len(data) < num_bytes:
            chunk = self.socket.recv(num_bytes - len(data))
            if not chunk:
                break
            data += chunk
        return data
    
    def authenticate(self) -> bool:
        """
        Perform HELLO authentication with the server.
        
        Returns:
            bool: True if authentication successful
            
        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Send HELLO command
            hello_frame = self.protocol_handler.create_hello_frame()
            self._send_frame(hello_frame)
            
            # Receive HELLO_ACK response
            response = self._receive_frame()
            
            # Validate response
            if response.cmd != Commands.HELLO_ACK:
                raise AuthenticationError(f"Expected HELLO_ACK, got {response.cmd:02x}")
            
            if not self.protocol_handler.validate_response_nonce(response):
                raise NonceError("Invalid nonce in HELLO_ACK response")
            
            self.logger.info("Authentication successful")
            return True
            
        except MiniTelError:
            raise
        except Exception as e:
            error_msg = f"Authentication failed: {e}"
            self.logger.error(error_msg)
            raise AuthenticationError(error_msg)
    
    def execute_dump_sequence(self) -> str:
        """
        Execute the DUMP command sequence to retrieve the override code.
        According to mission briefing, we need to call DUMP twice.
        
        Returns:
            str: The override code
            
        Raises:
            MiniTelError: If the sequence fails
        """
        self.logger.info("Starting DUMP sequence")
        
        # First DUMP command
        self.logger.info("Executing first DUMP command")
        dump_frame1 = self.protocol_handler.create_dump_frame()
        self._send_frame(dump_frame1)
        
        response1 = self._receive_frame()
        if not self.protocol_handler.validate_response_nonce(response1):
            raise NonceError("Invalid nonce in first DUMP response")
        
        if response1.cmd == Commands.DUMP_FAILED:
            self.logger.info("First DUMP failed as expected")
        elif response1.cmd == Commands.DUMP_OK:
            self.logger.warning("First DUMP succeeded unexpectedly")
        else:
            raise MiniTelError(f"Unexpected response to first DUMP: {response1.cmd:02x}")
        
        # Second DUMP command
        self.logger.info("Executing second DUMP command")
        dump_frame2 = self.protocol_handler.create_dump_frame()
        self._send_frame(dump_frame2)
        
        response2 = self._receive_frame()
        if not self.protocol_handler.validate_response_nonce(response2):
            raise NonceError("Invalid nonce in second DUMP response")
        
        if response2.cmd == Commands.DUMP_OK:
            override_code = response2.payload.decode('utf-8', errors='replace').strip()
            self.logger.info(f"Override code retrieved: {override_code}")
            self.override_code = override_code
            return override_code
        elif response2.cmd == Commands.DUMP_FAILED:
            raise MiniTelError("Second DUMP command failed")
        else:
            raise MiniTelError(f"Unexpected response to second DUMP: {response2.cmd:02x}")
    
    def send_stop_command(self) -> None:
        """Send STOP_CMD to gracefully end the session."""
        try:
            self.logger.info("Sending STOP command")
            stop_frame = self.protocol_handler.create_stop_frame()
            self._send_frame(stop_frame)
            
            response = self._receive_frame()
            if not self.protocol_handler.validate_response_nonce(response):
                self.logger.warning("Invalid nonce in STOP response")
            
            if response.cmd == Commands.STOP_OK:
                self.logger.info("STOP command acknowledged")
            else:
                self.logger.warning(f"Unexpected response to STOP: {response.cmd:02x}")
                
        except Exception as e:
            self.logger.warning(f"Error sending STOP command: {e}")
    
    def execute_mission(self) -> str:
        """
        Execute the complete JOSHUA override mission.
        
        Returns:
            str: The retrieved override code
            
        Raises:
            MiniTelError: If mission fails
        """
        try:
            # Reset protocol handler state for fresh mission
            self.protocol_handler.reset_nonces()
            
            # Connect to server
            self.connect()
            
            # Authenticate
            self.authenticate()
            
            # Execute DUMP sequence
            override_code = self.execute_dump_sequence()
            
            # Send STOP command
            self.send_stop_command()
            
            # Save session if recording
            if self.session_recorder:
                session_file = self.session_recorder.save_session()
                self.logger.info(f"Session saved to: {session_file}")
                
                # Print session summary
                summary = self.session_recorder.get_session_summary()
                self.logger.info(f"Session summary: {summary}")
            
            return override_code
            
        except Exception as e:
            if self.session_recorder:
                self.session_recorder.record_event("error", f"Mission failed: {e}", {"error_type": "mission_failed"})
            raise
        finally:
            self.disconnect()


def main():
    """Main entry point for the MiniTel client."""
    parser = argparse.ArgumentParser(description="MiniTel-Lite Emergency Protocol Client")
    parser.add_argument("--host", required=True, help="Server hostname or IP address")
    parser.add_argument("--port", type=int, required=True, help="Server port number")
    parser.add_argument("--timeout", type=float, default=2.0, help="Connection timeout in seconds")
    parser.add_argument("--record", action="store_true", help="Enable session recording")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set up logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Create and execute client
        client = MiniTelClient(
            host=args.host,
            port=args.port,
            timeout=args.timeout,
            record_session=args.record
        )
        
        print("=" * 60)
        print("NORAD MINITEL-LITE EMERGENCY PROTOCOL")
        print("Agent LIGHTMAN - JOSHUA Override Mission")
        print("=" * 60)
        
        override_code = client.execute_mission()
        
        print("\n" + "=" * 60)
        print("MISSION SUCCESSFUL!")
        print(f"OVERRIDE CODE: {override_code}")
        print("=" * 60)
        print("\nTransmit this code to NORAD command immediately!")
        
        return 0
        
    except KeyboardInterrupt:
        print("\nMission aborted by user")
        return 1
    except Exception as e:
        print(f"\nMISSION FAILED: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
