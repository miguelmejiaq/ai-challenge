# MiniTel-Lite Emergency Protocol Client

## Overview

This is a Python implementation of the MiniTel-Lite Emergency Protocol client for the NORAD JOSHUA override mission. The client connects to the MiniTel-Lite server, authenticates using the HELLO protocol, and retrieves emergency override codes by executing the DUMP command twice.

## Architecture

The project follows clean architecture principles with clear separation of concerns:

```
src/
├── minitel/
│   ├── __init__.py
│   ├── client.py          # Main MiniTel client implementation
│   ├── protocol.py        # Protocol frame encoding/decoding
│   ├── session.py         # Session recording functionality
│   └── exceptions.py      # Custom exceptions
├── tui/
│   ├── __init__.py
│   └── replay.py          # TUI replay application
└── utils/
    ├── __init__.py
    └── logging.py         # Logging configuration
```

## Key Design Decisions

1. **Protocol Implementation**: Strict adherence to MiniTel-Lite v3.0 specification with proper frame encoding/decoding
2. **Session Recording**: JSON-based recording with timestamps for all client-server interactions
3. **Error Handling**: Comprehensive error handling for network issues, protocol violations, and server disconnections
4. **Testing**: Extensive test coverage with mocked server responses and edge case handling
5. **Security**: No hardcoded credentials, proper hash validation, secure connection handling

## Features

- **TCP Client**: Connects to MiniTel-Lite server with proper timeout handling
- **Protocol Compliance**: Full implementation of MiniTel-Lite v3.0 protocol
- **Session Recording**: Captures all interactions with timestamps
- **TUI Replay**: Interactive replay of recorded sessions
- **Graceful Disconnection Handling**: Robust handling of server disconnections
- **Comprehensive Logging**: Detailed logging for debugging and monitoring

## Installation

```bash
# Set up the project (creates virtual environment and installs dependencies)
make setup

# Or use the alias
make install
```

## Usage

### Basic Client Usage

**Important**: You must specify the server host and port. No default values are provided for security reasons.

```bash
# Execute JOSHUA override mission with session recording
make run SERVER_HOST=<server_host> SERVER_PORT=<server_port>

# Execute with verbose logging
make run-verbose SERVER_HOST=<server_host> SERVER_PORT=<server_port>

# Execute without session recording
make run-no-record SERVER_HOST=<server_host> SERVER_PORT=<server_port>

# Quick mission execution (alias for run)
make mission SERVER_HOST=<server_host> SERVER_PORT=<server_port>
```

### Session Management

```bash
# List all recorded sessions
make list-sessions

# Replay a specific session
make replay SESSION_FILE=session_20250917_113136.json

# Replay the most recent session
make replay-latest
```

### Configuration

You can set environment variables or pass them to make commands:

```bash
# Using environment variables
export SERVER_HOST=<HOST_ID>
export SERVER_PORT=<HOST_PORT>
export TIMEOUT=5.0
make run

# Or pass directly to make
make run SERVER_HOST=192.168.1.100 SERVER_PORT=8080 TIMEOUT=10.0
```

## Testing

```bash
# Run all tests with coverage
make test-all SERVER_HOST=<server_host> SERVER_PORT=<server_port>

# Run only unit tests (fast)
make test-unit

# Run integration tests with real server
make test-integration SERVER_HOST=<server_host> SERVER_PORT=<server_port>

# Run tests without coverage (faster)
make test-fast

# Run specific test categories
make test-client    # Client tests only
make test-protocol  # Protocol tests only
```

## Development Commands

```bash
# Show all available commands
make help

# Show current configuration
make config

# Show project status
make status

# Verify requirements compliance
make verify

# Clean up cache files
make clean

# Clean up everything (cache + sessions)
make clean-all
```

## Protocol Specification

The client implements MiniTel-Lite Protocol v3.0:

- **Frame Format**: `LEN (2 bytes, big-endian) | DATA_B64 (Base64 encoded)`
- **Binary Frame**: `CMD (1 byte) | NONCE (4 bytes, big-endian) | PAYLOAD | HASH (32 bytes SHA-256)`
- **Commands**: HELLO (0x01), DUMP (0x02), STOP_CMD (0x04)
- **Nonce Sequence**: Proper nonce tracking and validation
- **Connection Timeout**: 2-second timeout handling

## Edge Cases Handled

1. **Server Disconnections**: Automatic reconnection attempts with exponential backoff
2. **Protocol Violations**: Proper error handling for malformed frames
3. **Hash Validation**: Strict SHA-256 hash verification
4. **Nonce Mismatches**: Detection and handling of sequence errors
5. **Network Timeouts**: Graceful timeout handling with retry logic

## Security Considerations

- No hardcoded credentials or secrets
- Proper hash validation for all frames
- Secure connection handling
- Input validation and sanitization
- Logging without exposing sensitive data

## Mission Completion

The client successfully:
1. Connects to the MiniTel-Lite server
2. Authenticates using HELLO protocol
3. Executes DUMP command twice to retrieve override code
4. Records all interactions for replay
5. Handles disconnections gracefully
6. Provides comprehensive logging and error handling
