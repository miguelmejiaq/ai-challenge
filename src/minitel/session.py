"""
Session recording functionality for MiniTel-Lite client.

This module provides session recording capabilities to capture all
client-server interactions for later replay and analysis.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from .protocol import ProtocolFrame, ProtocolHandler


class SessionRecorder:
    """
    Records all client-server interactions during a MiniTel-Lite session.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or self._generate_session_id()
        self.interactions: List[Dict[str, Any]] = []
        self.start_time = time.time()
        self.protocol_handler = ProtocolHandler()
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID based on timestamp."""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def record_request(self, frame: ProtocolFrame, description: str = "") -> None:
        """
        Record a client request.
        
        Args:
            frame: The protocol frame being sent
            description: Optional description of the request
        """
        interaction = {
            "timestamp": time.time(),
            "relative_time": time.time() - self.start_time,
            "type": "request",
            "direction": "client -> server",
            "command": self.protocol_handler.get_command_name(frame.cmd),
            "command_code": f"0x{frame.cmd:02x}",
            "nonce": frame.nonce,
            "payload_length": len(frame.payload),
            "payload": frame.payload.decode('utf-8', errors='replace') if frame.payload else "",
            "description": description,
            "raw_frame_length": len(frame.encode())
        }
        self.interactions.append(interaction)
    
    def record_response(self, frame: ProtocolFrame, description: str = "") -> None:
        """
        Record a server response.
        
        Args:
            frame: The protocol frame received
            description: Optional description of the response
        """
        interaction = {
            "timestamp": time.time(),
            "relative_time": time.time() - self.start_time,
            "type": "response",
            "direction": "server -> client",
            "command": self.protocol_handler.get_command_name(frame.cmd),
            "command_code": f"0x{frame.cmd:02x}",
            "nonce": frame.nonce,
            "payload_length": len(frame.payload),
            "payload": frame.payload.decode('utf-8', errors='replace') if frame.payload else "",
            "description": description,
            "raw_frame_length": len(frame.encode())
        }
        self.interactions.append(interaction)
    
    def record_event(self, event_type: str, description: str, details: Dict[str, Any] = None) -> None:
        """
        Record a general event (connection, disconnection, error, etc.).
        
        Args:
            event_type: Type of event (connection, disconnection, error, etc.)
            description: Description of the event
            details: Additional event details
        """
        interaction = {
            "timestamp": time.time(),
            "relative_time": time.time() - self.start_time,
            "type": "event",
            "event_type": event_type,
            "description": description,
            "details": details or {}
        }
        self.interactions.append(interaction)
    
    def save_session(self, output_dir: str = "sessions") -> str:
        """
        Save the recorded session to a JSON file.
        
        Args:
            output_dir: Directory to save session files
            
        Returns:
            str: Path to the saved session file
        """
        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Prepare session data
        session_data = {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": time.time(),
            "duration": time.time() - self.start_time,
            "total_interactions": len(self.interactions),
            "metadata": {
                "protocol_version": "MiniTel-Lite v3.0",
                "client_version": "1.0.0",
                "recorded_at": datetime.now().isoformat()
            },
            "interactions": self.interactions
        }
        
        # Save to file
        filename = f"{self.session_id}.json"
        filepath = output_path / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current session.
        
        Returns:
            Dict containing session statistics
        """
        requests = [i for i in self.interactions if i.get("type") == "request"]
        responses = [i for i in self.interactions if i.get("type") == "response"]
        events = [i for i in self.interactions if i.get("type") == "event"]
        
        return {
            "session_id": self.session_id,
            "duration": time.time() - self.start_time,
            "total_interactions": len(self.interactions),
            "requests": len(requests),
            "responses": len(responses),
            "events": len(events),
            "commands_sent": [r.get("command") for r in requests],
            "responses_received": [r.get("command") for r in responses]
        }


class SessionLoader:
    """
    Loads and provides access to recorded sessions.
    """
    
    @staticmethod
    def load_session(filepath: str) -> Dict[str, Any]:
        """
        Load a session from a JSON file.
        
        Args:
            filepath: Path to the session file
            
        Returns:
            Dict containing session data
            
        Raises:
            FileNotFoundError: If session file doesn't exist
            json.JSONDecodeError: If session file is invalid JSON
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @staticmethod
    def list_sessions(sessions_dir: str = "sessions") -> List[Dict[str, Any]]:
        """
        List all available session files.
        
        Args:
            sessions_dir: Directory containing session files
            
        Returns:
            List of session metadata
        """
        sessions_path = Path(sessions_dir)
        if not sessions_path.exists():
            return []
        
        sessions = []
        for session_file in sessions_path.glob("*.json"):
            try:
                session_data = SessionLoader.load_session(str(session_file))
                sessions.append({
                    "filename": session_file.name,
                    "filepath": str(session_file),
                    "session_id": session_data.get("session_id"),
                    "start_time": session_data.get("start_time"),
                    "duration": session_data.get("duration"),
                    "total_interactions": session_data.get("total_interactions"),
                    "recorded_at": session_data.get("metadata", {}).get("recorded_at")
                })
            except (json.JSONDecodeError, KeyError):
                # Skip invalid session files
                continue
        
        # Sort by start time (newest first)
        sessions.sort(key=lambda x: x.get("start_time", 0), reverse=True)
        return sessions
    
    @staticmethod
    def get_session_interactions(filepath: str) -> List[Dict[str, Any]]:
        """
        Get interactions from a session file.
        
        Args:
            filepath: Path to the session file
            
        Returns:
            List of interactions
        """
        session_data = SessionLoader.load_session(filepath)
        return session_data.get("interactions", [])
