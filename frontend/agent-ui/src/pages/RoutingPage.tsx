import { useEffect, useMemo, useState } from 'react'

import {
  controlPlaneApi,
  type RoutingModelEntry,
  type RoutingModelFilters,
  type RoutingModelsResponse,
} from '@/services/controlPlane'

interface RoutingRule {
  id: string
  name: string
  description: string
  enabled: boolean
  priority: number
  conditions: {
    taskType?: string[]
    keywords?: string[]
    agentDomain?: string[]
    priority?: string[]
    contentLength?: { min?: number; max?: number }
  }
  target: {
    type: 'agent' | 'model' | 'custom'
    value: string
    fallback?: string
  }
  stats: {
    totalRequests: number
    successRate: number
    avgResponseTime: number
    lastUsed?: Date
  }
}

const mockRoutingRules: RoutingRule[] = [
  {
    id: '1',
    name: 'Docker Tasks → DockerMaster',
    description: 'Route all Docker-related tasks to specialized Docker agent',
    enabled: true,
    priority: 1,
    conditions: {
      taskType: ['docker', 'container'],
      keywords: ['docker', 'container', 'deployment'],
      agentDomain: ['Container Management']
    },
    target: {
      type: 'agent',
      value: 'DockerMaster',
      fallback: 'GeneralAgent'
    },
    stats: {
      totalRequests: 247,
      successRate: 96.8,
      avgResponseTime: 2.3,
      lastUsed: new Date(Date.now() - 120000)
    }
  },
  {
    id: '2',
    name: 'High Priority → GPT-4',
    description: 'Route high priority tasks to most capable model',
    enabled: true,
    priority: 2,
    conditions: {
      priority: ['high', 'urgent']
    },
    target: {
      type: 'model',
      value: 'gpt-4-turbo',
      fallback: 'gpt-3.5-turbo'
    },
    stats: {
      totalRequests: 89,
      successRate: 98.9,
      avgResponseTime: 4.1,
      lastUsed: new Date(Date.now() - 300000)
    }
  },
  {
    id: '3',
    name: 'Long Content → Claude',
    description: 'Route long content analysis to Claude models',
    enabled: true,
    priority: 3,
    conditions: {
      contentLength: { min: 5000 },
      taskType: ['analysis', 'processing']
    },
    target: {
      type: 'model',
      value: 'claude-3-opus',
      fallback: 'claude-3-sonnet'
    },
    stats: {
      totalRequests: 156,
      successRate: 94.2,
      avgResponseTime: 6.7,
      lastUsed: new Date(Date.now() - 450000)
    }
  }
]

export default function ModernRoutingPage() {
  const [routingRules, setRoutingRules] = useState<RoutingRule[]>(mockRoutingRules)
  const [catalog, setCatalog] = useState<RoutingModelsResponse | null>(null)
  const [catalogLoading, setCatalogLoading] = useState(false)
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [catalogFilters, setCatalogFilters] = useState<RoutingModelFilters>({})
  const [activeTab, setActiveTab] = useState<'rules' | 'models' | 'analytics'>('rules')
  const [selectedRule] = useState<string | null>(null)
  const [isCreatingRule, setIsCreatingRule] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'enabled' | 'disabled'>('all')

  // Fetch `/control-plane/routing/models` (canonical catalog — §6.5 Green AI).
  // Refetch when filters change; empty filters query the full catalog.
  useEffect(() => {
    let cancelled = false
    setCatalogLoading(true)
    setCatalogError(null)
    controlPlaneApi
      .getRoutingModels(catalogFilters)
      .then((payload) => {
        if (cancelled) return
        setCatalog(payload)
      })
      .catch((err) => {
        if (cancelled) return
        setCatalogError(err instanceof Error ? err.message : 'Failed to load routing catalog')
      })
      .finally(() => {
        if (!cancelled) setCatalogLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [catalogFilters])

  const availableCatalogModelCount = useMemo(() => {
    if (!catalog) return 0
    return catalog.models.filter((m) => m.is_available).length
  }, [catalog])

  const getStatusColor = (enabled: boolean) => {
    return enabled 
      ? 'bg-green-100 text-green-800 border-green-200'
      : 'bg-gray-100 text-gray-800 border-gray-200'
  }

  const getModelStatusColor = (isAvailable: boolean) => {
    return isAvailable
      ? 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-300'
      : 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-300'
  }

  const getTierBadgeColor = (tier: string) => {
    switch (tier) {
      case 'local': return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300'
      case 'small': return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
      case 'medium': return 'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-300'
      case 'large': return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
    }
  }

  const formatCostPer1k = (cost: number | null) => {
    if (cost === null) return '—'
    if (cost === 0) return 'free'
    return `$${cost.toFixed(4)}`
  }

  const formatTimeAgo = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    
    if (minutes < 1) return 'Just now'
    if (minutes < 60) return `${minutes}m ago`
    if (minutes < 1440) return `${Math.floor(minutes / 60)}h ago`
    return `${Math.floor(minutes / 1440)}d ago`
  }

  const toggleRule = (id: string) => {
    setRoutingRules(prev => prev.map(rule => 
      rule.id === id ? { ...rule, enabled: !rule.enabled } : rule
    ))
  }

  const filteredRules = routingRules.filter(rule => {
    const matchesSearch = rule.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         rule.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = statusFilter === 'all' || 
                         (statusFilter === 'enabled' && rule.enabled) ||
                         (statusFilter === 'disabled' && !rule.enabled)
    return matchesSearch && matchesStatus
  })

  const RuleCard = ({ rule }: { rule: RoutingRule }) => (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm hover:shadow-md transition-all duration-200">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className={`w-3 h-3 rounded-full ${rule.enabled ? 'bg-green-500' : 'bg-gray-400'}`}></div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white text-lg">
              {rule.name}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Priority {rule.priority}
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <span className={`px-3 py-1 text-xs rounded-full border font-medium ${getStatusColor(rule.enabled)}`}>
            {rule.enabled ? '✅ Enabled' : '⏸️ Disabled'}
          </span>
          <button
            onClick={() => toggleRule(rule.id)}
            className={`w-11 h-6 rounded-full relative transition-colors ${
              rule.enabled ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-600'
            }`}
          >
            <span
              className={`absolute w-5 h-5 bg-white rounded-full shadow transform transition-transform top-0.5 ${
                rule.enabled ? 'translate-x-5' : 'translate-x-0.5'
              }`}
            />
          </button>
        </div>
      </div>

      <p className="text-gray-600 dark:text-gray-300 text-sm mb-4">
        {rule.description}
      </p>

      {/* Conditions */}
      <div className="mb-4">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Conditions:</h4>
        <div className="flex flex-wrap gap-2">
          {rule.conditions.taskType?.map((type, index) => (
            <span key={index} className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 text-xs rounded-lg">
              Type: {type}
            </span>
          ))}
          {rule.conditions.keywords?.map((keyword, index) => (
            <span key={index} className="px-2 py-1 bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 text-xs rounded-lg">
              "{keyword}"
            </span>
          ))}
          {rule.conditions.priority?.map((priority, index) => (
            <span key={index} className="px-2 py-1 bg-orange-100 dark:bg-orange-900 text-orange-700 dark:text-orange-300 text-xs rounded-lg">
              Priority: {priority}
            </span>
          ))}
          {rule.conditions.contentLength && (
            <span className="px-2 py-1 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 text-xs rounded-lg">
              Length: {rule.conditions.contentLength.min ? `>${rule.conditions.contentLength.min}` : ''}
              {rule.conditions.contentLength.max ? `<${rule.conditions.contentLength.max}` : ''}
            </span>
          )}
        </div>
      </div>

      {/* Target */}
      <div className="mb-4">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Target:</h4>
        <div className="flex items-center space-x-2">
          <span className="px-3 py-1 bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 text-sm rounded-lg font-medium">
            {rule.target.type === 'agent' ? '🤖' : '🧠'} {rule.target.value}
          </span>
          {rule.target.fallback && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              → Fallback: {rule.target.fallback}
            </span>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-100 dark:border-gray-700">
        <div className="text-center">
          <div className="text-lg font-bold text-gray-900 dark:text-white">{rule.stats.totalRequests}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400">Requests</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-green-600">{rule.stats.successRate}%</div>
          <div className="text-xs text-gray-500 dark:text-gray-400">Success</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-blue-600">{rule.stats.avgResponseTime}s</div>
          <div className="text-xs text-gray-500 dark:text-gray-400">Avg Time</div>
        </div>
      </div>

      {rule.stats.lastUsed && (
        <div className="mt-3 text-xs text-gray-500 dark:text-gray-400 text-center">
          Last used: {formatTimeAgo(rule.stats.lastUsed)}
        </div>
      )}
    </div>
  )

  const ModelCard = ({ model }: { model: RoutingModelEntry }) => (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm hover:shadow-md transition-all duration-200">
      <div className="flex items-start justify-between mb-4 gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-gray-900 dark:text-white text-lg break-all">
              {model.display_name}
            </h3>
            <span className={`px-2 py-0.5 text-xs rounded-md font-medium ${getTierBadgeColor(model.tier)}`}>
              {model.tier}
            </span>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 font-mono break-all">
            {model.model_id}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            provider: {model.provider}
          </p>
        </div>
        <span className={`px-3 py-1 text-xs rounded-full border font-medium whitespace-nowrap ${getModelStatusColor(model.is_available)}`}>
          {model.is_available ? 'available' : 'unavailable'}
        </span>
      </div>

      {/* Purposes */}
      <div className="mb-4">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Purposes</h4>
        <div className="flex flex-wrap gap-2">
          {model.purposes.length === 0 ? (
            <span className="text-xs text-gray-400 italic">none declared</span>
          ) : (
            model.purposes.map((purpose) => (
              <span key={purpose} className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs rounded-lg">
                {purpose}
              </span>
            ))
          )}
        </div>
      </div>

      {/* Capability flags */}
      <div className="mb-4 flex flex-wrap gap-2 text-xs">
        <span className={`px-2 py-1 rounded-md ${model.supports_tool_use ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300' : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'}`}>
          tool_use: {model.supports_tool_use ? 'yes' : 'no'}
        </span>
        <span className={`px-2 py-1 rounded-md ${model.supports_structured_output ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300' : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'}`}>
          structured_output: {model.supports_structured_output ? 'yes' : 'no'}
        </span>
      </div>

      {/* Catalog stats — canonical fields only */}
      <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-100 dark:border-gray-700 text-center">
        <div>
          <div className="text-lg font-semibold text-gray-900 dark:text-white">
            {model.context_window.toLocaleString()}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">context</div>
        </div>
        <div>
          <div className="text-lg font-semibold text-gray-900 dark:text-white">
            {formatCostPer1k(model.cost_per_1k_tokens)}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">$/1k tok</div>
        </div>
        <div>
          <div className="text-lg font-semibold text-gray-900 dark:text-white">
            {model.p95_latency_ms !== null ? `${model.p95_latency_ms}ms` : '—'}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">p95 latency</div>
        </div>
      </div>

      {/* §6.5 lineage + energy — honesty rule: `None` means not declared */}
      <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700 space-y-2 text-xs">
        <div>
          <span className="font-medium text-gray-700 dark:text-gray-300">quantization: </span>
          {model.quantization ? (
            <span className="text-gray-600 dark:text-gray-400">
              {model.quantization.method} ({model.quantization.bits}-bit,
              {' '}baseline {model.quantization.baseline_model_id}
              {model.quantization.quality_delta_vs_baseline !== null
                ? `, Δ ${model.quantization.quality_delta_vs_baseline.toFixed(3)}`
                : ''})
            </span>
          ) : (
            <span className="text-gray-400 italic">not declared</span>
          )}
        </div>
        <div>
          <span className="font-medium text-gray-700 dark:text-gray-300">distillation: </span>
          {model.distillation ? (
            <span className="text-gray-600 dark:text-gray-400">
              {model.distillation.recipe} (teacher {model.distillation.teacher_model_id}
              {model.distillation.quality_delta_vs_teacher !== null
                ? `, Δ ${model.distillation.quality_delta_vs_teacher.toFixed(3)}`
                : ''})
            </span>
          ) : (
            <span className="text-gray-400 italic">not declared</span>
          )}
        </div>
        <div>
          <span className="font-medium text-gray-700 dark:text-gray-300">energy_profile: </span>
          {model.energy_profile ? (
            <span className="text-gray-600 dark:text-gray-400">
              {model.energy_profile.avg_power_watts.toFixed(1)}W ({model.energy_profile.source})
            </span>
          ) : (
            <span className="text-gray-400 italic">not declared</span>
          )}
        </div>
      </div>
    </div>
  )

  return (
    <div className="p-6 bg-gray-50 dark:bg-gray-900 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              Request Routing
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Configure intelligent task routing and model selection
            </p>
          </div>
          
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setIsCreatingRule(true)}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center space-x-2"
            >
              <span>➕</span>
              <span>Add Rule</span>
            </button>
          </div>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
                <span className="text-blue-600 dark:text-blue-400">🔄</span>
              </div>
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Active Rules</span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {routingRules.filter(r => r.enabled).length}
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center">
                <span className="text-green-600 dark:text-green-400">🧠</span>
              </div>
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Available Models</span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {catalog ? availableCatalogModelCount : '—'}
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center">
                <span className="text-purple-600 dark:text-purple-400">📊</span>
              </div>
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Requests</span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {routingRules.reduce((acc, rule) => acc + rule.stats.totalRequests, 0).toLocaleString()}
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 bg-emerald-100 dark:bg-emerald-900 rounded-lg flex items-center justify-center">
                <span className="text-emerald-600 dark:text-emerald-400">✅</span>
              </div>
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Avg Success Rate</span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {routingRules.length > 0 ? 
                ((routingRules.reduce((acc, rule) => acc + rule.stats.successRate, 0) / routingRules.length).toFixed(1) + '%') 
                : '0%'
              }
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 mb-6">
          <div className="border-b border-gray-200 dark:border-gray-700">
            <nav className="flex space-x-8 px-6">
              {[
                { id: 'rules', label: 'Routing Rules', icon: '🔄' },
                { id: 'models', label: 'Models', icon: '🧠' },
                { id: 'analytics', label: 'Analytics', icon: '📊' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                  }`}
                >
                  <span className="mr-2">{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {activeTab === 'rules' && (
              <div>
                {/* Filters */}
                <div className="flex flex-col sm:flex-row gap-4 mb-6">
                  <div className="flex-1">
                    <input
                      type="text"
                      placeholder="Search routing rules..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:shadow-focus"
                    />
                  </div>
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value as any)}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:shadow-focus"
                  >
                    <option value="all">All Rules</option>
                    <option value="enabled">Enabled Only</option>
                    <option value="disabled">Disabled Only</option>
                  </select>
                </div>

                {/* Rules Grid */}
                {filteredRules.length === 0 ? (
                  <div className="text-center py-12">
                    <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
                      <span className="text-gray-400 text-2xl">🔄</span>
                    </div>
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No routing rules found</h3>
                    <p className="text-gray-500 dark:text-gray-400">Create your first routing rule to get started</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {filteredRules.map((rule) => (
                      <RuleCard key={rule.id} rule={rule} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'models' && (
              <div className="space-y-6">
                {/* Filters forwarded verbatim to `/control-plane/routing/models` */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                  <select
                    value={catalogFilters.tier ?? ''}
                    onChange={(e) =>
                      setCatalogFilters((prev) => ({
                        ...prev,
                        tier: e.target.value || null,
                      }))
                    }
                    className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    <option value="">All tiers</option>
                    <option value="local">local</option>
                    <option value="small">small</option>
                    <option value="medium">medium</option>
                    <option value="large">large</option>
                  </select>
                  <select
                    value={catalogFilters.provider ?? ''}
                    onChange={(e) =>
                      setCatalogFilters((prev) => ({
                        ...prev,
                        provider: e.target.value || null,
                      }))
                    }
                    className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    <option value="">All providers</option>
                    <option value="anthropic">anthropic</option>
                    <option value="openai">openai</option>
                    <option value="google">google</option>
                    <option value="local">local</option>
                    <option value="custom">custom</option>
                  </select>
                  <select
                    value={catalogFilters.purpose ?? ''}
                    onChange={(e) =>
                      setCatalogFilters((prev) => ({
                        ...prev,
                        purpose: e.target.value || null,
                      }))
                    }
                    className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    <option value="">All purposes</option>
                    <option value="planning">planning</option>
                    <option value="classification">classification</option>
                    <option value="ranking">ranking</option>
                    <option value="retrieval_assist">retrieval_assist</option>
                    <option value="local_assist">local_assist</option>
                    <option value="specialist">specialist</option>
                  </select>
                  <label className="flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white cursor-pointer">
                    <input
                      type="checkbox"
                      checked={Boolean(catalogFilters.available_only)}
                      onChange={(e) =>
                        setCatalogFilters((prev) => ({
                          ...prev,
                          available_only: e.target.checked,
                        }))
                      }
                    />
                    available only
                  </label>
                </div>

                {/* Catalog meta line — total / catalog_size verbatim from the service */}
                {catalog && !catalogError ? (
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {catalog.total} of {catalog.catalog_size} models match current filters
                  </p>
                ) : null}

                {catalogError ? (
                  <div className="rounded-xl border border-rose-200 bg-rose-50 dark:border-rose-900/40 dark:bg-rose-950/30 px-4 py-3 text-sm text-rose-700 dark:text-rose-200">
                    Failed to load routing catalog: {catalogError}
                  </div>
                ) : catalogLoading && !catalog ? (
                  <div className="py-12 text-center text-sm text-gray-500 dark:text-gray-400">
                    Loading routing catalog…
                  </div>
                ) : catalog && catalog.models.length === 0 ? (
                  <div className="py-12 text-center text-sm text-gray-500 dark:text-gray-400">
                    No models match the selected filters.
                  </div>
                ) : catalog ? (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {catalog.models.map((model) => (
                      <ModelCard key={model.model_id} model={model} />
                    ))}
                  </div>
                ) : null}
              </div>
            )}

            {activeTab === 'analytics' && (
              <div className="space-y-6">
                {/* Analytics placeholder */}
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-xl p-12 text-center">
                  <div className="text-4xl mb-4">📊</div>
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                    Routing Analytics
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400">
                    Detailed analytics and performance metrics coming soon
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
