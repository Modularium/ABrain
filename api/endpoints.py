"""API endpoints for ABrain."""
from typing import Dict, Any, Optional, List
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Security, status, File, UploadFile, Depends, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
import mlflow
import asyncio
import json

from core.agents import AgentRuntime
from core.execution import maybe_await

from .models import *
from managers.agent_manager import AgentManager
from managers.monitoring_system import MonitoringSystem
from managers.ab_testing import ABTestingManager
from managers.security_manager import SecurityManager
from managers.cache_manager import CacheManager
from managers.knowledge_manager import KnowledgeManager
from utils.logging_util import LoggerMixin
from utils.api_utils import api_route

class APIEndpoints(LoggerMixin):
    """API endpoints implementation."""
    
    def __init__(self):
        """Initialize endpoints."""
        super().__init__()
        self.router = APIRouter()
        
        # Initialize managers
        self.agent_manager = AgentManager()
        self.monitoring = MonitoringSystem()
        self.ab_testing = ABTestingManager()
        self.security = SecurityManager()
        self.cache = CacheManager()
        self.knowledge = KnowledgeManager()
        
        # Initialize agents for Smolitux UI
        self.runtime = AgentRuntime()
        self.supervisor = self.runtime.supervisor
        self.chatbot = self.runtime.chatbot
        self.active_connections = []
        self.task_history = []
        
        # Initialize MLflow
        self.experiment = mlflow.set_experiment("api_server")
        
        # Add routes
        self._add_routes()
        
    def _add_routes(self):
        """Add API routes."""
        oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
        
        # Authentication
        @api_route(version="v1.0.0")
        @self.router.post("/token", response_model=Token)
        async def login(form_data: OAuth2PasswordRequestForm = Depends()):
            """Login and get access token."""
            if not self.security.validate_credentials(
                form_data.username,
                form_data.password
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )
                
            token = self.security.generate_token(
                form_data.username,
                ["read", "write"],
            )
            return Token(
                access_token=token,
                token_type="bearer",
                expires_at=datetime.now() + timedelta(days=1)
            )
            
        @api_route(version="v1.0.0")
        @self.router.post("/users", response_model=User)
        async def create_user(user: UserCreate):
            """Create new user."""
            try:
                return await maybe_await(self.security.create_user(user))
            except Exception as e:
                self.log_error(e, {"user": user.dict()})
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
                
        # Task Management
        @api_route(version="v1.0.0")
        @self.router.post(
            "/tasks",
            response_model=Union[TaskResponse, BatchTaskResponse],
            dependencies=[Security(oauth2_scheme)]
        )
        async def create_task(task: Union[TaskRequest, BatchTaskRequest]):
            """Create and execute task(s)."""
            try:
                if isinstance(task, BatchTaskRequest):
                    return await self._handle_batch_task(task)
                else:
                    return await self._handle_single_task(task)
            except Exception as e:
                self.log_error(e, {"task": task.dict()})
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
                
        @api_route(version="v1.0.0")
        @self.router.get(
            "/tasks/{task_id}",
            response_model=TaskResponse,
            dependencies=[Security(oauth2_scheme)]
        )
        async def get_task(task_id: str):
            """Get task status and result."""
            try:
                result = await maybe_await(self.agent_manager.get_task_result(task_id))
                if not result:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Task not found"
                    )
                return result
            except Exception as e:
                self.log_error(e, {"task_id": task_id})
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
                
        # Agent Management
        @api_route(version="v1.0.0")
        @self.router.post(
            "/agents",
            response_model=AgentConfig,
            dependencies=[Security(oauth2_scheme)]
        )
        async def create_agent(config: AgentConfig):
            """Create new agent."""
            try:
                agent = await maybe_await(self.agent_manager.create_agent(config))
                return agent.get_config()
            except Exception as e:
                self.log_error(e, {"config": config.dict()})
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
                
        @api_route(version="v1.0.0")
        @self.router.get(
            "/agents",
            response_model=List[AgentStatus],
            dependencies=[Security(oauth2_scheme)]
        )
        async def list_agents():
            """List all agents."""
            try:
                return await maybe_await(self.agent_manager.get_all_agents())
            except Exception as e:
                self.log_error(e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
                
        @api_route(version="v1.0.0")
        @self.router.get(
            "/agents/{agent_id}",
            response_model=AgentStatus,
            dependencies=[Security(oauth2_scheme)]
        )
        async def get_agent(agent_id: str, format: Optional[str] = None):
            """Get agent status or Flowise-compatible definition."""
            try:
                agent = await maybe_await(self.agent_manager.get_agent(agent_id))
                if not agent:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Agent not found",
                    )

                if format == "flowise":
                    if not hasattr(agent, "get_config"):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=(
                                "Agent does not support Flowise export. "
                                "See docs/integrations/flowise.md#migration"
                            ),
                        )
                    from utils.flowise import agent_config_to_flowise

                    try:
                        return agent_config_to_flowise(agent.get_config())
                    except Exception as exc:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Flowise export failed: {exc}",
                        )

                return agent.get_status()
            except Exception as e:
                self.log_error(e, {"agent_id": agent_id})
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
                
        # Model Management
        @api_route(version="v1.0.0")
        @self.router.post(
            "/models",
            response_model=ModelConfig,
            dependencies=[Security(oauth2_scheme)]
        )
        async def create_model(config: ModelConfig):
            """Create new model."""
            try:
                with mlflow.start_run():
                    mlflow.log_params(config.dict())
                    model = await self._load_model(config)
                    return model
            except Exception as e:
                self.log_error(e, {"config": config.dict()})
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
                
        @api_route(version="v1.0.0")
        @self.router.get(
            "/models",
            response_model=List[ModelStatus],
            dependencies=[Security(oauth2_scheme)]
        )
        async def list_models():
            """List all models."""
            try:
                return await self._get_all_models()
            except Exception as e:
                self.log_error(e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
                
        # Knowledge Base Management
        @api_route(version="v1.0.0")
        @self.router.post(
            "/knowledge-bases",
            response_model=KnowledgeBase,
            dependencies=[Security(oauth2_scheme)]
        )
        async def create_knowledge_base(config: KnowledgeBase):
            """Create knowledge base."""
            try:
                kb = await maybe_await(self.knowledge.create_knowledge_base(config))
                return kb
            except Exception as e:
                self.log_error(e, {"config": config.dict()})
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
                
        @api_route(version="v1.0.0")
        @self.router.post(
            "/knowledge-bases/{kb_name}/documents",
            response_model=List[Document],
            dependencies=[Security(oauth2_scheme)]
        )
        async def upload_documents(
            kb_name: str,
            files: List[UploadFile] = File(...)
        ):
            """Upload documents to knowledge base."""
            try:
                results = []
                for file in files:
                    content = await file.read()
                    doc = await maybe_await(self.knowledge.add_document(
                        kb_name,
                        file.filename,
                        content
                    ))
                    results.append(doc)
                return results
            except Exception as e:
                self.log_error(e, {
                    "kb_name": kb_name,
                    "files": [f.filename for f in files]
                })
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
                
        # System Management
        @api_route(version="v1.0.0")
        @self.router.get(
            "/metrics",
            response_model=SystemMetrics,
            dependencies=[Security(oauth2_scheme)]
        )
        async def get_metrics():
            """Get system metrics."""
            try:
                return await maybe_await(self.monitoring.get_metrics())
            except Exception as e:
                self.log_error(e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
                
        @api_route(version="v1.0.0")
        @self.router.post(
            "/system/config",
            response_model=SystemConfig,
            dependencies=[Security(oauth2_scheme)]
        )
        async def update_system_config(config: SystemConfig):
            """Update system configuration."""
            try:
                return await self._update_system_config(config)
            except Exception as e:
                self.log_error(e, {"config": config.dict()})
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
                
        # A/B Testing
        @api_route(version="v1.0.0")
        @self.router.post(
            "/tests",
            response_model=TestConfig,
            dependencies=[Security(oauth2_scheme)]
        )
        async def create_test(config: TestConfig):
            """Create new A/B test."""
            try:
                test = await maybe_await(self.ab_testing.create_test(config))
                return test
            except Exception as e:
                self.log_error(e, {"config": config.dict()})
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
                
        @api_route(version="v1.0.0")
        @self.router.get(
            "/tests/{test_id}",
            response_model=TestResults,
            dependencies=[Security(oauth2_scheme)]
        )
        async def get_test_results(test_id: str):
            """Get A/B test results."""
            try:
                return await maybe_await(self.ab_testing.get_results(test_id))
            except Exception as e:
                self.log_error(e, {"test_id": test_id})
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
                
        # Smolitux UI Integration
        @api_route(version="v1.0.0")
        @self.router.post("/smolitux/tasks")
        async def smolitux_create_task(request: TaskRequest):
            """Create and execute task for Smolitux UI."""
            try:
                # Execute task
                result = await self.runtime.execute_task(request.description, request.context)
                
                # Create response
                task_id = str(uuid4())
                response = {
                    "task_id": task_id,
                    "result": result["result"],
                    "chosen_agent": result["chosen_agent"],
                    "execution_time": result["execution_time"],
                    "timestamp": datetime.now().isoformat()
                }
                
                # Store in history
                self.task_history.append({
                    "id": task_id,
                    "description": request.description,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
                
                return response
            except Exception as e:
                self.log_error(e, {
                    "task_description": request.description,
                    "context": request.context
                })
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error executing task: {str(e)}"
                )

        @api_route(version="v1.0.0")
        @self.router.get("/smolitux/tasks")
        async def smolitux_get_tasks():
            """Get task history for Smolitux UI."""
            return self.task_history

        @api_route(version="v1.0.0")
        @self.router.get("/smolitux/tasks/{task_id}")
        async def smolitux_get_task(task_id: str):
            """Get task details for Smolitux UI."""
            for task in self.task_history:
                if task["id"] == task_id:
                    return task
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )

        @api_route(version="v1.0.0")
        @self.router.get("/smolitux/agents")
        async def smolitux_get_agents():
            """Get agents for Smolitux UI."""
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

        @api_route(version="v1.0.0")
        @self.router.websocket("/smolitux/ws")
        async def smolitux_websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for Smolitux UI."""
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
                    response = await self.runtime.handle_user_message(task_description)
                    
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
                
        # Cache Management
        @api_route(version="v1.0.0")
        @self.router.post(
            "/cache/config",
            response_model=CacheConfig,
            dependencies=[Security(oauth2_scheme)]
        )
        async def update_cache_config(config: CacheConfig):
            """Update cache configuration."""
            try:
                return await maybe_await(self.cache.update_config(config))
            except Exception as e:
                self.log_error(e, {"config": config.dict()})
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
                
        @api_route(version="v1.0.0")
        @self.router.get(
            "/cache/stats",
            response_model=CacheStats,
            dependencies=[Security(oauth2_scheme)]
        )
        async def get_cache_stats():
            """Get cache statistics."""
            try:
                return await maybe_await(self.cache.get_stats())
            except Exception as e:
                self.log_error(e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
                
        @api_route(version="v1.0.0")
        @self.router.post(
            "/cache/clear",
            dependencies=[Security(oauth2_scheme)]
        )
        async def clear_cache():
            """Clear cache."""
            try:
                await maybe_await(self.cache.clear())
                return {"status": "cleared"}
            except Exception as e:
                self.log_error(e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
                
    async def _handle_single_task(self, task: TaskRequest) -> TaskResponse:
        """Handle single task execution.
        
        Args:
            task: Task request
            
        Returns:
            TaskResponse: Task response
        """
        # Select agent
        agent = await maybe_await(self.agent_manager.select_agent(task.description))
        if isinstance(agent, tuple):
            agent = agent[0]
        
        # Execute task
        start_time = datetime.now()
        result = await maybe_await(agent.execute_task(
            task.description,
            task.context,
            timeout=task.timeout
        ))
        duration = (datetime.now() - start_time).total_seconds()
        
        # Create response
        response = TaskResponse(
            task_id=result["task_id"],
            status="completed",
            result=result["output"],
            agent_id=agent.id,
            execution_time=duration,
            metrics=result["metrics"],
            created_at=start_time,
            completed_at=datetime.now()
        )
        
        # Log execution
        with mlflow.start_run():
            mlflow.log_metrics(result["metrics"])
            mlflow.log_params({
                "agent_id": agent.id,
                "duration": duration
            })
            
        return response
        
    async def _handle_batch_task(self, batch: BatchTaskRequest) -> BatchTaskResponse:
        """Handle batch task execution.
        
        Args:
            batch: Batch task request
            
        Returns:
            BatchTaskResponse: Batch response
        """
        start_time = datetime.now()
        
        # Execute tasks
        if batch.parallel:
            tasks = [
                self._handle_single_task(task)
                for task in batch.tasks[:batch.max_concurrent]
            ]
            results = await asyncio.gather(*tasks)
        else:
            results = []
            for task in batch.tasks:
                result = await self._handle_single_task(task)
                results.append(result)
                
        # Calculate statistics
        duration = (datetime.now() - start_time).total_seconds()
        completed = sum(1 for r in results if r.status == "completed")
        failed = len(results) - completed
        
        return BatchTaskResponse(
            batch_id=f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            total_tasks=len(batch.tasks),
            completed_tasks=completed,
            failed_tasks=failed,
            results=results,
            execution_time=duration
        )
        
    async def _load_model(self, config: ModelConfig) -> ModelConfig:
        """Load model based on configuration.
        
        Args:
            config: Model configuration
            
        Returns:
            ModelConfig: Updated configuration
        """
        if config.source == "local":
            # Load local model
            model = await self._load_local_model(config)
        elif config.source == "huggingface":
            # Load from HuggingFace
            model = await self._load_huggingface_model(config)
        elif config.source == "openai":
            # Configure OpenAI model
            model = await self._configure_openai_model(config)
        else:
            raise ValueError(f"Unknown source: {config.source}")
            
        return config
        
    async def _get_all_models(self) -> List[ModelStatus]:
        """Get all model statuses.
        
        Returns:
            List[ModelStatus]: List of model statuses
        """
        # Get models from MLflow
        client = mlflow.tracking.MlflowClient()
        models = []
        
        for model in client.search_registered_models():
            latest = client.get_latest_versions(model.name)[0]
            models.append(ModelStatus(
                model_id=latest.run_id,
                name=model.name,
                type=latest.tags.get("type", "unknown"),
                status=latest.current_stage,
                version=latest.version,
                total_requests=int(latest.tags.get("total_requests", 0)),
                avg_latency=float(latest.tags.get("avg_latency", 0)),
                last_used=datetime.fromisoformat(
                    latest.tags.get(
                        "last_used",
                        datetime.now().isoformat()
                    )
                )
            ))
            
        return models
        
    async def _update_system_config(self, config: SystemConfig) -> SystemConfig:
        """Update system configuration.
        
        Args:
            config: New configuration
            
        Returns:
            SystemConfig: Updated configuration
        """
        # Update monitoring interval
        self.monitoring.update_interval(config.monitoring_interval)
        
        # Update cache size
        await maybe_await(self.cache.update_config(CacheConfig(
            max_size=config.cache_size,
            ttl=3600,
            cleanup_interval=300,
            storage_type="memory"
        )))
        
        # Update logging
        self.log_level = config.log_level
        
        return config
