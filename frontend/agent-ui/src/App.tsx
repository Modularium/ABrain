import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Sidebar from './components/layout/Sidebar'
import Header from './components/layout/Header'
import AgentsPage from './pages/AgentsPage'
import ApprovalsPage from './pages/ApprovalsPage'
import PlansPage from './pages/PlansPage'
import SettingsPage from './pages/SettingsPage'
import DashboardPage from './pages/Dashboard'
import TracesPage from './pages/TracesPage'
import SystemHealthPage from './pages/SystemHealthPage'
import { LoadingSpinner } from './components/ui/LoadingSpinner'
import Toast from './components/ui/Toast'

interface AppState {
  theme: 'light' | 'dark'
  sidebarCollapsed: boolean
  user: {
    name: string
    avatar?: string
    role: string
  } | null
  notifications: Array<{
    id: string
    type: 'success' | 'error' | 'warning' | 'info'
    message: string
    timestamp: Date
  }>
}

export default function App() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [appState, setAppState] = useState<AppState>({
    theme: 'light',
    sidebarCollapsed: false,
    user: {
      name: 'Control Plane',
      role: 'Operator'
    },
    notifications: []
  })

  // Initialize app
  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Load user preferences
        const savedTheme = (localStorage.getItem('theme') as 'light' | 'dark') || 'light'
        const savedSidebarState = localStorage.getItem('sidebarCollapsed') === 'true'
        
        setAppState(prev => ({
          ...prev,
          theme: savedTheme,
          sidebarCollapsed: savedSidebarState
        }))

        // Apply theme to document element (correct for Tailwind dark mode)
        applyTheme(savedTheme)

        // Simulate loading time
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        setLoading(false)
      } catch (error) {
        console.error('Failed to initialize app:', error)
        setLoading(false)
      }
    }

    initializeApp()
  }, [])

  // Apply theme to document element
  const applyTheme = (theme: 'light' | 'dark') => {
    const root = document.documentElement
    
    if (theme === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
  }

  // Theme toggle
  const toggleTheme = () => {
    const newTheme = appState.theme === 'light' ? 'dark' : 'light'
    setAppState(prev => ({ ...prev, theme: newTheme }))
    localStorage.setItem('theme', newTheme)
    applyTheme(newTheme)
  }

  // Sidebar toggle
  const toggleSidebar = () => {
    const newState = !appState.sidebarCollapsed
    setAppState(prev => ({ ...prev, sidebarCollapsed: newState }))
    localStorage.setItem('sidebarCollapsed', newState.toString())
  }

  // Add notification
  const addNotification = (type: 'success' | 'error' | 'warning' | 'info', message: string) => {
    const notification = {
      id: Date.now().toString(),
      type,
      message,
      timestamp: new Date()
    }
    
    setAppState(prev => ({
      ...prev,
      notifications: [...prev.notifications, notification]
    }))

    // Auto remove after 5 seconds
    setTimeout(() => {
      removeNotification(notification.id)
    }, 5000)
  }

  // Remove notification
  const removeNotification = (id: string) => {
    setAppState(prev => ({
      ...prev,
      notifications: prev.notifications.filter(n => n.id !== id)
    }))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg mb-4 mx-auto">
            <span className="text-white font-bold text-2xl">A</span>
          </div>
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading ABrain...</p>
        </div>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        {/* Mobile Menu Button */}
        <button
          id="mobile-menu-button"
          className="sm:hidden fixed top-4 left-4 z-50 p-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700"
          onClick={() => setMenuOpen(true)}
          aria-label="Open menu"
        >
          <svg className="w-6 h-6 text-gray-600 dark:text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        {/* Sidebar */}
        <Sidebar 
          open={menuOpen} 
          setOpen={setMenuOpen} 
          collapsed={appState.sidebarCollapsed}
          onToggleCollapse={toggleSidebar}
        />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Header */}
          <Header 
            user={appState.user}
            theme={appState.theme}
            onToggleTheme={toggleTheme}
            onAddNotification={addNotification}
          />

          {/* Page Content */}
          <main className="flex-1 overflow-y-auto">
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/health" element={<SystemHealthPage />} />
              <Route path="/traces" element={<TracesPage />} />
              <Route path="/approvals" element={<ApprovalsPage />} />
              <Route path="/plans" element={<PlansPage />} />
              <Route path="/agents" element={<AgentsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </main>
        </div>

        {/* Toast Notifications */}
        <div className="fixed top-20 right-4 z-50 space-y-2">
          {appState.notifications.map((notification) => (
            <Toast
              key={notification.id}
              type={notification.type}
              message={notification.message}
              onClose={() => removeNotification(notification.id)}
            />
          ))}
        </div>
      </div>
    </BrowserRouter>
  )
}
