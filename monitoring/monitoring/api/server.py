#!/usr/bin/env python3
# monitoring/api/server.py
import os
import json
import asyncio
import uvicorn
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Depends, Query, Path, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED

# Import monitoring components
from system_monitor import SystemMonitor, MonitorConfig
from data_manager import DataManager

# Create FastAPI app
app = FastAPI(
    title="ABrain Monitoring API",
    description="API for monitoring and managing the ABrain system",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize monitoring components
monitor_config = MonitorConfig(
    interval=1.0,
    history_size=3600,
    log_to_file=True,
    log_to_mlflow=False,
    alert_enabled=True
)
system_monitor = SystemMonitor(monitor_config)
data_manager = DataManager()

# Start system monitoring
system_monitor.start()

# Authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Mock user database (replace with actual authentication in production)
USERS = {
    "admin": {
        "username": "admin",
        "password": "password",  # In production, store hashed passwords
        "role": "administrator",
        "permissions": ["read", "write", "manage"]
    }
}

# Models
class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    username: str
    role: str
    permissions: List[str]

class SystemMetrics(BaseModel):
    cpu_usage: float
    memory_usage: float
    gpu_usage: float
    disk_usage: float
    active_agents: int
    task_queue_size: int
    total_tasks_completed: int
    avg_response_time: float

class SystemComponent(BaseModel):
    name: str
    status: str
    version: str
    lastUpdated: str

class ActiveTask(BaseModel):
    id: str
    type: str
    agent: str
    status: str
    duration: str

class Agent(BaseModel):
    name: str
    domain: str
    status: str
    tasks: int
    successRate: float
    avgResponse: float
    lastActive: str

class Model(BaseModel):
    name: str
    type: str
    source: str
    version: str
    status: str
    requests: int
    latency: float

class KnowledgeBase(BaseModel):
    name: str
    documents: int
    lastUpdated: str
    size: str
    status: str

class SecurityEvent(BaseModel):
    type: str
    timestamp: str
    details: str
    severity: str

class SecurityStatus(BaseModel):
    overall: str
    lastScan: str
    vulnerabilities: Dict[str, int]
    events: List[SecurityEvent]

class TestResult(BaseModel):
    id: str
    name: str
    status: str
    variants: int
    winner: str
    improvement: str

class LogEntry(BaseModel):
    level: str
    timestamp: str
    message: str
    source: Optional[str] = None

class DashboardData(BaseModel):
    systemData: dict
    agents: List[dict]
    models: List[dict]
    knowledgeBases: List[dict]
    securityStatus: dict
    testResults: List[dict]
    logs: List[dict]

# Authentication functions
def authenticate_user(username: str, password: str):
    if username not in USERS:
        return False
    if USERS[username]["password"] != password:
        return False
    return USERS[username]

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # In production, verify the token properly
    # This is a simplified version for demo purposes
    try:
        username = token  # In a real implementation, decode the token
        if username not in USERS:
            raise credentials_exception
        return USERS[username]
    except:
        raise credentials_exception

# Routes

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # In production, generate a proper JWT token
    # This is a simplified version for demo purposes
    access_token = user["username"]
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/system/dashboard-data", response_model=DashboardData)
async def get_dashboard_data(user: User = Depends(get_current_user)):
    """Get all dashboard data in a single request."""
    try:
        # Get system metrics
        metrics = system_monitor.get_metrics(window=timedelta(minutes=5))
        
        # Format data for frontend
        dashboard_data = {
            "systemData": {
                "metrics": {
                    "cpu_usage": metrics.get("system.cpu", {}).get("current", 0),
                    "memory_usage": metrics.get("system.memory", {}).get("current", 0),
                    "gpu_usage": metrics.get("gpu.0.utilization", {}).get("current", 0),
                    "disk_usage": metrics.get("system.disk", {}).get("current", 0),
                    "active_agents": len(data_manager.get_active_agents()),
                    "task_queue_size": data_manager.get_task_queue_size(),
                    "total_tasks_completed": data_manager.get_total_tasks_completed(),
                    "avg_response_time": data_manager.get_avg_response_time()
                },
                "components": data_manager.get_system_components(),
                "activeTasks": data_manager.get_active_tasks()
            },
            "agents": data_manager.get_agents(),
            "models": data_manager.get_models(),
            "knowledgeBases": data_manager.get_knowledge_bases(),
            "securityStatus": data_manager.get_security_status(),
            "testResults": data_manager.get_test_results(),
            "logs": data_manager.get_logs(limit=10)
        }
        
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents", response_model=List[Agent])
async def get_all_agents(user: User = Depends(get_current_user)):
    """Get all agents."""
    return data_manager.get_agents()

@app.get("/api/agents/{agent_name}", response_model=dict)
async def get_agent_details(
    agent_name: str = Path(..., description="Name of the agent"),
    user: User = Depends(get_current_user)
):
    """Get details for a specific agent."""
    agent = data_manager.get_agent_details(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
    return agent

@app.post("/api/agents", response_model=dict)
async def create_agent(
    agent_data: dict,
    user: User = Depends(get_current_user)
):
    """Create a new agent."""
    if "write" not in user["permissions"]:
        raise HTTPException(status_code=403, detail="Not authorized to create agents")
    
    try:
        agent = data_manager.create_agent(agent_data)
        return agent
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/agents/{agent_name}/status", response_model=dict)
async def update_agent_status(
    agent_name: str,
    status_data: dict,
    user: User = Depends(get_current_user)
):
    """Update agent status."""
    if "write" not in user["permissions"]:
        raise HTTPException(status_code=403, detail="Not authorized to update agents")
    
    try:
        agent = data_manager.update_agent_status(agent_name, status_data.get("status"))
        return agent
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/models", response_model=List[Model])
async def get_all_models(user: User = Depends(get_current_user)):
    """Get all models."""
    return data_manager.get_models()

@app.post("/api/models", response_model=dict)
async def create_model(
    model_data: dict,
    user: User = Depends(get_current_user)
):
    """Create a new model."""
    if "write" not in user["permissions"]:
        raise HTTPException(status_code=403, detail="Not authorized to create models")
    
    try:
        model = data_manager.create_model(model_data)
        return model
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/knowledge-bases", response_model=List[KnowledgeBase])
async def get_all_knowledge_bases(user: User = Depends(get_current_user)):
    """Get all knowledge bases."""
    return data_manager.get_knowledge_bases()

@app.get("/api/logs", response_model=List[LogEntry])
async def get_logs(
    level: Optional[str] = Query(None, description="Filter by log level"),
    limit: int = Query(50, description="Maximum number of logs to return"),
    offset: int = Query(0, description="Logs offset"),
    user: User = Depends(get_current_user)
):
    """Get system logs."""
    return data_manager.get_logs(level=level, limit=limit, offset=offset)

@app.post("/api/logs/clear", response_model=dict)
async def clear_logs(user: User = Depends(get_current_user)):
    """Clear system logs."""
    if "manage" not in user["permissions"]:
        raise HTTPException(status_code=403, detail="Not authorized to clear logs")
    
    data_manager.clear_logs()
    return {"status": "cleared"}

@app.post("/api/system/restart", response_model=dict)
async def restart_system(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user)
):
    """Restart the system."""
    if "manage" not in user["permissions"]:
        raise HTTPException(status_code=403, detail="Not authorized to restart system")
    
    # Simulate system restart
    async def restart():
        await asyncio.sleep(5)
        # In a real implementation, this would restart the system
    
    background_tasks.add_task(restart)
    return {"status": "restarting"}

# Main
if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)


# monitoring/api/data_manager.py
import os
import json
import random
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

class DataManager:
    """Manager for system data retrieval and manipulation."""
    
    def __init__(self, data_dir: str = "data"):
        """Initialize the data manager.
        
        Args:
            data_dir: Directory for data files
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # Mock data for development
        self._initialize_mock_data()
        
    def _initialize_mock_data(self):
        """Initialize mock data for development."""
        self.agents = [
            {
                "name": "Finance Agent",
                "domain": "Finance",
                "status": "active",
                "tasks": 1245,
                "successRate": 92.5,
                "avgResponse": 1.2,
                "lastActive": "Just now"
            },
            {
                "name": "Tech Agent",
                "domain": "Technology",
                "status": "active",
                "tasks": 2153,
                "successRate": 94.1,
                "avgResponse": 0.9,
                "lastActive": "2 minutes ago"
            },
            {
                "name": "Marketing Agent",
                "domain": "Marketing",
                "status": "active",
                "tasks": 987,
                "successRate": 88.3,
                "avgResponse": 1.5,
                "lastActive": "5 minutes ago"
            },
            {
                "name": "Web Agent",
                "domain": "Web",
                "status": "active",
                "tasks": 1856,
                "successRate": 91.2,
                "avgResponse": 1.1,
                "lastActive": "10 minutes ago"
            },
            {
                "name": "Research Agent",
                "domain": "Research",
                "status": "idle",
                "tasks": 654,
                "successRate": 89.7,
                "avgResponse": 2.3,
                "lastActive": "1 hour ago"
            }
        ]
        
        self.models = [
            {
                "name": "gpt-4",
                "type": "LLM",
                "source": "OpenAI",
                "version": "v1.0",
                "status": "active",
                "requests": 32145,
                "latency": 1.2
            },
            {
                "name": "claude-3",
                "type": "LLM",
                "source": "Anthropic",
                "version": "v1.0",
                "status": "active",
                "requests": 18921,
                "latency": 1.5
            },
            {
                "name": "llama-3",
                "type": "LLM",
                "source": "Local",
                "version": "v1.0",
                "status": "active",
                "requests": 8752,
                "latency": 2.1
            }
        ]
        
        self.knowledge_bases = [
            {
                "name": "Finance KB",
                "documents": 1245,
                "lastUpdated": "2 hours ago",
                "size": "2.4 GB",
                "status": "active"
            },
            {
                "name": "Tech KB",
                "documents": 3567,
                "lastUpdated": "1 day ago",
                "size": "5.2 GB",
                "status": "active"
            },
            {
                "name": "Marketing KB",
                "documents": 982,
                "lastUpdated": "3 days ago",
                "size": "1.8 GB",
                "status": "active"
            },
            {
                "name": "General KB",
                "documents": 4521,
                "lastUpdated": "5 days ago",
                "size": "8.7 GB",
                "status": "active"
            }
        ]
        
        self.system_components = [
            {
                "name": "Supervisor Agent",
                "status": "online",
                "version": "2.1.0",
                "lastUpdated": "2 hours ago"
            },
            {
                "name": "MLflow Integration",
                "status": "online",
                "version": "1.4.2",
                "lastUpdated": "1 day ago"
            },
            {
                "name": "Vector Store",
                "status": "online",
                "version": "3.0.1",
                "lastUpdated": "3 days ago"
            },
            {
                "name": "Cache Manager",
                "status": "online",
                "version": "1.2.5",
                "lastUpdated": "5 days ago"
            }
        ]
        
        self.active_tasks = [
            {
                "id": "T-1254",
                "type": "Analysis",
                "agent": "Finance",
                "status": "running",
                "duration": "24s"
            },
            {
                "id": "T-1253",
                "type": "Research",
                "agent": "Web",
                "status": "completed",
                "duration": "3m 12s"
            },
            {
                "id": "T-1252",
                "type": "Code",
                "agent": "Tech",
                "status": "queued",
                "duration": "-"
            }
        ]
        
        self.security_events = [
            {
                "type": "Authentication",
                "timestamp": datetime.now().isoformat(),
                "details": "Successful login: admin",
                "severity": "low"
            },
            {
                "type": "Rate Limit",
                "timestamp": (datetime.now() - timedelta(minutes=15)).isoformat(),
                "details": "Rate limit exceeded: 192.168.1.105",
                "severity": "medium"
            },
            {
                "type": "Input Validation",
                "timestamp": (datetime.now() - timedelta(minutes=40)).isoformat(),
                "details": "Suspicious input detected and sanitized",
                "severity": "medium"
            }
        ]
        
        self.test_results = [
            {
                "id": "test-001",
                "name": "Prompt Optimization",
                "status": "completed",
                "variants": 2,
                "winner": "Variant B",
                "improvement": "+12.5%"
            },
            {
                "id": "test-002",
                "name": "Model Comparison",
                "status": "in-progress",
                "variants": 3,
                "winner": "-",
                "improvement": "-"
            },
            {
                "id": "test-003",
                "name": "Knowledge Source",
                "status": "completed",
                "variants": 2,
                "winner": "Variant A",
                "improvement": "+5.2%"
            }
        ]
        
        self.logs = [
            {
                "level": "INFO",
                "timestamp": datetime.now().isoformat(),
                "message": "Agent \"Finance\" created successfully"
            },
            {
                "level": "WARNING",
                "timestamp": (datetime.now() - timedelta(minutes=2)).isoformat(),
                "message": "High memory usage detected (78%)"
            },
            {
                "level": "ERROR",
                "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
                "message": "Failed to load model \"mistral-7b\" - CUDA out of memory"
            },
            {
                "level": "INFO",
                "timestamp": (datetime.now() - timedelta(minutes=6)).isoformat(),
                "message": "System started successfully"
            }
        ]
        
    def get_agents(self) -> List[Dict[str, Any]]:
        """Get all agents."""
        return self.agents
    
    def get_agent_details(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific agent."""
        for agent in self.agents:
            if agent["name"] == agent_name:
                # Add extra details
                details = agent.copy()
                details["capabilities"] = [
                    {
                        "name": "Data Analysis",
                        "description": "Analyze financial data and trends",
                        "successRate": 95.2
                    },
                    {
                        "name": "Market Prediction",
                        "description": "Predict market movements",
                        "successRate": 82.7
                    },
                    {
                        "name": "Risk Assessment",
                        "description": "Assess investment risks",
                        "successRate": 91.5
                    }
                ]
                details["knowledgeBase"] = "Finance KB"
                details["model"] = "gpt-4"
                details["createdAt"] = "2025-01-15T12:00:00Z"
                return details
        return None
    
    def create_agent(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new agent."""
        agent = {
            "name": agent_data["name"],
            "domain": agent_data["domain"],
            "status": "active",
            "tasks": 0,
            "successRate": 0.0,
            "avgResponse": 0.0,
            "lastActive": "Just now"
        }
        self.agents.append(agent)
        return agent
    
    def update_agent_status(self, agent_name: str, status: str) -> Dict[str, Any]:
        """Update agent status."""
        for agent in self.agents:
            if agent["name"] == agent_name:
                agent["status"] = status
                return agent
        raise ValueError(f"Agent {agent_name} not found")
    
    def get_models(self) -> List[Dict[str, Any]]:
        """Get all models."""
        return self.models
    
    def create_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new model."""
        model = {
            "name": model_data["name"],
            "type": model_data["type"],
            "source": model_data["source"],
            "version": model_data["version"],
            "status": "active",
            "requests": 0,
            "latency": 0.0
        }
        self.models.append(model)
        return model
    
    def get_knowledge_bases(self) -> List[Dict[str, Any]]:
        """Get all knowledge bases."""
        return self.knowledge_bases
    
    def get_system_components(self) -> List[Dict[str, Any]]:
        """Get system components."""
        return self.system_components
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get active tasks."""
        return self.active_tasks
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get security status."""
        return {
            "overall": "secure",
            "lastScan": (datetime.now() - timedelta(hours=8)).isoformat(),
            "vulnerabilities": {
                "high": 0,
                "medium": 2,
                "low": 5
            },
            "events": self.security_events
        }
    
    def get_test_results(self) -> List[Dict[str, Any]]:
        """Get test results."""
        return self.test_results
    
    def get_logs(self, level: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get system logs."""
        filtered_logs = self.logs
        if level:
            filtered_logs = [log for log in self.logs if log["level"] == level.upper()]
        
        return filtered_logs[offset:offset + limit]
    
    def clear_logs(self):
        """Clear system logs."""
        self.logs = []
    
    def get_active_agents(self) -> List[Dict[str, Any]]:
        """Get active agents."""
        return [agent for agent in self.agents if agent["status"] == "active"]
    
    def get_task_queue_size(self) -> int:
        """Get task queue size."""
        return random.randint(5, 20)
    
    def get_total_tasks_completed(self) -> int:
        """Get total tasks completed."""
        return sum(agent["tasks"] for agent in self.agents)
    
    def get_avg_response_time(self) -> float:
        """Get average response time."""
        times = [agent["avgResponse"] for agent in self.agents]
        return sum(times) / len(times) if times else 0.0


# monitoring/api/routes/system.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .. import schemas
from ..dependencies import get_current_user, get_system_monitor, get_data_manager

router = APIRouter(
    prefix="/api/system",
    tags=["system"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/metrics", response_model=Dict[str, Any])
async def get_system_metrics(
    window: Optional[int] = None,
    user: schemas.User = Depends(get_current_user),
    system_monitor = Depends(get_system_monitor)
):
    """Get system metrics."""
    try:
        if window:
            window_td = timedelta(seconds=window)
            return system_monitor.get_metrics(window=window_td)
        return system_monitor.get_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/restart", response_model=Dict[str, str])
async def restart_system(
    background_tasks: BackgroundTasks,
    user: schemas.User = Depends(get_current_user)
):
    """Restart system."""
    if "manage" not in user.permissions:
        raise HTTPException(status_code=403, detail="Not authorized to restart system")
    
    # Simulate system restart
    async def restart():
        import asyncio
        await asyncio.sleep(5)
        # In a real implementation, this would restart the system
    
    background_tasks.add_task(restart)
    return {"status": "restarting"}

@router.post("/cache/clear", response_model=Dict[str, str])
async def clear_cache(
    user: schemas.User = Depends(get_current_user)
):
    """Clear system cache."""
    if "manage" not in user.permissions:
        raise HTTPException(status_code=403, detail="Not authorized to clear cache")
    
    # In a real implementation, this would clear the cache
    return {"status": "cleared"}

@router.get("/config", response_model=Dict[str, Any])
async def get_system_config(
    user: schemas.User = Depends(get_current_user)
):
    """Get system configuration."""
    # In a real implementation, this would return the actual configuration
    return {
        "max_concurrent_tasks": 10,
        "task_timeout": 300,
        "cache_size": 1024,
        "log_level": "INFO",
        "monitoring_interval": 60,
        "backup_interval": 86400
    }

@router.post("/config", response_model=Dict[str, Any])
async def update_system_config(
    config: Dict[str, Any],
    user: schemas.User = Depends(get_current_user)
):
    """Update system configuration."""
    if "manage" not in user.permissions:
        raise HTTPException(status_code=403, detail="Not authorized to update system configuration")
    
    # In a real implementation, this would update the actual configuration
    return config
