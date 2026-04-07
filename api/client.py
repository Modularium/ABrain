"""API client for ABrain."""
import os
import json
import aiohttp
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pathlib import Path

from .models import *
from utils.logging_util import LoggerMixin

class APIClient(LoggerMixin):
    """API client for ABrain."""
    
    def __init__(self,
                base_url: str = "http://localhost:8000",
                token_file: str = "~/.smolit/token"):
        """Initialize API client.
        
        Args:
            base_url: API base URL
            token_file: Token file path
        """
        super().__init__()
        self.base_url = f"{base_url}/api/v2"
        self.token_file = os.path.expanduser(token_file)
        self.token = self._load_token()
        
    def _load_token(self) -> Optional[str]:
        """Load authentication token.
        
        Returns:
            Optional[str]: Authentication token
        """
        if os.path.exists(self.token_file):
            with open(self.token_file) as f:
                return f.read().strip()
        return None
        
    def _save_token(self, token: str):
        """Save authentication token.
        
        Args:
            token: Authentication token
        """
        os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
        with open(self.token_file, "w") as f:
            f.write(token)
            
    async def _request(self,
                     method: str,
                     endpoint: str,
                     data: Optional[Dict[str, Any]] = None,
                     files: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make API request.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Optional request data
            files: Optional files
            
        Returns:
            Dict[str, Any]: Response data
        """
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            
        async with aiohttp.ClientSession() as session:
            if files:
                # Handle file upload
                form = aiohttp.FormData()
                for key, file in files.items():
                    form.add_field(
                        key,
                        file["content"],
                        filename=file["filename"]
                    )
                response = await session.request(
                    method,
                    f"{self.base_url}/{endpoint}",
                    data=form,
                    headers=headers
                )
            else:
                # Regular request
                response = await session.request(
                    method,
                    f"{self.base_url}/{endpoint}",
                    json=data,
                    headers=headers
                )
                
            if response.status >= 400:
                error = await response.json()
                raise Exception(error.get("detail", str(error)))
                
            return await response.json()
            
    async def login(self, username: str, password: str) -> Token:
        """Login to API.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Token: Authentication token
        """
        data = {"username": username, "password": password}
        response = await self._request("POST", "token", data)
        token = Token(**response)
        self._save_token(token.access_token)
        self.token = token.access_token
        return token
        
    async def submit_task(self,
                       description: str,
                       domain: Optional[str] = None,
                       priority: int = 1,
                       timeout: Optional[int] = None,
                       context: Optional[Dict[str, Any]] = None,
                       batch: bool = False) -> Union[TaskResponse, BatchTaskResponse]:
        """Submit task for execution.
        
        Args:
            description: Task description
            domain: Optional domain hint
            priority: Task priority
            timeout: Optional timeout
            context: Optional context
            batch: Whether this is a batch task
            
        Returns:
            Union[TaskResponse, BatchTaskResponse]: Task response
        """
        data = TaskRequest(
            description=description,
            domain=domain,
            priority=priority,
            timeout=timeout,
            context=context,
            batch=batch
        ).dict()
        
        response = await self._request("POST", "tasks", data)
        if batch:
            return BatchTaskResponse(**response)
        return TaskResponse(**response)
        
    async def get_task(self, task_id: str) -> TaskResponse:
        """Get task status and result.
        
        Args:
            task_id: Task identifier
            
        Returns:
            TaskResponse: Task response
        """
        response = await self._request("GET", f"tasks/{task_id}")
        return TaskResponse(**response)
        
    async def create_agent(self, config: AgentConfig) -> AgentConfig:
        """Create new agent.
        
        Args:
            config: Agent configuration
            
        Returns:
            AgentConfig: Created agent configuration
        """
        response = await self._request("POST", "agents", config.dict())
        return AgentConfig(**response)
        
    async def list_agents(self) -> List[AgentStatus]:
        """List all agents.
        
        Returns:
            List[AgentStatus]: List of agent statuses
        """
        response = await self._request("GET", "agents")
        return [AgentStatus(**agent) for agent in response]
        
    async def get_metrics(self) -> SystemMetrics:
        """Get system metrics.
        
        Returns:
            SystemMetrics: System metrics
        """
        response = await self._request("GET", "metrics")
        return SystemMetrics(**response)
        
    async def create_test(self, config: TestConfig) -> TestConfig:
        """Create new A/B test.
        
        Args:
            config: Test configuration
            
        Returns:
            TestConfig: Created test configuration
        """
        response = await self._request("POST", "tests", config.dict())
        return TestConfig(**response)
        
    async def get_test_results(self, test_id: str) -> TestResults:
        """Get A/B test results.
        
        Args:
            test_id: Test identifier
            
        Returns:
            TestResults: Test results
        """
        response = await self._request("GET", f"tests/{test_id}")
        return TestResults(**response)
        
    async def upload_documents(self,
                           kb_name: str,
                           files: List[Dict[str, Any]]) -> List[Document]:
        """Upload documents to knowledge base.
        
        Args:
            kb_name: Knowledge base name
            files: List of files (dict with filename and content)
            
        Returns:
            List[Document]: Uploaded documents
        """
        response = await self._request(
            "POST",
            f"knowledge-bases/{kb_name}/documents",
            files=files
        )
        return [Document(**doc) for doc in response]
        
    async def clear_cache(self):
        """Clear system cache."""
        await self._request("POST", "cache/clear")
        
    async def get_cache_stats(self) -> CacheStats:
        """Get cache statistics.
        
        Returns:
            CacheStats: Cache statistics
        """
        response = await self._request("GET", "cache/stats")
        return CacheStats(**response)
