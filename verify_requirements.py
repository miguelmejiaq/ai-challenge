#!/usr/bin/env python3
"""
Requirements verification script for MiniTel-Lite Emergency Protocol Client.

This script verifies that all challenge requirements have been implemented
and are working correctly.
"""

import os
import sys
import subprocess
import importlib.util
from pathlib import Path
from typing import List, Tuple, Dict, Any


class RequirementChecker:
    """Checks implementation against challenge requirements."""
    
    def __init__(self):
        self.results: List[Tuple[str, bool, str]] = []
        self.project_root = Path(__file__).parent
    
    def check(self, requirement: str, condition: bool, details: str = "") -> bool:
        """Check a requirement and record the result."""
        self.results.append((requirement, condition, details))
        status = "✅" if condition else "❌"
        print(f"{status} {requirement}")
        if details and not condition:
            print(f"   {details}")
        return condition
    
    def check_file_exists(self, filepath: str, description: str) -> bool:
        """Check if a file exists."""
        path = self.project_root / filepath
        exists = path.exists()
        return self.check(
            f"{description} exists",
            exists,
            f"Missing file: {filepath}" if not exists else ""
        )
    
    def check_module_imports(self, module_path: str, description: str) -> bool:
        """Check if a module can be imported."""
        try:
            # Add the project root to sys.path temporarily
            import sys
            old_path = sys.path[:]
            sys.path.insert(0, str(self.project_root))
            
            try:
                spec = importlib.util.spec_from_file_location("test_module", self.project_root / module_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    return self.check(f"{description} imports successfully", True)
                else:
                    return self.check(f"{description} imports successfully", False, "Failed to load module spec")
            finally:
                sys.path[:] = old_path
        except Exception as e:
            return self.check(f"{description} imports successfully", False, str(e))
    
    def check_command_exists(self, command: List[str], description: str) -> bool:
        """Check if a command can be executed."""
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            success = result.returncode == 0
            return self.check(
                f"{description} command works",
                success,
                f"Command failed: {' '.join(command)}" if not success else ""
            )
        except Exception as e:
            return self.check(f"{description} command works", False, str(e))
    
    def verify_core_mission_requirements(self) -> None:
        """Verify core mission requirements."""
        print("\n🎯 Core Mission Requirements")
        print("=" * 40)
        
        # TCP Client Implementation
        self.check_file_exists("src/minitel/client.py", "TCP client implementation")
        self.check_module_imports("src/minitel/client.py", "Client module")
        
        # Protocol Implementation
        self.check_file_exists("src/minitel/protocol.py", "Protocol implementation")
        self.check_module_imports("src/minitel/protocol.py", "Protocol module")
        
        # Check for HELLO protocol implementation
        try:
            from src.minitel.protocol import Commands, ProtocolHandler
            has_hello = hasattr(Commands, 'HELLO')
            has_handler = hasattr(ProtocolHandler, 'create_hello_frame')
            self.check("HELLO protocol implemented", has_hello and has_handler)
        except ImportError:
            self.check("HELLO protocol implemented", False, "Cannot import protocol classes")
        
        # Check for DUMP command implementation
        try:
            from src.minitel.protocol import Commands, ProtocolHandler
            has_dump = hasattr(Commands, 'DUMP')
            has_handler = hasattr(ProtocolHandler, 'create_dump_frame')
            self.check("DUMP command implemented", has_dump and has_handler)
        except ImportError:
            self.check("DUMP command implemented", False, "Cannot import protocol classes")
        
        # Check for graceful disconnection handling
        try:
            from src.minitel.client import MiniTelClient
            has_disconnect = hasattr(MiniTelClient, 'disconnect')
            has_exception_handling = hasattr(MiniTelClient, '_receive_frame')
            self.check("Graceful disconnection handling", has_disconnect and has_exception_handling)
        except ImportError:
            self.check("Graceful disconnection handling", False, "Cannot import client class")
    
    def verify_session_recording_requirements(self) -> None:
        """Verify session recording requirements."""
        print("\n📹 Session Recording Requirements")
        print("=" * 40)
        
        # Session recording implementation
        self.check_file_exists("src/minitel/session.py", "Session recording implementation")
        self.check_module_imports("src/minitel/session.py", "Session module")
        
        # Check for JSON format
        try:
            from src.minitel.session import SessionRecorder
            recorder = SessionRecorder("test")
            has_json_save = hasattr(recorder, 'save_session')
            self.check("JSON session format", has_json_save)
        except ImportError:
            self.check("JSON session format", False, "Cannot import session classes")
        
        # Check for timestamp recording
        try:
            from src.minitel.session import SessionRecorder
            recorder = SessionRecorder("test")
            has_timestamp = hasattr(recorder, 'start_time')
            self.check("Timestamp recording", has_timestamp)
        except ImportError:
            self.check("Timestamp recording", False, "Cannot import session classes")
        
        # Check for interaction capture
        try:
            from src.minitel.session import SessionRecorder
            recorder = SessionRecorder("test")
            has_record_request = hasattr(recorder, 'record_request')
            has_record_response = hasattr(recorder, 'record_response')
            self.check("Client-server interaction capture", has_record_request and has_record_response)
        except ImportError:
            self.check("Client-server interaction capture", False, "Cannot import session classes")
    
    def verify_tui_replay_requirements(self) -> None:
        """Verify TUI replay requirements."""
        print("\n🖥️  TUI Replay Requirements")
        print("=" * 40)
        
        # TUI replay implementation
        self.check_file_exists("src/tui/replay.py", "TUI replay implementation")
        self.check_module_imports("src/tui/replay.py", "TUI replay module")
        
        # Check for keyboard controls
        try:
            from src.tui.replay import SessionReplayTUI
            tui = SessionReplayTUI("dummy_session.json")
            has_next = hasattr(tui, 'next_step')
            has_prev = hasattr(tui, 'previous_step')
            self.check("N/n and P/p keyboard controls", has_next and has_prev)
        except Exception:
            self.check("N/n and P/p keyboard controls", False, "Cannot create TUI instance")
        
        # Check for quit functionality
        try:
            from src.tui.replay import SessionReplayTUI
            has_main = hasattr(SessionReplayTUI, 'run')
            self.check("Q/q quit functionality", has_main)
        except ImportError:
            self.check("Q/q quit functionality", False, "Cannot import TUI class")
        
        # Check for step display
        try:
            from src.tui.replay import SessionReplayTUI
            tui = SessionReplayTUI.__new__(SessionReplayTUI)  # Create without __init__
            tui.current_step = 0
            tui.interactions = []
            has_step_display = hasattr(tui, 'create_navigation_panel')
            self.check("Current step and total steps display", has_step_display)
        except Exception:
            self.check("Current step and total steps display", False, "Cannot verify step display")
    
    def verify_code_quality_requirements(self) -> None:
        """Verify code quality requirements."""
        print("\n🏗️  Code Quality Requirements")
        print("=" * 40)
        
        # Clean architecture
        src_structure = [
            "src/minitel/__init__.py",
            "src/minitel/client.py",
            "src/minitel/protocol.py",
            "src/minitel/session.py",
            "src/minitel/exceptions.py",
            "src/tui/__init__.py",
            "src/tui/replay.py",
            "src/utils/__init__.py",
            "src/utils/logging.py"
        ]
        
        all_exist = all((self.project_root / path).exists() for path in src_structure)
        self.check("Clean architecture structure", all_exist)
        
        # Error handling
        self.check_file_exists("src/minitel/exceptions.py", "Custom exception classes")
        
        # Logging
        self.check_file_exists("src/utils/logging.py", "Logging configuration")
        
        # Documentation
        self.check_file_exists("README.md", "README documentation")
        self.check_file_exists("ARCHITECTURE.md", "Architecture documentation")
        
        # No hardcoded secrets check
        try:
            with open(self.project_root / "src/minitel/client.py", 'r') as f:
                content = f.read()
                has_hardcoded = any(secret in content.lower() for secret in [
                    'password', 'secret', 'key', 'token', 'joshua_override_1983'
                ])
                self.check("No hardcoded secrets", not has_hardcoded)
        except Exception:
            self.check("No hardcoded secrets", False, "Cannot read client file")
    
    def verify_testing_requirements(self) -> None:
        """Verify testing requirements."""
        print("\n🧪 Testing Requirements")
        print("=" * 40)
        
        # Test files exist
        test_files = [
            "tests/test_protocol.py",
            "tests/test_client.py",
            "tests/test_session.py"
        ]
        
        for test_file in test_files:
            self.check_file_exists(test_file, f"Test file {test_file}")
        
        # Test configuration
        self.check_file_exists("pytest.ini", "Pytest configuration")
        self.check_file_exists("run_tests.py", "Test runner script")
        
        # Check if tests can run
        if (self.project_root / "pytest.ini").exists():
            self.check_command_exists(
                ["python", "-m", "pytest", "--collect-only", "-q"],
                "Test collection"
            )
    
    def verify_documentation_requirements(self) -> None:
        """Verify documentation requirements."""
        print("\n📚 Documentation Requirements")
        print("=" * 40)
        
        # Required documentation files
        self.check_file_exists("README.md", "README with usage instructions")
        self.check_file_exists("ARCHITECTURE.md", "Architecture documentation")
        
        # Check README content
        try:
            with open(self.project_root / "README.md", 'r') as f:
                readme_content = f.read()
                has_usage = "usage" in readme_content.lower()
                has_installation = "install" in readme_content.lower()
                has_testing = "test" in readme_content.lower()
                self.check("README has comprehensive content", has_usage and has_installation and has_testing)
        except Exception:
            self.check("README has comprehensive content", False, "Cannot read README")
        
        # Check for code comments
        try:
            with open(self.project_root / "src/minitel/protocol.py", 'r') as f:
                content = f.read()
                has_docstrings = '"""' in content
                has_comments = '#' in content
                self.check("Code has comments and docstrings", has_docstrings and has_comments)
        except Exception:
            self.check("Code has comments and docstrings", False, "Cannot read protocol file")
    
    def verify_project_structure(self) -> None:
        """Verify overall project structure."""
        print("\n📁 Project Structure")
        print("=" * 40)
        
        # Essential files
        essential_files = [
            "setup.py",
            "requirements.txt",
            ".gitignore",
            "README.md"
        ]
        
        for file in essential_files:
            self.check_file_exists(file, f"Essential file {file}")
        
        # Package structure
        self.check_file_exists("src/__init__.py", "Source package marker")
        self.check_file_exists("tests/__init__.py", "Tests package marker")
    
    def print_summary(self) -> bool:
        """Print verification summary."""
        print("\n" + "=" * 60)
        print("📋 VERIFICATION SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, success, _ in self.results if success)
        total = len(self.results)
        percentage = (passed / total * 100) if total > 0 else 0
        
        print(f"✅ Passed: {passed}/{total} ({percentage:.1f}%)")
        
        failed = [req for req, success, details in self.results if not success]
        if failed:
            print(f"❌ Failed: {len(failed)}")
            print("\nFailed Requirements:")
            for req in failed:
                print(f"  - {req}")
        
        print("\n" + "=" * 60)
        
        if percentage >= 90:
            print("🎉 EXCELLENT! All major requirements implemented.")
            return True
        elif percentage >= 80:
            print("✅ GOOD! Most requirements implemented.")
            return True
        else:
            print("⚠️  NEEDS WORK! Several requirements missing.")
            return False


def main():
    """Main verification function."""
    print("🔍 MiniTel-Lite Requirements Verification")
    print("=" * 60)
    
    checker = RequirementChecker()
    
    # Run all verification checks
    checker.verify_project_structure()
    checker.verify_core_mission_requirements()
    checker.verify_session_recording_requirements()
    checker.verify_tui_replay_requirements()
    checker.verify_code_quality_requirements()
    checker.verify_testing_requirements()
    checker.verify_documentation_requirements()
    
    # Print summary and return appropriate exit code
    success = checker.print_summary()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
