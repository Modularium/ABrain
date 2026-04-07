# Cloud Deployment

For production environments the application can be deployed to any Kubernetes cluster using the provided Helm chart.

Ensure Prometheus and Grafana are installed. Example using Helm:

```bash
helm install monitoring prometheus-community/kube-prometheus-stack
```

Afterwards deploy ABrain with:

```bash
helm install agent-nn deploy/k8s/helm/agent-nn -n agent-nn --create-namespace
```
