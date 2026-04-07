import { useState, useEffect } from 'react'

interface SystemMetrics {
  timestamp: Date
  cpu: {
    usage: number
    cores: number
    temperature?: number
    processes: number
  }
  memory: {
    used: number
    total: number
    cached: number
    buffers: number
  }
  disk: {
    used: number
    total: number
    readSpeed: number
    writeSpeed: number
  }
  network: {
    inbound: number
    outbound: number
    connections: number
    latency: number
  }
}

interface Alert {
  id: string
  type: 'critical' | 'warning' | 'info'
  title: string
  message: string
  timestamp: Date
  source: string
  acknowledged: boolean
  resolved: boolean
}

interface ServiceStatus {
  id: string
  name: string
  status: 'healthy' | 'warning' | 'critical' | 'unknown'
  uptime: number
  responseTime: number
  lastCheck: Date
  endpoint: string
  version?: string
  description: string
}

const mockMetrics: SystemMetrics[] = Array.from({ length: 50 }, (_, i) => ({
  timestamp: new Date(Date.now() - (49 - i) * 60000),
  cpu: {
    usage: Math.random() * 60 + 20 + Math.sin(i * 0.1) * 15,
    cores: 8,
    temperature: Math.random() * 20 + 45,
    processes: Math.floor(Math.random() * 50 + 150)
  },
  memory: {
    used: Math.random() * 4 + 4,
    total: 16,
    cached: Math.random() * 2 + 1,
    buffers: Math.random() * 0.5 + 0.2
  },
  disk: {
    used: 45.7,
    total: 100,
    readSpeed: Math.random() * 100 + 50,
    writeSpeed: Math.random() * 80 + 30
  },
  network: {
    inbound: Math.random() * 500 + 100,
    outbound: Math.random() * 300 + 50,
    connections: Math.floor(Math.random() * 100 + 50),
    latency: Math.random() * 10 + 5
  }
}))

const mockAlerts: Alert[] = [
  {
    id: '1',
    type: 'critical',
    title: 'High CPU Usage',
    message: 'CPU usage has exceeded 90% for more than 5 minutes',
    timestamp: new Date(Date.now() - 300000),
    source: 'System Monitor',
    acknowledged: false,
    resolved: false
  },
  {
    id: '2',
    type: 'warning',
    title: 'Memory Usage High',
    message: 'Memory usage is at 85% - consider investigating running processes',
    timestamp: new Date(Date.now() - 600000),
    source: 'Memory Monitor',
    acknowledged: true,
    resolved: false
  },
  {
    id: '3',
    type: 'info',
    title: 'DockerMaster Agent Restarted',
    message: 'DockerMaster agent has been automatically restarted due to memory leak',
    timestamp: new Date(Date.now() - 900000),
    source: 'Agent Monitor',
    acknowledged: true,
    resolved: true
  },
  {
    id: '4',
    type: 'warning',
    title: 'Disk Space Warning',
    message: 'Available disk space is below 20GB',
    timestamp: new Date(Date.now() - 1200000),
    source: 'Disk Monitor',
    acknowledged: false,
    resolved: false
  }
]

const mockServices: ServiceStatus[] = [
  {
    id: '1',
    name: 'ABrain API',
    status: 'healthy',
    uptime: 99.8,
    responseTime: 145,
    lastCheck: new Date(Date.now() - 30000),
    endpoint: '/api/health',
    version: 'v2.1.0',
    description: 'Main API service for agent management'
  },
  {
    id: '2',
    name: 'Database',
    status: 'healthy',
    uptime: 99.9,
    responseTime: 23,
    lastCheck: new Date(Date.now() - 45000),
    endpoint: 'postgresql://localhost:5432',
    version: '15.2',
    description: 'Primary PostgreSQL database'
  },
  {
    id: '3',
    name: 'Redis Cache',
    status: 'warning',
    uptime: 98.5,
    responseTime: 8,
    lastCheck: new Date(Date.now() - 15000),
    endpoint: 'redis://localhost:6379',
    version: '7.0',
    description: 'Redis cache for session and data caching'
  },
  {
    id: '4',
    name: 'Message Queue',
    status: 'healthy',
    uptime: 99.2,
    responseTime: 67,
    lastCheck: new Date(Date.now() - 60000),
    endpoint: 'rabbitmq://localhost:5672',
    version: '3.11',
    description: 'RabbitMQ message broker for task queuing'
  },
  {
    id: '5',
    name: 'DockerMaster Agent',
    status: 'critical',
    uptime: 95.3,
    responseTime: 2340,
    lastCheck: new Date(Date.now() - 120000),
    endpoint: '/agents/dockermaster/health',
    version: 'v2.1.0',
    description: 'Docker container management agent'
  }
]

export default function ModernMonitoringPage() {
  const [metrics, setMetrics] = useState<SystemMetrics[]>(mockMetrics)
  const [alerts, setAlerts] = useState<Alert[]>(mockAlerts)
  const [services, setServices] = useState<ServiceStatus[]>(mockServices)
  const [selectedTimeRange, setSelectedTimeRange] = useState<'1h' | '6h' | '24h' | '7d'>('1h')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [refreshInterval, setRefreshInterval] = useState(30) // seconds
  const [alertsFilter, setAlertsFilter] = useState<'all' | 'unacknowledged' | 'critical'>('unacknowledged')

  // Real-time updates simulation
  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      // Add new metric point
      setMetrics(prev => {
        const newMetric: SystemMetrics = {
          timestamp: new Date(),
          cpu: {
            usage: Math.random() * 60 + 20 + Math.sin(Date.now() * 0.0001) * 15,
            cores: 8,
            temperature: Math.random() * 20 + 45,
            processes: Math.floor(Math.random() * 50 + 150)
          },
          memory: {
            used: Math.random() * 4 + 4,
            total: 16,
            cached: Math.random() * 2 + 1,
            buffers: Math.random() * 0.5 + 0.2
          },
          disk: {
            used: 45.7,
            total: 100,
            readSpeed: Math.random() * 100 + 50,
            writeSpeed: Math.random() * 80 + 30
          },
          network: {
            inbound: Math.random() * 500 + 100,
            outbound: Math.random() * 300 + 50,
            connections: Math.floor(Math.random() * 100 + 50),
            latency: Math.random() * 10 + 5
          }
        }
        return [...prev.slice(-49), newMetric]
      })

      // Update service status occasionally
      if (Math.random() < 0.1) {
        setServices(prev => prev.map(service => ({
          ...service,
          responseTime: Math.max(10, service.responseTime + (Math.random() - 0.5) * 100),
          lastCheck: new Date()
        })))
      }
    }, refreshInterval * 1000)

    return () => clearInterval(interval)
  }, [autoRefresh, refreshInterval])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-100 text-green-800 border-green-200'
      case 'warning': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'critical': return 'bg-red-100 text-red-800 border-red-200'
      case 'unknown': return 'bg-gray-100 text-gray-800 border-gray-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getAlertColor = (type: string) => {
    switch (type) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200'
      case 'warning': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'info': return 'bg-blue-100 text-blue-800 border-blue-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return '✅'
      case 'warning': return '⚠️'
      case 'critical': return '❌'
      case 'unknown': return '❓'
      default: return '⚪'
    }
  }

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'critical': return '🚨'
      case 'warning': return '⚠️'
      case 'info': return 'ℹ️'
      default: return '📄'
    }
  }

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
  }

  const formatUptime = (uptime: number) => {
    return `${uptime.toFixed(1)}%`
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

  const acknowledgeAlert = (id: string) => {
    setAlerts(prev => prev.map(alert => 
      alert.id === id ? { ...alert, acknowledged: true } : alert
    ))
  }

  const resolveAlert = (id: string) => {
    setAlerts(prev => prev.map(alert => 
      alert.id === id ? { ...alert, resolved: true } : alert
    ))
  }

  const filteredAlerts = alerts.filter(alert => {
    switch (alertsFilter) {
      case 'unacknowledged':
        return !alert.acknowledged && !alert.resolved
      case 'critical':
        return alert.type === 'critical' && !alert.resolved
      default:
        return !alert.resolved
    }
  })

  const currentMetrics = metrics[metrics.length - 1]
  const cpuUsage = currentMetrics?.cpu.usage || 0
  const memoryUsage = currentMetrics ? (currentMetrics.memory.used / currentMetrics.memory.total) * 100 : 0
  const diskUsage = currentMetrics ? (currentMetrics.disk.used / currentMetrics.disk.total) * 100 : 0

  const SimpleChart = ({ data, color, unit = '%', height = 60 }: {
    data: number[]
    color: string
    unit?: string
    height?: number
  }) => {
    const max = Math.max(...data)
    const min = Math.min(...data)
    const range = max - min || 1

    return (
      <div className="relative" style={{ height }}>
        <svg width="100%" height="100%" className="absolute inset-0">
          <polyline
            fill="none"
            stroke={color}
            strokeWidth="2"
            points={data
              .map((value, index) => {
                const x = (index / (data.length - 1)) * 100
                const y = 100 - ((value - min) / range) * 100
                return `${x},${y}`
              })
              .join(' ')}
          />
        </svg>
        <div className="absolute top-0 right-0 text-xs text-gray-500 dark:text-gray-400">
          {data[data.length - 1]?.toFixed(1)}{unit}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 bg-gray-50 dark:bg-gray-900 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              System Monitoring
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Real-time system health and performance monitoring
            </p>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <label className="text-sm text-gray-600 dark:text-gray-400">Auto-refresh:</label>
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`w-11 h-6 rounded-full relative transition-colors ${
                  autoRefresh ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-600'
                }`}
              >
                <span
                  className={`absolute w-5 h-5 bg-white rounded-full shadow transform transition-transform top-0.5 ${
                    autoRefresh ? 'translate-x-5' : 'translate-x-0.5'
                  }`}
                />
              </button>
            </div>
            
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Number(e.target.value))}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm focus:outline-none focus:shadow-focus"
            >
              <option value={10}>10s</option>
              <option value={30}>30s</option>
              <option value={60}>1m</option>
              <option value={300}>5m</option>
            </select>
          </div>
        </div>

        {/* System Overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
                  <span className="text-blue-600 dark:text-blue-400">⚡</span>
                </div>
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400">CPU Usage</span>
              </div>
              <span className={`text-sm font-medium px-2 py-1 rounded ${
                cpuUsage > 80 ? 'bg-red-100 text-red-800' : 
                cpuUsage > 60 ? 'bg-yellow-100 text-yellow-800' : 
                'bg-green-100 text-green-800'
              }`}>
                {cpuUsage.toFixed(1)}%
              </span>
            </div>
            <SimpleChart 
              data={metrics.slice(-20).map(m => m.cpu.usage)} 
              color="#3b82f6" 
            />
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center">
                  <span className="text-green-600 dark:text-green-400">💾</span>
                </div>
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Memory</span>
              </div>
              <span className={`text-sm font-medium px-2 py-1 rounded ${
                memoryUsage > 85 ? 'bg-red-100 text-red-800' : 
                memoryUsage > 70 ? 'bg-yellow-100 text-yellow-800' : 
                'bg-green-100 text-green-800'
              }`}>
                {memoryUsage.toFixed(1)}%
              </span>
            </div>
            <SimpleChart 
              data={metrics.slice(-20).map(m => (m.memory.used / m.memory.total) * 100)} 
              color="#10b981" 
            />
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center">
                  <span className="text-purple-600 dark:text-purple-400">💿</span>
                </div>
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Disk Usage</span>
              </div>
              <span className={`text-sm font-medium px-2 py-1 rounded ${
                diskUsage > 85 ? 'bg-red-100 text-red-800' : 
                diskUsage > 70 ? 'bg-yellow-100 text-yellow-800' : 
                'bg-green-100 text-green-800'
              }`}>
                {diskUsage.toFixed(1)}%
              </span>
            </div>
            <SimpleChart 
              data={Array(20).fill(diskUsage)} 
              color="#8b5cf6" 
            />
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-orange-100 dark:bg-orange-900 rounded-lg flex items-center justify-center">
                  <span className="text-orange-600 dark:text-orange-400">🌐</span>
                </div>
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Network</span>
              </div>
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                {currentMetrics?.network.latency.toFixed(1)}ms
              </span>
            </div>
            <SimpleChart 
              data={metrics.slice(-20).map(m => m.network.inbound)} 
              color="#f59e0b" 
              unit=" MB/s"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Alerts */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Recent Alerts
              </h3>
              <select
                value={alertsFilter}
                onChange={(e) => setAlertsFilter(e.target.value as any)}
                className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:shadow-focus"
              >
                <option value="all">All Alerts</option>
                <option value="unacknowledged">Unacknowledged</option>
                <option value="critical">Critical Only</option>
              </select>
            </div>
            
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {filteredAlerts.length === 0 ? (
                <div className="text-center py-8">
                  <div className="w-12 h-12 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center mx-auto mb-3">
                    <span className="text-green-600 dark:text-green-400">✅</span>
                  </div>
                  <p className="text-gray-500 dark:text-gray-400">No alerts to show</p>
                </div>
              ) : (
                filteredAlerts.map((alert) => (
                  <div key={alert.id} className={`p-4 rounded-lg border ${
                    alert.acknowledged ? 'opacity-60' : ''
                  } ${getAlertColor(alert.type).replace('text-', 'border-').replace('bg-', 'bg-opacity-50 bg-')}`}>
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-3">
                        <span className="text-lg">{getAlertIcon(alert.type)}</span>
                        <div className="flex-1">
                          <h4 className="font-medium text-gray-900 dark:text-white">
                            {alert.title}
                          </h4>
                          <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                            {alert.message}
                          </p>
                          <div className="flex items-center space-x-2 mt-2 text-xs text-gray-500 dark:text-gray-400">
                            <span>{alert.source}</span>
                            <span>•</span>
                            <span>{formatTimeAgo(alert.timestamp)}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex space-x-2">
                        {!alert.acknowledged && (
                          <button
                            onClick={() => acknowledgeAlert(alert.id)}
                            className="px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
                          >
                            Ack
                          </button>
                        )}
                        {!alert.resolved && (
                          <button
                            onClick={() => resolveAlert(alert.id)}
                            className="px-2 py-1 text-xs bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded hover:bg-green-200 dark:hover:bg-green-800 transition-colors"
                          >
                            Resolve
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Service Status */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Service Status
              </h3>
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm text-gray-500 dark:text-gray-400">Live</span>
              </div>
            </div>
            
            <div className="space-y-4">
              {services.map((service) => (
                <div key={service.id} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <span className="text-lg">{getStatusIcon(service.status)}</span>
                    <div>
                      <h4 className="font-medium text-gray-900 dark:text-white">
                        {service.name}
                      </h4>
                      <p className="text-sm text-gray-600 dark:text-gray-300">
                        {service.description}
                      </p>
                      <div className="flex items-center space-x-4 mt-1 text-xs text-gray-500 dark:text-gray-400">
                        <span>Uptime: {formatUptime(service.uptime)}</span>
                        <span>•</span>
                        <span>Response: {service.responseTime}ms</span>
                        <span>•</span>
                        <span>Last check: {formatTimeAgo(service.lastCheck)}</span>
                      </div>
                    </div>
                  </div>
                  <span className={`px-3 py-1 text-xs rounded-full border font-medium ${getStatusColor(service.status)}`}>
                    {service.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Detailed Metrics */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Detailed System Metrics
            </h3>
            <select
              value={selectedTimeRange}
              onChange={(e) => setSelectedTimeRange(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:shadow-focus"
            >
              <option value="1h">Last Hour</option>
              <option value="6h">Last 6 Hours</option>
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
            </select>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {currentMetrics && (
              <>
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white mb-3">CPU Information</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Cores:</span>
                      <span className="font-medium">{currentMetrics.cpu.cores}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Usage:</span>
                      <span className="font-medium">{currentMetrics.cpu.usage.toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Temperature:</span>
                      <span className="font-medium">{currentMetrics.cpu.temperature?.toFixed(1)}°C</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Processes:</span>
                      <span className="font-medium">{currentMetrics.cpu.processes}</span>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white mb-3">Memory Information</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Used:</span>
                      <span className="font-medium">{formatBytes(currentMetrics.memory.used * 1024 * 1024 * 1024)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Total:</span>
                      <span className="font-medium">{formatBytes(currentMetrics.memory.total * 1024 * 1024 * 1024)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Cached:</span>
                      <span className="font-medium">{formatBytes(currentMetrics.memory.cached * 1024 * 1024 * 1024)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Buffers:</span>
                      <span className="font-medium">{formatBytes(currentMetrics.memory.buffers * 1024 * 1024 * 1024)}</span>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white mb-3">Disk Information</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Used:</span>
                      <span className="font-medium">{currentMetrics.disk.used.toFixed(1)} GB</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Total:</span>
                      <span className="font-medium">{currentMetrics.disk.total.toFixed(1)} GB</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Read Speed:</span>
                      <span className="font-medium">{currentMetrics.disk.readSpeed.toFixed(1)} MB/s</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Write Speed:</span>
                      <span className="font-medium">{currentMetrics.disk.writeSpeed.toFixed(1)} MB/s</span>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white mb-3">Network Information</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Inbound:</span>
                      <span className="font-medium">{currentMetrics.network.inbound.toFixed(1)} MB/s</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Outbound:</span>
                      <span className="font-medium">{currentMetrics.network.outbound.toFixed(1)} MB/s</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Connections:</span>
                      <span className="font-medium">{currentMetrics.network.connections}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600 dark:text-gray-400">Latency:</span>
                      <span className="font-medium">{currentMetrics.network.latency.toFixed(1)} ms</span>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
