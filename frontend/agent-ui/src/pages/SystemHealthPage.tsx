import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import {
  controlPlaneApi,
  type ControlPlaneOverview,
} from '@/services/controlPlane'

function formatTimestamp(value?: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleString()
}

function overallClass(overall: string): { bg: string; text: string; dot: string; label: string } {
  switch (overall) {
    case 'healthy':
      return {
        bg: 'bg-emerald-50 border-emerald-200 dark:bg-emerald-950/30 dark:border-emerald-800',
        text: 'text-emerald-800 dark:text-emerald-300',
        dot: 'bg-emerald-500',
        label: 'Healthy',
      }
    case 'attention':
      return {
        bg: 'bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800',
        text: 'text-amber-800 dark:text-amber-300',
        dot: 'bg-amber-500',
        label: 'Attention needed',
      }
    case 'degraded':
      return {
        bg: 'bg-rose-50 border-rose-200 dark:bg-rose-950/30 dark:border-rose-800',
        text: 'text-rose-800 dark:text-rose-300',
        dot: 'bg-rose-500 animate-pulse',
        label: 'Degraded',
      }
    default:
      return {
        bg: 'bg-slate-50 border-slate-200 dark:bg-gray-900/40 dark:border-gray-700',
        text: 'text-slate-700 dark:text-gray-300',
        dot: 'bg-slate-400',
        label: overall,
      }
  }
}

function layerClass(status: string): string {
  switch (status) {
    case 'available':
      return 'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-800'
    case 'unavailable':
      return 'bg-rose-100 text-rose-800 border-rose-200 dark:bg-rose-900/30 dark:text-rose-300 dark:border-rose-800'
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600'
  }
}

function availabilityClass(availability: string | null | undefined): string {
  switch ((availability ?? '').toLowerCase()) {
    case 'online':
      return 'bg-emerald-100 text-emerald-800 border-emerald-200'
    case 'degraded':
      return 'bg-amber-100 text-amber-800 border-amber-200'
    case 'offline':
      return 'bg-rose-100 text-rose-800 border-rose-200'
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200'
  }
}

function planStatusClass(status: string): string {
  switch (status) {
    case 'completed':
      return 'bg-emerald-100 text-emerald-800 border-emerald-200'
    case 'paused':
      return 'bg-amber-100 text-amber-800 border-amber-200'
    case 'failed':
    case 'rejected':
      return 'bg-rose-100 text-rose-800 border-rose-200'
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200'
  }
}

function qualityBandClass(band: string | null | undefined): string {
  switch (band) {
    case 'good':
      return 'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-700'
    case 'fair':
      return 'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-700'
    case 'poor':
      return 'bg-rose-100 text-rose-800 border-rose-200 dark:bg-rose-900/30 dark:text-rose-300 dark:border-rose-700'
    default:
      return 'bg-slate-100 text-slate-500 border-slate-200 dark:bg-gray-700 dark:text-gray-400 dark:border-gray-600'
  }
}

function governanceClass(effect: string): string {
  switch (effect) {
    case 'allow':
      return 'bg-emerald-100 text-emerald-800 border-emerald-200'
    case 'require_approval':
      return 'bg-amber-100 text-amber-800 border-amber-200'
    case 'deny':
      return 'bg-rose-100 text-rose-800 border-rose-200'
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200'
  }
}

export default function SystemHealthPage() {
  const [overview, setOverview] = useState<ControlPlaneOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadOverview = async () => {
    setLoading(true)
    setError(null)
    try {
      setOverview(await controlPlaneApi.getOverview())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load system health')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadOverview()
  }, [])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">Loading system health</p>
        </div>
      </div>
    )
  }

  if (error && overview === null) {
    return (
      <div className="min-h-screen bg-gray-50 p-6 dark:bg-gray-900">
        <div className="mx-auto max-w-4xl rounded-2xl border border-rose-200 bg-white p-6 shadow-sm dark:border-rose-900/50 dark:bg-gray-800">
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">System Health</h1>
          <p className="mt-3 text-sm text-rose-700 dark:text-rose-300">{error}</p>
          <button
            className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            onClick={loadOverview}
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  const health = overview?.health
  const system = overview?.system
  const overall = health?.overall ?? 'healthy'
  const overallStyle = overallClass(overall)

  const attentionAgents = (overview?.agents ?? []).filter(
    (a) => a.availability === 'degraded' || a.availability === 'offline'
  )

  return (
    <div className="min-h-screen bg-gray-50 p-6 dark:bg-gray-900">
      <div className="mx-auto max-w-7xl space-y-6">

        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-blue-600 dark:text-blue-400">
              Operator View
            </p>
            <h1 className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">System Health</h1>
            <p className="mt-2 max-w-2xl text-sm text-gray-600 dark:text-gray-300">
              Derived from canonical control-plane signals. No new runtime or monitoring infrastructure.
            </p>
          </div>
          <button
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
            onClick={loadOverview}
          >
            Refresh
          </button>
        </div>

        {/* Overall Status Banner */}
        <div className={`rounded-3xl border p-6 ${overallStyle.bg}`}>
          <div className="flex items-center gap-4">
            <div className={`h-4 w-4 rounded-full flex-shrink-0 ${overallStyle.dot}`} />
            <div>
              <p className={`text-xl font-semibold ${overallStyle.text}`}>{overallStyle.label}</p>
              <p className={`mt-1 text-sm ${overallStyle.text} opacity-80`}>
                {overall === 'healthy'
                  ? 'All signals nominal. No attention items.'
                  : overall === 'attention'
                  ? 'Some items need operator review — see below.'
                  : 'One or more layers or agents are unavailable or offline.'}
              </p>
            </div>
          </div>

          {/* Quick counts */}
          <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {[
              { label: 'Pending Approvals', value: health?.pending_approval_count ?? 0, urgent: (health?.pending_approval_count ?? 0) > 0 },
              { label: 'Paused Plans', value: health?.paused_plan_count ?? 0, urgent: (health?.paused_plan_count ?? 0) > 0 },
              { label: 'Failed Plans', value: health?.failed_plan_count ?? 0, urgent: (health?.failed_plan_count ?? 0) > 0 },
              { label: 'Degraded Agents', value: health?.degraded_agent_count ?? 0, urgent: (health?.degraded_agent_count ?? 0) > 0 },
              { label: 'Offline Agents', value: health?.offline_agent_count ?? 0, urgent: (health?.offline_agent_count ?? 0) > 0 },
              { label: 'Warnings', value: (system?.warnings ?? []).length, urgent: (system?.warnings ?? []).length > 0 },
            ].map(({ label, value, urgent }) => (
              <div
                key={label}
                className="rounded-2xl bg-white/60 px-4 py-3 dark:bg-gray-800/40"
              >
                <p className="text-xs font-medium uppercase tracking-[0.15em] text-slate-500 dark:text-gray-400">{label}</p>
                <p className={`mt-1 text-2xl font-semibold ${urgent ? 'text-amber-700 dark:text-amber-400' : 'text-slate-800 dark:text-gray-200'}`}>
                  {value}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Attention Items + Layer Grid */}
        <div className="grid gap-6 xl:grid-cols-[1fr_1.2fr]">

          {/* Attention Items */}
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Attention Items</h2>
            <div className="mt-4 space-y-2">
              {(health?.attention_items ?? []).length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-center text-sm text-slate-500 dark:border-gray-600 dark:text-gray-400">
                  No attention items — system is healthy.
                </div>
              ) : (
                (health?.attention_items ?? []).map((item, idx) => (
                  <div
                    key={idx}
                    className={`flex items-start gap-3 rounded-2xl border px-4 py-3 ${
                      item.level === 'warning'
                        ? 'border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30'
                        : 'border-slate-200 bg-slate-50 dark:border-gray-700 dark:bg-gray-900/30'
                    }`}
                  >
                    <span className={`mt-0.5 flex-shrink-0 text-xs font-bold uppercase ${
                      item.level === 'warning' ? 'text-amber-600 dark:text-amber-400' : 'text-slate-400'
                    }`}>
                      {item.level === 'warning' ? '!' : 'i'}
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-900 dark:text-white">{item.label}</p>
                      <p className="mt-0.5 text-xs text-slate-500 dark:text-gray-400">{item.detail}</p>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* System warnings from read failures */}
            {(system?.warnings ?? []).length > 0 && (
              <div className="mt-4">
                <p className="mb-2 text-xs font-semibold uppercase tracking-[0.15em] text-slate-500 dark:text-gray-400">
                  System Warnings
                </p>
                {system?.warnings.map((w, i) => (
                  <div
                    key={i}
                    className="mb-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700 dark:border-rose-800 dark:bg-rose-950/30 dark:text-rose-300"
                  >
                    {w}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Layer Health Grid */}
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Layer Status</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {(system?.layers ?? []).map((layer) => (
                <div
                  key={layer.name}
                  className="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3 dark:border-gray-700 dark:bg-gray-900/30"
                >
                  <span className="text-sm font-medium text-slate-800 dark:text-gray-100">{layer.name}</span>
                  <span className={`rounded-full border px-2 py-1 text-xs font-medium ${layerClass(layer.status)}`}>
                    {layer.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Agent Health + Plan Signals */}
        <div className="grid gap-6 xl:grid-cols-2">

          {/* Agent Health Summary */}
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Agent Health</h2>
              <Link
                to="/agents"
                className="text-sm text-blue-600 hover:underline dark:text-blue-400"
              >
                View all
              </Link>
            </div>
            <div className="mt-4 space-y-2">
              {attentionAgents.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-4 text-center text-sm text-slate-500 dark:border-gray-600 dark:text-gray-400">
                  All agents online or unknown.
                </div>
              ) : (
                attentionAgents.map((agent) => (
                  <div
                    key={agent.agent_id}
                    className="flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3 dark:border-gray-700"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-900 dark:text-white truncate">{agent.display_name}</p>
                      <p className="mt-0.5 text-xs text-slate-500 dark:text-gray-400 truncate">{agent.agent_id}</p>
                    </div>
                    <div className="flex flex-shrink-0 items-center gap-2">
                      {agent.quality && (
                        <span
                          className={`rounded-full border px-2 py-1 text-xs font-medium ${qualityBandClass(agent.quality.quality_band)}`}
                          title={`Quality score: ${agent.quality.quality_score.toFixed(2)}`}
                        >
                          {agent.quality.quality_band}
                        </span>
                      )}
                      <span className={`rounded-full border px-2 py-1 text-xs font-medium ${availabilityClass(agent.availability)}`}>
                        {agent.availability ?? 'unknown'}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
            {(overview?.agents ?? []).length > 0 && (
              <div className="mt-3 text-xs text-slate-500 dark:text-gray-400">
                {overview!.agents.length} agents total · {health?.degraded_agent_count ?? 0} degraded · {health?.offline_agent_count ?? 0} offline
              </div>
            )}
          </div>

          {/* Recent Plan Signals */}
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Recent Plans</h2>
              <Link
                to="/plans"
                className="text-sm text-blue-600 hover:underline dark:text-blue-400"
              >
                View all
              </Link>
            </div>
            <div className="mt-4 space-y-2">
              {(overview?.recent_plans ?? []).length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-4 text-center text-sm text-slate-500 dark:border-gray-600 dark:text-gray-400">
                  No recent plans.
                </div>
              ) : (
                (overview?.recent_plans ?? []).map((plan) => (
                  <div
                    key={plan.plan_id}
                    className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 px-4 py-3 dark:border-gray-700"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
                        {plan.workflow_name}
                      </p>
                      <p className="mt-0.5 text-xs text-slate-500 dark:text-gray-400">
                        {formatTimestamp(plan.started_at)}
                      </p>
                    </div>
                    <span className={`flex-shrink-0 rounded-full border px-2 py-1 text-xs font-medium ${planStatusClass(plan.status)}`}>
                      {plan.status}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Governance Signal Feed + Pending Approvals */}
        <div className="grid gap-6 xl:grid-cols-2">

          {/* Recent Governance Decisions */}
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Governance Signals</h2>
            <div className="mt-4 space-y-2">
              {(overview?.recent_governance ?? []).length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-4 text-center text-sm text-slate-500 dark:border-gray-600 dark:text-gray-400">
                  No recent governance events.
                </div>
              ) : (
                (overview?.recent_governance ?? []).map((event) => (
                  <div
                    key={event.trace_id}
                    className="flex items-start justify-between gap-3 rounded-2xl border border-slate-200 px-4 py-3 dark:border-gray-700"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
                        {event.workflow_name ?? event.trace_id}
                      </p>
                      <p className="mt-0.5 text-xs text-slate-500 dark:text-gray-400 truncate">
                        Agent: {event.selected_agent_id ?? 'n/a'}
                        {event.matched_policy_ids.length > 0 && ` · rules: ${event.matched_policy_ids.slice(0, 2).join(', ')}`}
                      </p>
                    </div>
                    <span className={`flex-shrink-0 rounded-full border px-2 py-1 text-xs font-medium ${governanceClass(event.effect)}`}>
                      {event.effect}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Pending Approvals */}
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                Pending Approvals
                {(health?.pending_approval_count ?? 0) > 0 && (
                  <span className="ml-2 inline-flex h-5 w-5 items-center justify-center rounded-full bg-amber-500 text-xs font-bold text-white">
                    {health?.pending_approval_count}
                  </span>
                )}
              </h2>
              <Link
                to="/approvals"
                className="text-sm text-blue-600 hover:underline dark:text-blue-400"
              >
                Manage
              </Link>
            </div>
            <div className="mt-4 space-y-2">
              {(overview?.pending_approvals ?? []).length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-4 text-center text-sm text-slate-500 dark:border-gray-600 dark:text-gray-400">
                  No pending approvals.
                </div>
              ) : (
                (overview?.pending_approvals ?? []).map((approval) => (
                  <div
                    key={approval.approval_id}
                    className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 dark:border-amber-800 dark:bg-amber-950/20"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-medium text-slate-900 dark:text-white text-sm truncate">{approval.step_id}</span>
                      <span className="flex-shrink-0 rounded-full border border-amber-300 bg-amber-100 px-2 py-1 text-xs font-medium text-amber-800">
                        {approval.risk}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-600 dark:text-gray-300 truncate">{approval.task_summary}</p>
                    <p className="mt-0.5 text-xs text-slate-400 dark:text-gray-500">{approval.reason}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
