import asyncio
import tempfile
import os
import json
import logging
import time
from typing import Optional, Dict, Any
from fastapi import WebSocket
from dotenv import load_dotenv
from celery import Celery
from celery.result import AsyncResult

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Configure Celery
celery_app = Celery('python_executor')
celery_app.config_from_object('celery_config.CELERY_CONFIG')

@celery_app.task(bind=True)
def execute_python_code(self, code: str, execution_id: str):
    """Execute Python code in a Celery worker with timeout protection"""
    try:
        # Create temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name
        
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
            
            # Return results
            return {
                'status': 'success',
                'stdout': stdout_content,
                'stderr': stderr_content,
                'exit_code': 0
            }
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass
                
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'exit_code': 1
        }

class PythonExecutor:
    def __init__(self, timeout: int = None):
        self.timeout = timeout or int(os.getenv("PYTHON_EXECUTION_TIMEOUT", 30))
        self._active_executions: Dict[str, Dict[str, Any]] = {}
    
    async def execute_and_stream(self, code: str, websocket: WebSocket):
        """Execute Python code and stream results in real-time using Celery"""
        
        # Generate unique execution ID
        execution_id = f"exec_{int(time.time() * 1000)}_{os.getpid()}"
        
        try:
            # Send execution start message
            await websocket.send_text(json.dumps({
                "type": "execution_start",
                "execution_id": execution_id,
                "message": "Starting Python execution..."
            }))
            
            # Submit task to Celery
            task = execute_python_code.delay(code, execution_id)
            
            # Store execution info
            self._active_executions[execution_id] = {
                'task_id': task.id,
                'websocket': websocket,
                'start_time': time.time()
            }
            
            # Monitor task progress
            start_time = time.time()
            while not task.ready():
                # Check for timeout
                if time.time() - start_time > self.timeout:
                    logger.warning(f"Execution {execution_id} timed out after {self.timeout} seconds")
                    await self._force_terminate_task(execution_id)
                    return
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
            
            # Get task result
            result = task.get()
            
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
    
    async def _force_terminate_task(self, execution_id: str):
        """Forcefully terminate a running Celery task"""
        if execution_id not in self._active_executions:
            return
        
        execution_info = self._active_executions[execution_id]
        task_id = execution_info['task_id']
        websocket = execution_info.get('websocket')
        
        try:
            # Revoke the task (this will terminate it)
            celery_app.control.revoke(task_id, terminate=True, signal='SIGKILL')
            
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "timeout",
                    "execution_id": execution_id,
                    "message": f"Execution timed out after {self.timeout} seconds. Did you check for infinite loops?"
                }))
            
        except Exception as e:
            logger.error(f"Error terminating task {execution_id}: {e}")
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
        
        await self._force_terminate_task(execution_id)
        return True
    
    def get_active_executions(self):
        """Get list of active execution IDs"""
        return list(self._active_executions.keys())
