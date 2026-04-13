import { useState, useEffect, useRef } from 'react'

interface LogEntry {
  id: string
  timestamp: Date
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'FATAL'
  source: string
  message: string
  metadata?: Record<string, any>
  stackTrace?: string
}

interface SystemInfo {
  platform: string
  nodeVersion: string
  architecture: string
  totalMemory: string
  freeMemory: string
  uptime: string
  cpuCores: number
  hostname: string
  version: string
  environment: string
  buildTime: string
  gitCommit: string
}

interface EnvironmentVariable {
  key: string
  value: string
  masked: boolean
  category: 'system' | 'database' | 'api' | 'security' | 'custom'
}

interface ApiEndpoint {
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  path: string
  description: string
  authenticated: boolean
  parameters?: Array<{
    name: string
    type: string
    required: boolean
    description: string
  }>
}

interface NetworkTest {
  id: string
  name: string
  url: string
  status: 'pending' | 'success' | 'failed' | 'timeout'
  responseTime?: number
  statusCode?: number
  error?: string
}

interface CacheEntry {
  key: string
  type: 'redis' | 'memory' | 'file'
  size: string
  ttl: number
  lastAccessed: Date
  hitCount: number
}

const mockLogs: LogEntry[] = [
  {
    id: '1',
    timestamp: new Date(Date.now() - 1000),
    level: 'INFO',
    source: 'AgentManager',
    message: 'DockerMaster agent task completed successfully',
    metadata: { taskId: 'task_123', duration: 2340, agent: 'DockerMaster' }
  },
  {
    id: '2',
    timestamp: new Date(Date.now() - 5000),
    level: 'WARN',
    source: 'DatabaseManager',
    message: 'Slow query detected - execution time exceeded threshold',
    metadata: { query: 'SELECT * FROM tasks WHERE status = ?', executionTime: 1205 }
  },
  {
    id: '3',
    timestamp: new Date(Date.now() - 8000),
    level: 'ERROR',
    source: 'ApiController',
    message: 'Authentication failed for API request',
    metadata: { endpoint: '/api/agents', method: 'POST', ip: '192.168.1.100' },
    stackTrace: 'Error: Invalid API key\n    at AuthMiddleware.validate (/app/middleware/auth.js:42:15)\n    at Router.post (/app/routes/agents.js:15:8)'
  },
  {
    id: '4',
    timestamp: new Date(Date.now() - 12000),
    level: 'DEBUG',
    source: 'TaskScheduler',
    message: 'Scheduling new task for execution',
    metadata: { taskType: 'analysis', priority: 'medium', estimatedDuration: 300 }
  },
  {
    id: '5',
    timestamp: new Date(Date.now() - 15000),
    level: 'INFO',
    source: 'MetricsCollector',
    message: 'Metrics collection cycle completed',
    metadata: { metricsCount: 47, collectionTime: 89 }
  }
]

const mockSystemInfo: SystemInfo = {
  platform: 'Linux x64',
  nodeVersion: 'v18.17.0',
  architecture: 'x64',
  totalMemory: '16.0 GB',
  freeMemory: '5.2 GB',
  uptime: '15d 8h 42m',
  cpuCores: 8,
  hostname: 'abrain-prod-01',
  version: '2.1.0',
  environment: 'production',
  buildTime: '2024-01-15T10:30:00Z',
  gitCommit: 'a7b8c9d'
}

const mockEnvironmentVars: EnvironmentVariable[] = [
  { key: 'NODE_ENV', value: 'production', masked: false, category: 'system' },
  { key: 'PORT', value: '8000', masked: false, category: 'system' },
  { key: 'DATABASE_URL', value: 'postgresql://***:***@localhost:5432/abrain', masked: true, category: 'database' },
  { key: 'REDIS_URL', value: 'redis://localhost:6379', masked: false, category: 'database' },
  { key: 'JWT_SECRET', value: '***hidden***', masked: true, category: 'security' },
  { key: 'OPENAI_API_KEY', value: 'sk-***hidden***', masked: true, category: 'api' },
  { key: 'ANTHROPIC_API_KEY', value: 'sk-ant-***hidden***', masked: true, category: 'api' },
  { key: 'LOG_LEVEL', value: 'info', masked: false, category: 'system' },
  { key: 'MAX_AGENTS', value: '20', masked: false, category: 'custom' },
  { key: 'RATE_LIMIT_REQUESTS', value: '1000', masked: false, category: 'custom' }
]

const mockApiEndpoints: ApiEndpoint[] = [
  {
    method: 'GET',
    path: '/api/agents',
    description: 'List all available agents',
    authenticated: true,
    parameters: [
      { name: 'status', type: 'string', required: false, description: 'Filter by agent status' },
      { name: 'limit', type: 'number', required: false, description: 'Maximum number of results' }
    ]
  },
  {
    method: 'POST',
    path: '/api/agents',
    description: 'Create a new agent',
    authenticated: true,
    parameters: [
      { name: 'name', type: 'string', required: true, description: 'Agent name' },
      { name: 'domain', type: 'string', required: true, description: 'Agent domain/specialty' },
      { name: 'configuration', type: 'object', required: false, description: 'Agent configuration' }
    ]
  },
  {
    method: 'GET',
    path: '/api/tasks',
    description: 'List tasks with filtering options',
    authenticated: true,
    parameters: [
      { name: 'status', type: 'string', required: false, description: 'Filter by task status' },
      { name: 'agent_id', type: 'string', required: false, description: 'Filter by agent ID' }
    ]
  },
  {
    method: 'POST',
    path: '/api/tasks',
    description: 'Create a new task',
    authenticated: true,
    parameters: [
      { name: 'title', type: 'string', required: true, description: 'Task title' },
      { name: 'description', type: 'string', required: true, description: 'Task description' },
      { name: 'agent_id', type: 'string', required: true, description: 'Target agent ID' }
    ]
  },
  {
    method: 'GET',
    path: '/api/health',
    description: 'System health check',
    authenticated: false
  }
]

const mockCacheEntries: CacheEntry[] = [
  {
    key: 'user_sessions:*',
    type: 'redis',
    size: '2.1 MB',
    ttl: 3600,
    lastAccessed: new Date(Date.now() - 120000),
    hitCount: 1247
  },
  {
    key: 'agent_configs:*',
    type: 'memory',
    size: '156 KB',
    ttl: -1,
    lastAccessed: new Date(Date.now() - 300000),
    hitCount: 89
  },
  {
    key: 'metrics_cache:*',
    type: 'redis',
    size: '5.7 MB',
    ttl: 300,
    lastAccessed: new Date(Date.now() - 30000),
    hitCount: 2341
  },
  {
    key: 'task_results:*',
    type: 'file',
    size: '12.3 MB',
    ttl: 86400,
    lastAccessed: new Date(Date.now() - 600000),
    hitCount: 156
  }
]

export default function DebugPage() {
  const [logs, setLogs] = useState<LogEntry[]>(mockLogs)
  const [activeTab, setActiveTab] = useState<'console' | 'system' | 'api' | 'network' | 'cache' | 'profiler'>('console')
  const [logLevel, setLogLevel] = useState<'all' | 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'FATAL'>('all')
  const [autoScroll, setAutoScroll] = useState(true)
  const [logFilter, setLogFilter] = useState('')
  const [systemInfo] = useState<SystemInfo>(mockSystemInfo)
  const [environmentVars] = useState<EnvironmentVariable[]>(mockEnvironmentVars)
  const [showMaskedVars, setShowMaskedVars] = useState(false)
  const [apiEndpoints] = useState<ApiEndpoint[]>(mockApiEndpoints)
  const [selectedEndpoint, setSelectedEndpoint] = useState<ApiEndpoint | null>(null)
  const [apiTestBody, setApiTestBody] = useState('')
  const [apiTestHeaders, setApiTestHeaders] = useState('{\n  "Authorization": "Bearer YOUR_TOKEN",\n  "Content-Type": "application/json"\n}')
  const [apiTestResult, setApiTestResult] = useState<any>(null)
  const [networkTests, setNetworkTests] = useState<NetworkTest[]>([])
  const [cacheEntries] = useState<CacheEntry[]>(mockCacheEntries)
  const [sqlQuery, setSqlQuery] = useState('SELECT * FROM agents LIMIT 10;')
  const [sqlResult, setSqlResult] = useState<any>(null)
  const [performance, setPerformance] = useState({
    cpuUsage: 0,
    memoryUsage: 0,
    responseTime: 0,
    throughput: 0
  })

  const logsEndRef = useRef<HTMLDivElement>(null)
  const consoleRef = useRef<HTMLDivElement>(null)

  // Simulate real-time logs
  useEffect(() => {
    const interval = setInterval(() => {
      const newLog: LogEntry = {
        id: Date.now().toString(),
        timestamp: new Date(),
        level: ['DEBUG', 'INFO', 'WARN', 'ERROR'][Math.floor(Math.random() * 4)] as LogEntry['level'],
        source: ['AgentManager', 'DatabaseManager', 'ApiController', 'TaskScheduler', 'MetricsCollector'][Math.floor(Math.random() * 5)],
        message: [
          'Task processing completed',
          'Memory usage within normal limits',
          'API request processed successfully',
          'Cache hit ratio optimal',
          'Agent heartbeat received'
        ][Math.floor(Math.random() * 5)],
        metadata: { timestamp: Date.now() }
      }
      
      setLogs(prev => [...prev.slice(-100), newLog]) // Keep last 100 logs
    }, 2000 + Math.random() * 3000) // Random interval between 2-5 seconds

    return () => clearInterval(interval)
  }, [])

  // Auto-scroll logs
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  // Simulate performance metrics
  useEffect(() => {
    const interval = setInterval(() => {
      setPerformance(prev => ({
        cpuUsage: Math.max(0, Math.min(100, prev.cpuUsage + (Math.random() - 0.5) * 10)),
        memoryUsage: Math.max(0, Math.min(100, prev.memoryUsage + (Math.random() - 0.5) * 5)),
        responseTime: Math.max(50, prev.responseTime + (Math.random() - 0.5) * 50),
        throughput: Math.max(0, prev.throughput + (Math.random() - 0.5) * 20)
      }))
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'DEBUG': return 'bg-gray-100 text-gray-800 border-gray-200'
      case 'INFO': return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'WARN': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'ERROR': return 'bg-red-100 text-red-800 border-red-200'
      case 'FATAL': return 'bg-red-200 text-red-900 border-red-300'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getLevelIcon = (level: string) => {
    switch (level) {
      case 'DEBUG': return '🔍'
      case 'INFO': return 'ℹ️'
      case 'WARN': return '⚠️'
      case 'ERROR': return '❌'
      case 'FATAL': return '💀'
      default: return '📝'
    }
  }

  const filteredLogs = logs.filter(log => {
    const matchesLevel = logLevel === 'all' || log.level === logLevel
    const matchesFilter = logFilter === '' || 
      log.message.toLowerCase().includes(logFilter.toLowerCase()) ||
      log.source.toLowerCase().includes(logFilter.toLowerCase())
    
    return matchesLevel && matchesFilter
  })

  const formatTimeAgo = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const seconds = Math.floor(diff / 1000)
    
    if (seconds < 60) return `${seconds}s ago`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
    return `${Math.floor(seconds / 86400)}d ago`
  }

  const executeApiTest = async () => {
    if (!selectedEndpoint) return

    try {
      // Simulate API call
      setApiTestResult({ status: 'loading' })
      
      await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000))
      
      const mockResponse = {
        status: 200,
        statusText: 'OK',
        headers: {
          'content-type': 'application/json',
          'x-response-time': `${Math.floor(Math.random() * 500)}ms`
        },
        data: selectedEndpoint.method === 'GET' ? 
          { items: [{ id: 1, name: 'Sample Data' }], total: 1 } :
          { id: Date.now(), message: 'Created successfully' }
      }
      
      setApiTestResult(mockResponse)
    } catch (error) {
      setApiTestResult({
        status: 500,
        statusText: 'Internal Server Error',
        error: 'Failed to execute request'
      })
    }
  }

  const runNetworkTests = async () => {
    const tests: NetworkTest[] = [
      { id: '1', name: 'Database Connection', url: 'postgresql://localhost:5432', status: 'pending' },
      { id: '2', name: 'Redis Cache', url: 'redis://localhost:6379', status: 'pending' },
      { id: '3', name: 'OpenAI API', url: 'https://api.openai.com/v1/models', status: 'pending' },
      { id: '4', name: 'External Service', url: 'https://httpbin.org/get', status: 'pending' }
    ]
    
    setNetworkTests(tests)
    
    // Simulate network tests
    for (let i = 0; i < tests.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 500 + Math.random() * 1500))
      
      const success = Math.random() > 0.2 // 80% success rate
      const responseTime = Math.floor(Math.random() * 500) + 50
      
      setNetworkTests(prev => prev.map(test => 
        test.id === tests[i].id ? {
          ...test,
          status: success ? 'success' : 'failed',
          responseTime: success ? responseTime : undefined,
          statusCode: success ? 200 : 500,
          error: success ? undefined : 'Connection timeout'
        } : test
      ))
    }
  }

  const executeSqlQuery = async () => {
    setSqlResult({ status: 'loading' })
    
    try {
      await new Promise(resolve => setTimeout(resolve, 800 + Math.random() * 1200))
      
      // Mock SQL result
      const mockResult = {
        rows: [
          { id: 1, name: 'DockerMaster', domain: 'Container Management', status: 'active' },
          { id: 2, name: 'CodeAnalyzer', domain: 'Code Analysis', status: 'idle' },
          { id: 3, name: 'DataProcessor', domain: 'Data Processing', status: 'active' }
        ],
        rowCount: 3,
        executionTime: Math.floor(Math.random() * 100) + 10
      }
      
      setSqlResult(mockResult)
    } catch (error) {
      setSqlResult({
        error: 'Query execution failed',
        details: 'Syntax error near unexpected token'
      })
    }
  }

  const clearCache = (cacheType: string) => {
    console.log(`Clearing ${cacheType} cache...`)
    // Simulate cache clearing
  }

  const exportLogs = () => {
    const logsData = filteredLogs.map(log => ({
      timestamp: log.timestamp.toISOString(),
      level: log.level,
      source: log.source,
      message: log.message,
      metadata: log.metadata
    }))
    
    const blob = new Blob([JSON.stringify(logsData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `debug-logs-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="p-6 bg-gray-50 dark:bg-gray-900 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              Debug Console
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              System debugging, monitoring, and diagnostic tools
            </p>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 px-3 py-2 bg-green-100 dark:bg-green-900 rounded-lg">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-green-700 dark:text-green-300 font-medium text-sm">Debug Mode</span>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
                <span className="text-blue-600 dark:text-blue-400">⚡</span>
              </div>
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">CPU Usage</span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {performance.cpuUsage.toFixed(1)}%
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center">
                <span className="text-green-600 dark:text-green-400">💾</span>
              </div>
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Memory</span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {performance.memoryUsage.toFixed(1)}%
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center">
                <span className="text-purple-600 dark:text-purple-400">🕐</span>
              </div>
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Response Time</span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {performance.responseTime.toFixed(0)}ms
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 bg-orange-100 dark:bg-orange-900 rounded-lg flex items-center justify-center">
                <span className="text-orange-600 dark:text-orange-400">📊</span>
              </div>
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Throughput</span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {performance.throughput.toFixed(0)}/s
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 mb-6">
          <div className="border-b border-gray-200 dark:border-gray-700">
            <nav className="flex space-x-8 px-6 overflow-x-auto">
              {[
                { id: 'console', label: 'Console Logs', icon: '📝' },
                { id: 'system', label: 'System Info', icon: '💻' },
                { id: 'api', label: 'API Testing', icon: '🔗' },
                { id: 'network', label: 'Network Diagnostics', icon: '🌐' },
                { id: 'cache', label: 'Cache Management', icon: '🗄️' },
                { id: 'profiler', label: 'Performance', icon: '📈' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors whitespace-nowrap ${
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
            {activeTab === 'console' && (
              <div>
                {/* Console Controls */}
                <div className="flex flex-col md:flex-row gap-4 mb-6">
                  <input
                    type="text"
                    placeholder="Filter logs..."
                    value={logFilter}
                    onChange={(e) => setLogFilter(e.target.value)}
                    className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:shadow-focus"
                  />
                  
                  <select
                    value={logLevel}
                    onChange={(e) => setLogLevel(e.target.value as any)}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:shadow-focus"
                  >
                    <option value="all">All Levels</option>
                    <option value="DEBUG">DEBUG</option>
                    <option value="INFO">INFO</option>
                    <option value="WARN">WARN</option>
                    <option value="ERROR">ERROR</option>
                    <option value="FATAL">FATAL</option>
                  </select>

                  <div className="flex items-center space-x-2">
                    <label className="text-sm text-gray-600 dark:text-gray-400">Auto-scroll:</label>
                    <button
                      onClick={() => setAutoScroll(!autoScroll)}
                      className={`w-11 h-6 rounded-full relative transition-colors ${
                        autoScroll ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-600'
                      }`}
                    >
                      <span
                        className={`absolute w-5 h-5 bg-white rounded-full shadow transform transition-transform top-0.5 ${
                          autoScroll ? 'translate-x-5' : 'translate-x-0.5'
                        }`}
                      />
                    </button>
                  </div>

                  <button
                    onClick={exportLogs}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center space-x-2"
                  >
                    <span>📥</span>
                    <span>Export</span>
                  </button>
                </div>

                {/* Console Output */}
                <div 
                  ref={consoleRef}
                  className="bg-gray-900 text-green-400 rounded-xl p-4 font-mono text-sm h-96 overflow-y-auto"
                >
                  {filteredLogs.length === 0 ? (
                    <div className="text-gray-500 text-center py-8">
                      No logs match current filters
                    </div>
                  ) : (
                    <div className="space-y-1">
                      {filteredLogs.map((log) => (
                        <div key={log.id} className="flex items-start space-x-3 py-1 hover:bg-gray-800 rounded px-2 -mx-2">
                          <span className="text-gray-500 text-xs mt-0.5 w-20 flex-shrink-0">
                            {log.timestamp.toLocaleTimeString()}
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded border font-medium w-16 text-center flex-shrink-0 ${getLevelColor(log.level)}`}>
                            {log.level}
                          </span>
                          <span className="text-blue-400 text-xs w-24 flex-shrink-0">
                            {log.source}
                          </span>
                          <span className="text-green-400 flex-1">
                            {log.message}
                          </span>
                        </div>
                      ))}
                      <div ref={logsEndRef} />
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'system' && (
              <div className="space-y-6">
                {/* System Information */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-xl p-6 border border-blue-200 dark:border-blue-800">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">System Information</h3>
                    <div className="space-y-3 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Platform:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{systemInfo.platform}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Node Version:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{systemInfo.nodeVersion}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Architecture:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{systemInfo.architecture}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">CPU Cores:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{systemInfo.cpuCores}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Total Memory:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{systemInfo.totalMemory}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Free Memory:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{systemInfo.freeMemory}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Uptime:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{systemInfo.uptime}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Hostname:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{systemInfo.hostname}</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl p-6 border border-green-200 dark:border-green-800">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Application Info</h3>
                    <div className="space-y-3 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Version:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{systemInfo.version}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Environment:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{systemInfo.environment}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Build Time:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{systemInfo.buildTime}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Git Commit:</span>
                        <span className="font-medium text-gray-900 dark:text-white font-mono">{systemInfo.gitCommit}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Environment Variables */}
                <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Environment Variables</h3>
                    <div className="flex items-center space-x-2">
                      <label className="text-sm text-gray-600 dark:text-gray-400">Show masked:</label>
                      <button
                        onClick={() => setShowMaskedVars(!showMaskedVars)}
                        className={`w-11 h-6 rounded-full relative transition-colors ${
                          showMaskedVars ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-600'
                        }`}
                      >
                        <span
                          className={`absolute w-5 h-5 bg-white rounded-full shadow transform transition-transform top-0.5 ${
                            showMaskedVars ? 'translate-x-5' : 'translate-x-0.5'
                          }`}
                        />
                      </button>
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    {Object.entries(
                      environmentVars.reduce((acc, env) => {
                        if (!acc[env.category]) acc[env.category] = []
                        acc[env.category].push(env)
                        return acc
                      }, {} as Record<string, EnvironmentVariable[]>)
                    ).map(([category, vars]) => (
                      <div key={category}>
                        <h4 className="font-medium text-gray-900 dark:text-white mb-2 capitalize">{category}</h4>
                        <div className="space-y-2">
                          {vars.map((env) => (
                            <div key={env.key} className="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                              <span className="font-mono text-sm text-gray-900 dark:text-white">{env.key}</span>
                              <span className="font-mono text-sm text-gray-600 dark:text-gray-400">
                                {env.masked && !showMaskedVars ? '***hidden***' : env.value}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'api' && (
              <div className="space-y-6">
                {/* API Endpoint Selection */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Available Endpoints</h3>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {apiEndpoints.map((endpoint, index) => (
                        <button
                          key={index}
                          onClick={() => setSelectedEndpoint(endpoint)}
                          className={`w-full text-left p-3 rounded-lg border transition-colors ${
                            selectedEndpoint === endpoint
                              ? 'border-blue-300 bg-blue-50 dark:bg-blue-900/20'
                              : 'border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                          }`}
                        >
                          <div className="flex items-center space-x-3">
                            <span className={`px-2 py-1 text-xs rounded font-mono ${
                              endpoint.method === 'GET' ? 'bg-green-100 text-green-800' :
                              endpoint.method === 'POST' ? 'bg-blue-100 text-blue-800' :
                              endpoint.method === 'PUT' ? 'bg-yellow-100 text-yellow-800' :
                              endpoint.method === 'DELETE' ? 'bg-red-100 text-red-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {endpoint.method}
                            </span>
                            <span className="font-mono text-sm">{endpoint.path}</span>
                          </div>
                          <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">{endpoint.description}</p>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">API Test</h3>
                    
                    {selectedEndpoint ? (
                      <div className="space-y-4">
                        <div>
                          <div className="flex items-center space-x-3 mb-3">
                            <span className={`px-3 py-1 text-sm rounded font-mono ${
                              selectedEndpoint.method === 'GET' ? 'bg-green-100 text-green-800' :
                              selectedEndpoint.method === 'POST' ? 'bg-blue-100 text-blue-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {selectedEndpoint.method}
                            </span>
                            <span className="font-mono text-gray-900 dark:text-white">{selectedEndpoint.path}</span>
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-400">{selectedEndpoint.description}</p>
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Headers</label>
                          <textarea
                            value={apiTestHeaders}
                            onChange={(e) => setApiTestHeaders(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm focus:outline-none focus:shadow-focus"
                            rows={4}
                          />
                        </div>

                        {selectedEndpoint.method !== 'GET' && (
                          <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Request Body</label>
                            <textarea
                              value={apiTestBody}
                              onChange={(e) => setApiTestBody(e.target.value)}
                              placeholder='{"key": "value"}'
                              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm focus:outline-none focus:shadow-focus"
                              rows={4}
                            />
                          </div>
                        )}

                        <button
                          onClick={executeApiTest}
                          className="w-full px-4 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors font-medium"
                        >
                          Execute Request
                        </button>

                        {apiTestResult && (
                          <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                            <h4 className="font-medium text-gray-900 dark:text-white mb-2">Response</h4>
                            <pre className="text-sm bg-gray-900 text-green-400 p-3 rounded overflow-x-auto font-mono">
                              {JSON.stringify(apiTestResult, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                        Select an endpoint to test
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'network' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Network Diagnostics</h3>
                  <button
                    onClick={runNetworkTests}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center space-x-2"
                  >
                    <span>🔍</span>
                    <span>Run Tests</span>
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {networkTests.map((test) => (
                    <div key={test.id} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="font-medium text-gray-900 dark:text-white">{test.name}</h4>
                        <span className={`px-2 py-1 text-xs rounded-full border font-medium ${
                          test.status === 'success' ? 'bg-green-100 text-green-800 border-green-200' :
                          test.status === 'failed' ? 'bg-red-100 text-red-800 border-red-200' :
                          test.status === 'pending' ? 'bg-yellow-100 text-yellow-800 border-yellow-200' :
                          'bg-gray-100 text-gray-800 border-gray-200'
                        }`}>
                          {test.status === 'pending' && '⏳'}
                          {test.status === 'success' && '✅'}
                          {test.status === 'failed' && '❌'}
                          {test.status}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">{test.url}</p>
                      {test.responseTime && (
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          Response: {test.responseTime}ms
                        </p>
                      )}
                      {test.error && (
                        <p className="text-sm text-red-600 dark:text-red-400">{test.error}</p>
                      )}
                    </div>
                  ))}
                </div>

                {networkTests.length === 0 && (
                  <div className="text-center py-12">
                    <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
                      <span className="text-gray-400 text-2xl">🌐</span>
                    </div>
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">Network Diagnostics</h3>
                    <p className="text-gray-500 dark:text-gray-400">Click "Run Tests" to check network connectivity</p>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'cache' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Cache Management</h3>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => clearCache('all')}
                      className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors flex items-center space-x-2"
                    >
                      <span>🗑️</span>
                      <span>Clear All</span>
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {cacheEntries.map((entry, index) => (
                    <div key={index} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="font-medium text-gray-900 dark:text-white font-mono text-sm">{entry.key}</h4>
                        <span className={`px-2 py-1 text-xs rounded border font-medium ${
                          entry.type === 'redis' ? 'bg-red-100 text-red-800 border-red-200' :
                          entry.type === 'memory' ? 'bg-blue-100 text-blue-800 border-blue-200' :
                          'bg-green-100 text-green-800 border-green-200'
                        }`}>
                          {entry.type}
                        </span>
                      </div>
                      
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Size:</span>
                          <span className="font-medium text-gray-900 dark:text-white">{entry.size}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">TTL:</span>
                          <span className="font-medium text-gray-900 dark:text-white">
                            {entry.ttl === -1 ? 'Never' : `${entry.ttl}s`}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Hits:</span>
                          <span className="font-medium text-gray-900 dark:text-white">{entry.hitCount}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Last Access:</span>
                          <span className="font-medium text-gray-900 dark:text-white">
                            {formatTimeAgo(entry.lastAccessed)}
                          </span>
                        </div>
                      </div>

                      <button
                        onClick={() => clearCache(entry.key)}
                        className="w-full mt-4 px-3 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors text-sm"
                      >
                        Clear Cache
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'profiler' && (
              <div className="space-y-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Performance Profiler</h3>
                
                {/* SQL Query Tool */}
                <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
                  <h4 className="font-medium text-gray-900 dark:text-white mb-4">SQL Query Tool</h4>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Query</label>
                      <textarea
                        value={sqlQuery}
                        onChange={(e) => setSqlQuery(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm focus:outline-none focus:shadow-focus"
                        rows={4}
                        placeholder="SELECT * FROM table_name LIMIT 10;"
                      />
                    </div>
                    
                    <button
                      onClick={executeSqlQuery}
                      className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
                    >
                      Execute Query
                    </button>

                    {sqlResult && (
                      <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                        <h5 className="font-medium text-gray-900 dark:text-white mb-2">Query Result</h5>
                        <pre className="text-sm bg-gray-900 text-green-400 p-3 rounded overflow-x-auto font-mono">
                          {JSON.stringify(sqlResult, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>

                {/* Memory Usage Visualization */}
                <div className="bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-xl p-12 text-center border border-purple-200 dark:border-purple-800">
                  <div className="text-4xl mb-4">📊</div>
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                    Advanced Profiling
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400">
                    Memory heap analysis, CPU profiling, and performance bottleneck detection
                  </p>
                  <button className="mt-4 px-6 py-3 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors">
                    Start Profiling Session
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
