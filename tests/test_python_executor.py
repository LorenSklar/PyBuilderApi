#!/usr/bin/env python3
"""
Test suite for the multiprocessing-based PythonExecutor
"""

import asyncio
import json
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.python_executor import PythonExecutor

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
    async def test_simple_execution(self, executor, websocket):
        """Test simple Python code execution"""
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
    async def test_error_handling(self, executor, websocket):
        """Test execution with syntax errors"""
        code = 'print("Hello" + )'  # Syntax error
        
        await executor.execute_and_stream(code, websocket)
        
        # Check that execution started
        start_msgs = websocket.get_messages_by_type("execution_start")
        assert len(start_msgs) == 1
        
        # Check that we got an error message
        error_msgs = websocket.get_messages_by_type("error")
        assert len(error_msgs) >= 1
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, executor, websocket):
        """Test that infinite loops are properly timed out"""
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
    
    @pytest.mark.asyncio
    async def test_stop_execution(self, executor, websocket):
        """Test stopping an execution manually"""
        # Create a new executor with a short timeout so we can manually stop it before it times out
        test_executor = PythonExecutor(timeout=5)  # 5 second timeout
        
        # Use a simple infinite loop that will run until stopped or timed out
        code = '''
import time
print("Starting infinite loop...")
i = 0
while True:
    print(f"Loop iteration {i}")
    i += 1
    time.sleep(0.1)  # Slower to ensure we can stop it
'''
        
        # Start execution in background
        execution_task = asyncio.create_task(
            test_executor.execute_and_stream(code, websocket)
        )
        
        # Wait for execution to start and produce some output
        await asyncio.sleep(0.3)
        
        # Get the execution ID from the start message
        start_msgs = websocket.get_messages_by_type("execution_start")
        assert len(start_msgs) == 1
        execution_id = start_msgs[0]["execution_id"]
        
        # Verify execution is in the active executions list
        assert execution_id in test_executor._active_executions, "Execution should be in active executions"
        
        # Verify we're getting output (execution is running)
        stdout_msgs = websocket.get_messages_by_type("stdout")
        assert len(stdout_msgs) > 0, "Execution should be producing output"
        
        # Stop the execution
        stop_result = await test_executor.stop_execution(execution_id)
        assert stop_result is True
        
        # Wait for execution to complete
        await execution_task
        
        # Check that execution was stopped
        assert len(test_executor._active_executions) == 0
    
    def test_get_active_executions(self, executor):
        """Test getting list of active execution IDs"""
        # Should be empty initially
        assert executor.get_active_executions() == []
        
        # Add a mock execution
        executor._active_executions["test_id"] = {
            'process': None,
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
    async def test_concurrent_executions(self, executor):
        """Test multiple concurrent executions"""
        websocket1 = MockWebSocket()
        websocket2 = MockWebSocket()
        
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
