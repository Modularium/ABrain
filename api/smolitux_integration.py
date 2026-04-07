"""Integration with Smolitux-UI for ABrain."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import asyncio
import json
from datetime import datetime

from agents.supervisor_agent import SupervisorAgent
from agents.chatbot_agent import ChatbotAgent
from utils.logging_util import LoggerMixin

class SmolituxIntegration(LoggerMixin):
    """Integration with Smolitux-UI for ABrain."""
    
    def __init__(self):
        """Initialize Smolitux integration."""
        super().__init__()
        self.router = APIRouter(prefix="/smolitux", tags=["smolitux"])
        self.supervisor = SupervisorAgent()
        self.chatbot = ChatbotAgent(self.supervisor)
        self.active_connections: List[WebSocket] = []
        self.task_history: List[Dict[str, Any]] = []
        
        # Register routes
        self._register_routes()
        
    def _register_routes(self):
        """Register API routes."""
        
        # Models
        class TaskRequest(BaseModel):
            task_description: str
            context: Optional[str] = None

        class TaskResponse(BaseModel):
            task_id: str
            result: str
            chosen_agent: str
            execution_time: float
            timestamp: str
            
        @self.router.post("/tasks", response_model=TaskResponse)
        async def create_task(request: TaskRequest):
            try:
                # Execute task
                result = await self.supervisor.execute_task(request.task_description, request.context)
                
                # Create response
                task_id = str(uuid.uuid4())
                response = TaskResponse(
                    task_id=task_id,
                    result=result["result"],
                    chosen_agent=result["chosen_agent"],
                    execution_time=result["execution_time"],
                    timestamp=datetime.now().isoformat()
                )
                
                # Store in history
                self.task_history.append({
                    "id": task_id,
                    "description": request.task_description,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
                
                return response
            except Exception as e:
                self.log_error(e, {
                    "task_description": request.task_description,
                    "context": request.context
                })
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error executing task: {str(e)}"
                )

        @self.router.get("/tasks", response_model=List[Dict[str, Any]])
        async def get_tasks():
            return self.task_history

        @self.router.get("/tasks/{task_id}", response_model=Dict[str, Any])
        async def get_task(task_id: str):
            for task in self.task_history:
                if task["id"] == task_id:
                    return task
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )

        @self.router.get("/agents", response_model=List[Dict[str, Any]])
        async def get_agents():
            agents = self.supervisor.agent_manager.get_all_agents()
            agent_data = []
            
            for agent_name in agents:
                agent = self.supervisor.agent_manager.get_agent(agent_name)
                if agent:
                    # Get agent status
                    status = self.supervisor.get_agent_status(agent_name)
                    agent_data.append({
                        "id": agent_name,
                        "name": agent_name,
                        "domain": agent.name,
                        "totalTasks": status.get("total_tasks", 0),
                        "successRate": status.get("success_rate", 0),
                        "avgExecutionTime": status.get("avg_execution_time", 0),
                        "description": f"Specialized in {agent.name} domain",
                        "knowledgeBase": {
                            "documentsCount": len(agent.search_knowledge_base("", k=1000))
                        }
                    })
            
            return agent_data

        @self.router.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)
            
            try:
                while True:
                    data = await websocket.receive_text()
                    request_data = json.loads(data)
                    
                    # Process the request
                    task_description = request_data.get("task_description", "")
                    context = request_data.get("context")
                    
                    # Handle the message through the chatbot
                    response = await self.chatbot.handle_user_message(task_description)
                    
                    # Send response back
                    await websocket.send_json({
                        "response": response,
                        "timestamp": datetime.now().isoformat()
                    })
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
            except Exception as e:
                self.log_error(e, {
                    "websocket": "disconnect",
                    "error": str(e)
                })
                await websocket.send_json({
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                self.active_connections.remove(websocket)
