#!/usr/bin/env python3
"""
Test suite for the Celery-based PythonExecutor
"""

import asyncio
import json
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.python_executor import PythonExecutor

# Mock Celery for testing
class MockCeleryTask:
    def __init__(self, task_id="mock_task_123"):
        self.id = task_id
        self._ready = False
        self._result = None
    
    def ready(self):
        return self._ready
    
    def get(self):
        return self._result
    
    def set_ready(self, ready=True):
        self._ready = ready
    
    def set_result(self, result):
        self._result = result

class MockCeleryApp:
    def __init__(self):
        self.control = MockCeleryControl()

class MockCeleryControl:
    def revoke(self, task_id, terminate=True, signal='SIGKILL'):
        pass

class MockWebSocket:
    """Mock WebSocket for testing"""
    def __init__(self):
        self.messages = []
        self.closed = False
    
    async def send_text(self, message):
        if not self.closed:
            parsed_message = json.loads(message)
            self.messages.append(parsed_message)
            print(f"DEBUG: MockWebSocket received: {parsed_message}")  # Debug output
    
    def get_messages_by_type(self, msg_type):
        return [msg for msg in self.messages if msg.get("type") == msg_type]
    
    def print_all_messages(self):
        """Debug method to print all received messages"""
        print(f"DEBUG: All messages received: {self.messages}")


@pytest.fixture
def executor():
    """Create a PythonExecutor instance for testing"""
    return PythonExecutor(timeout=5)  # 5 second timeout for testing


@pytest.fixture
def websocket():
    """Create a mock WebSocket for testing"""
    return MockWebSocket()


class TestPythonExecutor:
    """Test cases for PythonExecutor"""
    
    def test_init(self, executor):
        """Test executor initialization"""
        assert executor.timeout == 5
        assert executor._active_executions == {}
    
    def test_init_with_env_timeout(self):
        """Test executor initialization with environment variable"""
        # This would test the os.getenv fallback, but we'll keep it simple
        executor = PythonExecutor()
        assert executor.timeout > 0
    
    @pytest.mark.asyncio
    @patch('app.services.python_executor.execute_python_code')
    async def test_simple_execution(self, mock_task_func, executor, websocket):
        """Test simple Python code execution"""
        # Mock the Celery task
        mock_task = MockCeleryTask()
        mock_task.set_result({
            'status': 'success',
            'stdout': 'Hello, World!\n',
            'stderr': '',
            'exit_code': 0
        })
        mock_task.set_ready(True)
        mock_task_func.delay.return_value = mock_task
        
        code = 'print("Hello, World!")'
        
        await executor.execute_and_stream(code, websocket)
        
        # Debug: Print all messages received
        websocket.print_all_messages()
        
        # Check that execution started
        start_msgs = websocket.get_messages_by_type("execution_start")
        assert len(start_msgs) == 1
        assert "execution_id" in start_msgs[0]
        
        # Check that execution completed
        complete_msgs = websocket.get_messages_by_type("execution_complete")
        assert len(complete_msgs) == 1
        
        # Check that we got output
        stdout_msgs = websocket.get_messages_by_type("stdout")
        print(f"DEBUG: stdout messages: {stdout_msgs}")  # Debug output
        assert len(stdout_msgs) == 1
        assert stdout_msgs[0]["content"] == "Hello, World!"
    
    @pytest.mark.asyncio
    @patch('app.services.python_executor.execute_python_code')
    async def test_error_handling(self, mock_task_func, executor, websocket):
        """Test execution with syntax errors"""
        # Mock the Celery task with error
        mock_task = MockCeleryTask()
        mock_task.set_result({
            'status': 'error',
            'error': 'invalid syntax (<string>, line 1)',
            'exit_code': 1
        })
        mock_task.set_ready(True)
        mock_task_func.delay.return_value = mock_task
        
        code = 'print("Hello" + )'  # Syntax error
        
        await executor.execute_and_stream(code, websocket)
        
        # Check that execution started
        start_msgs = websocket.get_messages_by_type("execution_start")
        assert len(start_msgs) == 1
        
        # Check that we got an error message
        error_msgs = websocket.get_messages_by_type("error")
        assert len(error_msgs) >= 1
    
    @pytest.mark.asyncio
    @patch('app.services.python_executor.execute_python_code')
    @patch('app.services.python_executor.celery_app')
    async def test_timeout_handling(self, mock_celery_app, mock_task_func, executor, websocket):
        """Test that infinite loops are properly timed out"""
        # Mock the Celery app control methods
        mock_control = MagicMock()
        mock_celery_app.control = mock_control
        
        # Mock the Celery task that never completes
        mock_task = MockCeleryTask()
        mock_task.set_ready(False)  # Never ready
        mock_task_func.delay.return_value = mock_task
        
        code = '''
import time
while True:
    print("Still running...")
    time.sleep(0.1)
'''
        
        start_time = time.time()
        await executor.execute_and_stream(code, websocket)
        execution_time = time.time() - start_time
        
        # Check that execution started
        start_msgs = websocket.get_messages_by_type("execution_start")
        assert len(start_msgs) == 1
        
        # Check that timeout occurred
        timeout_msgs = websocket.get_messages_by_type("timeout")
        assert len(timeout_msgs) == 1
        assert "timed out" in timeout_msgs[0]["message"].lower()
        
        # Check that execution didn't take much longer than timeout
        assert execution_time <= executor.timeout + 2  # Allow 2 second buffer
        
        # Verify no active executions remain
        assert len(executor._active_executions) == 0
        
        # Verify that revoke was called
        mock_control.revoke.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.services.python_executor.execute_python_code')
    @patch('app.services.python_executor.celery_app')
    async def test_stop_execution(self, mock_celery_app, mock_task_func, executor, websocket):
        """Test stopping an execution manually"""
        # Mock the Celery app control methods
        mock_control = MagicMock()
        mock_celery_app.control = mock_control
        
        # Mock the Celery task
        mock_task = MockCeleryTask()
        mock_task.set_ready(False)  # Never ready
        mock_task_func.delay.return_value = mock_task
        
        code = '''
import time
for i in range(100):
    print(f"Line {i}")
    time.sleep(0.1)
'''
        
        # Start execution in background
        execution_task = asyncio.create_task(
            executor.execute_and_stream(code, websocket)
        )
        
        # Wait a bit for execution to start
        await asyncio.sleep(0.1)
        
        # Get the execution ID from the start message
        start_msgs = websocket.get_messages_by_type("execution_start")
        assert len(start_msgs) == 1
        execution_id = start_msgs[0]["execution_id"]
        
        # Stop the execution
        stop_result = await executor.stop_execution(execution_id)
        assert stop_result is True
        
        # Wait for execution to complete
        await execution_task
        
        # Check that execution was stopped
        assert len(executor._active_executions) == 0
        
        # Verify that revoke was called
        mock_control.revoke.assert_called_once()
    
    def test_get_active_executions(self, executor):
        """Test getting list of active executions"""
        # Should be empty initially
        assert executor.get_active_executions() == []
        
        # Add a mock execution
        executor._active_executions["test_id"] = {
            'task_id': 'mock_task_123',
            'temp_file': '/tmp/test.py',
            'start_time': time.time(),
            'websocket': None
        }
        
        active = executor.get_active_executions()
        assert "test_id" in active
        assert len(active) == 1
        
        # Clean up
        del executor._active_executions["test_id"]
    
    @pytest.mark.asyncio
    async def test_stop_nonexistent_execution(self, executor):
        """Test stopping an execution that doesn't exist"""
        result = await executor.stop_execution("nonexistent_id")
        assert result is False
    
    @pytest.mark.asyncio
    @patch('app.services.python_executor.execute_python_code')
    async def test_concurrent_executions(self, mock_task_func, executor):
        """Test multiple concurrent executions"""
        websocket1 = MockWebSocket()
        websocket2 = MockWebSocket()
        
        # Mock tasks for both executions
        mock_task1 = MockCeleryTask("task1")
        mock_task1.set_result({
            'status': 'success',
            'stdout': 'Execution 1\n',
            'stderr': '',
            'exit_code': 0
        })
        mock_task1.set_ready(True)
        
        mock_task2 = MockCeleryTask("task2")
        mock_task2.set_result({
            'status': 'success',
            'stdout': 'Execution 2\n',
            'stderr': '',
            'exit_code': 0
        })
        mock_task2.set_ready(True)
        
        # Make the mock function return different tasks for different calls
        mock_task_func.delay.side_effect = [mock_task1, mock_task2]
        
        code1 = 'print("Execution 1")'
        code2 = 'print("Execution 2")'
        
        # Start both executions concurrently
        task1 = asyncio.create_task(
            executor.execute_and_stream(code1, websocket1)
        )
        task2 = asyncio.create_task(
            executor.execute_and_stream(code2, websocket2)
        )
        
        # Wait for both to complete
        await asyncio.gather(task1, task2)
        
        # Check that both completed successfully
        assert len(websocket1.get_messages_by_type("execution_complete")) == 1
        assert len(websocket2.get_messages_by_type("execution_complete")) == 1
        
        # Verify no active executions remain
        assert len(executor._active_executions) == 0


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
