import { useState, useEffect } from 'react'

interface User {
  id: string
  name: string
  email: string
  role: 'admin' | 'developer' | 'viewer' | 'operator'
  status: 'active' | 'inactive' | 'suspended'
  lastLogin: Date
  createdAt: Date
  permissions: string[]
  sessions: number
  avatar?: string
}

interface AuditLog {
  id: string
  timestamp: Date
  user: string
  action: string
  resource: string
  details: string
  ipAddress: string
  userAgent: string
  status: 'success' | 'failed' | 'warning'
}

interface SystemConfig {
  id: string
  category: string
  key: string
  value: any
  description: string
  type: 'string' | 'number' | 'boolean' | 'json'
  editable: boolean
  requiresRestart: boolean
}

interface ApiKey {
  id: string
  name: string
  key: string
  permissions: string[]
  rateLimit: number
  createdBy: string
  createdAt: Date
  lastUsed?: Date
  expiresAt?: Date
  status: 'active' | 'revoked' | 'expired'
  usage: {
    requests: number
    errors: number
    lastRequest?: Date
  }
}

interface DatabaseInfo {
  connectionStatus: 'connected' | 'disconnected' | 'error'
  version: string
  size: string
  tables: number
  lastBackup: Date
  uptime: string
  activeConnections: number
  performance: {
    queriesPerSecond: number
    avgResponseTime: number
    slowQueries: number
  }
}

const mockUsers: User[] = [
  {
    id: '1',
    name: 'John Admin',
    email: 'john@admin.com',
    role: 'admin',
    status: 'active',
    lastLogin: new Date(Date.now() - 3600000),
    createdAt: new Date(Date.now() - 86400000 * 30),
    permissions: ['all'],
    sessions: 2,
    avatar: undefined
  },
  {
    id: '2',
    name: 'Sarah Developer',
    email: 'sarah@dev.com',
    role: 'developer',
    status: 'active',
    lastLogin: new Date(Date.now() - 7200000),
    createdAt: new Date(Date.now() - 86400000 * 15),
    permissions: ['agents.read', 'agents.write', 'tasks.read', 'tasks.write'],
    sessions: 1
  },
  {
    id: '3',
    name: 'Mike Viewer',
    email: 'mike@viewer.com',
    role: 'viewer',
    status: 'active',
    lastLogin: new Date(Date.now() - 14400000),
    createdAt: new Date(Date.now() - 86400000 * 7),
    permissions: ['agents.read', 'tasks.read', 'metrics.read'],
    sessions: 0
  },
  {
    id: '4',
    name: 'Lisa Operator',
    email: 'lisa@ops.com',
    role: 'operator',
    status: 'suspended',
    lastLogin: new Date(Date.now() - 86400000 * 3),
    createdAt: new Date(Date.now() - 86400000 * 60),
    permissions: ['monitoring.read', 'alerts.write'],
    sessions: 0
  }
]

const mockAuditLogs: AuditLog[] = [
  {
    id: '1',
    timestamp: new Date(Date.now() - 300000),
    user: 'john@admin.com',
    action: 'CREATE_USER',
    resource: 'users/5',
    details: 'Created new user account for jane@dev.com',
    ipAddress: '192.168.1.100',
    userAgent: 'Mozilla/5.0 (Chrome)',
    status: 'success'
  },
  {
    id: '2',
    timestamp: new Date(Date.now() - 600000),
    user: 'sarah@dev.com',
    action: 'UPDATE_AGENT',
    resource: 'agents/dockermaster',
    details: 'Updated DockerMaster agent configuration',
    ipAddress: '192.168.1.101',
    userAgent: 'Mozilla/5.0 (Firefox)',
    status: 'success'
  },
  {
    id: '3',
    timestamp: new Date(Date.now() - 900000),
    user: 'system',
    action: 'BACKUP_DATABASE',
    resource: 'database',
    details: 'Automated database backup completed',
    ipAddress: '127.0.0.1',
    userAgent: 'System/Internal',
    status: 'success'
  },
  {
    id: '4',
    timestamp: new Date(Date.now() - 1200000),
    user: 'mike@viewer.com',
    action: 'LOGIN_FAILED',
    resource: 'auth',
    details: 'Failed login attempt with incorrect password',
    ipAddress: '192.168.1.200',
    userAgent: 'Mozilla/5.0 (Safari)',
    status: 'failed'
  }
]

const mockSystemConfig: SystemConfig[] = [
  {
    id: '1',
    category: 'General',
    key: 'app.name',
    value: 'ABrain',
    description: 'Application name displayed in UI',
    type: 'string',
    editable: true,
    requiresRestart: false
  },
  {
    id: '2',
    category: 'Security',
    key: 'auth.session_timeout',
    value: 3600,
    description: 'User session timeout in seconds',
    type: 'number',
    editable: true,
    requiresRestart: false
  },
  {
    id: '3',
    category: 'Performance',
    key: 'agents.max_concurrent',
    value: 10,
    description: 'Maximum concurrent agent tasks',
    type: 'number',
    editable: true,
    requiresRestart: true
  },
  {
    id: '4',
    category: 'Security',
    key: 'api.rate_limit_enabled',
    value: true,
    description: 'Enable API rate limiting',
    type: 'boolean',
    editable: true,
    requiresRestart: false
  },
  {
    id: '5',
    category: 'Monitoring',
    key: 'metrics.retention_days',
    value: 30,
    description: 'Days to retain metric data',
    type: 'number',
    editable: true,
    requiresRestart: false
  }
]

const mockApiKeys: ApiKey[] = [
  {
    id: '1',
    name: 'Production API',
    key: 'ak_prod_****_****_****_****',
    permissions: ['agents.*', 'tasks.*', 'metrics.read'],
    rateLimit: 1000,
    createdBy: 'john@admin.com',
    createdAt: new Date(Date.now() - 86400000 * 10),
    lastUsed: new Date(Date.now() - 3600000),
    status: 'active',
    usage: {
      requests: 15847,
      errors: 23,
      lastRequest: new Date(Date.now() - 3600000)
    }
  },
  {
    id: '2',
    name: 'Development API',
    key: 'ak_dev_****_****_****_****',
    permissions: ['agents.read', 'tasks.read'],
    rateLimit: 100,
    createdBy: 'sarah@dev.com',
    createdAt: new Date(Date.now() - 86400000 * 5),
    lastUsed: new Date(Date.now() - 7200000),
    status: 'active',
    usage: {
      requests: 2341,
      errors: 5,
      lastRequest: new Date(Date.now() - 7200000)
    }
  },
  {
    id: '3',
    name: 'Legacy Integration',
    key: 'ak_legacy_****_****_****_****',
    permissions: ['tasks.write'],
    rateLimit: 50,
    createdBy: 'john@admin.com',
    createdAt: new Date(Date.now() - 86400000 * 60),
    expiresAt: new Date(Date.now() - 86400000),
    status: 'expired',
    usage: {
      requests: 892,
      errors: 0
    }
  }
]

const mockDatabaseInfo: DatabaseInfo = {
  connectionStatus: 'connected',
  version: 'PostgreSQL 15.2',
  size: '2.3 GB',
  tables: 23,
  lastBackup: new Date(Date.now() - 86400000),
  uptime: '15 days, 8 hours',
  activeConnections: 12,
  performance: {
    queriesPerSecond: 145.7,
    avgResponseTime: 23.4,
    slowQueries: 3
  }
}

export default function AdminPage() {
  const [users, setUsers] = useState<User[]>(mockUsers)
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>(mockAuditLogs)
  const [systemConfig, setSystemConfig] = useState<SystemConfig[]>(mockSystemConfig)
  const [apiKeys, setApiKeys] = useState<ApiKey[]>(mockApiKeys)
  const [databaseInfo] = useState<DatabaseInfo>(mockDatabaseInfo)
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'config' | 'security' | 'logs' | 'database'>('overview')
  const [selectedUser, setSelectedUser] = useState<string | null>(null)
  const [showCreateUser, setShowCreateUser] = useState(false)
  const [showCreateApiKey, setShowCreateApiKey] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [logFilter, setLogFilter] = useState<'all' | 'success' | 'failed' | 'warning'>('all')

  const [newUser, setNewUser] = useState({
    name: '',
    email: '',
    role: 'viewer' as User['role'],
    permissions: [] as string[]
  })

  const [newApiKey, setNewApiKey] = useState({
    name: '',
    permissions: [] as string[]
  })

  const formatTimeAgo = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    
    if (minutes < 1) return 'Just now'
    if (minutes < 60) return `${minutes}m ago`
    if (minutes < 1440) return `${Math.floor(minutes / 60)}h ago`
    return `${Math.floor(minutes / 1440)}d ago`
  }

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin': return 'bg-red-100 text-red-800 border-red-200'
      case 'developer': return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'operator': return 'bg-green-100 text-green-800 border-green-200'
      case 'viewer': return 'bg-gray-100 text-gray-800 border-gray-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800 border-green-200'
      case 'inactive': return 'bg-gray-100 text-gray-800 border-gray-200'
      case 'suspended': return 'bg-red-100 text-red-800 border-red-200'
      case 'expired': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'revoked': return 'bg-red-100 text-red-800 border-red-200'
      case 'connected': return 'bg-green-100 text-green-800 border-green-200'
      case 'disconnected': return 'bg-red-100 text-red-800 border-red-200'
      case 'error': return 'bg-red-100 text-red-800 border-red-200'
      case 'success': return 'bg-green-100 text-green-800 border-green-200'
      case 'failed': return 'bg-red-100 text-red-800 border-red-200'
      case 'warning': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active': case 'connected': case 'success': return '✅'
      case 'inactive': case 'disconnected': return '⚪'
      case 'suspended': case 'revoked': case 'failed': case 'error': return '❌'
      case 'expired': case 'warning': return '⚠️'
      default: return '⚪'
    }
  }

  const updateUserStatus = (userId: string, status: User['status']) => {
    setUsers(prev => prev.map(user => 
      user.id === userId ? { ...user, status } : user
    ))
  }

  const createUser = () => {
    if (!newUser.name.trim() || !newUser.email.trim()) return

    const user: User = {
      id: Date.now().toString(),
      ...newUser,
      status: 'active',
      lastLogin: new Date(),
      createdAt: new Date(),
      sessions: 0
    }

    setUsers(prev => [user, ...prev])
    setNewUser({
      name: '',
      email: '',
      role: 'viewer',
      permissions: []
    })
    setShowCreateUser(false)
  }

  const createApiKey = () => {
    if (!newApiKey.name.trim()) return

    const apiKey: ApiKey = {
      id: Date.now().toString(),
      name: newApiKey.name,
      key: `ak_${Date.now()}_****_****_****_****`,
      permissions: newApiKey.permissions,
      rateLimit: 100,
      createdBy: 'current_user@admin.com',
      createdAt: new Date(),
      status: 'active',
      usage: {
        requests: 0,
        errors: 0
      }
    }

    setApiKeys(prev => [apiKey, ...prev])
    setNewApiKey({
      name: '',
      permissions: []
    })
    setShowCreateApiKey(false)
  }

  const revokeApiKey = (keyId: string) => {
    setApiKeys(prev => prev.map(key => 
      key.id === keyId ? { ...key, status: 'revoked' } : key
    ))
  }

  const updateConfig = (configId: string, newValue: any) => {
    setSystemConfig(prev => prev.map(config => 
      config.id === configId ? { ...config, value: newValue } : config
    ))
  }

  const filteredLogs = auditLogs.filter(log => {
    const matchesFilter = logFilter === 'all' || log.status === logFilter
    const matchesSearch = searchQuery === '' || 
      log.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.user.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.resource.toLowerCase().includes(searchQuery.toLowerCase())
    
    return matchesFilter && matchesSearch
  })

  const systemStats = {
    totalUsers: users.length,
    activeUsers: users.filter(u => u.status === 'active').length,
    totalApiKeys: apiKeys.length,
    activeApiKeys: apiKeys.filter(k => k.status === 'active').length,
    totalRequests: apiKeys.reduce((acc, key) => acc + key.usage.requests, 0),
    errorRate: (apiKeys.reduce((acc, key) => acc + key.usage.errors, 0) / Math.max(1, apiKeys.reduce((acc, key) => acc + key.usage.requests, 0)) * 100)
  }

  return (
    <div className="p-6 bg-gray-50 dark:bg-gray-900 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              System Administration
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Manage users, system configuration, and monitor system health
            </p>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 px-3 py-2 bg-green-100 dark:bg-green-900 rounded-lg">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-green-700 dark:text-green-300 font-medium text-sm">System Healthy</span>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
                <span className="text-blue-600 dark:text-blue-400">👥</span>
              </div>
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Users</span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{systemStats.totalUsers}</p>
            <p className="text-sm text-green-600 dark:text-green-400 mt-1">
              {systemStats.activeUsers} active
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center">
                <span className="text-purple-600 dark:text-purple-400">🔑</span>
              </div>
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">API Keys</span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{systemStats.totalApiKeys}</p>
            <p className="text-sm text-green-600 dark:text-green-400 mt-1">
              {systemStats.activeApiKeys} active
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center">
                <span className="text-green-600 dark:text-green-400">📡</span>
              </div>
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">API Requests</span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {systemStats.totalRequests.toLocaleString()}
            </p>
            <p className="text-sm text-blue-600 dark:text-blue-400 mt-1">
              Last 30 days
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-8 h-8 bg-red-100 dark:bg-red-900 rounded-lg flex items-center justify-center">
                <span className="text-red-600 dark:text-red-400">⚠️</span>
              </div>
              <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Error Rate</span>
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {systemStats.errorRate.toFixed(2)}%
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              API errors
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 mb-6">
          <div className="border-b border-gray-200 dark:border-gray-700">
            <nav className="flex space-x-8 px-6 overflow-x-auto">
              {[
                { id: 'overview', label: 'Overview', icon: '🏠' },
                { id: 'users', label: 'User Management', icon: '👥' },
                { id: 'config', label: 'Configuration', icon: '⚙️' },
                { id: 'security', label: 'Security & API', icon: '🔒' },
                { id: 'logs', label: 'Audit Logs', icon: '📋' },
                { id: 'database', label: 'Database', icon: '🗄️' }
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
            {activeTab === 'overview' && (
              <div className="space-y-6">
                {/* System Health */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl p-6 border border-green-200 dark:border-green-800">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 bg-green-100 dark:bg-green-900 rounded-xl flex items-center justify-center">
                        <span className="text-green-600 dark:text-green-400 text-lg">💚</span>
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">System Health</h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">All systems operational</p>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Uptime:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-white">99.9%</span>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Memory:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-white">67%</span>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">CPU:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-white">42%</span>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Disk:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-white">23%</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-xl p-6 border border-blue-200 dark:border-blue-800">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-xl flex items-center justify-center">
                        <span className="text-blue-600 dark:text-blue-400 text-lg">📊</span>
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Activity</h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Last 24 hours</p>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Logins:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-white">127</span>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">API Calls:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-white">2,847</span>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Tasks:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-white">156</span>
                      </div>
                      <div>
                        <span className="text-gray-600 dark:text-gray-400">Errors:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-white">3</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Quick Actions */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <button 
                    onClick={() => setActiveTab('users')}
                    className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:shadow-md transition-all text-left"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">👥</span>
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-white">Manage Users</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Add, edit, or deactivate users</p>
                      </div>
                    </div>
                  </button>

                  <button 
                    onClick={() => setActiveTab('security')}
                    className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:shadow-md transition-all text-left"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">🔒</span>
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-white">Security Settings</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Configure API keys and permissions</p>
                      </div>
                    </div>
                  </button>

                  <button 
                    onClick={() => setActiveTab('database')}
                    className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:shadow-md transition-all text-left"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">🗄️</span>
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-white">Database</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Backup, restore, and maintenance</p>
                      </div>
                    </div>
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'users' && (
              <div>
                {/* User Management Header */}
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">User Management</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Manage user accounts and permissions</p>
                  </div>
                  <button
                    onClick={() => setShowCreateUser(true)}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center space-x-2"
                  >
                    <span>➕</span>
                    <span>Add User</span>
                  </button>
                </div>

                {/* Users Table */}
                <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                        <tr>
                          <th className="text-left p-4 font-medium text-gray-900 dark:text-white">User</th>
                          <th className="text-left p-4 font-medium text-gray-900 dark:text-white">Role</th>
                          <th className="text-left p-4 font-medium text-gray-900 dark:text-white">Status</th>
                          <th className="text-left p-4 font-medium text-gray-900 dark:text-white">Last Login</th>
                          <th className="text-left p-4 font-medium text-gray-900 dark:text-white">Sessions</th>
                          <th className="text-left p-4 font-medium text-gray-900 dark:text-white">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {users.map((user) => (
                          <tr key={user.id} className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                            <td className="p-4">
                              <div className="flex items-center space-x-3">
                                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center">
                                  <span className="text-white font-bold text-sm">
                                    {user.name.charAt(0).toUpperCase()}
                                  </span>
                                </div>
                                <div>
                                  <div className="font-medium text-gray-900 dark:text-white">{user.name}</div>
                                  <div className="text-sm text-gray-600 dark:text-gray-400">{user.email}</div>
                                </div>
                              </div>
                            </td>
                            <td className="p-4">
                              <span className={`px-2 py-1 text-xs rounded-full border font-medium ${getRoleColor(user.role)}`}>
                                {user.role}
                              </span>
                            </td>
                            <td className="p-4">
                              <span className={`px-2 py-1 text-xs rounded-full border font-medium ${getStatusColor(user.status)}`}>
                                {getStatusIcon(user.status)} {user.status}
                              </span>
                            </td>
                            <td className="p-4 text-sm text-gray-600 dark:text-gray-400">
                              {formatTimeAgo(user.lastLogin)}
                            </td>
                            <td className="p-4 text-sm text-gray-900 dark:text-white">
                              {user.sessions}
                            </td>
                            <td className="p-4">
                              <div className="flex space-x-2">
                                <button className="p-1 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors">
                                  <span className="text-sm">✏️</span>
                                </button>
                                {user.status === 'active' ? (
                                  <button 
                                    onClick={() => updateUserStatus(user.id, 'suspended')}
                                    className="p-1 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                                  >
                                    <span className="text-sm">🚫</span>
                                  </button>
                                ) : (
                                  <button 
                                    onClick={() => updateUserStatus(user.id, 'active')}
                                    className="p-1 text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20 rounded transition-colors"
                                  >
                                    <span className="text-sm">✅</span>
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Create User Modal */}
                {showCreateUser && (
                  <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
                    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 w-full max-w-md">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Create New User</h3>
                        <button 
                          onClick={() => setShowCreateUser(false)}
                          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                        >
                          <span className="text-xl">×</span>
                        </button>
                      </div>
                      
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Name</label>
                          <input
                            type="text"
                            value={newUser.name}
                            onChange={(e) => setNewUser(prev => ({ ...prev, name: e.target.value }))}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:shadow-focus"
                            placeholder="Enter user name"
                          />
                        </div>
                        
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Email</label>
                          <input
                            type="email"
                            value={newUser.email}
                            onChange={(e) => setNewUser(prev => ({ ...prev, email: e.target.value }))}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:shadow-focus"
                            placeholder="Enter email address"
                          />
                        </div>
                        
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Role</label>
                          <select
                            value={newUser.role}
                            onChange={(e) => setNewUser(prev => ({ ...prev, role: e.target.value as User['role'] }))}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:shadow-focus"
                          >
                            <option value="viewer">Viewer</option>
                            <option value="operator">Operator</option>
                            <option value="developer">Developer</option>
                            <option value="admin">Admin</option>
                          </select>
                        </div>
                        
                        <div className="flex space-x-3 pt-4">
                          <button
                            onClick={() => setShowCreateUser(false)}
                            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={createUser}
                            className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                          >
                            Create User
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'config' && (
              <div>
                <div className="mb-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">System Configuration</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Manage system-wide settings and parameters</p>
                </div>

                <div className="space-y-6">
                  {Object.entries(
                    systemConfig.reduce((acc, config) => {
                      if (!acc[config.category]) acc[config.category] = []
                      acc[config.category].push(config)
                      return acc
                    }, {} as Record<string, SystemConfig[]>)
                  ).map(([category, configs]) => (
                    <div key={category} className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
                      <h4 className="font-semibold text-gray-900 dark:text-white mb-4">{category}</h4>
                      <div className="space-y-4">
                        {configs.map((config) => (
                          <div key={config.id} className="flex items-center justify-between py-3 border-b border-gray-100 dark:border-gray-700 last:border-b-0">
                            <div className="flex-1">
                              <div className="flex items-center space-x-2">
                                <span className="font-medium text-gray-900 dark:text-white">{config.key}</span>
                                {config.requiresRestart && (
                                  <span className="px-2 py-1 text-xs bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-300 rounded">
                                    Restart Required
                                  </span>
                                )}
                              </div>
                              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{config.description}</p>
                            </div>
                            <div className="ml-4">
                              {config.editable ? (
                                config.type === 'boolean' ? (
                                  <button
                                    onClick={() => updateConfig(config.id, !config.value)}
                                    className={`w-11 h-6 rounded-full relative transition-colors ${
                                      config.value ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-600'
                                    }`}
                                  >
                                    <span
                                      className={`absolute w-5 h-5 bg-white rounded-full shadow transform transition-transform top-0.5 ${
                                        config.value ? 'translate-x-5' : 'translate-x-0.5'
                                      }`}
                                    />
                                  </button>
                                ) : (
                                  <input
                                    type={config.type === 'number' ? 'number' : 'text'}
                                    value={config.value}
                                    onChange={(e) => updateConfig(config.id, config.type === 'number' ? Number(e.target.value) : e.target.value)}
                                    className="w-32 px-3 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:shadow-focus"
                                  />
                                )
                              ) : (
                                <span className="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white rounded text-sm">
                                  {config.value.toString()}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'security' && (
              <div>
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Security & API Management</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Manage API keys and access permissions</p>
                  </div>
                  <button
                    onClick={() => setShowCreateApiKey(true)}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center space-x-2"
                  >
                    <span>🔑</span>
                    <span>Create API Key</span>
                  </button>
                </div>

                {/* API Keys Table */}
                <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                        <tr>
                          <th className="text-left p-4 font-medium text-gray-900 dark:text-white">Name</th>
                          <th className="text-left p-4 font-medium text-gray-900 dark:text-white">Key</th>
                          <th className="text-left p-4 font-medium text-gray-900 dark:text-white">Status</th>
                          <th className="text-left p-4 font-medium text-gray-900 dark:text-white">Usage</th>
                          <th className="text-left p-4 font-medium text-gray-900 dark:text-white">Last Used</th>
                          <th className="text-left p-4 font-medium text-gray-900 dark:text-white">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {apiKeys.map((apiKey) => (
                          <tr key={apiKey.id} className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                            <td className="p-4">
                              <div>
                                <div className="font-medium text-gray-900 dark:text-white">{apiKey.name}</div>
                                <div className="text-sm text-gray-600 dark:text-gray-400">
                                  Created by {apiKey.createdBy}
                                </div>
                              </div>
                            </td>
                            <td className="p-4">
                              <code className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white rounded text-sm font-mono">
                                {apiKey.key}
                              </code>
                            </td>
                            <td className="p-4">
                              <span className={`px-2 py-1 text-xs rounded-full border font-medium ${getStatusColor(apiKey.status)}`}>
                                {getStatusIcon(apiKey.status)} {apiKey.status}
                              </span>
                            </td>
                            <td className="p-4">
                              <div className="text-sm">
                                <div className="text-gray-900 dark:text-white">{apiKey.usage.requests.toLocaleString()} requests</div>
                                <div className="text-gray-600 dark:text-gray-400">{apiKey.usage.errors} errors</div>
                              </div>
                            </td>
                            <td className="p-4 text-sm text-gray-600 dark:text-gray-400">
                              {apiKey.lastUsed ? formatTimeAgo(apiKey.lastUsed) : 'Never'}
                            </td>
                            <td className="p-4">
                              <div className="flex space-x-2">
                                <button className="p-1 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors">
                                  <span className="text-sm">✏️</span>
                                </button>
                                {apiKey.status === 'active' && (
                                  <button 
                                    onClick={() => revokeApiKey(apiKey.id)}
                                    className="p-1 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                                  >
                                    <span className="text-sm">🗑️</span>
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Create API Key Modal */}
                {showCreateApiKey && (
                  <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
                    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 w-full max-w-md">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Create API Key</h3>
                        <button 
                          onClick={() => setShowCreateApiKey(false)}
                          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                        >
                          <span className="text-xl">×</span>
                        </button>
                      </div>
                      
                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Name</label>
                          <input
                            type="text"
                            value={newApiKey.name}
                            onChange={(e) => setNewApiKey(prev => ({ ...prev, name: e.target.value }))}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:shadow-focus"
                            placeholder="e.g., Production API"
                          />
                        </div>
                        
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Permissions</label>
                          <div className="space-y-2 max-h-32 overflow-y-auto">
                            {['agents.read', 'agents.write', 'tasks.read', 'tasks.write', 'metrics.read'].map(permission => (
                              <label key={permission} className="flex items-center">
                                <input
                                  type="checkbox"
                                  checked={newApiKey.permissions.includes(permission)}
                                  onChange={(e) => {
                                    if (e.target.checked) {
                                      setNewApiKey(prev => ({ ...prev, permissions: [...prev.permissions, permission] }))
                                    } else {
                                      setNewApiKey(prev => ({ ...prev, permissions: prev.permissions.filter(p => p !== permission) }))
                                    }
                                  }}
                                  className="mr-2"
                                />
                                <span className="text-sm text-gray-700 dark:text-gray-300">{permission}</span>
                              </label>
                            ))}
                          </div>
                        </div>
                        
                        <div className="flex space-x-3 pt-4">
                          <button
                            onClick={() => setShowCreateApiKey(false)}
                            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={createApiKey}
                            className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                          >
                            Create Key
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'logs' && (
              <div>
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Audit Logs</h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">System activity and security events</p>
                  </div>
                  <div className="flex space-x-4">
                    <input
                      type="text"
                      placeholder="Search logs..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:shadow-focus"
                    />
                    <select
                      value={logFilter}
                      onChange={(e) => setLogFilter(e.target.value as any)}
                      className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:shadow-focus"
                    >
                      <option value="all">All Events</option>
                      <option value="success">Success</option>
                      <option value="failed">Failed</option>
                      <option value="warning">Warning</option>
                    </select>
                  </div>
                </div>

                {/* Logs Table */}
                <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                        <tr>
                          <th className="text-left p-4 font-medium text-gray-900 dark:text-white">Timestamp</th>
                          <th className="text-left p-4 font-medium text-gray-900 dark:text-white">User</th>
                          <th className="text-left p-4 font-medium text-gray-900 dark:text-white">Action</th>
                          <th className="text-left p-4 font-medium text-gray-900 dark:text-white">Resource</th>
                          <th className="text-left p-4 font-medium text-gray-900 dark:text-white">Status</th>
                          <th className="text-left p-4 font-medium text-gray-900 dark:text-white">IP Address</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredLogs.map((log) => (
                          <tr key={log.id} className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                            <td className="p-4 text-sm text-gray-600 dark:text-gray-400">
                              {log.timestamp.toLocaleString()}
                            </td>
                            <td className="p-4 text-sm text-gray-900 dark:text-white">
                              {log.user}
                            </td>
                            <td className="p-4">
                              <div>
                                <div className="font-medium text-gray-900 dark:text-white text-sm">
                                  {log.action.replace('_', ' ')}
                                </div>
                                <div className="text-xs text-gray-600 dark:text-gray-400">
                                  {log.details}
                                </div>
                              </div>
                            </td>
                            <td className="p-4 text-sm text-gray-900 dark:text-white">
                              {log.resource}
                            </td>
                            <td className="p-4">
                              <span className={`px-2 py-1 text-xs rounded-full border font-medium ${getStatusColor(log.status)}`}>
                                {getStatusIcon(log.status)} {log.status}
                              </span>
                            </td>
                            <td className="p-4 text-sm text-gray-600 dark:text-gray-400">
                              {log.ipAddress}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'database' && (
              <div>
                <div className="mb-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Database Management</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Monitor database health and perform maintenance</p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                  {/* Database Status */}
                  <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
                    <div className="flex items-center gap-3 mb-4">
                      <span className={`px-2 py-1 text-xs rounded-full border font-medium ${getStatusColor(databaseInfo.connectionStatus)}`}>
                        {getStatusIcon(databaseInfo.connectionStatus)} {databaseInfo.connectionStatus}
                      </span>
                      <h4 className="font-semibold text-gray-900 dark:text-white">Database Status</h4>
                    </div>
                    <div className="space-y-3 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Version:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{databaseInfo.version}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Size:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{databaseInfo.size}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Tables:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{databaseInfo.tables}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Uptime:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{databaseInfo.uptime}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Connections:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{databaseInfo.activeConnections}</span>
                      </div>
                    </div>
                  </div>

                  {/* Performance Metrics */}
                  <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
                    <h4 className="font-semibold text-gray-900 dark:text-white mb-4">Performance Metrics</h4>
                    <div className="space-y-3 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Queries/sec:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{databaseInfo.performance.queriesPerSecond}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Avg Response:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{databaseInfo.performance.avgResponseTime}ms</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Slow Queries:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{databaseInfo.performance.slowQueries}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">Last Backup:</span>
                        <span className="font-medium text-gray-900 dark:text-white">{formatTimeAgo(databaseInfo.lastBackup)}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Database Actions */}
                <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
                  <h4 className="font-semibold text-gray-900 dark:text-white mb-4">Database Operations</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <button className="p-4 border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors">
                      <div className="text-center">
                        <span className="text-2xl mb-2 block">💾</span>
                        <h5 className="font-medium text-gray-900 dark:text-white">Create Backup</h5>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Create manual database backup</p>
                      </div>
                    </button>

                    <button className="p-4 border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/30 transition-colors">
                      <div className="text-center">
                        <span className="text-2xl mb-2 block">🔄</span>
                        <h5 className="font-medium text-gray-900 dark:text-white">Restore</h5>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Restore from backup file</p>
                      </div>
                    </button>

                    <button className="p-4 border border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-900/20 rounded-lg hover:bg-purple-100 dark:hover:bg-purple-900/30 transition-colors">
                      <div className="text-center">
                        <span className="text-2xl mb-2 block">🧹</span>
                        <h5 className="font-medium text-gray-900 dark:text-white">Optimize</h5>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Run database optimization</p>
                      </div>
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
