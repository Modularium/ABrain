#!/usr/bin/env python3
"""
ABrain Frontend-Backend Bridge Server.

Connects the React frontend with the ABrain backend system.
"""

import os
import sys
import asyncio
import uvicorn
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Security, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import ABrain modules or create fallbacks
try:
    from core.agents import AgentRuntime
    from core.execution import maybe_await
    from managers.agent_manager import AgentManager
    from managers.monitoring_system import MonitoringSystem
    from utils.logging_util import LoggerMixin
    AGENT_NN_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import ABrain modules: {e}")
    print("Server will run in mock mode.")
    AGENT_NN_AVAILABLE = False
    
    # Fallback LoggerMixin
    class LoggerMixin:
        def log_error(self, error, context=None):
            print(f"ERROR: {error}")
            if context:
                print(f"Context: {context}")

# Pydantic Models for API
class User(BaseModel):
    id: str
    name: str
    email: str
    avatar: Optional[str] = None
    role: str
    permissions: List[str]

class Agent(BaseModel):
    id: str
    name: str
    domain: str
    status: str = Field(..., pattern="^(active|idle|error|maintenance)$")
    version: str
    description: str
    capabilities: List[str]
    metrics: Dict[str, Any]
    configuration: Dict[str, Any]

class Task(BaseModel):
    id: str
    title: str
    description: str
    status: str = Field(..., pattern="^(pending|running|completed|failed|cancelled)$")
    priority: str = Field(..., pattern="^(low|medium|high|urgent)$")
    type: str
    agentId: str
    assignedAt: datetime
    startedAt: Optional[datetime] = None
    completedAt: Optional[datetime] = None
    progress: int = Field(ge=0, le=100)
    metadata: Dict[str, Any]
    error: Optional[Dict[str, str]] = None

class CreateTaskRequest(BaseModel):
    title: str
    description: str
    priority: str = "medium"
    type: str = "general"
    metadata: Optional[Dict[str, Any]] = None

class CreateAgentRequest(BaseModel):
    name: str
    domain: str
    description: str
    capabilities: List[str]
    configuration: Optional[Dict[str, Any]] = None

class ChatMessage(BaseModel):
    content: str
    taskType: Optional[str] = "general"
    metadata: Optional[Dict[str, Any]] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    user: User
    token: str

class ApiResponse(BaseModel):
    data: Any
    success: bool = True
    message: Optional[str] = None
    errors: Optional[List[str]] = None
    meta: Optional[Dict[str, Any]] = None

# Server Implementation
class AgentNNServer(LoggerMixin):
    def __init__(self):
        super().__init__()
        
        # Initialize FastAPI
        self.app = FastAPI(
            title="ABrain API Server",
            description="Bridge server connecting the React frontend with the ABrain backend",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, restrict this
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Security
        self.security = HTTPBearer()
        
        # Initialize ABrain components
        if AGENT_NN_AVAILABLE:
            try:
                self.runtime = AgentRuntime()
                self.supervisor = self.runtime.supervisor
                self.chatbot = self.runtime.chatbot
                self.agent_manager = AgentManager()
                self.monitoring = MonitoringSystem()
                self.mock_mode = False
            except Exception as e:
                print(f"Failed to initialize ABrain components: {e}")
                print("Running in mock mode")
                self.mock_mode = True
        else:
            self.mock_mode = True
            
        # In-memory storage (replace with proper database in production)
        self.sessions = {}
        self.users = {
            "user1": {
                "id": "user1",
                "name": "Demo User",
                "email": "demo@abrain.local",
                "role": "admin",
                "permissions": ["read", "write", "admin"],
                "password": "demo"
            }
        }
        
        self.setup_routes()
    
    async def verify_token(self, credentials: HTTPAuthorizationCredentials = Security(HTTPBearer(auto_error=False))):
        """Verify JWT token (simplified for demo)"""
        if not credentials:
            return None
        # In production, properly verify JWT tokens
        return {"user_id": "user1", "permissions": ["read", "write", "admin"]}
    
    def setup_routes(self):
        """Setup API routes"""
        
        # Health check
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.now()}
        
        # Authentication routes
        @self.app.post("/auth/login", response_model=ApiResponse)
        async def login(request: LoginRequest):
            user_data = self.users.get("user1")
            if not user_data or request.password != user_data["password"]:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )
            
            # Create mock token (use proper JWT in production)
            token = f"token_{uuid4().hex}"
            
            user = User(
                id=user_data["id"],
                name=user_data["name"],
                email=user_data["email"],
                role=user_data["role"],
                permissions=user_data["permissions"]
            )
            
            return ApiResponse(
                data={"user": user, "token": token}
            )
        
        @self.app.post("/auth/logout")
        async def logout():
            return ApiResponse(data={"message": "Logged out successfully"})
        
        # User routes
        @self.app.get("/user/me", response_model=ApiResponse)
        async def get_current_user(auth=Depends(self.verify_token)):
            if not auth:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            
            user_data = self.users["user1"]
            user = User(
                id=user_data["id"],
                name=user_data["name"],
                email=user_data["email"],
                role=user_data["role"],
                permissions=user_data["permissions"]
            )
            
            return ApiResponse(data=user)
        
        # Agents routes
        @self.app.get("/agents", response_model=ApiResponse)
        async def list_agents(
            status: Optional[str] = None,
            domain: Optional[str] = None,
            search: Optional[str] = None,
            auth=Depends(self.verify_token)
        ):
            if not auth:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            
            agents = await self.get_agents()
            
            # Apply filters
            if status:
                agents = [a for a in agents if a.status == status]
            if domain:
                agents = [a for a in agents if domain.lower() in a.domain.lower()]
            if search:
                agents = [a for a in agents if search.lower() in a.name.lower() or search.lower() in a.description.lower()]
            
            return ApiResponse(data=agents)
        
        @self.app.get("/agents/{agent_id}", response_model=ApiResponse)
        async def get_agent(agent_id: str, auth=Depends(self.verify_token)):
            if not auth:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            
            agents = await self.get_agents()
            agent = next((a for a in agents if a.id == agent_id), None)
            
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            
            return ApiResponse(data=agent)
        
        @self.app.post("/agents", response_model=ApiResponse)
        async def create_agent(request: CreateAgentRequest, auth=Depends(self.verify_token)):
            if not auth:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            
            # Create new agent
            agent = Agent(
                id=f"agent_{uuid4().hex[:8]}",
                name=request.name,
                domain=request.domain,
                status="active",
                version="1.0.0",
                description=request.description,
                capabilities=request.capabilities,
                metrics={
                    "totalTasks": 0,
                    "successRate": 0.0,
                    "avgResponseTime": 0.0,
                    "lastActive": datetime.now()
                },
                configuration=request.configuration or {}
            )
            
            return ApiResponse(data=agent)
        
        @self.app.patch("/agents/{agent_id}", response_model=ApiResponse)
        async def update_agent(agent_id: str, updates: Dict[str, Any], auth=Depends(self.verify_token)):
            if not auth:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            
            agents = await self.get_agents()
            agent = next((a for a in agents if a.id == agent_id), None)
            
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            
            # Update agent (in production, save to database)
            for key, value in updates.items():
                if hasattr(agent, key):
                    setattr(agent, key, value)
            
            return ApiResponse(data=agent)
        
        @self.app.delete("/agents/{agent_id}")
        async def delete_agent(agent_id: str, auth=Depends(self.verify_token)):
            if not auth:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            
            return ApiResponse(data={"message": "Agent deleted successfully"})
        
        # Tasks routes
        @self.app.get("/tasks", response_model=ApiResponse)
        async def list_tasks(
            status: Optional[str] = None,
            priority: Optional[str] = None,
            agentId: Optional[str] = None,
            search: Optional[str] = None,
            limit: Optional[int] = 50,
            offset: Optional[int] = 0,
            auth=Depends(self.verify_token)
        ):
            if not auth:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            
            tasks = await self.get_tasks()
            
            # Apply filters
            if status:
                tasks = [t for t in tasks if t.status == status]
            if priority:
                tasks = [t for t in tasks if t.priority == priority]
            if agentId:
                tasks = [t for t in tasks if t.agentId == agentId]
            if search:
                tasks = [t for t in tasks if search.lower() in t.title.lower() or search.lower() in t.description.lower()]
            
            # Apply pagination
            tasks = tasks[offset:offset+limit]
            
            return ApiResponse(data=tasks)
        
        @self.app.get("/tasks/{task_id}", response_model=ApiResponse)
        async def get_task(task_id: str, auth=Depends(self.verify_token)):
            if not auth:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            
            tasks = await self.get_tasks()
            task = next((t for t in tasks if t.id == task_id), None)
            
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            
            return ApiResponse(data=task)
        
        @self.app.post("/tasks", response_model=ApiResponse)
        async def create_task(request: CreateTaskRequest, auth=Depends(self.verify_token)):
            if not auth:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            
            # Create new task
            agents = await self.get_agents()
            if not agents:
                raise HTTPException(status_code=400, detail="No agents available")
            
            # Assign to first available agent (in production, use proper assignment logic)
            selected_agent = agents[0]
            
            task = Task(
                id=f"task_{uuid4().hex[:8]}",
                title=request.title,
                description=request.description,
                status="pending",
                priority=request.priority,
                type=request.type,
                agentId=selected_agent.id,
                assignedAt=datetime.now(),
                progress=0,
                metadata=request.metadata or {}
            )
            
            # Execute task if not in mock mode
            if not self.mock_mode:
                try:
                    asyncio.create_task(self.execute_task(task))
                except Exception as e:
                    self.log_error(e, {"task_id": task.id})
            
            return ApiResponse(data=task)
        
        @self.app.patch("/tasks/{task_id}", response_model=ApiResponse)
        async def update_task(task_id: str, updates: Dict[str, Any], auth=Depends(self.verify_token)):
            if not auth:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            
            tasks = await self.get_tasks()
            task = next((t for t in tasks if t.id == task_id), None)
            
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            
            # Update task
            for key, value in updates.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            
            return ApiResponse(data=task)
        
        # Chat routes
        @self.app.get("/chat/sessions/{session_id}", response_model=ApiResponse)
        async def get_chat_session(session_id: str, auth=Depends(self.verify_token)):
            if not auth:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            
            session = self.sessions.get(session_id, {
                "id": session_id,
                "messages": [],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            })
            
            return ApiResponse(data=session)
        
        @self.app.post("/chat/sessions/{session_id}/messages", response_model=ApiResponse)
        async def send_message(session_id: str, message: ChatMessage, auth=Depends(self.verify_token)):
            if not auth:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            
            # Get or create session
            if session_id not in self.sessions:
                self.sessions[session_id] = {
                    "id": session_id,
                    "messages": [],
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
            
            session = self.sessions[session_id]
            
            # Add user message
            user_message = {
                "id": f"msg_{uuid4().hex[:8]}",
                "role": "user",
                "content": message.content,
                "timestamp": datetime.now(),
                "metadata": message.metadata or {}
            }
            session["messages"].append(user_message)
            
            # Generate response
            if self.mock_mode:
                response_content = f"Mock response to: {message.content}"
            else:
                try:
                    response_content = await self.runtime.handle_user_message(message.content)
                except Exception as e:
                    self.log_error(e, {"session_id": session_id})
                    response_content = f"Error processing message: {str(e)}"
            
            # Add assistant response
            assistant_message = {
                "id": f"msg_{uuid4().hex[:8]}",
                "role": "assistant",
                "content": response_content,
                "timestamp": datetime.now(),
                "metadata": {}
            }
            session["messages"].append(assistant_message)
            session["updated_at"] = datetime.now()
            
            return ApiResponse(data=assistant_message)
        
        # System metrics routes
        @self.app.get("/metrics/system", response_model=ApiResponse)
        async def get_system_metrics(auth=Depends(self.verify_token)):
            if not auth:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
            
            if self.mock_mode:
                metrics = {
                    "cpu_usage": 25.5,
                    "memory_usage": 60.2,
                    "disk_usage": 45.8,
                    "active_agents": 3,
                    "running_tasks": 2,
                    "completed_tasks": 150,
                    "failed_tasks": 5,
                    "uptime": "2d 14h 30m",
                    "timestamp": datetime.now()
                }
            else:
                try:
                    metrics = await maybe_await(self.monitoring.get_metrics())
                except Exception as e:
                    self.log_error(e, {})
                    metrics = {"error": str(e), "timestamp": datetime.now()}
            
            return ApiResponse(data=metrics)
        
        @self.app.get("/system/health", response_model=ApiResponse)
        async def get_system_health():
            health_status = {
                "status": "healthy" if not self.mock_mode else "mock",
                "timestamp": datetime.now(),
                "services": {
                    "api": "up",
                    "agents": "up" if not self.mock_mode else "mock",
                    "database": "up" if not self.mock_mode else "mock",
                    "monitoring": "up" if not self.mock_mode else "mock"
                }
            }
            
            return ApiResponse(data=health_status)
    
    async def get_agents(self) -> List[Agent]:
        """Get list of available agents"""
        if self.mock_mode:
            return [
                Agent(
                    id="agent_1",
                    name="General Assistant",
                    domain="general",
                    status="active",
                    version="1.0.0",
                    description="General purpose AI assistant",
                    capabilities=["chat", "analysis", "task_execution"],
                    metrics={
                        "totalTasks": 45,
                        "successRate": 92.5,
                        "avgResponseTime": 1.2,
                        "lastActive": datetime.now() - timedelta(minutes=5)
                    },
                    configuration={"max_tokens": 2000, "temperature": 0.7}
                ),
                Agent(
                    id="agent_2",
                    name="Code Assistant",
                    domain="development",
                    status="active",
                    version="1.0.0",
                    description="Specialized in code analysis and programming tasks",
                    capabilities=["code_review", "debugging", "documentation"],
                    metrics={
                        "totalTasks": 32,
                        "successRate": 88.0,
                        "avgResponseTime": 2.1,
                        "lastActive": datetime.now() - timedelta(minutes=10)
                    },
                    configuration={"max_tokens": 4000, "temperature": 0.3}
                ),
                Agent(
                    id="agent_3",
                    name="Data Analyst",
                    domain="analytics",
                    status="idle",
                    version="1.0.0",
                    description="Specializes in data analysis and visualization",
                    capabilities=["data_processing", "visualization", "statistics"],
                    metrics={
                        "totalTasks": 28,
                        "successRate": 95.0,
                        "avgResponseTime": 3.5,
                        "lastActive": datetime.now() - timedelta(hours=2)
                    },
                    configuration={"max_tokens": 3000, "temperature": 0.5}
                )
            ]
        else:
            # Get agents from the ABrain system
            try:
                agent_names = self.agent_manager.get_all_agents()
                agents = []
                
                for name in agent_names:
                    agent_obj = self.agent_manager.get_agent(name)
                    if agent_obj:
                        status_info = self.supervisor.get_agent_status(name)
                        agents.append(Agent(
                            id=name,
                            name=name,
                            domain=agent_obj.name,
                            status="active",  # Simplify for demo
                            version="1.0.0",
                            description=f"Specialized in {agent_obj.name} domain",
                            capabilities=agent_obj.capabilities if hasattr(agent_obj, 'capabilities') else [],
                            metrics={
                                "totalTasks": status_info.get("total_tasks", 0),
                                "successRate": status_info.get("success_rate", 0),
                                "avgResponseTime": status_info.get("avg_execution_time", 0),
                                "lastActive": datetime.now()
                            },
                            configuration={}
                        ))
                
                return agents
            except Exception as e:
                self.log_error(e, {})
                return []
    
    async def get_tasks(self) -> List[Task]:
        """Get list of tasks"""
        if self.mock_mode:
            return [
                Task(
                    id="task_1",
                    title="Analyze customer feedback",
                    description="Process and analyze customer feedback from last quarter",
                    status="completed",
                    priority="high",
                    type="analysis",
                    agentId="agent_3",
                    assignedAt=datetime.now() - timedelta(hours=6),
                    startedAt=datetime.now() - timedelta(hours=5),
                    completedAt=datetime.now() - timedelta(hours=1),
                    progress=100,
                    metadata={"source": "customer_surveys", "quarter": "Q4_2024"}
                ),
                Task(
                    id="task_2",
                    title="Review code changes",
                    description="Review recent code changes in the main branch",
                    status="running",
                    priority="medium",
                    type="code_review",
                    agentId="agent_2",
                    assignedAt=datetime.now() - timedelta(hours=2),
                    startedAt=datetime.now() - timedelta(hours=1),
                    progress=75,
                    metadata={"branch": "main", "files_changed": 12}
                ),
                Task(
                    id="task_3",
                    title="Generate weekly report",
                    description="Create weekly performance report for management",
                    status="pending",
                    priority="low",
                    type="reporting",
                    agentId="agent_1",
                    assignedAt=datetime.now() - timedelta(minutes=30),
                    progress=0,
                    metadata={"report_type": "weekly", "period": "2024-W30"}
                )
            ]
        else:
            # In production, get tasks from database or task manager
            return []
    
    async def execute_task(self, task: Task):
        """Execute a task using the ABrain system."""
        if self.mock_mode:
            return
        
        try:
            # Use supervisor to execute the task
            result = await self.runtime.execute_task(
                task.description,
                {"task_id": task.id, "priority": task.priority}
            )
            
            # Update task status (in production, save to database)
            task.status = "completed" if result.get("success") else "failed"
            task.progress = 100
            task.completedAt = datetime.now()
            
            if not result.get("success"):
                task.error = {
                    "code": "EXECUTION_ERROR",
                    "message": result.get("error", "Task execution failed")
                }
        
        except Exception as e:
            self.log_error(e, {"task_id": task.id})
            task.status = "failed"
            task.error = {
                "code": "SYSTEM_ERROR",
                "message": str(e)
            }
            task.completedAt = datetime.now()

def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    server = AgentNNServer()
    return server.app

def main():
    """Run the server"""
    app = create_app()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        access_log=True
    )

if __name__ == "__main__":
    main()
