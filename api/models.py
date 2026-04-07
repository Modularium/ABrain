"""API models for ABrain."""
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field
from datetime import datetime

# Authentication Models
class Token(BaseModel):
    """Authentication token."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_at: datetime = Field(..., description="Token expiration time")

class UserCreate(BaseModel):
    """User creation request."""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    email: str = Field(..., description="Email address")
    role: str = Field("user", description="User role")

class User(BaseModel):
    """User information."""
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    role: str = Field(..., description="User role")
    created_at: datetime = Field(..., description="Account creation time")
    last_login: Optional[datetime] = Field(None, description="Last login time")

# Task Models
class TaskRequest(BaseModel):
    """Task execution request."""
    description: str = Field(..., description="Task description")
    domain: Optional[str] = Field(None, description="Optional domain hint")
    priority: int = Field(1, ge=1, le=10, description="Task priority (1-10)")
    timeout: Optional[int] = Field(None, description="Timeout in seconds")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context")
    batch: bool = Field(False, description="Whether this is a batch task")

class TaskResponse(BaseModel):
    """Task execution response."""
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Task status")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result")
    agent_id: str = Field(..., description="Agent identifier")
    execution_time: float = Field(..., description="Execution time in seconds")
    metrics: Dict[str, float] = Field(..., description="Performance metrics")
    created_at: datetime = Field(..., description="Task creation time")
    completed_at: Optional[datetime] = Field(None, description="Task completion time")

class BatchTaskRequest(BaseModel):
    """Batch task request."""
    tasks: List[TaskRequest] = Field(..., description="List of tasks")
    parallel: bool = Field(True, description="Execute tasks in parallel")
    max_concurrent: Optional[int] = Field(None, description="Maximum concurrent tasks")

class BatchTaskResponse(BaseModel):
    """Batch task response."""
    batch_id: str = Field(..., description="Batch identifier")
    total_tasks: int = Field(..., description="Total number of tasks")
    completed_tasks: int = Field(..., description="Completed tasks")
    failed_tasks: int = Field(..., description="Failed tasks")
    results: List[TaskResponse] = Field(..., description="Task results")
    execution_time: float = Field(..., description="Total execution time")

# Agent Models
class AgentConfig(BaseModel):
    """Agent configuration."""
    name: str = Field(..., description="Agent name")
    domain: str = Field(..., description="Agent domain")
    capabilities: List[str] = Field(..., description="Agent capabilities")
    config: Dict[str, Any] = Field(..., description="Agent configuration")
    model_config: Optional[Dict[str, Any]] = Field(None, description="Model configuration")
    knowledge_base: Optional[Dict[str, Any]] = Field(None, description="Knowledge base configuration")

class AgentStatus(BaseModel):
    """Agent status."""
    agent_id: str = Field(..., description="Agent identifier")
    name: str = Field(..., description="Agent name")
    domain: str = Field(..., description="Agent domain")
    status: str = Field(..., description="Agent status")
    capabilities: List[str] = Field(..., description="Agent capabilities")
    total_tasks: int = Field(..., description="Total tasks processed")
    success_rate: float = Field(..., description="Task success rate")
    avg_response_time: float = Field(..., description="Average response time")
    last_active: datetime = Field(..., description="Last activity time")

# Model Management Models
class ModelConfig(BaseModel):
    """Model configuration."""
    name: str = Field(..., description="Model name")
    type: str = Field(..., description="Model type (llm, nn, hybrid)")
    source: str = Field(..., description="Model source (local, huggingface, openai)")
    config: Dict[str, Any] = Field(..., description="Model configuration")
    version: Optional[str] = Field(None, description="Model version")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Model metadata")

class ModelStatus(BaseModel):
    """Model status."""
    model_id: str = Field(..., description="Model identifier")
    name: str = Field(..., description="Model name")
    type: str = Field(..., description="Model type")
    status: str = Field(..., description="Model status")
    version: str = Field(..., description="Model version")
    total_requests: int = Field(..., description="Total requests")
    avg_latency: float = Field(..., description="Average latency")
    last_used: datetime = Field(..., description="Last usage time")

# Knowledge Base Models
class KnowledgeBase(BaseModel):
    """Knowledge base configuration."""
    name: str = Field(..., description="Knowledge base name")
    domain: str = Field(..., description="Knowledge domain")
    sources: List[str] = Field(..., description="Data sources")
    update_interval: int = Field(3600, description="Update interval in seconds")
    embedding_config: Optional[Dict[str, Any]] = Field(None, description="Embedding configuration")
    storage_config: Optional[Dict[str, Any]] = Field(None, description="Storage configuration")

class Document(BaseModel):
    """Document metadata."""
    doc_id: str = Field(..., description="Document identifier")
    title: str = Field(..., description="Document title")
    source: str = Field(..., description="Document source")
    content_type: str = Field(..., description="Content type")
    metadata: Dict[str, Any] = Field(..., description="Document metadata")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")

# System Models
class SystemConfig(BaseModel):
    """System configuration."""
    max_concurrent_tasks: int = Field(..., description="Maximum concurrent tasks")
    task_timeout: int = Field(..., description="Task timeout in seconds")
    cache_size: int = Field(..., description="Cache size in MB")
    log_level: str = Field("INFO", description="Logging level")
    monitoring_interval: int = Field(60, description="Monitoring interval in seconds")
    backup_interval: int = Field(86400, description="Backup interval in seconds")

class SystemMetrics(BaseModel):
    """System metrics."""
    cpu_usage: float = Field(..., description="CPU usage percentage")
    memory_usage: float = Field(..., description="Memory usage percentage")
    active_agents: int = Field(..., description="Number of active agents")
    task_queue_size: int = Field(..., description="Task queue size")
    avg_response_time: float = Field(..., description="Average response time")
    total_tasks: int = Field(..., description="Total tasks processed")
    success_rate: float = Field(..., description="Task success rate")
    timestamp: datetime = Field(..., description="Metrics timestamp")

# A/B Testing Models
class TestConfig(BaseModel):
    """A/B test configuration."""
    name: str = Field(..., description="Test name")
    description: str = Field(..., description="Test description")
    variants: List[Dict[str, Any]] = Field(..., description="Test variants")
    metrics: List[str] = Field(..., description="Metrics to track")
    duration_days: int = Field(..., description="Test duration in days")
    sample_size: Optional[int] = Field(None, description="Required sample size")
    significance_level: float = Field(0.05, description="Statistical significance level")

class TestResults(BaseModel):
    """A/B test results."""
    test_id: str = Field(..., description="Test identifier")
    name: str = Field(..., description="Test name")
    status: str = Field(..., description="Test status")
    start_time: datetime = Field(..., description="Test start time")
    end_time: Optional[datetime] = Field(None, description="Test end time")
    total_samples: int = Field(..., description="Total samples collected")
    variant_results: Dict[str, Dict[str, float]] = Field(..., description="Results by variant")
    winner: Optional[str] = Field(None, description="Winning variant")
    confidence: Optional[float] = Field(None, description="Statistical confidence")

# Cache Models
class CacheConfig(BaseModel):
    """Cache configuration."""
    max_size: int = Field(..., description="Maximum cache size in MB")
    ttl: int = Field(..., description="Time to live in seconds")
    cleanup_interval: int = Field(..., description="Cleanup interval in seconds")
    storage_type: str = Field("memory", description="Cache storage type")

class CacheStats(BaseModel):
    """Cache statistics."""
    size: int = Field(..., description="Current size in MB")
    items: int = Field(..., description="Number of cached items")
    hits: int = Field(..., description="Cache hits")
    misses: int = Field(..., description="Cache misses")
    hit_rate: float = Field(..., description="Cache hit rate")
    evictions: int = Field(..., description="Number of evictions")
    last_cleanup: datetime = Field(..., description="Last cleanup time")
