# Simple Multiprocessing Setup for Python Code Execution

This project now uses a lightweight multiprocessing approach for robust Python code execution with proper timeout handling and process isolation.

## Overview

The system uses Python's built-in `multiprocessing` module to:
- Execute student code in isolated processes
- Prevent infinite loops from freezing the main server
- Provide clean timeout handling and process termination
- Keep the implementation simple and lightweight

## Prerequisites

1. **Python 3.7+** - Built-in multiprocessing support
2. **Python Dependencies** - Install with `pip install -r requirements.txt`

## Installation

Install Python dependencies:
```bash
pip install -r requirements.txt
```

That's it! No additional services or servers required.

## How It Works

1. **Task Submission**: When code is submitted, it's sent to a new multiprocessing process
2. **Process Execution**: The code runs in complete isolation from the main FastAPI process
3. **Timeout Protection**: Built-in timeout handling prevents infinite loops
4. **Result Handling**: Results are captured and streamed back via WebSocket
5. **Process Isolation**: Each execution runs in its own process

## Benefits of This Approach

- **Lightweight**: No external dependencies or services
- **Simple**: Uses only Python standard library
- **Robust**: Proper process isolation and timeout handling
- **Fast**: No network overhead or serialization delays
- **Reliable**: Built-in multiprocessing reliability

## Configuration

The system is configured via environment variables:

- `PYTHON_EXECUTION_TIMEOUT`: Execution timeout in seconds (default: 30)

## Running the System

Just start your FastAPI application:
```bash
python main.py
```

No additional processes or services needed!

## Testing

Run the test suite:
```bash
bash run_tests.sh
```

The tests verify that the multiprocessing system properly handles:
- Normal code execution
- Syntax errors
- Infinite loops with timeout
- Manual execution stopping
- Concurrent executions

## Demo

Run the demo script to see the system in action:
```bash
python demo_infinite_loop.py
```

This demonstrates both normal execution and infinite loop timeout handling.

## Troubleshooting

### Common Issues

1. **Process Not Starting**: Check that multiprocessing is supported on your platform
2. **Timeout Not Working**: Verify the timeout value is reasonable
3. **Memory Issues**: Long-running processes are automatically terminated

### Debug Mode

Enable debug logging in your FastAPI app to see detailed execution logs.

## Why This Approach?

This solution is perfect for:
- **Development environments** - Simple setup, no external dependencies
- **Learning platforms** - Lightweight, easy to understand
- **Single-machine deployments** - No need for distributed systems
- **Prototyping** - Quick to implement and test

The multiprocessing approach provides all the safety and isolation benefits without the complexity of message queues or distributed systems.
