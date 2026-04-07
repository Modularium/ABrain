import { useState, useEffect } from 'react'

interface Settings {
  general: {
    theme: 'light' | 'dark' | 'auto'
    language: string
    timezone: string
    notifications: boolean
    autoSave: boolean
  }
  api: {
    openaiKey: string
    anthropicKey: string
    localEndpoint: string
    defaultModel: string
    maxTokens: number
    temperature: number
    timeout: number
  }
  agents: {
    maxConcurrentTasks: number
    defaultTimeout: number
    retryAttempts: number
    logLevel: 'error' | 'warn' | 'info' | 'debug'
    enableMetrics: boolean
  }
  security: {
    enableSSL: boolean
    enableAuth: boolean
    sessionTimeout: number
    allowedOrigins: string[]
    enableRateLimit: boolean
    maxRequestsPerMinute: number
  }
  advanced: {
    debugMode: boolean
    enableTelemetry: boolean
    cacheSize: number
    maxLogFiles: number
    enableBackup: boolean
    backupInterval: number
  }
}

const defaultSettings: Settings = {
  general: {
    theme: 'light',
    language: 'en',
    timezone: 'UTC',
    notifications: true,
    autoSave: true
  },
  api: {
    openaiKey: '',
    anthropicKey: '',
    localEndpoint: 'http://localhost:8000',
    defaultModel: 'gpt-3.5-turbo',
    maxTokens: 2048,
    temperature: 0.7,
    timeout: 30000
  },
  agents: {
    maxConcurrentTasks: 10,
    defaultTimeout: 30000,
    retryAttempts: 3,
    logLevel: 'info',
    enableMetrics: true
  },
  security: {
    enableSSL: true,
    enableAuth: false,
    sessionTimeout: 3600,
    allowedOrigins: ['http://localhost:3000'],
    enableRateLimit: true,
    maxRequestsPerMinute: 100
  },
  advanced: {
    debugMode: false,
    enableTelemetry: true,
    cacheSize: 100,
    maxLogFiles: 10,
    enableBackup: true,
    backupInterval: 86400
  }
}

const tabItems = [
  { id: 'general', label: 'General', icon: '⚙️' },
  { id: 'api', label: 'API Configuration', icon: '🔗' },
  { id: 'agents', label: 'Agent Settings', icon: '🤖' },
  { id: 'security', label: 'Security', icon: '🔒' },
  { id: 'advanced', label: 'Advanced', icon: '🔧' }
]

export default function ModernSettingsPage() {
  const [settings, setSettings] = useState<Settings>(defaultSettings)
  const [activeTab, setActiveTab] = useState('general')
  const [hasChanges, setHasChanges] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<{ [key: string]: 'success' | 'error' | null }>({})

  // Load settings from localStorage on mount
  useEffect(() => {
    const savedSettings = localStorage.getItem('agent-nn-settings')
    if (savedSettings) {
      try {
        setSettings(JSON.parse(savedSettings))
      } catch (error) {
        console.error('Failed to load settings:', error)
      }
    }
  }, [])

  // Track changes
  useEffect(() => {
    const currentSettings = JSON.stringify(settings)
    const defaultSettingsStr = JSON.stringify(defaultSettings)
    setHasChanges(currentSettings !== defaultSettingsStr)
  }, [settings])

  const updateSetting = (section: keyof Settings, key: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: value
      }
    }))
  }

  const saveSettings = async () => {
    setSaving(true)
    try {
      localStorage.setItem('agent-nn-settings', JSON.stringify(settings))
      await new Promise(resolve => setTimeout(resolve, 1000)) // Simulate API call
      setHasChanges(false)
    } catch (error) {
      console.error('Failed to save settings:', error)
    } finally {
      setSaving(false)
    }
  }

  const resetSettings = () => {
    if (window.confirm('Are you sure you want to reset all settings to defaults?')) {
      setSettings(defaultSettings)
      localStorage.removeItem('agent-nn-settings')
    }
  }

  const testConnection = async (type: string) => {
    setTesting(type)
    setTestResults(prev => ({ ...prev, [type]: null }))
    
    try {
      await new Promise(resolve => setTimeout(resolve, 2000)) // Simulate test
      const success = Math.random() > 0.3 // 70% success rate for demo
      setTestResults(prev => ({ ...prev, [type]: success ? 'success' : 'error' }))
    } catch (error) {
      setTestResults(prev => ({ ...prev, [type]: 'error' }))
    } finally {
      setTesting(null)
    }
  }

  const InputField = ({ 
    label, 
    value, 
    onChange, 
    type = 'text', 
    placeholder, 
    description,
    required = false 
  }: {
    label: string
    value: string | number
    onChange: (value: any) => void
    type?: string
    placeholder?: string
    description?: string
    required?: boolean
  }) => (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(type === 'number' ? Number(e.target.value) : e.target.value)}
        placeholder={placeholder}
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:shadow-focus focus:border-transparent"
      />
      {description && (
        <p className="text-xs text-gray-500 dark:text-gray-400">{description}</p>
      )}
    </div>
  )

  const SelectField = ({ 
    label, 
    value, 
    onChange, 
    options, 
    description 
  }: {
    label: string
    value: string
    onChange: (value: string) => void
    options: { value: string; label: string }[]
    description?: string
  }) => (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:shadow-focus focus:border-transparent"
      >
        {options.map(option => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {description && (
        <p className="text-xs text-gray-500 dark:text-gray-400">{description}</p>
      )}
    </div>
  )

  const ToggleField = ({ 
    label, 
    value, 
    onChange, 
    description 
  }: {
    label: string
    value: boolean
    onChange: (value: boolean) => void
    description?: string
  }) => (
    <div className="flex items-start justify-between">
      <div className="flex-1">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          {label}
        </label>
        {description && (
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{description}</p>
        )}
      </div>
      <button
        onClick={() => onChange(!value)}
        className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:outline-none focus:shadow-focus ${
          value ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-600'
        }`}
      >
        <span
          className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
            value ? 'translate-x-5' : 'translate-x-0'
          }`}
        />
      </button>
    </div>
  )

  const renderTabContent = () => {
    switch (activeTab) {
      case 'general':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <SelectField
                label="Theme"
                value={settings.general.theme}
                onChange={(value) => updateSetting('general', 'theme', value)}
                options={[
                  { value: 'light', label: 'Light' },
                  { value: 'dark', label: 'Dark' },
                  { value: 'auto', label: 'Auto (System)' }
                ]}
                description="Choose your preferred color scheme"
              />
              
              <SelectField
                label="Language"
                value={settings.general.language}
                onChange={(value) => updateSetting('general', 'language', value)}
                options={[
                  { value: 'en', label: 'English' },
                  { value: 'de', label: 'Deutsch' },
                  { value: 'es', label: 'Español' },
                  { value: 'fr', label: 'Français' }
                ]}
                description="Select your preferred language"
              />
              
              <SelectField
                label="Timezone"
                value={settings.general.timezone}
                onChange={(value) => updateSetting('general', 'timezone', value)}
                options={[
                  { value: 'UTC', label: 'UTC' },
                  { value: 'Europe/London', label: 'London' },
                  { value: 'Europe/Berlin', label: 'Berlin' },
                  { value: 'America/New_York', label: 'New York' },
                  { value: 'Asia/Tokyo', label: 'Tokyo' }
                ]}
                description="Select your timezone"
              />
            </div>
            
            <div className="space-y-4">
              <ToggleField
                label="Enable Notifications"
                value={settings.general.notifications}
                onChange={(value) => updateSetting('general', 'notifications', value)}
                description="Receive system notifications and alerts"
              />
              
              <ToggleField
                label="Auto Save"
                value={settings.general.autoSave}
                onChange={(value) => updateSetting('general', 'autoSave', value)}
                description="Automatically save changes as you work"
              />
            </div>
          </div>
        )

      case 'api':
        return (
          <div className="space-y-6">
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <span className="text-blue-400">ℹ️</span>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200">
                    API Configuration
                  </h3>
                  <div className="mt-2 text-sm text-blue-700 dark:text-blue-300">
                    Configure your AI model providers and endpoints. API keys are stored securely and encrypted.
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <InputField
                  label="OpenAI API Key"
                  value={settings.api.openaiKey}
                  onChange={(value) => updateSetting('api', 'openaiKey', value)}
                  type="password"
                  placeholder="sk-..."
                  description="Your OpenAI API key for GPT models"
                />
                
                <div className="flex gap-2">
                  <button
                    onClick={() => testConnection('openai')}
                    disabled={!settings.api.openaiKey || testing === 'openai'}
                    className="px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                  >
                    {testing === 'openai' ? 'Testing...' : 'Test Connection'}
                  </button>
                  {testResults.openai && (
                    <span className={`px-2 py-1 rounded text-sm ${
                      testResults.openai === 'success' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {testResults.openai === 'success' ? '✓ Connected' : '✗ Failed'}
                    </span>
                  )}
                </div>
              </div>

              <div className="space-y-4">
                <InputField
                  label="Anthropic API Key"
                  value={settings.api.anthropicKey}
                  onChange={(value) => updateSetting('api', 'anthropicKey', value)}
                  type="password"
                  placeholder="sk-ant-..."
                  description="Your Anthropic API key for Claude models"
                />
                
                <div className="flex gap-2">
                  <button
                    onClick={() => testConnection('anthropic')}
                    disabled={!settings.api.anthropicKey || testing === 'anthropic'}
                    className="px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                  >
                    {testing === 'anthropic' ? 'Testing...' : 'Test Connection'}
                  </button>
                  {testResults.anthropic && (
                    <span className={`px-2 py-1 rounded text-sm ${
                      testResults.anthropic === 'success' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {testResults.anthropic === 'success' ? '✓ Connected' : '✗ Failed'}
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <InputField
                label="Local Endpoint"
                value={settings.api.localEndpoint}
                onChange={(value) => updateSetting('api', 'localEndpoint', value)}
                placeholder="http://localhost:8000"
                description="URL for local AI model endpoint"
              />
              
              <SelectField
                label="Default Model"
                value={settings.api.defaultModel}
                onChange={(value) => updateSetting('api', 'defaultModel', value)}
                options={[
                  { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
                  { value: 'gpt-4', label: 'GPT-4' },
                  { value: 'claude-3-sonnet', label: 'Claude 3 Sonnet' },
                  { value: 'claude-3-opus', label: 'Claude 3 Opus' },
                  { value: 'local', label: 'Local Model' }
                ]}
                description="Default model for new conversations"
              />
              
              <InputField
                label="Max Tokens"
                value={settings.api.maxTokens}
                onChange={(value) => updateSetting('api', 'maxTokens', value)}
                type="number"
                description="Maximum tokens per response"
              />
              
              <InputField
                label="Temperature"
                value={settings.api.temperature}
                onChange={(value) => updateSetting('api', 'temperature', value)}
                type="number"
                description="Model creativity (0.0-1.0)"
              />
            </div>
          </div>
        )

      case 'agents':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <InputField
                label="Max Concurrent Tasks"
                value={settings.agents.maxConcurrentTasks}
                onChange={(value) => updateSetting('agents', 'maxConcurrentTasks', value)}
                type="number"
                description="Maximum number of tasks running simultaneously"
              />
              
              <InputField
                label="Default Timeout (ms)"
                value={settings.agents.defaultTimeout}
                onChange={(value) => updateSetting('agents', 'defaultTimeout', value)}
                type="number"
                description="Default timeout for agent tasks"
              />
              
              <InputField
                label="Retry Attempts"
                value={settings.agents.retryAttempts}
                onChange={(value) => updateSetting('agents', 'retryAttempts', value)}
                type="number"
                description="Number of retry attempts for failed tasks"
              />
              
              <SelectField
                label="Log Level"
                value={settings.agents.logLevel}
                onChange={(value) => updateSetting('agents', 'logLevel', value)}
                options={[
                  { value: 'error', label: 'Error' },
                  { value: 'warn', label: 'Warning' },
                  { value: 'info', label: 'Info' },
                  { value: 'debug', label: 'Debug' }
                ]}
                description="Minimum log level to record"
              />
            </div>
            
            <ToggleField
              label="Enable Metrics Collection"
              value={settings.agents.enableMetrics}
              onChange={(value) => updateSetting('agents', 'enableMetrics', value)}
              description="Collect performance metrics for agents"
            />
          </div>
        )

      case 'security':
        return (
          <div className="space-y-6">
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <span className="text-yellow-400">⚠️</span>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                    Security Settings
                  </h3>
                  <div className="mt-2 text-sm text-yellow-700 dark:text-yellow-300">
                    These settings affect system security. Changes may require restart.
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <ToggleField
                label="Enable SSL/TLS"
                value={settings.security.enableSSL}
                onChange={(value) => updateSetting('security', 'enableSSL', value)}
                description="Use HTTPS for all connections"
              />
              
              <ToggleField
                label="Enable Authentication"
                value={settings.security.enableAuth}
                onChange={(value) => updateSetting('security', 'enableAuth', value)}
                description="Require user authentication"
              />
              
              <ToggleField
                label="Enable Rate Limiting"
                value={settings.security.enableRateLimit}
                onChange={(value) => updateSetting('security', 'enableRateLimit', value)}
                description="Limit request frequency per client"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <InputField
                label="Session Timeout (seconds)"
                value={settings.security.sessionTimeout}
                onChange={(value) => updateSetting('security', 'sessionTimeout', value)}
                type="number"
                description="User session timeout duration"
              />
              
              <InputField
                label="Max Requests per Minute"
                value={settings.security.maxRequestsPerMinute}
                onChange={(value) => updateSetting('security', 'maxRequestsPerMinute', value)}
                type="number"
                description="Rate limit threshold"
              />
            </div>
          </div>
        )

      case 'advanced':
        return (
          <div className="space-y-6">
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <span className="text-red-400">🚨</span>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                    Advanced Settings
                  </h3>
                  <div className="mt-2 text-sm text-red-700 dark:text-red-300">
                    These are advanced settings. Only modify if you understand the implications.
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <ToggleField
                label="Debug Mode"
                value={settings.advanced.debugMode}
                onChange={(value) => updateSetting('advanced', 'debugMode', value)}
                description="Enable verbose logging and debug features"
              />
              
              <ToggleField
                label="Enable Telemetry"
                value={settings.advanced.enableTelemetry}
                onChange={(value) => updateSetting('advanced', 'enableTelemetry', value)}
                description="Send anonymous usage data to improve the system"
              />
              
              <ToggleField
                label="Enable Automatic Backup"
                value={settings.advanced.enableBackup}
                onChange={(value) => updateSetting('advanced', 'enableBackup', value)}
                description="Automatically backup system data"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <InputField
                label="Cache Size (MB)"
                value={settings.advanced.cacheSize}
                onChange={(value) => updateSetting('advanced', 'cacheSize', value)}
                type="number"
                description="Maximum cache size in megabytes"
              />
              
              <InputField
                label="Max Log Files"
                value={settings.advanced.maxLogFiles}
                onChange={(value) => updateSetting('advanced', 'maxLogFiles', value)}
                type="number"
                description="Maximum number of log files to keep"
              />
              
              <InputField
                label="Backup Interval (seconds)"
                value={settings.advanced.backupInterval}
                onChange={(value) => updateSetting('advanced', 'backupInterval', value)}
                type="number"
                description="How often to create backups"
              />
            </div>
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div className="p-6 bg-gray-50 dark:bg-gray-900 min-h-screen">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Settings</h1>
            <p className="text-gray-600 dark:text-gray-400">Configure your ABrain system</p>
          </div>
          
          <div className="flex items-center gap-3">
            {hasChanges && (
              <span className="text-sm text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/20 px-3 py-1 rounded-full">
                Unsaved changes
              </span>
            )}
            
            <button
              onClick={resetSettings}
              className="px-4 py-2 text-red-600 dark:text-red-400 border border-red-300 dark:border-red-600 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
            >
              Reset to Defaults
            </button>
            
            <button
              onClick={saveSettings}
              disabled={!hasChanges || saving}
              className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {saving ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Saving...
                </>
              ) : (
                'Save Changes'
              )}
            </button>
          </div>
        </div>

        <div className="flex gap-8">
          {/* Sidebar Tabs */}
          <div className="w-64 flex-shrink-0">
            <nav className="space-y-1">
              {tabItems.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left rounded-lg transition-colors ${
                    activeTab === tab.id
                      ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                  }`}
                >
                  <span className="text-lg">{tab.icon}</span>
                  <span className="font-medium">{tab.label}</span>
                </button>
              ))}
            </nav>
          </div>

          {/* Content Area */}
          <div className="flex-1">
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-8">
              <div className="mb-6">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                  {tabItems.find(tab => tab.id === activeTab)?.label}
                </h2>
                <p className="text-gray-600 dark:text-gray-400">
                  Configure {tabItems.find(tab => tab.id === activeTab)?.label.toLowerCase()} settings for your system.
                </p>
              </div>
              
              {renderTabContent()}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
