"""
Integration tests for MiniTel-Lite client with real server.

These tests connect to the actual MiniTel-Lite server to verify
end-to-end functionality.

Configuration is done via environment variables:
- SERVER_HOST: Server hostname or IP (default: 35.153.159.192)
- SERVER_PORT: Server port (default: 7321)
- TIMEOUT: Connection timeout in seconds (default: 5.0)
"""

import os
import pytest
import tempfile
from pathlib import Path
from src.minitel.client import MiniTelClient
from src.minitel.session import SessionLoader
from src.minitel.exceptions import MiniTelError


# Real server configuration from environment variables (required)
SERVER_HOST = os.getenv("SERVER_HOST")
SERVER_PORT_STR = os.getenv("SERVER_PORT")
TIMEOUT = float(os.getenv("TIMEOUT", "5.0"))

# Validate required environment variables
if not SERVER_HOST:
    pytest.skip("SERVER_HOST environment variable is required for integration tests", allow_module_level=True)

if not SERVER_PORT_STR:
    pytest.skip("SERVER_PORT environment variable is required for integration tests", allow_module_level=True)

try:
    SERVER_PORT = int(SERVER_PORT_STR)
except (ValueError, TypeError):
    pytest.skip(f"SERVER_PORT must be a valid integer, got: {SERVER_PORT_STR}", allow_module_level=True)


# Skip integration tests if server is not configured
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may be slow)"
    )


def pytest_collection_modifyitems(config, items):
    """Add integration marker to all tests in this module."""
    for item in items:
        if "test_integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def server_config():
    """Provide server configuration for tests."""
    return {
        "host": SERVER_HOST,
        "port": SERVER_PORT,
        "timeout": TIMEOUT
    }


@pytest.fixture(scope="session", autouse=True)
def check_server_availability(server_config):
    """Check if the server is available before running tests."""
    import socket
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2.0)
            result = sock.connect_ex((server_config["host"], server_config["port"]))
            if result != 0:
                pytest.skip(f"Server {server_config['host']}:{server_config['port']} is not available")
    except Exception as e:
        pytest.skip(f"Cannot check server availability: {e}")


class TestRealServerIntegration:
    """Integration tests with the real MiniTel-Lite server."""
    
    def test_successful_mission_execution(self):
        """Test complete mission execution against real server."""
        client = MiniTelClient(SERVER_HOST, SERVER_PORT, timeout=TIMEOUT, record_session=True)
        
        # Execute the complete mission
        override_code = client.execute_mission()
        
        # Verify we got a valid override code
        assert override_code is not None
        assert len(override_code) > 0
        assert isinstance(override_code, str)
        
        # Verify session was recorded
        assert client.session_recorder is not None
        assert len(client.session_recorder.interactions) > 0
        
        # Verify the protocol sequence
        summary = client.session_recorder.get_session_summary()
        assert summary["requests"] >= 3  # HELLO, DUMP, DUMP, STOP
        assert summary["responses"] >= 3  # HELLO_ACK, DUMP_FAILED, DUMP_OK, STOP_OK
        assert "HELLO" in summary["commands_sent"]
        assert "DUMP" in summary["commands_sent"]
        assert "STOP_CMD" in summary["commands_sent"]
    
    def test_authentication_flow(self):
        """Test HELLO authentication against real server."""
        client = MiniTelClient(SERVER_HOST, SERVER_PORT, timeout=TIMEOUT)
        
        try:
            # Connect and authenticate
            client.connect()
            result = client.authenticate()
            
            assert result is True
            
        finally:
            client.disconnect()
    
    def test_dump_sequence_behavior(self):
        """Test DUMP command sequence behavior."""
        client = MiniTelClient(SERVER_HOST, SERVER_PORT, timeout=TIMEOUT, record_session=True)
        
        try:
            # Connect and authenticate first
            client.connect()
            client.authenticate()
            
            # Execute DUMP sequence
            override_code = client.execute_dump_sequence()
            
            # Verify we got the override code
            assert override_code is not None
            assert len(override_code) > 0
            
            # Verify the sequence in session recording
            interactions = client.session_recorder.interactions
            dump_requests = [i for i in interactions if i.get("command") == "DUMP"]
            dump_responses = [i for i in interactions if i.get("command") in ["DUMP_FAILED", "DUMP_OK"]]
            
            # Should have exactly 2 DUMP requests
            assert len(dump_requests) == 2
            # Should have 2 responses (DUMP_FAILED, then DUMP_OK)
            assert len(dump_responses) == 2
            
        finally:
            client.disconnect()
    
    def test_session_recording_with_real_server(self):
        """Test session recording functionality with real server."""
        with tempfile.TemporaryDirectory() as temp_dir:
            client = MiniTelClient(SERVER_HOST, SERVER_PORT, timeout=TIMEOUT, record_session=True)
            
            # Execute mission
            override_code = client.execute_mission()
            
            # Save session
            session_file = client.session_recorder.save_session(temp_dir)
            
            # Verify session file was created
            assert Path(session_file).exists()
            
            # Load and verify session content
            session_data = SessionLoader.load_session(session_file)
            
            assert session_data["session_id"] is not None
            assert session_data["total_interactions"] > 0
            assert len(session_data["interactions"]) > 0
            
            # Verify we have the expected interaction types
            interactions = session_data["interactions"]
            has_connection = any(i.get("event_type") == "connection" for i in interactions)
            has_requests = any(i.get("type") == "request" for i in interactions)
            has_responses = any(i.get("type") == "response" for i in interactions)
            
            assert has_connection
            assert has_requests
            assert has_responses
            
            # Verify override code is in the session
            dump_ok_interactions = [i for i in interactions if i.get("command") == "DUMP_OK"]
            assert len(dump_ok_interactions) == 1
            assert dump_ok_interactions[0]["payload"] == override_code
    
    def test_protocol_compliance(self):
        """Test protocol compliance with real server."""
        client = MiniTelClient(SERVER_HOST, SERVER_PORT, timeout=TIMEOUT, record_session=True)
        
        # Execute mission
        client.execute_mission()
        
        # Analyze protocol compliance from session
        interactions = client.session_recorder.interactions
        
        # Verify nonce sequence
        requests = [i for i in interactions if i.get("type") == "request"]
        responses = [i for i in interactions if i.get("type") == "response"]
        
        # Check nonce progression for requests (should be 0, 2, 4, 6...)
        request_nonces = [i["nonce"] for i in requests]
        expected_request_nonces = list(range(0, len(requests) * 2, 2))
        assert request_nonces == expected_request_nonces
        
        # Check nonce progression for responses (should be 1, 3, 5, 7...)
        response_nonces = [i["nonce"] for i in responses]
        expected_response_nonces = list(range(1, len(responses) * 2, 2))
        assert response_nonces == expected_response_nonces
    
    def test_error_handling_with_real_server(self):
        """Test error handling scenarios."""
        # Test with invalid port (should fail gracefully)
        client = MiniTelClient(SERVER_HOST, 9999, timeout=1.0)  # Invalid port
        
        with pytest.raises(MiniTelError):
            client.execute_mission()
    
    def test_connection_timeout_handling(self):
        """Test connection timeout handling."""
        # Test with very short timeout
        client = MiniTelClient("192.0.2.1", 80, timeout=0.1)  # Non-routable IP
        
        with pytest.raises(MiniTelError):
            client.execute_mission()


class TestRealServerPerformance:
    """Performance tests with real server."""
    
    def test_mission_execution_time(self):
        """Test that mission completes within reasonable time."""
        import time
        
        client = MiniTelClient(SERVER_HOST, SERVER_PORT, timeout=TIMEOUT)
        
        start_time = time.time()
        override_code = client.execute_mission()
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Mission should complete within 10 seconds
        assert execution_time < 10.0
        assert override_code is not None
    
    def test_multiple_connections(self):
        """Test multiple sequential connections."""
        override_codes = []
        
        for i in range(3):
            client = MiniTelClient(SERVER_HOST, SERVER_PORT, timeout=TIMEOUT)
            override_code = client.execute_mission()
            override_codes.append(override_code)
        
        # All should succeed and return the same code
        assert len(override_codes) == 3
        assert all(code is not None for code in override_codes)
        # All codes should be the same (server should be consistent)
        assert len(set(override_codes)) == 1


class TestRealServerEdgeCases:
    """Edge case tests with real server."""
    
    def test_session_recording_disabled(self):
        """Test mission execution without session recording."""
        client = MiniTelClient(SERVER_HOST, SERVER_PORT, timeout=TIMEOUT, record_session=False)
        
        override_code = client.execute_mission()
        
        assert override_code is not None
        assert client.session_recorder is None
    
    def test_verbose_logging(self):
        """Test mission execution with verbose logging."""
        import logging
        
        # Set debug level logging
        logging.getLogger().setLevel(logging.DEBUG)
        
        client = MiniTelClient(SERVER_HOST, SERVER_PORT, timeout=TIMEOUT)
        override_code = client.execute_mission()
        
        assert override_code is not None
        
        # Reset logging level
        logging.getLogger().setLevel(logging.INFO)
    
    def test_client_reuse(self):
        """Test that client handles multiple mission attempts correctly."""
        client = MiniTelClient(SERVER_HOST, SERVER_PORT, timeout=TIMEOUT)
        
        # First mission
        override_code1 = client.execute_mission()
        
        # Second mission (should work with fresh client state)
        override_code2 = client.execute_mission()
        
        assert override_code1 is not None
        assert override_code2 is not None
        assert override_code1 == override_code2
