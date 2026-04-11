import { useEffect, useState } from 'react'

import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import {
  controlPlaneApi,
  type ControlPlaneOverview,
  type RunPayload,
} from '@/services/controlPlane'

const emptyPayload: RunPayload = {
  task_type: 'system_status',
  description: 'Summarize current ABrain system status',
  input_data: {},
  options: {},
}

function formatTimestamp(value?: string | null): string {
  if (!value) {
    return 'Not finished'
  }
  return new Date(value).toLocaleString()
}

function badgeClass(status: string): string {
  switch (status) {
    case 'completed':
    case 'allow':
    case 'available':
      return 'bg-emerald-100 text-emerald-800 border-emerald-200'
    case 'paused':
    case 'require_approval':
      return 'bg-amber-100 text-amber-800 border-amber-200'
    case 'failed':
    case 'denied':
    case 'deny':
      return 'bg-rose-100 text-rose-800 border-rose-200'
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200'
  }
}

export default function DashboardPage() {
  const [overview, setOverview] = useState<ControlPlaneOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [runTaskPayload, setRunTaskPayload] = useState<RunPayload>(emptyPayload)
  const [runTaskResult, setRunTaskResult] = useState<any | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const loadOverview = async () => {
    setLoading(true)
    setError(null)
    try {
      setOverview(await controlPlaneApi.getOverview())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load control plane overview')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadOverview()
  }, [])

  const handleRunTask = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const result = await controlPlaneApi.runTask(runTaskPayload)
      setRunTaskResult(result)
      await loadOverview()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run task')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">Loading control plane overview</p>
        </div>
      </div>
    )
  }

  if (error && overview === null) {
    return (
      <div className="min-h-screen bg-gray-50 p-6 dark:bg-gray-900">
        <div className="mx-auto max-w-4xl rounded-2xl border border-rose-200 bg-white p-6 shadow-sm dark:border-rose-900/50 dark:bg-gray-800">
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Control Plane Overview</h1>
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

  const summary = overview?.summary

  return (
    <div className="min-h-screen bg-gray-50 p-6 dark:bg-gray-900">
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="grid gap-6 xl:grid-cols-[1.4fr_0.9fr]">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium uppercase tracking-[0.2em] text-blue-600 dark:text-blue-400">
                  Canonical Control Plane
                </p>
                <h1 className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
                  ABrain Runtime Overview
                </h1>
                <p className="mt-3 max-w-2xl text-sm text-gray-600 dark:text-gray-300">
                  This surface reflects the current core state via the canonical gateway and service entry points.
                  It does not execute its own policy, approval, or orchestration logic.
                </p>
              </div>
              <button
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
                onClick={loadOverview}
              >
                Refresh
              </button>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              <div className="rounded-2xl bg-slate-50 p-4 dark:bg-gray-900/40">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Agents</p>
                <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-white">
                  {summary?.agent_count ?? 0}
                </p>
              </div>
              <div className="rounded-2xl bg-slate-50 p-4 dark:bg-gray-900/40">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Approvals</p>
                <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-white">
                  {summary?.pending_approvals ?? 0}
                </p>
              </div>
              <div className="rounded-2xl bg-slate-50 p-4 dark:bg-gray-900/40">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Recent Traces</p>
                <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-white">
                  {summary?.recent_traces ?? 0}
                </p>
              </div>
              <div className="rounded-2xl bg-slate-50 p-4 dark:bg-gray-900/40">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Plan Runs</p>
                <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-white">
                  {summary?.recent_plans ?? 0}
                </p>
              </div>
              <div className="rounded-2xl bg-slate-50 p-4 dark:bg-gray-900/40">
                <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Governance</p>
                <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-white">
                  {summary?.recent_governance_events ?? 0}
                </p>
              </div>
            </div>

            <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {overview?.system.layers.map((layer) => (
                <div
                  key={layer.name}
                  className="rounded-2xl border border-slate-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-900/30"
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium text-slate-800 dark:text-gray-100">{layer.name}</span>
                    <span className={`rounded-full border px-2 py-1 text-xs font-medium ${badgeClass(layer.status)}`}>
                      {layer.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium uppercase tracking-[0.18em] text-slate-500">
                  Canonical Task Entry
                </p>
                <h2 className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">Run Task</h2>
              </div>
              {submitting ? <LoadingSpinner size="sm" /> : null}
            </div>

            <div className="mt-5 space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-gray-200">Task Type</label>
                <input
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 focus:outline-none focus:shadow-focus dark:border-gray-600 dark:bg-gray-900 dark:text-white"
                  value={runTaskPayload.task_type}
                  onChange={(event) =>
                    setRunTaskPayload((current) => ({ ...current, task_type: event.target.value }))
                  }
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-gray-200">Description</label>
                <textarea
                  className="min-h-28 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 focus:outline-none focus:shadow-focus dark:border-gray-600 dark:bg-gray-900 dark:text-white"
                  value={runTaskPayload.description ?? ''}
                  onChange={(event) =>
                    setRunTaskPayload((current) => ({ ...current, description: event.target.value }))
                  }
                />
              </div>
              <button
                className="w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                disabled={submitting}
                onClick={handleRunTask}
              >
                Run through services/core.run_task
              </button>
              {error ? (
                <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/30 dark:text-rose-200">
                  {error}
                </div>
              ) : null}
              {runTaskResult ? (
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-gray-700 dark:bg-gray-900/40">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Latest task result</h3>
                    <span className={`rounded-full border px-2 py-1 text-xs font-medium ${badgeClass(runTaskResult.status ?? 'completed')}`}>
                      {runTaskResult.status}
                    </span>
                  </div>
                  <p className="mt-3 text-xs text-slate-600 dark:text-gray-300">
                    Trace: {runTaskResult.trace?.trace_id ?? 'not available'}
                  </p>
                  <p className="mt-1 text-xs text-slate-600 dark:text-gray-300">
                    Selected agent: {runTaskResult.decision?.selected_agent_id ?? 'n/a'}
                  </p>
                </div>
              ) : null}
            </div>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-3">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Recent Traces</h2>
            <div className="mt-4 space-y-3">
              {overview?.recent_traces.map((trace) => (
                <div
                  key={trace.trace_id}
                  className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-gray-700"
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-medium text-slate-900 dark:text-white">{trace.workflow_name}</span>
                    <span className={`rounded-full border px-2 py-1 text-xs font-medium ${badgeClass(trace.status)}`}>
                      {trace.status}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-slate-500 dark:text-gray-400">{trace.trace_id}</p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-gray-400">
                    Started {formatTimestamp(trace.started_at)}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Pending Approvals</h2>
            <div className="mt-4 space-y-3">
              {overview?.pending_approvals.length ? (
                overview.pending_approvals.map((approval) => (
                  <div
                    key={approval.approval_id}
                    className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-gray-700"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-medium text-slate-900 dark:text-white">{approval.step_id}</span>
                      <span className={`rounded-full border px-2 py-1 text-xs font-medium ${badgeClass(approval.status)}`}>
                        {approval.status}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-slate-600 dark:text-gray-300">{approval.task_summary}</p>
                    <p className="mt-1 text-xs text-slate-500 dark:text-gray-400">{approval.reason}</p>
                  </div>
                ))
              ) : (
                <p className="rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500 dark:border-gray-700 dark:text-gray-400">
                  No pending approvals.
                </p>
              )}
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Governance Decisions</h2>
            <div className="mt-4 space-y-3">
              {overview?.recent_governance.map((event) => (
                <div
                  key={event.trace_id}
                  className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-gray-700"
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-medium text-slate-900 dark:text-white">{event.workflow_name}</span>
                    <span className={`rounded-full border px-2 py-1 text-xs font-medium ${badgeClass(event.effect)}`}>
                      {event.effect}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-slate-500 dark:text-gray-400">
                    Agent: {event.selected_agent_id ?? 'n/a'}
                  </p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-gray-400">
                    Rules: {event.matched_policy_ids.length ? event.matched_policy_ids.join(', ') : 'none'}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
