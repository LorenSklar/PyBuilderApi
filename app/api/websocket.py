import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.python_executor import PythonExecutor
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter()
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

manager = ConnectionManager()

@router.websocket("/python")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    executor = PythonExecutor()
    
    try:
        while True:
            # Wait for message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                code = message.get("code", "")
                message_type = message.get("type", "execute")
                
                if message_type == "execute" and code:
                    # Validate code length
                    max_length = int(os.getenv("MAX_CODE_LENGTH", 3000))
                    if len(code) > max_length:
                        await manager.send_personal_message(
                            json.dumps({
                                "type": "error", 
                                "message": f"{len(code)} charactersis greater than the {max_length} characters allowed. Please submit a shorter string."
                            }),
                            websocket
                        )
                        continue
                    
                    # Execute Python code and stream results
                    await executor.execute_and_stream(code, websocket)
                else:
                    await manager.send_personal_message(
                        json.dumps({"type": "error", "message": "Message format is invalid. Please send JSON with 'type' and 'code' fields."}),
                        websocket
                    )
                    
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    json.dumps({"type": "error", "message": "Invalid JSON format. Please send properly formatted JSON data."}),
                    websocket
                )
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await manager.send_personal_message(
                    json.dumps({"type": "error", "message": f"Server error occurred: {str(e)}. Please try again or contact support if the problem persists."}),
                    websocket
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket disconnected")
