# API Reference

This document provides detailed information about the ABrain API endpoints.

> Status: Diese Referenz beschreibt den breiten API-Bestand auf hoher Ebene. Einige Endpunkte gehören zu historischen oder optionalen Pfaden. Für den gehärteten Integrationspfad sind die aktiven FastAPI-Apps und der Core-Dispatcher maßgeblich.

## Authentication

Many API endpoints expect authentication, but the exact mechanism depends on the deployment and active service composition.

### Login

```http
POST /token
```

Request body:
```json
{
    "username": "string",
    "password": "string"
}
```

Response:
```json
{
    "access_token": "string",
    "token_type": "bearer"
}
```

## Task Management

### Create Task

```http
POST /tasks
```

Request body:
```json
{
    "description": "string",
    "domain": "string (optional)",
    "priority": "integer (1-10)",
    "timeout": "integer (optional)",
    "context": {
        "key": "value"
    }
}
```

Response:
```json
{
    "task_id": "string",
    "status": "string",
    "result": {
        "key": "value"
    },
    "agent_id": "string",
    "execution_time": "float",
    "metrics": {
        "metric_name": "float"
    }
}
```

### Get Task Status

```http
GET /tasks/{task_id}
```

Response:
```json
{
    "task_id": "string",
    "status": "string",
    "result": {
        "key": "value"
    },
    "agent_id": "string",
    "execution_time": "float",
    "metrics": {
        "metric_name": "float"
    }
}
```

## Agent Management

### Create Agent

```http
POST /agents
```

Request body:
```json
{
    "name": "string",
    "domain": "string",
    "capabilities": ["string"],
    "config": {
        "key": "value"
    }
}
```

Response:
```json
{
    "name": "string",
    "domain": "string",
    "capabilities": ["string"],
    "config": {
        "key": "value"
    }
}
```

### List Agents

```http
GET /agents
```

Response:
```json
[
    {
        "name": "string",
        "domain": "string",
        "capabilities": ["string"],
        "config": {
            "key": "value"
        }
    }
]
```

## Monitoring

### Get System Metrics

```http
GET /metrics
```

Response:
```json
{
    "cpu_usage": "float",
    "memory_usage": "float",
    "active_agents": "integer",
    "task_queue_size": "integer",
    "avg_response_time": "float"
}
```

### Get Specific Metric

```http
GET /metrics/{metric_name}
```

Response:
```json
{
    "mean": "float",
    "std": "float",
    "min": "float",
    "max": "float",
    "count": "integer"
}
```

## A/B Testing

### Create Test

```http
POST /tests
```

Request body:
```json
{
    "name": "string",
    "variants": [
        {
            "name": "string",
            "config": {
                "key": "value"
            }
        }
    ],
    "metrics": ["string"],
    "duration_days": "integer"
}
```

Response:
```json
{
    "test_id": "string"
}
```

### Get Test Results

```http
GET /tests/{test_id}
```

Response:
```json
{
    "test_id": "string",
    "status": "string",
    "variants": {
        "variant_name": {
            "metrics": {
                "metric_name": {
                    "mean": "float",
                    "std": "float",
                    "min": "float",
                    "max": "float",
                    "samples": "integer"
                }
            }
        }
    },
    "analysis": {
        "metric_name": {
            "t_statistic": "float",
            "p_value": "float",
            "effect_size": "float",
            "significant": "boolean",
            "winner": "string"
        }
    }
}
```

## Error Responses

All endpoints may return the following error responses:

### 401 Unauthorized
```json
{
    "detail": "Invalid credentials"
}
```

### 404 Not Found
```json
{
    "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
    "detail": "Error message"
}
```

## Rate Limiting

API requests are rate-limited to:
- 100 requests per hour for standard users
- 1000 requests per hour for premium users

Rate limit headers are included in all responses:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1635789600
```
