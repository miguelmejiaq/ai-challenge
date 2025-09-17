# MiniTel-Lite Client Architecture

## Overview

This document describes the architecture and design decisions for the MiniTel-Lite Emergency Protocol Client, developed for the NORAD JOSHUA override mission.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MiniTel-Lite Client                     │
├─────────────────────────────────────────────────────────────┤
│  CLI Interface (client.py)                                 │
│  ├── Argument parsing                                      │
│  ├── Mission orchestration                                 │
│  └── User feedback                                         │
├─────────────────────────────────────────────────────────────┤
│  Protocol Layer (protocol.py)                              │
│  ├── Frame encoding/decoding                               │
│  ├── Hash validation (SHA-256)                             │
│  ├── Nonce management                                      │
│  └── Command definitions                                   │
├─────────────────────────────────────────────────────────────┤
│  Session Recording (session.py)                            │
│  ├── Interaction capture                                   │
│  ├── JSON serialization                                    │
│  ├── Timestamp management                                  │
│  └── Session metadata                                      │
├─────────────────────────────────────────────────────────────┤
│  TUI Replay (tui/replay.py)                               │
│  ├── Rich-based interface                                  │
│  ├── Keyboard navigation                                   │
│  ├── Timeline visualization                                │
│  └── Interaction details                                   │
├─────────────────────────────────────────────────────────────┤
│  Network Layer (client.py)                                 │
│  ├── TCP socket management                                 │
│  ├── Connection handling                                   │
│  ├── Timeout management                                    │
│  └── Error recovery                                        │
├─────────────────────────────────────────────────────────────┤
│  Utilities (utils/)                                        │
│  ├── Logging configuration                                 │
│  ├── Error handling                                        │
│  └── Helper functions                                      │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Protocol Implementation (`protocol.py`)

**Purpose**: Implements the MiniTel-Lite v3.0 protocol specification.

**Key Classes**:
- `ProtocolFrame`: Represents a single protocol frame
- `ProtocolHandler`: Manages protocol operations and nonce sequences
- `Commands`: Protocol command constants

**Design Decisions**:
- **Immutable Frames**: Protocol frames are immutable after creation
- **Automatic Hash Calculation**: SHA-256 hashes are calculated automatically
- **Strict Validation**: All frames undergo rigorous validation
- **Big-Endian Encoding**: Follows specification for network byte order

**Frame Structure**:
```
Wire Format: LEN (2 bytes) | DATA_B64 (Base64 encoded)
Binary Frame: CMD (1 byte) | NONCE (4 bytes) | PAYLOAD | HASH (32 bytes)
```

### 2. Client Implementation (`client.py`)

**Purpose**: Main client logic for executing the JOSHUA override mission.

**Key Classes**:
- `MiniTelClient`: Primary client implementation

**Design Decisions**:
- **State Management**: Clear separation of connection, authentication, and mission phases
- **Error Handling**: Comprehensive exception handling with specific error types
- **Graceful Degradation**: Continues operation even if non-critical operations fail
- **Session Integration**: Optional session recording without affecting core functionality

**Mission Flow**:
1. Connect to server
2. Authenticate with HELLO protocol
3. Execute DUMP sequence (twice as specified)
4. Send STOP command
5. Disconnect and save session

### 3. Session Recording (`session.py`)

**Purpose**: Captures all client-server interactions for analysis and replay.

**Key Classes**:
- `SessionRecorder`: Records interactions in real-time
- `SessionLoader`: Loads and manages recorded sessions

**Design Decisions**:
- **JSON Format**: Human-readable and easily parseable
- **Timestamp Precision**: Both absolute and relative timestamps
- **Metadata Rich**: Comprehensive interaction details
- **Non-Intrusive**: Recording doesn't affect protocol operation

**Session Structure**:
```json
{
  "session_id": "unique_identifier",
  "start_time": 1234567890.123,
  "duration": 45.67,
  "total_interactions": 10,
  "metadata": {
    "protocol_version": "MiniTel-Lite v3.0",
    "client_version": "1.0.0"
  },
  "interactions": [...]
}
```

### 4. TUI Replay Application (`tui/replay.py`)

**Purpose**: Interactive replay of recorded sessions.

**Key Classes**:
- `SessionReplayTUI`: Rich-based terminal interface

**Design Decisions**:
- **Rich Framework**: Modern terminal UI with colors and layouts
- **Keyboard Navigation**: Intuitive controls (N/n, P/p, Q/q)
- **Timeline View**: Visual representation of interaction sequence
- **Cross-Platform**: Works on Unix and Windows systems

**Interface Layout**:
```
┌─────────────────────────────────────────────────────────┐
│                Session Information                      │
├─────────────────┬───────────────────────────────────────┤
│   Navigation    │                                       │
│   & Timeline    │        Current Interaction            │
│                 │                                       │
├─────────────────┴───────────────────────────────────────┤
│                    Controls                             │
└─────────────────────────────────────────────────────────┘
```

## Design Patterns

### 1. Clean Architecture

- **Separation of Concerns**: Each module has a single responsibility
- **Dependency Inversion**: High-level modules don't depend on low-level details
- **Interface Segregation**: Small, focused interfaces

### 2. Error Handling Strategy

- **Custom Exceptions**: Specific exception types for different error conditions
- **Graceful Degradation**: Non-critical failures don't stop mission execution
- **Comprehensive Logging**: Detailed logging for debugging and monitoring

### 3. State Management

- **Explicit State**: Clear state transitions in protocol handler
- **Immutable Data**: Protocol frames and session data are immutable
- **Validation**: Input validation at every boundary

## Security Considerations

### 1. Protocol Security

- **Hash Validation**: SHA-256 verification of all frames
- **Nonce Sequences**: Protection against replay attacks
- **Input Validation**: Strict validation of all incoming data

### 2. Implementation Security

- **No Hardcoded Secrets**: All credentials passed as parameters
- **Safe Defaults**: Secure default configurations
- **Error Information**: Careful not to leak sensitive information in errors

### 3. Session Recording Security

- **Local Storage**: Sessions stored locally, not transmitted
- **Data Sanitization**: Binary data handled safely
- **Access Control**: Standard file system permissions

## Testing Strategy

### 1. Unit Tests

- **Protocol Layer**: Comprehensive frame encoding/decoding tests
- **Client Logic**: Mocked network interactions
- **Session Recording**: File I/O and data integrity tests

### 2. Integration Tests

- **End-to-End Scenarios**: Complete mission simulation
- **Error Conditions**: Network failures and protocol violations
- **Session Replay**: Full record/replay cycles

### 3. Coverage Requirements

- **Minimum 80%**: Code coverage requirement
- **Critical Paths**: 100% coverage for mission-critical code
- **Edge Cases**: Comprehensive edge case testing

## Performance Considerations

### 1. Network Efficiency

- **Minimal Overhead**: Efficient frame encoding
- **Connection Reuse**: Single connection for entire mission
- **Timeout Management**: Appropriate timeouts for reliability

### 2. Memory Management

- **Streaming**: Large payloads handled efficiently
- **Session Limits**: Reasonable limits on session recording
- **Garbage Collection**: Proper cleanup of resources

### 3. Scalability

- **Single Connection**: Designed for one-to-one communication
- **Session Storage**: Efficient JSON serialization
- **TUI Performance**: Responsive interface even with large sessions

## Future Enhancements

### 1. Protocol Extensions

- **Compression**: Optional payload compression
- **Encryption**: End-to-end encryption support
- **Authentication**: Enhanced authentication mechanisms

### 2. Client Features

- **Retry Logic**: Automatic retry with exponential backoff
- **Configuration**: External configuration file support
- **Monitoring**: Real-time connection monitoring

### 3. Analysis Tools

- **Session Analysis**: Statistical analysis of sessions
- **Performance Metrics**: Timing and throughput analysis
- **Visualization**: Graphical session visualization

## Conclusion

The MiniTel-Lite client architecture prioritizes:

1. **Reliability**: Robust error handling and validation
2. **Maintainability**: Clean, well-documented code
3. **Testability**: Comprehensive test coverage
4. **Security**: Secure protocol implementation
5. **Usability**: Intuitive interfaces and clear feedback

This architecture successfully implements the MiniTel-Lite v3.0 protocol while providing comprehensive session recording and replay capabilities, meeting all requirements of the NORAD JOSHUA override mission.
