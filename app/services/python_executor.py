import asyncio
import subprocess
import tempfile
import os
import signal
import json
from typing import Optional
from fastapi import WebSocket
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class PythonExecutor:
    def __init__(self, timeout: int = None):
        self.timeout = timeout or int(os.getenv("PYTHON_EXECUTION_TIMEOUT", 30))
    
    async def execute_and_stream(self, code: str, websocket: WebSocket):
        """Execute Python code and stream results in real-time"""
        
        # Create temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name
        
        try:
            # Send execution start message
            await websocket.send_text(json.dumps({
                "type": "execution_start",
                "message": "Starting Python execution..."
            }))
            
            # Execute Python code with timeout
            process = await asyncio.create_subprocess_exec(
                'python', temp_file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Stream stdout in real-time
            stdout_task = asyncio.create_task(self._stream_output(process.stdout, websocket, "stdout"))
            stderr_task = asyncio.create_task(self._stream_output(process.stderr, websocket, "stderr"))
            
            # Wait for process to complete or timeout
            try:
                await asyncio.wait_for(process.wait(), timeout=self.timeout)
            except asyncio.TimeoutError:
                # Kill process if it times out
                process.terminate()
                await websocket.send_text(json.dumps({
                    "type": "timeout",
                    "message": f"Execution timed out after {self.timeout} seconds. Did you check for infinite loops?"
                }))
                return
            
            # Wait for streaming to complete
            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
            
            # Send completion message
            await websocket.send_text(json.dumps({
                "type": "execution_complete",
                "message": f"Execution completed with exit code: {process.returncode}. {'Success!' if process.returncode == 0 else 'Code completed but may have encountered errors.'}"
            }))
            
        except Exception as e:
            logger.error(f"Error executing Python code: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Execution error occurred: {str(e)}. Please check your code syntax and try again."
            }))
        
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass
    
    async def _stream_output(self, stream: Optional[asyncio.StreamReader], websocket: WebSocket, output_type: str):
        """Stream output from a process stream to WebSocket"""
        if stream is None:
            return
            
        try:
            while True:
                line = await stream.readline()
                if not line:
                    break
                    
                # Decode and send the line
                output_line = line.decode('utf-8', errors='replace').rstrip()
                if output_line:  # Only send non-empty lines
                    await websocket.send_text(json.dumps({
                        "type": output_type,
                        "content": output_line
                    }))
                    
        except Exception as e:
            logger.error(f"Error streaming {output_type}: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Error occurred while streaming {output_type} output: {str(e)}. Please try again."
            }))
