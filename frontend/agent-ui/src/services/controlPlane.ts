import { useAppStore } from '@/store/useAppStore'

export interface ControlPlaneLayer {
  name: string
  status: string
}

export interface HealthAttentionItem {
  level: 'warning' | 'info'
  label: string
  detail: string
}

export interface HealthSummary {
  overall: 'healthy' | 'attention' | 'degraded'
  degraded_agent_count: number
  offline_agent_count: number
  paused_plan_count: number
  failed_plan_count: number
  pending_approval_count: number
  has_warnings: boolean
  attention_items: HealthAttentionItem[]
}

export interface ControlPlaneOverview {
  system: {
    name: string
    layers: ControlPlaneLayer[]
    governance: Record<string, unknown>
    warnings: string[]
  }
  summary: {
    agent_count: number
    pending_approvals: number
    recent_traces: number
    recent_plans: number
    recent_governance_events: number
  }
  health: HealthSummary
  agents: ControlPlaneAgent[]
  pending_approvals: ApprovalRequest[]
  recent_traces: TraceRecord[]
  recent_plans: PlanRun[]
  recent_governance: GovernanceEvent[]
}

export interface AgentQualitySummary {
  quality_score: number
  quality_band: 'good' | 'fair' | 'poor'
  score_components: Record<string, number>
  attention_flags: string[]
  data_sufficient: boolean
  execution_count: number
}

export interface ExecutionCapabilities {
  execution_protocol: 'cli_process' | 'http_api' | 'webhook_json' | 'tool_dispatch'
  requires_network: boolean
  requires_local_process: boolean
  supports_cost_reporting: boolean
  supports_token_reporting: boolean
  runtime_constraints: string[]
}

export interface ControlPlaneAgent {
  agent_id: string
  display_name: string
  capabilities: string[]
  source_type?: string | null
  execution_kind?: string | null
  availability?: string | null
  trust_level?: string | null
  quality?: AgentQualitySummary | null
  execution_capabilities?: ExecutionCapabilities | null
  metadata: Record<string, unknown>
}

export interface TraceRecord {
  trace_id: string
  workflow_name: string
  task_id?: string | null
  started_at: string
  ended_at?: string | null
  status: string
  metadata: Record<string, unknown>
}

export interface TraceEvent {
  event_type: string
  timestamp: string
  message: string
  payload: Record<string, unknown>
}

export interface SpanRecord {
  span_id: string
  trace_id: string
  parent_span_id?: string | null
  span_type: string
  name: string
  started_at: string
  ended_at?: string | null
  status: string
  attributes: Record<string, unknown>
  events: TraceEvent[]
  error?: Record<string, unknown> | null
}

export interface ExplainabilityRecord {
  trace_id: string
  step_id?: string | null
  selected_agent_id?: string | null
  candidate_agent_ids: string[]
  selected_score?: number | null
  routing_reason_summary: string
  matched_policy_ids: string[]
  approval_required: boolean
  approval_id?: string | null
  // S10 — first-class forensics fields
  routing_confidence?: number | null
  score_gap?: number | null
  confidence_band?: 'high' | 'medium' | 'low' | null
  policy_effect?: 'allow' | 'deny' | 'require_approval' | null
  scored_candidates: Array<{
    agent_id: string
    score: number
    capability_match_score: number
  }>
  metadata: Record<string, any>
}

export interface ReplayStepInput {
  step_id: string
  task_type?: string | null
  required_capabilities: string[]
  selected_agent_id?: string | null
  candidate_agent_ids: string[]
  routing_confidence?: number | null
  confidence_band?: string | null
  policy_effect?: string | null
}

export interface ReplayDescriptor {
  trace_id: string
  workflow_name: string
  task_type?: string | null
  task_id?: string | null
  started_at?: string | null
  step_inputs: ReplayStepInput[]
  can_replay: boolean
  missing_inputs: string[]
  metadata: Record<string, any>
}

export interface TraceSnapshot {
  trace: TraceRecord
  spans: SpanRecord[]
  explainability: ExplainabilityRecord[]
  replay_descriptor?: ReplayDescriptor | null
}

export interface ApprovalRequest {
  approval_id: string
  plan_id: string
  step_id: string
  task_summary: string
  agent_id?: string | null
  source_type?: string | null
  execution_kind?: string | null
  reason: string
  risk: string
  requested_at: string
  status: string
  preview: Record<string, unknown>
  proposed_action_summary: string
  metadata: Record<string, any>
}

export interface PlanRun {
  trace_id: string
  plan_id: string
  workflow_name: string
  task_id?: string | null
  status: string
  started_at: string
  ended_at?: string | null
  pending_approval_id?: string | null
  policy_effect?: string | null
  plan?: Record<string, any> | null
  state?: Record<string, any> | null
}

export interface GovernanceEvent {
  trace_id: string
  workflow_name: string
  task_id?: string | null
  status: string
  effect: string
  selected_agent_id?: string | null
  matched_policy_ids: string[]
  winning_policy_rule?: string | null
  approval_required: boolean
  started_at: string
  ended_at?: string | null
}

export interface RunPayload {
  task_type: string
  description?: string
  task_id?: string
  input_data?: Record<string, unknown>
  options?: Record<string, unknown>
}

function getBaseUrl(): string {
  return useAppStore.getState().settings.api.baseUrl.replace(/\/$/, '')
}

function getHeaders(): HeadersInit {
  const token = localStorage.getItem('auth_token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getBaseUrl()}${path}`, {
    ...init,
    headers: {
      ...getHeaders(),
      ...(init?.headers ?? {}),
    },
  })

  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const payload = await response.json()
      detail = typeof payload?.detail === 'string' ? payload.detail : JSON.stringify(payload)
    } catch {
      // Keep fallback detail.
    }
    throw new Error(detail)
  }

  return response.json() as Promise<T>
}

export const controlPlaneApi = {
  getOverview: () => request<ControlPlaneOverview>('/control-plane/overview'),
  listAgents: async () => (await request<{ agents: ControlPlaneAgent[] }>('/control-plane/agents')).agents,
  listTraces: async (limit = 12) =>
    (await request<{ traces: TraceRecord[] }>(`/control-plane/traces?limit=${limit}`)).traces,
  getTrace: async (traceId: string) =>
    (await request<{ trace: TraceSnapshot | null }>(`/control-plane/traces/${traceId}`)).trace,
  getExplainability: async (traceId: string) =>
    (await request<{ explainability: ExplainabilityRecord[] }>(
      `/control-plane/traces/${traceId}/explainability`
    )).explainability,
  listApprovals: async () =>
    (await request<{ approvals: ApprovalRequest[] }>('/control-plane/approvals')).approvals,
  approve: (approvalId: string, comment?: string, rating?: number) =>
    request(`/control-plane/approvals/${approvalId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ decided_by: 'agent-ui', comment, rating }),
    }),
  reject: (approvalId: string, comment?: string, rating?: number) =>
    request(`/control-plane/approvals/${approvalId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ decided_by: 'agent-ui', comment, rating }),
    }),
  listPlans: async (limit = 10) =>
    (await request<{ plans: PlanRun[] }>(`/control-plane/plans?limit=${limit}`)).plans,
  listGovernance: async (limit = 10) =>
    (await request<{ governance: GovernanceEvent[] }>(`/control-plane/governance?limit=${limit}`))
      .governance,
  runTask: (payload: RunPayload) =>
    request('/control-plane/tasks/run', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  runPlan: (payload: RunPayload) =>
    request('/control-plane/plans/run', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
}
