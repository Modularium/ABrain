import { useEffect, useState } from 'react'

import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { controlPlaneApi, type ApprovalRequest } from '@/services/controlPlane'

function formatTimestamp(value: string): string {
  return new Date(value).toLocaleString()
}

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([])
  const [comments, setComments] = useState<Record<string, string>>({})
  const [ratings, setRatings] = useState<Record<string, number | null>>({})
  const [loading, setLoading] = useState(true)
  const [actingId, setActingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lastDecision, setLastDecision] = useState<any | null>(null)

  const loadApprovals = async () => {
    setLoading(true)
    setError(null)
    try {
      setApprovals(await controlPlaneApi.listApprovals())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load approvals')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadApprovals()
  }, [])

  const handleDecision = async (approvalId: string, action: 'approve' | 'reject') => {
    setActingId(approvalId)
    setError(null)
    try {
      const comment = comments[approvalId]
      const rawRating = ratings[approvalId]
      const rating = typeof rawRating === 'number' ? rawRating / 5 : undefined
      const result =
        action === 'approve'
          ? await controlPlaneApi.approve(approvalId, comment, rating)
          : await controlPlaneApi.reject(approvalId, comment, rating)
      setLastDecision(result)
      await loadApprovals()
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action} approval`)
    } finally {
      setActingId(null)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6 dark:bg-gray-900">
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-blue-600 dark:text-blue-400">
              Human in the Loop
            </p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-900 dark:text-white">Pending Approvals</h1>
          </div>
          <button
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
            onClick={loadApprovals}
          >
            Refresh
          </button>
        </div>

        {error ? (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/30 dark:text-rose-200">
            {error}
          </div>
        ) : null}

        {lastDecision ? (
          <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:border-emerald-900/40 dark:bg-emerald-950/30 dark:text-emerald-200">
            Last decision finished with result status {lastDecision.result?.status ?? 'unknown'} and trace{' '}
            {lastDecision.trace?.trace_id ?? 'n/a'}.
          </div>
        ) : null}

        {loading ? (
          <div className="flex min-h-[22rem] items-center justify-center rounded-3xl border border-slate-200 bg-white dark:border-gray-700 dark:bg-gray-800">
            <div className="text-center">
              <LoadingSpinner size="lg" />
              <p className="mt-4 text-sm text-slate-500 dark:text-gray-400">Loading approvals</p>
            </div>
          </div>
        ) : approvals.length ? (
          <div className="space-y-4">
            {approvals.map((approval) => (
              <div
                key={approval.approval_id}
                className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800"
              >
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-sm uppercase tracking-[0.18em] text-slate-500">{approval.step_id}</p>
                    <h2 className="mt-2 text-xl font-semibold text-slate-900 dark:text-white">
                      {approval.task_summary}
                    </h2>
                    <p className="mt-2 text-sm text-slate-600 dark:text-gray-300">{approval.proposed_action_summary}</p>
                  </div>
                  <div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm dark:bg-gray-900/40">
                    <p className="text-slate-500 dark:text-gray-400">Requested</p>
                    <p className="mt-1 font-medium text-slate-900 dark:text-white">
                      {formatTimestamp(approval.requested_at)}
                    </p>
                  </div>
                </div>

                <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-2xl bg-slate-50 p-4 dark:bg-gray-900/40">
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Approval ID</p>
                    <p className="mt-2 break-all text-sm text-slate-800 dark:text-gray-100">{approval.approval_id}</p>
                  </div>
                  <div className="rounded-2xl bg-slate-50 p-4 dark:bg-gray-900/40">
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Plan</p>
                    <p className="mt-2 text-sm text-slate-800 dark:text-gray-100">{approval.plan_id}</p>
                  </div>
                  <div className="rounded-2xl bg-slate-50 p-4 dark:bg-gray-900/40">
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Risk</p>
                    <p className="mt-2 text-sm text-slate-800 dark:text-gray-100">{approval.risk}</p>
                  </div>
                  <div className="rounded-2xl bg-slate-50 p-4 dark:bg-gray-900/40">
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Agent</p>
                    <p className="mt-2 text-sm text-slate-800 dark:text-gray-100">{approval.agent_id ?? 'n/a'}</p>
                  </div>
                </div>

                <div className="mt-6 rounded-2xl border border-slate-200 p-4 dark:border-gray-700">
                  <p className="text-sm font-medium text-slate-900 dark:text-white">Policy reason</p>
                  <p className="mt-2 text-sm text-slate-600 dark:text-gray-300">{approval.reason}</p>
                </div>

                <div className="mt-6">
                  <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-gray-200">
                    Reviewer comment
                  </label>
                  <textarea
                    className="min-h-24 w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 focus:outline-none focus:shadow-focus dark:border-gray-600 dark:bg-gray-900 dark:text-white"
                    placeholder="Optional approval or rejection note"
                    value={comments[approval.approval_id] ?? ''}
                    onChange={(event) =>
                      setComments((current) => ({
                        ...current,
                        [approval.approval_id]: event.target.value,
                      }))
                    }
                  />
                </div>

                <div className="mt-4">
                  <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-gray-200">
                    Rating (optional)
                  </label>
                  <div className="flex gap-2">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        type="button"
                        className={`text-2xl transition-colors ${
                          (ratings[approval.approval_id] ?? 0) >= star
                            ? 'text-amber-400'
                            : 'text-slate-300 dark:text-gray-600'
                        }`}
                        onClick={() =>
                          setRatings((current) => ({
                            ...current,
                            [approval.approval_id]:
                              current[approval.approval_id] === star ? null : star,
                          }))
                        }
                      >
                        ★
                      </button>
                    ))}
                    {ratings[approval.approval_id] != null && (
                      <span className="ml-2 self-center text-xs text-slate-500 dark:text-gray-400">
                        {ratings[approval.approval_id]}/5
                      </span>
                    )}
                  </div>
                </div>

                <div className="mt-6 flex flex-wrap gap-3">
                  <button
                    className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                    disabled={actingId === approval.approval_id}
                    onClick={() => handleDecision(approval.approval_id, 'approve')}
                  >
                    {actingId === approval.approval_id ? 'Working...' : 'Approve'}
                  </button>
                  <button
                    className="rounded-xl bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-700 disabled:opacity-50"
                    disabled={actingId === approval.approval_id}
                    onClick={() => handleDecision(approval.approval_id, 'reject')}
                  >
                    {actingId === approval.approval_id ? 'Working...' : 'Reject'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center text-sm text-slate-500 shadow-sm dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
            No pending approvals in the canonical approval store.
          </div>
        )}
      </div>
    </div>
  )
}
