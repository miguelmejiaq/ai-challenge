"""
Tests for session recording functionality.
"""

import pytest
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, mock_open
from src.minitel.session import SessionRecorder, SessionLoader
from src.minitel.protocol import ProtocolFrame, Commands


class TestSessionRecorder:
    """Test cases for SessionRecorder class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.recorder = SessionRecorder("test_session")
    
    def test_recorder_initialization(self):
        """Test recorder initialization."""
        assert self.recorder.session_id == "test_session"
        assert self.recorder.interactions == []
        assert self.recorder.start_time > 0
        assert self.recorder.protocol_handler is not None
    
    def test_recorder_auto_session_id(self):
        """Test automatic session ID generation."""
        recorder = SessionRecorder()
        assert recorder.session_id.startswith("session_")
        assert len(recorder.session_id) > 8  # Should have timestamp
    
    def test_record_request(self):
        """Test recording a request."""
        frame = ProtocolFrame(Commands.HELLO, 0, b"test payload")
        self.recorder.record_request(frame, "Test HELLO request")
        
        assert len(self.recorder.interactions) == 1
        interaction = self.recorder.interactions[0]
        
        assert interaction["type"] == "request"
        assert interaction["direction"] == "client -> server"
        assert interaction["command"] == "HELLO"
        assert interaction["command_code"] == "0x01"
        assert interaction["nonce"] == 0
        assert interaction["payload_length"] == 12
        assert interaction["payload"] == "test payload"
        assert interaction["description"] == "Test HELLO request"
        assert "timestamp" in interaction
        assert "relative_time" in interaction
    
    def test_record_response(self):
        """Test recording a response."""
        frame = ProtocolFrame(Commands.HELLO_ACK, 1)
        self.recorder.record_response(frame, "Test HELLO_ACK response")
        
        assert len(self.recorder.interactions) == 1
        interaction = self.recorder.interactions[0]
        
        assert interaction["type"] == "response"
        assert interaction["direction"] == "server -> client"
        assert interaction["command"] == "HELLO_ACK"
        assert interaction["command_code"] == "0x81"
        assert interaction["nonce"] == 1
        assert interaction["payload_length"] == 0
        assert interaction["payload"] == ""
        assert interaction["description"] == "Test HELLO_ACK response"
    
    def test_record_event(self):
        """Test recording an event."""
        details = {"host": "localhost", "port": 8080}
        self.recorder.record_event("connection", "Connected to server", details)
        
        assert len(self.recorder.interactions) == 1
        interaction = self.recorder.interactions[0]
        
        assert interaction["type"] == "event"
        assert interaction["event_type"] == "connection"
        assert interaction["description"] == "Connected to server"
        assert interaction["details"] == details
        assert "timestamp" in interaction
        assert "relative_time" in interaction
    
    def test_record_event_without_details(self):
        """Test recording an event without details."""
        self.recorder.record_event("disconnection", "Client disconnected")
        
        assert len(self.recorder.interactions) == 1
        interaction = self.recorder.interactions[0]
        
        assert interaction["details"] == {}
    
    def test_record_binary_payload(self):
        """Test recording with binary payload."""
        binary_payload = b"\x00\x01\x02\xff"
        frame = ProtocolFrame(Commands.DUMP_OK, 42, binary_payload)
        self.recorder.record_response(frame)
        
        interaction = self.recorder.interactions[0]
        # Should handle binary data gracefully
        assert interaction["payload_length"] == 4
        assert isinstance(interaction["payload"], str)
    
    def test_get_session_summary(self):
        """Test session summary generation."""
        # Record some interactions
        self.recorder.record_request(ProtocolFrame(Commands.HELLO, 0), "HELLO")
        self.recorder.record_response(ProtocolFrame(Commands.HELLO_ACK, 1), "HELLO_ACK")
        self.recorder.record_event("connection", "Connected")
        
        summary = self.recorder.get_session_summary()
        
        assert summary["session_id"] == "test_session"
        assert summary["total_interactions"] == 3
        assert summary["requests"] == 1
        assert summary["responses"] == 1
        assert summary["events"] == 1
        assert summary["commands_sent"] == ["HELLO"]
        assert summary["responses_received"] == ["HELLO_ACK"]
        assert "duration" in summary
    
    def test_save_session(self):
        """Test saving session to file."""
        # Record some interactions
        self.recorder.record_request(ProtocolFrame(Commands.HELLO, 0))
        self.recorder.record_response(ProtocolFrame(Commands.HELLO_ACK, 1))
        
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = self.recorder.save_session(temp_dir)
            
            # Check file was created
            assert Path(filepath).exists()
            assert filepath.endswith("test_session.json")
            
            # Check file contents
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            assert data["session_id"] == "test_session"
            assert data["total_interactions"] == 2
            assert len(data["interactions"]) == 2
            assert "metadata" in data
            assert data["metadata"]["protocol_version"] == "MiniTel-Lite v3.0"
    
    def test_save_session_creates_directory(self):
        """Test that save_session creates output directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_dir = Path(temp_dir) / "sessions"
            assert not non_existent_dir.exists()
            
            filepath = self.recorder.save_session(str(non_existent_dir))
            
            assert non_existent_dir.exists()
            assert Path(filepath).exists()


class TestSessionLoader:
    """Test cases for SessionLoader class."""
    
    def create_test_session_file(self, temp_dir: str, session_data: dict) -> str:
        """Helper to create a test session file."""
        filepath = Path(temp_dir) / "test_session.json"
        with open(filepath, 'w') as f:
            json.dump(session_data, f)
        return str(filepath)
    
    def test_load_session_success(self):
        """Test successful session loading."""
        session_data = {
            "session_id": "test_session",
            "start_time": 1234567890,
            "duration": 10.5,
            "total_interactions": 2,
            "interactions": [
                {"type": "request", "command": "HELLO"},
                {"type": "response", "command": "HELLO_ACK"}
            ]
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = self.create_test_session_file(temp_dir, session_data)
            loaded_data = SessionLoader.load_session(filepath)
            
            assert loaded_data == session_data
    
    def test_load_session_file_not_found(self):
        """Test loading non-existent session file."""
        with pytest.raises(FileNotFoundError):
            SessionLoader.load_session("non_existent_file.json")
    
    def test_load_session_invalid_json(self):
        """Test loading invalid JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = Path(temp_dir) / "invalid.json"
            with open(filepath, 'w') as f:
                f.write("invalid json content")
            
            with pytest.raises(json.JSONDecodeError):
                SessionLoader.load_session(str(filepath))
    
    def test_list_sessions_empty_directory(self):
        """Test listing sessions in empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            sessions = SessionLoader.list_sessions(temp_dir)
            assert sessions == []
    
    def test_list_sessions_non_existent_directory(self):
        """Test listing sessions in non-existent directory."""
        sessions = SessionLoader.list_sessions("non_existent_directory")
        assert sessions == []
    
    def test_list_sessions_with_files(self):
        """Test listing sessions with multiple files."""
        session1_data = {
            "session_id": "session_1",
            "start_time": 1234567890,
            "duration": 5.0,
            "total_interactions": 3,
            "metadata": {"recorded_at": "2023-01-01T12:00:00"}
        }
        
        session2_data = {
            "session_id": "session_2",
            "start_time": 1234567900,  # Later timestamp
            "duration": 8.0,
            "total_interactions": 5,
            "metadata": {"recorded_at": "2023-01-01T12:01:00"}
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create session files
            filepath1 = self.create_test_session_file(temp_dir, session1_data)
            Path(filepath1).rename(Path(temp_dir) / "session_1.json")
            
            filepath2 = self.create_test_session_file(temp_dir, session2_data)
            Path(filepath2).rename(Path(temp_dir) / "session_2.json")
            
            # Create a non-JSON file (should be ignored)
            with open(Path(temp_dir) / "not_a_session.txt", 'w') as f:
                f.write("not json")
            
            sessions = SessionLoader.list_sessions(temp_dir)
            
            assert len(sessions) == 2
            
            # Should be sorted by start time (newest first)
            assert sessions[0]["session_id"] == "session_2"
            assert sessions[1]["session_id"] == "session_1"
            
            # Check session metadata
            session = sessions[0]
            assert session["filename"] == "session_2.json"
            assert session["start_time"] == 1234567900
            assert session["duration"] == 8.0
            assert session["total_interactions"] == 5
            assert session["recorded_at"] == "2023-01-01T12:01:00"
    
    def test_list_sessions_with_invalid_files(self):
        """Test listing sessions with some invalid JSON files."""
        valid_session = {
            "session_id": "valid_session",
            "start_time": 1234567890,
            "duration": 5.0,
            "total_interactions": 3
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create valid session file
            self.create_test_session_file(temp_dir, valid_session)
            (Path(temp_dir) / "test_session.json").rename(Path(temp_dir) / "valid.json")
            
            # Create invalid JSON file
            with open(Path(temp_dir) / "invalid.json", 'w') as f:
                f.write("invalid json")
            
            # Create JSON file with missing required fields
            with open(Path(temp_dir) / "incomplete.json", 'w') as f:
                json.dump({"some_field": "value"}, f)
            
            sessions = SessionLoader.list_sessions(temp_dir)
            
            # Should only return the valid session
            assert len(sessions) == 1
            assert sessions[0]["session_id"] == "valid_session"
    
    def test_get_session_interactions(self):
        """Test getting interactions from session file."""
        interactions = [
            {"type": "request", "command": "HELLO", "timestamp": 1234567890},
            {"type": "response", "command": "HELLO_ACK", "timestamp": 1234567891}
        ]
        
        session_data = {
            "session_id": "test_session",
            "interactions": interactions
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = self.create_test_session_file(temp_dir, session_data)
            loaded_interactions = SessionLoader.get_session_interactions(filepath)
            
            assert loaded_interactions == interactions
    
    def test_get_session_interactions_no_interactions(self):
        """Test getting interactions from session with no interactions."""
        session_data = {"session_id": "test_session"}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = self.create_test_session_file(temp_dir, session_data)
            interactions = SessionLoader.get_session_interactions(filepath)
            
            assert interactions == []


class TestSessionIntegration:
    """Integration tests for session recording and loading."""
    
    def test_record_and_load_complete_session(self):
        """Test recording a complete session and loading it back."""
        recorder = SessionRecorder("integration_test")
        
        # Simulate a complete protocol sequence
        recorder.record_event("connection", "Connected to server")
        recorder.record_request(ProtocolFrame(Commands.HELLO, 0), "Authentication")
        recorder.record_response(ProtocolFrame(Commands.HELLO_ACK, 1), "Auth successful")
        recorder.record_request(ProtocolFrame(Commands.DUMP, 2), "First DUMP")
        recorder.record_response(ProtocolFrame(Commands.DUMP_FAILED, 3), "First DUMP failed")
        recorder.record_request(ProtocolFrame(Commands.DUMP, 4), "Second DUMP")
        
        override_code = b"JOSHUA_OVERRIDE_1983"
        recorder.record_response(ProtocolFrame(Commands.DUMP_OK, 5, override_code), "Override code received")
        recorder.record_request(ProtocolFrame(Commands.STOP_CMD, 6), "Session end")
        recorder.record_response(ProtocolFrame(Commands.STOP_OK, 7), "Session ended")
        recorder.record_event("disconnection", "Disconnected from server")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save session
            filepath = recorder.save_session(temp_dir)
            
            # Load session back
            loaded_data = SessionLoader.load_session(filepath)
            
            # Verify session data
            assert loaded_data["session_id"] == "integration_test"
            assert loaded_data["total_interactions"] == 10
            assert len(loaded_data["interactions"]) == 10
            
            # Verify specific interactions
            interactions = loaded_data["interactions"]
            assert interactions[0]["type"] == "event"
            assert interactions[1]["command"] == "HELLO"
            assert interactions[6]["payload"] == "JOSHUA_OVERRIDE_1983"
            assert interactions[-1]["type"] == "event"
            
            # Test session listing
            sessions = SessionLoader.list_sessions(temp_dir)
            assert len(sessions) == 1
            assert sessions[0]["session_id"] == "integration_test"
            assert sessions[0]["total_interactions"] == 10
    
    def test_session_timing_accuracy(self):
        """Test that session timing is recorded accurately."""
        recorder = SessionRecorder("timing_test")
        
        start_time = time.time()
        recorder.record_event("start", "Test started")
        
        # Small delay
        time.sleep(0.1)
        
        recorder.record_event("end", "Test ended")
        end_time = time.time()
        
        # Check timing accuracy
        interactions = recorder.interactions
        assert len(interactions) == 2
        
        start_interaction = interactions[0]
        end_interaction = interactions[1]
        
        # Relative times should be reasonable
        assert start_interaction["relative_time"] < 0.01  # Very close to start
        assert 0.09 < end_interaction["relative_time"] < 0.15  # Around 0.1s later
        
        # Timestamps should be in reasonable range
        assert start_time <= start_interaction["timestamp"] <= end_time
        assert start_time <= end_interaction["timestamp"] <= end_time
