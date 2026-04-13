import { useEffect, useState } from 'react'

import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { controlPlaneApi, type ControlPlaneAgent } from '@/services/controlPlane'

function valueOrFallback(value: unknown): string {
  if (typeof value === 'string' && value.trim()) {
    return value
  }
  return 'not exposed'
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<ControlPlaneAgent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadAgents = async () => {
    setLoading(true)
    setError(null)
    try {
      setAgents(await controlPlaneApi.listAgents())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load agents')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAgents()
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 p-6 dark:bg-gray-900">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-blue-600 dark:text-blue-400">
              Capability Surface
            </p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-900 dark:text-white">Agents and Capabilities</h1>
          </div>
          <button
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
            onClick={loadAgents}
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
          <div className="flex min-h-[22rem] items-center justify-center rounded-3xl border border-slate-200 bg-white dark:border-gray-700 dark:bg-gray-800">
            <div className="text-center">
              <LoadingSpinner size="lg" />
              <p className="mt-4 text-sm text-slate-500 dark:text-gray-400">Loading agents</p>
            </div>
          </div>
        ) : agents.length ? (
          <div className="grid gap-6 lg:grid-cols-2">
            {agents.map((agent) => {
              const projectionComplete = Boolean(agent.metadata?.descriptor_projection_complete)

              return (
                <article
                  key={agent.agent_id}
                  className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
                >
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <p className="text-sm uppercase tracking-[0.18em] text-slate-500">{agent.agent_id}</p>
                      <h2 className="mt-2 text-2xl font-semibold text-slate-900 dark:text-white">
                        {agent.display_name}
                      </h2>
                    </div>
                    <span
                      className={`rounded-full border px-3 py-1 text-xs font-medium ${
                        projectionComplete
                          ? 'border-emerald-200 bg-emerald-100 text-emerald-800'
                          : 'border-amber-200 bg-amber-100 text-amber-800'
                      }`}
                    >
                      {projectionComplete ? 'descriptor-complete' : 'projected view'}
                    </span>
                  </div>

                  <div className="mt-6 grid gap-4 md:grid-cols-2">
                    <div className="rounded-2xl bg-slate-50 p-4 dark:bg-gray-900/40">
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Source Type</p>
                      <p className="mt-2 text-sm text-slate-800 dark:text-gray-100">
                        {valueOrFallback(agent.source_type)}
                      </p>
                    </div>
                    <div className="rounded-2xl bg-slate-50 p-4 dark:bg-gray-900/40">
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Execution Kind</p>
                      <p className="mt-2 text-sm text-slate-800 dark:text-gray-100">
                        {valueOrFallback(agent.execution_kind)}
                      </p>
                    </div>
                    <div className="rounded-2xl bg-slate-50 p-4 dark:bg-gray-900/40">
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Availability</p>
                      <p className="mt-2 text-sm text-slate-800 dark:text-gray-100">
                        {valueOrFallback(agent.availability)}
                      </p>
                    </div>
                    <div className="rounded-2xl bg-slate-50 p-4 dark:bg-gray-900/40">
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Trust Level</p>
                      <p className="mt-2 text-sm text-slate-800 dark:text-gray-100">
                        {valueOrFallback(agent.trust_level)}
                      </p>
                    </div>
                  </div>

                  <div className="mt-6 rounded-2xl border border-slate-200 p-4 dark:border-gray-700">
                    <p className="text-sm font-medium text-slate-900 dark:text-white">Capabilities</p>
                    {agent.capabilities.length ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {agent.capabilities.map((capability) => (
                          <span
                            key={capability}
                            className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 dark:border-blue-900/50 dark:bg-blue-950/30 dark:text-blue-200"
                          >
                            {capability}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="mt-3 text-sm text-slate-500 dark:text-gray-400">No capabilities exposed by the registry entry.</p>
                    )}
                  </div>

                  <div className="mt-6 rounded-2xl border border-slate-200 p-4 dark:border-gray-700">
                    <p className="text-sm font-medium text-slate-900 dark:text-white">Execution Surface</p>
                    {agent.execution_capabilities ? (
                      <>
                        <div className="mt-3 grid gap-3 md:grid-cols-2">
                          <div className="rounded-2xl bg-slate-50 p-4 text-sm dark:bg-gray-900/40">
                            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Protocol</p>
                            <p className="mt-2 text-slate-800 dark:text-gray-100">
                              {agent.execution_capabilities.execution_protocol}
                            </p>
                          </div>
                          <div className="rounded-2xl bg-slate-50 p-4 text-sm dark:bg-gray-900/40">
                            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Runtime</p>
                            <div className="mt-2 flex flex-wrap gap-2">
                              <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200">
                                network {agent.execution_capabilities.requires_network ? 'required' : 'not-required'}
                              </span>
                              <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200">
                                local process {agent.execution_capabilities.requires_local_process ? 'required' : 'not-required'}
                              </span>
                            </div>
                          </div>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700 dark:border-gray-700 dark:bg-gray-900/40 dark:text-gray-200">
                            cost reporting {agent.execution_capabilities.supports_cost_reporting ? 'yes' : 'no'}
                          </span>
                          <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700 dark:border-gray-700 dark:bg-gray-900/40 dark:text-gray-200">
                            token reporting {agent.execution_capabilities.supports_token_reporting ? 'yes' : 'no'}
                          </span>
                        </div>
                        <div className="mt-4">
                          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Runtime Constraints</p>
                          {agent.execution_capabilities.runtime_constraints.length ? (
                            <div className="mt-3 flex flex-wrap gap-2">
                              {agent.execution_capabilities.runtime_constraints.map((constraint) => (
                                <span
                                  key={constraint}
                                  className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 dark:border-emerald-900/40 dark:bg-emerald-950/30 dark:text-emerald-200"
                                >
                                  {constraint}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <p className="mt-3 text-sm text-slate-500 dark:text-gray-400">
                              No additional runtime constraints exposed.
                            </p>
                          )}
                        </div>
                      </>
                    ) : (
                      <p className="mt-3 text-sm text-slate-500 dark:text-gray-400">
                        No execution surface exposed for this agent.
                      </p>
                    )}
                  </div>

                  <div className="mt-6 grid gap-3 md:grid-cols-2">
                    <div className="rounded-2xl bg-slate-50 p-4 text-sm dark:bg-gray-900/40">
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Version</p>
                      <p className="mt-2 text-slate-800 dark:text-gray-100">
                        {valueOrFallback(agent.metadata?.version)}
                      </p>
                    </div>
                    <div className="rounded-2xl bg-slate-50 p-4 text-sm dark:bg-gray-900/40">
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Domain</p>
                      <p className="mt-2 text-slate-800 dark:text-gray-100">
                        {valueOrFallback(agent.metadata?.domain)}
                      </p>
                    </div>
                  </div>
                </article>
              )
            })}
          </div>
        ) : (
          <div className="rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center text-sm text-slate-500 shadow-sm dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
            No agents are currently exposed through the canonical listing path.
          </div>
        )}
      </div>
    </div>
  )
}
