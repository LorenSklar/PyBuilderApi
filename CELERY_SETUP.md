# Celery Setup for Python Code Execution

This project now uses Celery for robust Python code execution with proper timeout handling and process isolation.

## Prerequisites

1. **Redis Server** - Required as the message broker and result backend
2. **Python Dependencies** - Install with `pip install -r requirements.txt`

## Installation

1. Install Redis:
   ```bash
   # macOS with Homebrew
   brew install redis
   
   # Ubuntu/Debian
   sudo apt-get install redis-server
   
   # Or use Docker
   docker run -d -p 6379:6379 redis:alpine
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the System

### 1. Start Redis Server
```bash
redis-server
```

### 2. Start Celery Worker
```bash
# In a separate terminal
celery -A app.services.python_executor worker --loglevel=info
```

### 3. Start Your FastAPI Application
```bash
python main.py
```

## Configuration

The system is configured via environment variables:

- `REDIS_URL`: Redis connection string (default: `redis://localhost:6379/0`)
- `PYTHON_EXECUTION_TIMEOUT`: Execution timeout in seconds (default: 30)

## How It Works

1. **Task Submission**: When code is submitted, it's sent to Celery as a task
2. **Worker Execution**: A Celery worker picks up the task and executes it in isolation
3. **Timeout Protection**: Built-in soft/hard time limits prevent infinite loops
4. **Result Handling**: Results are captured and streamed back via WebSocket
5. **Process Isolation**: Each execution runs in its own worker process

## Benefits of Celery

- **Robust Timeout Handling**: Soft/hard time limits with graceful termination
- **Process Isolation**: Bad code can't affect other executions
- **Scalability**: Can run multiple workers across multiple machines
- **Monitoring**: Built-in task monitoring and result storage
- **Error Handling**: Robust error handling and recovery mechanisms

## Testing

Run the test suite:
```bash
bash run_tests.sh
```

The tests use mocked Celery tasks to avoid requiring a running Redis server during testing.

## Troubleshooting

### Common Issues

1. **Redis Connection Error**: Make sure Redis is running and accessible
2. **Worker Not Starting**: Check that all dependencies are installed
3. **Tasks Not Executing**: Verify the worker is running and connected to Redis

### Debug Mode

Enable debug logging:
```bash
celery -A app.services.python_executor worker --loglevel=debug
```
