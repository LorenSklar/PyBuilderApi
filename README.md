# Python Sandbox API

A WebSocket-based Python execution sandbox for learning purposes. This backend allows students to write Python code and see the results streamed back in real-time.

## Features

- **Real-time execution**: See Python output as it happens
- **WebSocket streaming**: Immediate feedback for learning
- **Safe execution**: Timeout protection and process isolation
- **FastAPI backend**: Modern, fast Python web framework

## Project Structure

```
pybuilderapi/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── websocket.py      # WebSocket endpoint handling
│   ├── services/
│   │   ├── __init__.py
│   │   └── python_executor.py # Python code execution service
│   └── __init__.py
├── main.py                    # FastAPI application entry point
├── requirements.txt           # Python dependencies
└── README.md
```

## Installation

### Quick Start (Recommended)
```bash
bash run.sh
```

This script will:
- Check Python version requirements (3.8+)
- Create a virtual environment
- Install all dependencies
- Start the server

### Manual Installation
If you prefer to set up manually:

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
python main.py
```

The server will start on `http://localhost:8000`

## WebSocket Usage

Connect to `ws://localhost:8000/ws/python` and send JSON messages:

```json
{
  "type": "execute",
  "code": "print('Hello, World!')\nfor i in range(5):\n    print(f'Count: {i}')"
}
```

## Message Types

- `execution_start`: Sent when execution begins
- `stdout`: Standard output from Python code
- `stderr`: Standard error from Python code
- `execution_complete`: Sent when execution finishes
- `timeout`: Sent if execution exceeds timeout limit
- `error`: Sent if any errors occur

## Deployment

### **Current Platform: Render/Railway (Recommended)**

This backend is optimized for **Render** or **Railway** deployment, which handle many production concerns automatically:

#### **What They Handle For You**
- **Containerization**: Automatic Docker containerization
- **Process management**: Auto-restart, scaling, health monitoring
- **Basic logging**: Built-in log aggregation and viewing
- **Environment variables**: Easy .env management through their UI
- **SSL/TLS**: Automatic HTTPS certificates

#### **Why This Choice**
- **Simplified deployment**: Focus on learning WebSockets/FastAPI, not DevOps
- **Production-ready**: Handles scaling and monitoring automatically
- **Cost-effective**: Free tiers available for learning projects
- **Fast iteration**: Easy to deploy and test changes

### **Alternative Deployment Options**

If you need to deploy elsewhere, here are the additional components you'll need:

#### **Self-Hosted (VPS/Dedicated Server)**
```bash
# Add to requirements.txt
gunicorn
uvicorn[standard]

# Add process manager (systemd, supervisor, or PM2)
# Add reverse proxy (nginx, Caddy)
# Add SSL certificates (Let's Encrypt)
# Add containerization (Docker)
```

#### **Docker Deployment**
```dockerfile
# Create Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["python", "main.py"]
```

#### **Advanced Logging & Monitoring**
```python
# Add structured logging
import structlog
logger = structlog.get_logger()

# Add metrics
from prometheus_client import Counter, Histogram
# Add health checks with detailed status
```

## Security Notes

⚠️ **Warning**: This sandbox executes arbitrary Python code. In production, consider:
- Container isolation
- Resource limits
- Network restrictions
- User authentication
