# Metrics Reference

The following Prometheus metrics are exported by ABrain services.

- `agentnn_feedback_positive_total{agent}` – number of positive feedback entries per worker
- `agentnn_feedback_negative_total{agent}` – number of negative feedback entries per worker
- `agentnn_task_success_total{task_type}` – count of successful tasks per task type
- `agentnn_routing_decisions_total{task_type,worker}` – distribution of routing decisions
- `agentnn_response_seconds{service,path}` – request latency per route
- `agentnn_request_errors_total{service,path,status}` – count of error responses
- `agentnn_active_sessions{service}` – currently active sessions

Use `/metrics` on each service to scrape these values.

## Test Coverage

All metrics-related utilities and services are covered by automated tests in
`tests/test_metrics.py` and related modules, ensuring stable behaviour.
