import asyncio
import tempfile
import os
import json
import logging
import time
import multiprocessing
from typing import Optional, Dict, Any
from fastapi import WebSocket
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

def execute_code_in_process(code: str, result_queue: multiprocessing.Queue):
    """Execute Python code in a separate process and send results back via queue"""
    try:
        # Capture stdout and stderr
        import sys
        from io import StringIO
        
        # Redirect stdout and stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        stdout_capture = StringIO()
        stderr_capture = StringIO()
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        
        # Execute the code
        exec_globals = {'__builtins__': __builtins__}
        exec(code, exec_globals)
        
        # Get captured output
        stdout_content = stdout_capture.getvalue()
        stderr_content = stderr_capture.getvalue()
        
        # Restore stdout and stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        
        # Send results back to parent process
        result_queue.put({
            'status': 'success',
            'stdout': stdout_content,
            'stderr': stderr_content,
            'exit_code': 0
        })
        
    except Exception as e:
        # Send error back to parent process
        result_queue.put({
            'status': 'error',
            'error': str(e),
            'exit_code': 1
        })

class PythonExecutor:
    def __init__(self, timeout: int = None):
        self.timeout = timeout or int(os.getenv("PYTHON_EXECUTION_TIMEOUT", 30))
        self._active_executions: Dict[str, Dict[str, Any]] = {}
    
    async def execute_and_stream(self, code: str, websocket: WebSocket):
        """Execute Python code and stream results in real-time using multiprocessing"""
        
        # Generate unique execution ID
        execution_id = f"exec_{int(time.time() * 1000)}_{os.getpid()}"
        
        try:
            # Send execution start message
            await websocket.send_text(json.dumps({
                "type": "execution_start",
                "execution_id": execution_id,
                "message": "Starting Python execution..."
            }))
            
            # Create a queue for communication between processes
            result_queue = multiprocessing.Queue()
            
            # Create and start the process
            process = multiprocessing.Process(
                target=execute_code_in_process,
                args=(code, result_queue)
            )
            
            # Store execution info
            self._active_executions[execution_id] = {
                'process': process,
                'websocket': websocket,
                'start_time': time.time()
            }
            
            process.start()
            
            # Wait for process to complete with timeout
            start_time = time.time()
            process.join(timeout=self.timeout)
            
            # Check if process is still alive (timed out)
            if process.is_alive():
                logger.warning(f"Execution {execution_id} timed out after {self.timeout} seconds")
                await self._force_terminate_process(execution_id)
                return
            
            # Get result from queue
            try:
                result = result_queue.get(timeout=1)  # 1 second timeout for getting result
            except Exception as e:
                logger.error(f"Error getting result from queue: {e}")
                result = {
                    'status': 'error',
                    'error': 'Failed to get execution result',
                    'exit_code': 1
                }
            
            # Stream output
            if result.get('stdout'):
                for line in result['stdout'].splitlines():
                    if line.strip():
                        await websocket.send_text(json.dumps({
                            "type": "stdout",
                            "content": line
                        }))
            
            if result.get('stderr'):
                for line in result['stderr'].splitlines():
                    if line.strip():
                        await websocket.send_text(json.dumps({
                            "type": "stderr",
                            "content": line
                        }))
            
            # Send completion message
            if result['status'] == 'success':
                await websocket.send_text(json.dumps({
                    "type": "execution_complete",
                    "message": f"Execution completed with exit code: {result.get('exit_code', 0)}"
                }))
            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Execution failed: {result.get('error', 'Unknown error')}"
                }))
            
        except Exception as e:
            logger.error(f"Error executing Python code: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"Execution error occurred: {str(e)}. Please check your code syntax and try again."
            }))
            
        finally:
            # Clean up execution record
            if execution_id in self._active_executions:
                del self._active_executions[execution_id]
    
    async def _force_terminate_process(self, execution_id: str):
        """Forcefully terminate a running process"""
        if execution_id not in self._active_executions:
            return
        
        execution_info = self._active_executions[execution_id]
        process = execution_info['process']
        websocket = execution_info.get('websocket')
        
        try:
            # Try graceful termination first
            process.terminate()
            process.join(timeout=2)
            
            # If still alive, force kill
            if process.is_alive():
                logger.warning(f"Force killing process {execution_id}")
                process.kill()
                process.join(timeout=1)
            
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "timeout",
                    "execution_id": execution_id,
                    "message": f"Execution timed out after {self.timeout} seconds. Did you check for infinite loops?"
                }))
            
        except Exception as e:
            logger.error(f"Error terminating process {execution_id}: {e}")
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Error terminating execution: {str(e)}"
                }))
        
        finally:
            # Clean up execution record
            if execution_id in self._active_executions:
                del self._active_executions[execution_id]
    
    async def stop_execution(self, execution_id: str) -> bool:
        """Stop a running execution"""
        if execution_id not in self._active_executions:
            return False
        
        await self._force_terminate_process(execution_id)
        return True
    
    def get_active_executions(self):
        """Get list of active execution IDs"""
        return list(self._active_executions.keys())
