// src/store/useAppStore.ts
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'

export interface User {
  id: string
  name: string
  email: string
  avatar?: string
  role: string
  permissions: string[]
}

export interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  timestamp: Date
  read: boolean
  actions?: Array<{
    label: string
    action: () => void
    variant?: 'primary' | 'secondary'
  }>
}

export interface Agent {
  id: string
  name: string
  domain: string
  status: 'active' | 'idle' | 'error' | 'maintenance'
  version: string
  description: string
  capabilities: string[]
  metrics: {
    totalTasks: number
    successRate: number
    avgResponseTime: number
    lastActive: Date
  }
  configuration: Record<string, unknown>
}

export interface Task {
  id: string
  title: string
  description: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  priority: 'low' | 'medium' | 'high' | 'urgent'
  type: string
  agentId: string
  assignedAt: Date
  startedAt?: Date
  completedAt?: Date
  progress: number
  metadata: Record<string, unknown>
  error?: {
    code: string
    message: string
    stack?: string
  }
}

export interface AppSettings {
  theme: 'light' | 'dark' | 'auto'
  language: string
  notifications: {
    enabled: boolean
    sound: boolean
    desktop: boolean
  }
  ui: {
    sidebarCollapsed: boolean
    density: 'compact' | 'comfortable' | 'spacious'
    animations: boolean
  }
  api: {
    baseUrl: string
    timeout: number
    retries: number
  }
}

interface AppState {
  sidebarOpen: boolean
  loading: boolean
  online: boolean
  user: User | null
  authenticated: boolean
  agents: Agent[]
  tasks: Task[]
  notifications: Notification[]
  settings: AppSettings
  error: string | null
}

interface AppActions {
  setSidebarOpen: (open: boolean) => void
  setLoading: (loading: boolean) => void
  setOnline: (online: boolean) => void
  setUser: (user: User | null) => void
  setAuthenticated: (authenticated: boolean) => void
  logout: () => void
  setAgents: (agents: Agent[]) => void
  addAgent: (agent: Agent) => void
  updateAgent: (id: string, updates: Partial<Agent>) => void
  removeAgent: (id: string) => void
  setTasks: (tasks: Task[]) => void
  addTask: (task: Task) => void
  updateTask: (id: string, updates: Partial<Task>) => void
  removeTask: (id: string) => void
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void
  markNotificationRead: (id: string) => void
  removeNotification: (id: string) => void
  clearAllNotifications: () => void
  updateSettings: (updates: Partial<AppSettings>) => void
  resetSettings: () => void
  setError: (error: string | null) => void
  clearError: () => void
}

type AppStore = AppState & AppActions

const defaultSettings: AppSettings = {
  theme: 'light',
  language: 'en',
  notifications: {
    enabled: true,
    sound: true,
    desktop: true
  },
  ui: {
    sidebarCollapsed: false,
    density: 'comfortable',
    animations: true
  },
  api: {
    baseUrl: import.meta.env.VITE_API_URL || 'http://localhost:8080',
    timeout: 30000,
    retries: 3
  }
}

export const useAppStore = create<AppStore>()(
  immer(
    persist(
      (set, _get) => ({
        sidebarOpen: false,
        loading: false,
        online: navigator.onLine,
        user: null,
        authenticated: false,
        agents: [],
        tasks: [],
        notifications: [],
        settings: defaultSettings,
        error: null,

        setSidebarOpen: (open) => set((state) => { state.sidebarOpen = open }),
        setLoading: (loading) => set((state) => { state.loading = loading }),
        setOnline: (online) => set((state) => { state.online = online }),
        setUser: (user) => set((state) => { state.user = user; state.authenticated = !!user }),
        setAuthenticated: (auth) => set((state) => { state.authenticated = auth; if (!auth) state.user = null }),
        logout: () => set((state) => { state.user = null; state.authenticated = false; state.notifications = [] }),
        setAgents: (agents) => set((state) => { state.agents = agents }),
        addAgent: (agent) => set((state) => { state.agents.push(agent) }),
        updateAgent: (id, updates) => set((state) => { const i = state.agents.findIndex(a => a.id === id); if (i !== -1) state.agents[i] = { ...state.agents[i], ...updates } }),
        removeAgent: (id) => set((state) => { state.agents = state.agents.filter(a => a.id !== id) }),
        setTasks: (tasks) => set((state) => { state.tasks = tasks }),
        addTask: (task) => set((state) => { state.tasks.push(task) }),
        updateTask: (id, updates) => set((state) => { const i = state.tasks.findIndex(t => t.id === id); if (i !== -1) state.tasks[i] = { ...state.tasks[i], ...updates } }),
        removeTask: (id) => set((state) => { state.tasks = state.tasks.filter(t => t.id !== id) }),
        addNotification: (notification) => set((state) => { const n: Notification = { ...notification, id: Date.now().toString(), timestamp: new Date(), read: false }; state.notifications.unshift(n); if (state.notifications.length > 50) state.notifications = state.notifications.slice(0, 50) }),
        markNotificationRead: (id) => set((state) => { const n = state.notifications.find(n => n.id === id); if (n) n.read = true }),
        removeNotification: (id) => set((state) => { state.notifications = state.notifications.filter(n => n.id !== id) }),
        clearAllNotifications: () => set((state) => { state.notifications = [] }),
        updateSettings: (updates) => set((state) => { state.settings = { ...state.settings, ...updates } }),
        resetSettings: () => set((state) => { state.settings = defaultSettings }),
        setError: (error) => set((state) => { state.error = error }),
        clearError: () => set((state) => { state.error = null })
      }),
      {
        name: 'abrain-store',
        storage: createJSONStorage(() => localStorage),
        partialize: (state): Partial<AppStore> => ({
          settings: state.settings,
          user: state.user,
          authenticated: state.authenticated
        })
      }
    )
  )
)

export const useUser = () => useAppStore((state) => state.user)
export const useAuthenticated = () => useAppStore((state) => state.authenticated)
export const useAgents = () => useAppStore((state) => state.agents)
export const useTasks = () => useAppStore((state) => state.tasks)
export const useNotifications = () => useAppStore((state) => state.notifications)
export const useSettings = () => useAppStore((state) => state.settings)
export const useLoading = () => useAppStore((state) => state.loading)
export const useError = () => useAppStore((state) => state.error)
