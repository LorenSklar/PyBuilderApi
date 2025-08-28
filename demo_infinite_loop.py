#!/usr/bin/env python3
"""
Demo script showing how the multiprocessing-based PythonExecutor handles infinite loops
"""

import asyncio
import json
from app.services.python_executor import PythonExecutor

class DemoWebSocket:
    """Simple demo WebSocket that prints messages"""
    def __init__(self):
        self.messages = []
    
    async def send_text(self, message):
        parsed = json.loads(message)
        self.messages.append(parsed)
        print(f"📡 {parsed['type'].upper()}: {parsed.get('message', parsed.get('content', ''))}")
    
    def get_messages_by_type(self, msg_type):
        return [msg for msg in self.messages if msg.get("type") == msg_type]

async def demo_infinite_loop():
    """Demonstrate infinite loop handling"""
    print("🚀 Starting infinite loop demo...")
    print("=" * 50)
    
    executor = PythonExecutor(timeout=10)  # 10 second timeout
    websocket = DemoWebSocket()
    
    # This code will run for 10 seconds then be terminated
    infinite_code = '''
import time
print("Starting infinite loop...")
i = 0
while True:
    print(f"Loop iteration {i}")
    i += 1
    time.sleep(0.5)
'''
    
    print("🔍 Executing code with infinite loop...")
    print("⏰ This should timeout after 10 seconds...")
    print("-" * 50)
    
    await executor.execute_and_stream(infinite_code, websocket)
    
    print("-" * 50)
    print("✅ Demo completed!")
    
    # Show what messages we received
    print("\n📊 Messages received:")
    for msg in websocket.messages:
        print(f"  - {msg['type']}: {msg.get('message', msg.get('content', ''))}")

async def demo_normal_execution():
    """Demonstrate normal code execution"""
    print("\n🚀 Starting normal execution demo...")
    print("=" * 50)
    
    executor = PythonExecutor(timeout=10)
    websocket = DemoWebSocket()
    
    normal_code = '''
print("Hello from normal execution!")
for i in range(5):
    print(f"Count: {i}")
print("Execution completed successfully!")
'''
    
    print("🔍 Executing normal code...")
    print("-" * 50)
    
    await executor.execute_and_stream(normal_code, websocket)
    
    print("-" * 50)
    print("✅ Normal execution demo completed!")
    
    # Show what messages we received
    print("\n📊 Messages received:")
    for msg in websocket.messages:
        print(f"  - {msg['type']}: {msg.get('message', msg.get('content', ''))}")

async def main():
    """Run both demos"""
    print("🎯 Multiprocessing-based PythonExecutor Demo")
    print("This demonstrates how the system handles infinite loops and normal execution")
    print()
    
    print("✅ This demo works with the simple multiprocessing implementation!")
    print("   - No Redis required")
    print("   - No Celery workers needed")
    print("   - Just pure Python multiprocessing")
    print()
    
    try:
        await demo_normal_execution()
        await demo_infinite_loop()
    except Exception as e:
        print(f"❌ Demo failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
