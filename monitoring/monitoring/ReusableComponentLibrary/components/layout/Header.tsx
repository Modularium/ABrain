// monitoring/dashboard/components/layout/Header.tsx
import React, { useState } from 'react';
import { Bell, Sun, Moon, User, Settings, Search, RefreshCw } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useDashboard } from '../../context/DashboardContext';
import { useAuth } from '../../context/AuthContext';
import { formatRelativeTime } from '../../utils/formatters';

const Header: React.FC = () => {
  const { themeMode, toggleTheme } = useTheme();
  const { refreshData, lastUpdated } = useDashboard();
  const { user, logout } = useAuth();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  
  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await refreshData();
    } finally {
      setIsRefreshing(false);
    }
  };
  
  return (
    <header className="bg-indigo-700 dark:bg-indigo-900 text-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold">ABrain Dashboard</h1>
            <span className="bg-indigo-600 dark:bg-indigo-800 text-sm px-2 py-1 rounded">v2.0.0</span>
          </div>
          
          <div className="flex items-center space-x-6">
            {/* Search */}
            <div className="relative hidden md:block">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-indigo-300" />
              </div>
              <input
                type="text"
                placeholder="Search..."
                className="bg-indigo-600 dark:bg-indigo-800 text-white placeholder-indigo-300 block w-full pl-10 pr-3 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-indigo-700"
              />
            </div>
            
            {/* Last updated indicator */}
            <div className="flex items-center text-sm">
              <span className="hidden md:inline">
                {lastUpdated ? `Last updated: ${formatRelativeTime(lastUpdated.toISOString())}` : 'Never updated'}
              </span>
              <button 
                className="ml-2 flex items-center space-x-1 bg-indigo-600 dark:bg-indigo-800 px-3 py-2 rounded hover:bg-indigo-500 dark:hover:bg-indigo-700 transition"
                onClick={handleRefresh}
                disabled={isRefreshing}
              >
                <RefreshCw size={16} className={isRefreshing ? "animate-spin" : ""} />
                <span className="hidden md:inline">Refresh</span>
              </button>
            </div>
            
            {/* Theme Toggle */}
            <button
              className="text-white hover:text-indigo-200 transition"
              onClick={toggleTheme}
              aria-label={`Switch to ${themeMode === 'light' ? 'dark' : 'light'} mode`}
            >
              {themeMode === 'light' ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
            </button>
            
            {/* Notifications */}
            <div className="relative">
              <button
                className="text-white hover:text-indigo-200 transition relative"
                onClick={() => setShowNotifications(!showNotifications)}
                aria-label="Show notifications"
              >
                <Bell className="h-5 w-5" />
                <span className="absolute top-0 right-0 block h-2 w-2 rounded-full bg-red-500"></span>
              </button>
              
              {/* Notification Dropdown */}
              {showNotifications && (
                <div className="origin-top-right absolute right-0 mt-2 w-80 rounded-md shadow-lg bg-white dark:bg-gray-800 ring-1 ring-black ring-opacity-5 z-10">
                  <div className="py-1">
                    <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
                      <h3 className="text-sm font-medium text-gray-900 dark:text-white">Notifications</h3>
                    </div>
                    <div className="max-h-60 overflow-y-auto">
                      <a href="#" className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700">
                        <div className="font-medium">High Memory Usage</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">Memory usage has reached 78%, which exceeds the warning threshold</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">2 minutes ago</div>
                      </a>
                      <a href="#" className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700">
                        <div className="font-medium">Daily System Backup Completed</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">The daily system backup was successfully completed</div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">2 hours ago</div>
                      </a>
                    </div>
                    <div className="border-t border-gray-200 dark:border-gray-700">
                      <a href="#" className="block px-4 py-2 text-sm text-indigo-600 dark:text-indigo-400">
                        View all notifications
                      </a>
                    </div>
                  </div>
                </div>
              )}
            </div>
            
            {/* User Menu */}
            <div className="relative">
              <button
                className="flex items-center text-white hover:text-indigo-200 transition"
                onClick={() => setShowUserMenu(!showUserMenu)}
                aria-label="User menu"
              >
                <span className="hidden md:inline-block mr-2">{user?.username || 'User'}</span>
                <div className="w-8 h-8 bg-indigo-500 dark:bg-indigo-600 rounded-full flex items-center justify-center">
                  <User className="h-5 w-5" />
                </div>
              </button>
              
              {/* User Dropdown */}
              {showUserMenu && (
                <div className="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white dark:bg-gray-800 ring-1 ring-black ring-opacity-5 z-10">
                  <div className="py-1">
                    <a href="#" className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700">
                      Your Profile
                    </a>
                    <a href="#" className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700">
                      <div className="flex items-center">
                        <Settings className="h-4 w-4 mr-2" />
                        Settings
                      </div>
                    </a>
                    <button
                      onClick={logout}
                      className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      Sign out
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;

// monitoring/dashboard/components/layout/Sidebar.tsx
import React from 'react';
import { 
  Server, 
  Users, 
  Cpu, 
  Database, 
  BarChart, 
  Shield, 
  GitBranch, 
  Settings, 
  AlertTriangle, 
  Book,
  Menu,
  X
} from 'lucide-react';
import { useDashboard } from '../../context/DashboardContext';

interface SidebarProps {
  collapsed: boolean;
  toggleCollapse: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ collapsed, toggleCollapse }) => {
  const { activeTab, setActiveTab } = useDashboard();
  
  const navItems = [
    { id: 'system', label: 'System Overview', icon: <Server size={20} /> },
    { id: 'agents', label: 'Agents', icon: <Users size={20} /> },
    { id: 'models', label: 'Models', icon: <Cpu size={20} /> },
    { id: 'knowledge', label: 'Knowledge Bases', icon: <Database size={20} /> },
    { id: 'monitoring', label: 'Monitoring', icon: <BarChart size={20} /> },
    { id: 'security', label: 'Security', icon: <Shield size={20} /> },
    { id: 'testing', label: 'A/B Testing', icon: <GitBranch size={20} /> },
    { id: 'settings', label: 'Settings', icon: <Settings size={20} /> },
    { id: 'logs', label: 'Logs & Alerts', icon: <AlertTriangle size={20} /> },
    { id: 'docs', label: 'Documentation', icon: <Book size={20} /> },
  ];
  
  return (
    <aside className={`${collapsed ? 'w-16' : 'w-64'} bg-white dark:bg-gray-800 shadow-md transition-width duration-300 flex flex-col`}>
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        {!collapsed && <h2 className="text-lg font-semibold text-gray-800 dark:text-white">Navigation</h2>}
        <button 
          className="text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-white"
          onClick={toggleCollapse}
        >
          {collapsed ? <Menu size={20} /> : <X size={20} />}
        </button>
      </div>
      
      <nav className="flex-1 overflow-y-auto p-2">
        <ul className="space-y-1">
          {navItems.map(item => (
            <li key={item.id}>
              <button 
                className={`flex items-center ${collapsed ? 'justify-center' : 'space-x-3'} w-full p-3 rounded-md ${activeTab === item.id ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300' : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'}`}
                onClick={() => setActiveTab(item.id)}
              >
                <span>{item.icon}</span>
                {!collapsed && <span>{item.label}</span>}
              </button>
            </li>
          ))}
        </ul>
      </nav>
      
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className={`flex ${collapsed ? 'justify-center' : 'items-center space-x-3'}`}>
          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
          {!collapsed && <span className="text-sm text-gray-600 dark:text-gray-400">System Online</span>}
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;

// monitoring/dashboard/components/layout/MainContent.tsx
import React from 'react';
import { useDashboard } from '../../context/DashboardContext';
import SystemOverviewPanel from '../panels/SystemOverviewPanel';
import AgentsPanel from '../panels/AgentsPanel';
import ModelsPanel from '../panels/ModelsPanel';
import KnowledgePanel from '../panels/KnowledgePanel';
import MonitoringPanel from '../panels/MonitoringPanel';
import SecurityPanel from '../panels/SecurityPanel';
import TestingPanel from '../panels/TestingPanel';
import SettingsPanel from '../panels/SettingsPanel';
import LogsPanel from '../panels/LogsPanel';
import DocsPanel from '../panels/DocsPanel';
import LoadingSpinner from '../common/LoadingSpinner';
import Alert from '../common/Alert';

const MainContent: React.FC = () => {
  const { activeTab, loading, error } = useDashboard();
  
  if (loading) {
    return <LoadingSpinner fullPage text="Loading dashboard data..." />;
  }
  
  if (error) {
    return (
      <div className="flex items-center justify-center h-full p-6">
        <Alert 
          type="error" 
          title="Failed to load dashboard data" 
          message={error.message || 'An unexpected error occurred while loading the dashboard.'}
        />
      </div>
    );
  }
  
  return (
    <main className="flex-1 overflow-auto p-6 bg-gray-100 dark:bg-gray-900">
      {activeTab === 'system' && <SystemOverviewPanel />}
      {activeTab === 'agents' && <AgentsPanel />}
      {activeTab === 'models' && <ModelsPanel />}
      {activeTab === 'knowledge' && <KnowledgePanel />}
      {activeTab === 'monitoring' && <MonitoringPanel />}
      {activeTab === 'security' && <SecurityPanel />}
      {activeTab === 'testing' && <TestingPanel />}
      {activeTab === 'settings' && <SettingsPanel />}
      {activeTab === 'logs' && <LogsPanel />}
      {activeTab === 'docs' && <DocsPanel />}
    </main>
  );
};

export default MainContent;

// monitoring/dashboard/components/layout/Footer.tsx
import React from 'react';

const Footer: React.FC = () => {
  return (
    <footer className="bg-white dark:bg-gray-800 shadow-md py-3 px-6 text-center border-t border-gray-200 dark:border-gray-700">
      <div className="text-sm text-gray-500 dark:text-gray-400">
        <p>© 2025 ABrain Dashboard. All rights reserved.</p>
        <p className="mt-1 text-xs">
          Version 2.0.0 | <a href="#" className="text-indigo-600 dark:text-indigo-400 hover:underline">View Changelog</a> | <a href="#" className="text-indigo-600 dark:text-indigo-400 hover:underline">Report Issue</a>
        </p>
      </div>
    </footer>
  );
};

export default Footer;
