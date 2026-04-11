import { useEffect, useState } from 'react'

import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { controlPlaneApi, type PlanRun, type RunPayload } from '@/services/controlPlane'

const defaultPlanPayload: RunPayload = {
  task_type: 'workflow_automation',
  description: 'Execute a multi-step workflow through canonical orchestration',
  input_data: {},
  options: {
    allow_parallel: false,
  },
}

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
    case 'rejected':
      return 'bg-rose-100 text-rose-800 border-rose-200'
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200'
  }
}

export default function PlansPage() {
  const [plans, setPlans] = useState<PlanRun[]>([])
  const [payload, setPayload] = useState<RunPayload>(defaultPlanPayload)
  const [latestResult, setLatestResult] = useState<any | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadPlans = async () => {
    setLoading(true)
    setError(null)
    try {
      setPlans(await controlPlaneApi.listPlans(12))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load plan history')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPlans()
  }, [])

  const handleRunPlan = async () => {
    setRunning(true)
    setError(null)
    try {
      const result = await controlPlaneApi.runPlan(payload)
      setLatestResult(result)
      await loadPlans()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run plan')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6 dark:bg-gray-900">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-blue-600 dark:text-blue-400">
              Orchestration
            </p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-900 dark:text-white">Plans and Step State</h1>
          </div>
          <button
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
            onClick={loadPlans}
          >
            Refresh
          </button>
        </div>

        {error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/30 dark:text-rose-200">
            {error}
          </div>
        ) : null}

        <section className="grid gap-6 xl:grid-cols-[0.9fr_1.3fr]">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm uppercase tracking-[0.18em] text-slate-500">Canonical plan entry</p>
                <h2 className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">Run Plan</h2>
              </div>
              {running ? <LoadingSpinner size="sm" /> : null}
            </div>

            <div className="mt-5 space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-gray-200">Task Type</label>
                <input
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 focus:outline-none focus:shadow-focus dark:border-gray-600 dark:bg-gray-900 dark:text-white"
                  value={payload.task_type}
                  onChange={(event) => setPayload((current) => ({ ...current, task_type: event.target.value }))}
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-gray-200">Description</label>
                <textarea
                  className="min-h-28 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 focus:outline-none focus:shadow-focus dark:border-gray-600 dark:bg-gray-900 dark:text-white"
                  value={payload.description ?? ''}
                  onChange={(event) => setPayload((current) => ({ ...current, description: event.target.value }))}
                />
              </div>
              <button
                className="w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                disabled={running}
                onClick={handleRunPlan}
              >
                Run through services/core.run_task_plan
              </button>
            </div>

            {latestResult ? (
              <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-gray-700 dark:bg-gray-900/40">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Latest plan result</h3>
                  <span className={`rounded-full border px-2 py-1 text-xs font-medium ${statusClass(latestResult.result?.status ?? 'completed')}`}>
                    {latestResult.result?.status ?? 'unknown'}
                  </span>
                </div>
                <p className="mt-3 text-xs text-slate-600 dark:text-gray-300">
                  Trace: {latestResult.trace?.trace_id ?? 'n/a'}
                </p>
                <p className="mt-1 text-xs text-slate-600 dark:text-gray-300">
                  Pending approval: {latestResult.result?.state?.pending_approval_id ?? 'none'}
                </p>
              </div>
            ) : null}
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Recent plan runs</h2>
              <span className="text-xs uppercase tracking-[0.18em] text-slate-500">{plans.length} loaded</span>
            </div>

            {loading ? (
              <div className="flex min-h-[20rem] items-center justify-center">
                <LoadingSpinner size="lg" />
              </div>
            ) : plans.length ? (
              <div className="mt-5 space-y-4">
                {plans.map((plan) => {
                  const stepResults = Array.isArray(plan.state?.step_results) ? plan.state.step_results : []
                  const steps = Array.isArray(plan.plan?.steps) ? plan.plan.steps : []

                  return (
                    <div
                      key={plan.trace_id}
                      className="rounded-2xl border border-slate-200 px-4 py-4 dark:border-gray-700"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-slate-900 dark:text-white">{plan.plan_id}</p>
                          <p className="mt-1 text-xs text-slate-500 dark:text-gray-400">{plan.trace_id}</p>
                        </div>
                        <span className={`rounded-full border px-2 py-1 text-xs font-medium ${statusClass(plan.status)}`}>
                          {plan.status}
                        </span>
                      </div>

                      <div className="mt-4 grid gap-3 md:grid-cols-2">
                        <div className="rounded-xl bg-slate-50 p-3 text-sm dark:bg-gray-900/40">
                          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Started</p>
                          <p className="mt-2 text-slate-800 dark:text-gray-100">{formatTimestamp(plan.started_at)}</p>
                        </div>
                        <div className="rounded-xl bg-slate-50 p-3 text-sm dark:bg-gray-900/40">
                          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Ended</p>
                          <p className="mt-2 text-slate-800 dark:text-gray-100">{formatTimestamp(plan.ended_at)}</p>
                        </div>
                      </div>

                      <div className="mt-4">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm font-medium text-slate-900 dark:text-white">Step state</p>
                          <p className="text-xs text-slate-500 dark:text-gray-400">
                            {stepResults.length} / {steps.length || '?'} steps reported
                          </p>
                        </div>
                        {stepResults.length ? (
                          <div className="mt-3 space-y-2">
                            {stepResults.map((step: any) => (
                              <div
                                key={step.step_id}
                                className="rounded-xl bg-slate-50 px-3 py-3 text-sm dark:bg-gray-900/40"
                              >
                                <div className="flex items-center justify-between gap-3">
                                  <span className="font-medium text-slate-800 dark:text-gray-100">{step.step_id}</span>
                                  <span className={`rounded-full border px-2 py-1 text-xs font-medium ${statusClass(step.status ?? (step.success ? 'completed' : 'failed'))}`}>
                                    {step.status ?? (step.success ? 'completed' : 'failed')}
                                  </span>
                                </div>
                                <p className="mt-2 text-xs text-slate-500 dark:text-gray-400">
                                  Agent: {step.agent_id ?? 'n/a'}
                                </p>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="mt-3 rounded-xl border border-dashed border-slate-300 px-3 py-4 text-sm text-slate-500 dark:border-gray-700 dark:text-gray-400">
                            No persisted step results for this run. Paused plans expose state through approvals. Completed
                            runs remain trace-driven in V1.
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="mt-5 rounded-2xl border border-dashed border-slate-300 px-4 py-10 text-center text-sm text-slate-500 dark:border-gray-700 dark:text-gray-400">
                No plan traces found.
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
