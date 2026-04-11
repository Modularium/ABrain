import { useEffect, useState } from 'react'

import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import {
  controlPlaneApi,
  type ExplainabilityRecord,
  type TraceRecord,
  type TraceSnapshot,
} from '@/services/controlPlane'

function formatTimestamp(value?: string | null): string {
  if (!value) {
    return 'Not finished'
  }
  return new Date(value).toLocaleString()
}

function statusClass(status: string): string {
  switch (status) {
    case 'completed':
      return 'bg-emerald-100 text-emerald-800 border-emerald-200'
    case 'paused':
      return 'bg-amber-100 text-amber-800 border-amber-200'
    case 'failed':
    case 'denied':
      return 'bg-rose-100 text-rose-800 border-rose-200'
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200'
  }
}

export default function TracesPage() {
  const [traces, setTraces] = useState<TraceRecord[]>([])
  const [selectedTraceId, setSelectedTraceId] = useState<string>('')
  const [trace, setTrace] = useState<TraceSnapshot | null>(null)
  const [explainability, setExplainability] = useState<ExplainabilityRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadTraceDetail = async (traceId: string) => {
    setSelectedTraceId(traceId)
    setDetailLoading(true)
    setError(null)
    try {
      const [traceResult, explainabilityResult] = await Promise.all([
        controlPlaneApi.getTrace(traceId),
        controlPlaneApi.getExplainability(traceId),
      ])
      setTrace(traceResult)
      setExplainability(explainabilityResult)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load trace detail')
    } finally {
      setDetailLoading(false)
    }
  }

  const loadTraces = async () => {
    setLoading(true)
    setError(null)
    try {
      const recent = await controlPlaneApi.listTraces(16)
      setTraces(recent)
      if (recent[0]) {
        await loadTraceDetail(recent[0].trace_id)
      } else {
        setTrace(null)
        setExplainability([])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load traces')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTraces()
    // eslint-disable-next-line react-hooks/exhaustive-deps
    // loadTraces is defined inline without useCallback; adding it as a dependency
    // would cause an infinite fetch loop. It only runs once on mount intentionally.
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 p-6 dark:bg-gray-900">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-blue-600 dark:text-blue-400">
              Audit and Explainability
            </p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-900 dark:text-white">Trace Explorer</h1>
          </div>
          <button
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
            onClick={loadTraces}
          >
            Refresh
          </button>
        </div>

        {error ? (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/30 dark:text-rose-200">
            {error}
          </div>
        ) : null}

        {loading ? (
          <div className="flex min-h-[24rem] items-center justify-center rounded-3xl border border-slate-200 bg-white dark:border-gray-700 dark:bg-gray-800">
            <div className="text-center">
              <LoadingSpinner size="lg" />
              <p className="mt-4 text-sm text-slate-500 dark:text-gray-400">Loading traces</p>
            </div>
          </div>
        ) : (
          <div className="grid gap-6 xl:grid-cols-[0.9fr_1.4fr]">
            <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Recent traces</h2>
                <span className="text-xs uppercase tracking-[0.18em] text-slate-500">{traces.length} loaded</span>
              </div>
              <div className="mt-4 space-y-3">
                {traces.map((item) => (
                  <button
                    key={item.trace_id}
                    className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                      selectedTraceId === item.trace_id
                        ? 'border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-950/30'
                        : 'border-slate-200 hover:bg-slate-50 dark:border-gray-700 dark:hover:bg-gray-900/40'
                    }`}
                    onClick={() => loadTraceDetail(item.trace_id)}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-medium text-slate-900 dark:text-white">{item.workflow_name}</span>
                      <span className={`rounded-full border px-2 py-1 text-xs font-medium ${statusClass(item.status)}`}>
                        {item.status}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-slate-500 dark:text-gray-400">{item.trace_id}</p>
                    <p className="mt-1 text-xs text-slate-500 dark:text-gray-400">
                      Started {formatTimestamp(item.started_at)}
                    </p>
                  </button>
                ))}
              </div>
            </section>

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
              {detailLoading ? (
                <div className="flex min-h-[24rem] items-center justify-center">
                  <LoadingSpinner size="lg" />
                </div>
              ) : trace ? (
                <div className="space-y-6">
                  <div>
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-sm uppercase tracking-[0.18em] text-slate-500">Trace detail</p>
                        <h2 className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">
                          {trace.trace.workflow_name}
                        </h2>
                      </div>
                      <span className={`rounded-full border px-3 py-1 text-sm font-medium ${statusClass(trace.trace.status)}`}>
                        {trace.trace.status}
                      </span>
                    </div>
                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                      <div className="rounded-2xl bg-slate-50 p-4 dark:bg-gray-900/40">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Trace ID</p>
                        <p className="mt-2 break-all text-sm text-slate-800 dark:text-gray-100">{trace.trace.trace_id}</p>
                      </div>
                      <div className="rounded-2xl bg-slate-50 p-4 dark:bg-gray-900/40">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Task ID</p>
                        <p className="mt-2 text-sm text-slate-800 dark:text-gray-100">{trace.trace.task_id ?? 'n/a'}</p>
                      </div>
                      <div className="rounded-2xl bg-slate-50 p-4 dark:bg-gray-900/40">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Started</p>
                        <p className="mt-2 text-sm text-slate-800 dark:text-gray-100">{formatTimestamp(trace.trace.started_at)}</p>
                      </div>
                      <div className="rounded-2xl bg-slate-50 p-4 dark:bg-gray-900/40">
                        <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Ended</p>
                        <p className="mt-2 text-sm text-slate-800 dark:text-gray-100">{formatTimestamp(trace.trace.ended_at)}</p>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Spans</h3>
                    <div className="mt-4 space-y-3">
                      {trace.spans.map((span) => (
                        <div
                          key={span.span_id}
                          className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-gray-700"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div>
                              <p className="font-medium text-slate-900 dark:text-white">{span.name}</p>
                              <p className="text-xs text-slate-500 dark:text-gray-400">{span.span_type}</p>
                            </div>
                            <span className={`rounded-full border px-2 py-1 text-xs font-medium ${statusClass(span.status)}`}>
                              {span.status}
                            </span>
                          </div>
                          <div className="mt-3 grid gap-2 text-xs text-slate-500 dark:text-gray-400 md:grid-cols-2">
                            <p>Started {formatTimestamp(span.started_at)}</p>
                            <p>Ended {formatTimestamp(span.ended_at)}</p>
                          </div>
                          {span.events.length ? (
                            <div className="mt-3 space-y-2 rounded-xl bg-slate-50 p-3 dark:bg-gray-900/40">
                              {span.events.map((event) => (
                                <div key={`${span.span_id}-${event.timestamp}-${event.event_type}`} className="text-xs">
                                  <p className="font-medium text-slate-800 dark:text-gray-100">{event.event_type}</p>
                                  <p className="mt-1 text-slate-600 dark:text-gray-300">{event.message}</p>
                                </div>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Explainability</h3>
                    <div className="mt-4 space-y-3">
                      {explainability.length ? (
                        explainability.map((item) => (
                          <div
                            key={`${item.trace_id}-${item.step_id ?? 'step'}`}
                            className="rounded-2xl border border-slate-200 px-4 py-3 dark:border-gray-700"
                          >
                            <div className="flex items-center justify-between gap-3">
                              <div>
                                <p className="font-medium text-slate-900 dark:text-white">{item.step_id ?? 'task'}</p>
                                <p className="text-xs text-slate-500 dark:text-gray-400">
                                  Selected agent: {item.selected_agent_id ?? 'n/a'}
                                </p>
                              </div>
                              <span
                                className={`rounded-full border px-2 py-1 text-xs font-medium ${
                                  item.approval_required ? statusClass('paused') : statusClass('completed')
                                }`}
                              >
                                {item.approval_required ? 'approval required' : 'allow'}
                              </span>
                            </div>
                            <p className="mt-3 text-sm text-slate-700 dark:text-gray-200">
                              {item.routing_reason_summary}
                            </p>
                            <p className="mt-2 text-xs text-slate-500 dark:text-gray-400">
                              Policy rules: {item.matched_policy_ids.length ? item.matched_policy_ids.join(', ') : 'none'}
                            </p>
                          </div>
                        ))
                      ) : (
                        <div className="rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500 dark:border-gray-700 dark:text-gray-400">
                          No explainability records for this trace.
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex min-h-[24rem] items-center justify-center text-sm text-slate-500 dark:text-gray-400">
                  No trace selected.
                </div>
              )}
            </section>
          </div>
        )}
      </div>
    </div>
  )
}
