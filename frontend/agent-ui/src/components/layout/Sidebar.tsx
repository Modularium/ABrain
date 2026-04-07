import { useState, useEffect } from 'react'
import { useLocation, Link } from 'react-router-dom'

interface SidebarProps {
  open: boolean
  setOpen: (open: boolean) => void
  collapsed: boolean
  onToggleCollapse: () => void
}

const navigationItems = [
  { path: '/', name: 'Dashboard', icon: '📊', end: true },
  { path: '/chat', name: 'Chat', icon: '💬' },
  { path: '/agents', name: 'Agents', icon: '🤖' },
  { path: '/tasks', name: 'Tasks', icon: '📋' },
  { path: '/routing', name: 'Routing', icon: '🔄' },
  { path: '/feedback', name: 'Feedback', icon: '💭' },
  { path: '/monitoring', name: 'Monitoring', icon: '📊' },
  { path: '/metrics', name: 'Metrics', icon: '📈' },
  { path: '/settings', name: 'Settings', icon: '⚙️' },
  { path: '/admin', name: 'Admin', icon: '👤' },
  { path: '/debug', name: 'Debug', icon: '🔧' },
]

export default function Sidebar({ open, setOpen, collapsed, onToggleCollapse }: SidebarProps) {
  const location = useLocation()

  // Close sidebar on mobile when route changes
  useEffect(() => {
    setOpen(false)
  }, [location.pathname, setOpen])

  // Close sidebar when clicking outside on mobile
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const sidebar = document.getElementById('sidebar')
      const menuButton = document.getElementById('mobile-menu-button')
      
      if (open && sidebar && !sidebar.contains(event.target as Node) && 
          menuButton && !menuButton.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    if (open) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [open, setOpen])

  const linkClass = (isActive: boolean) =>
    `flex items-center gap-3 px-4 py-3 mx-2 rounded-xl transition-all duration-200 hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 dark:hover:from-blue-900/20 dark:hover:to-indigo-900/20 hover:shadow-sm group cursor-pointer ${
      isActive 
        ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-lg shadow-blue-500/25' 
        : 'text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400'
    }`

  return (
    <>
      {/* Mobile Overlay */}
      {open && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 sm:hidden transition-opacity duration-300" 
          onClick={() => setOpen(false)}
        />
      )}
      
      {/* Sidebar */}
      <aside
        id="sidebar"
        className={`
          ${open ? 'translate-x-0' : '-translate-x-full'} 
          sm:translate-x-0 
          ${collapsed ? 'w-16' : 'w-64'} 
          bg-white dark:bg-gray-800 
          border-r border-gray-200 dark:border-gray-700 
          h-full 
          fixed sm:static 
          z-50 
          transition-all duration-300 ease-in-out 
          shadow-xl sm:shadow-none 
          flex flex-col
          overflow-hidden
        `}
      >
        {/* Header */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
          <div className="flex items-center justify-between">
            {!collapsed && (
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg flex-shrink-0">
                  <span className="text-white font-bold text-lg">A</span>
                </div>
                <div className="min-w-0">
                  <h1 className="font-bold text-xl text-gray-900 dark:text-white truncate">ABrain</h1>
                  <p className="text-sm text-gray-500 dark:text-gray-400 truncate">AI Management</p>
                </div>
              </div>
            )}
            
            {collapsed && (
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg mx-auto">
                <span className="text-white font-bold text-lg">A</span>
              </div>
            )}

            {/* Close button for mobile */}
            <button
              className="sm:hidden p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              onClick={() => setOpen(false)}
              aria-label="Close menu"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            {/* Collapse toggle for desktop */}
            <button
              className="hidden sm:block p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              onClick={onToggleCollapse}
              aria-label="Toggle sidebar"
            >
              <svg className={`w-5 h-5 transition-transform duration-200 ${collapsed ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 overflow-y-auto custom-scrollbar">
          <ul className="space-y-2">
            {navigationItems.map((item) => {
              const isActive = item.end ? location.pathname === item.path : location.pathname.startsWith(item.path)
              
              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className={linkClass(isActive)}
                    title={collapsed ? item.name : undefined}
                  >
                    <span className="text-xl flex-shrink-0">{item.icon}</span>
                    {!collapsed && (
                      <>
                        <span className="font-medium truncate">{item.name}</span>
                        {isActive && (
                          <div className="ml-auto w-2 h-2 bg-white rounded-full flex-shrink-0"></div>
                        )}
                      </>
                    )}
                  </Link>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Bottom section */}
        <div className="p-4 bg-gradient-to-r from-gray-50 to-blue-50 dark:from-gray-800 dark:to-blue-900/20 border-t border-gray-200 dark:border-gray-700 flex-shrink-0">
          <div className={`text-center ${collapsed ? 'px-2' : ''}`}>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
              {collapsed ? 'Status' : 'System Status'}
            </p>
            <div className="flex items-center justify-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              {!collapsed && (
                <span className="text-sm text-gray-600 dark:text-gray-300 font-medium">Online</span>
              )}
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}
