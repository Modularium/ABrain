import React, { useState, useEffect } from 'react';
import { Home, Settings, BarChart, Database, Users, Code, Server, Shield, AlertTriangle, Book, RefreshCw, GitBranch, Cpu, HardDrive, Cloud, Search, Info, UploadCloud, FileText, MessagesSquare, Network } from 'lucide-react';

const Dashboard = () => {
  const [activeTab, setActiveTab] = useState('system');
  const [systemData, setSystemData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Simulate fetch data from API
  const fetchSystemData = () => {
    setLoading(true);
    
    // In a real application, this would be an API call
    setTimeout(() => {
      setSystemData({
        cpu_usage: 24,
        memory_usage: 78,
        gpu_usage: 42,
        disk_usage: 36,
        active_agents: 5,
        task_queue_size: 12,
        total_tasks_completed: 2435,
        avg_response_time: 1.2,
        models: [
          { name: 'gpt-4', type: 'LLM', source: 'OpenAI', version: 'v1.0', status: 'active', requests: 32145, latency: 1.2 },
          { name: 'claude-3', type: 'LLM', source: 'Anthropic', version: 'v1.0', status: 'active', requests: 18921, latency: 1.5 },
          { name: 'llama-3', type: 'LLM', source: 'Local', version: 'v1.0', status: 'active', requests: 8752, latency: 2.1 }
        ],
        activeTasks: [
          { id: 'T-1254', type: 'Analysis', agent: 'Finance', status: 'running', duration: '24s' },
          { id: 'T-1253', type: 'Research', agent: 'Web', status: 'completed', duration: '3m 12s' },
          { id: 'T-1252', type: 'Code', agent: 'Tech', status: 'queued', duration: '-' }
        ],
        systemComponents: [
          { name: 'Supervisor Agent', status: 'online', version: '2.1.0', lastUpdated: '2 hours ago' },
          { name: 'MLflow Integration', status: 'online', version: '1.4.2', lastUpdated: '1 day ago' },
          { name: 'Vector Store', status: 'online', version: '3.0.1', lastUpdated: '3 days ago' },
          { name: 'Cache Manager', status: 'online', version: '1.2.5', lastUpdated: '5 days ago' }
        ],
        logs: [
          { level: 'INFO', timestamp: '2025-03-16T14:23:45', message: 'Agent "Finance" created successfully' },
          { level: 'WARNING', timestamp: '2025-03-16T14:22:30', message: 'High memory usage detected (78%)' },
          { level: 'ERROR', timestamp: '2025-03-16T14:20:15', message: 'Failed to load model "mistral-7b" - CUDA out of memory' },
          { level: 'INFO', timestamp: '2025-03-16T14:19:45', message: 'System started successfully' }
        ],
        agents: [
          { name: 'Finance Agent', domain: 'Finance', status: 'active', tasks: 1245, successRate: 92.5, avgResponse: 1.2, lastActive: 'Just now' },
          { name: 'Tech Agent', domain: 'Technology', status: 'active', tasks: 2153, successRate: 94.1, avgResponse: 0.9, lastActive: '2 minutes ago' },
          { name: 'Marketing Agent', domain: 'Marketing', status: 'active', tasks: 987, successRate: 88.3, avgResponse: 1.5, lastActive: '5 minutes ago' },
          { name: 'Web Agent', domain: 'Web', status: 'active', tasks: 1856, successRate: 91.2, avgResponse: 1.1, lastActive: '10 minutes ago' },
          { name: 'Research Agent', domain: 'Research', status: 'idle', tasks: 654, successRate: 89.7, avgResponse: 2.3, lastActive: '1 hour ago' }
        ],
        knowledgeBases: [
          { name: 'Finance KB', documents: 1245, lastUpdated: '2 hours ago', size: '2.4 GB', status: 'active' },
          { name: 'Tech KB', documents: 3567, lastUpdated: '1 day ago', size: '5.2 GB', status: 'active' },
          { name: 'Marketing KB', documents: 982, lastUpdated: '3 days ago', size: '1.8 GB', status: 'active' },
          { name: 'General KB', documents: 4521, lastUpdated: '5 days ago', size: '8.7 GB', status: 'active' }
        ],
        testResults: [
          { id: 'test-001', name: 'Prompt Optimization', status: 'completed', variants: 2, winner: 'Variant B', improvement: '+12.5%' },
          { id: 'test-002', name: 'Model Comparison', status: 'in-progress', variants: 3, winner: '-', improvement: '-' },
          { id: 'test-003', name: 'Knowledge Source', status: 'completed', variants: 2, winner: 'Variant A', improvement: '+5.2%' }
        ],
        securityEvents: [
          { type: 'Authentication', timestamp: '2025-03-16T14:23:45', details: 'Successful login: admin' },
          { type: 'Rate Limit', timestamp: '2025-03-16T14:10:30', details: 'Rate limit exceeded: 192.168.1.105' },
          { type: 'Input Validation', timestamp: '2025-03-16T13:45:15', details: 'Suspicious input detected and sanitized' }
        ]
      });
      setLoading(false);
      setLastUpdated(new Date().toLocaleTimeString());
    }, 500);
  };

  // Initial data fetch
  useEffect(() => {
    fetchSystemData();
    // Set up auto-refresh if needed
    const interval = setInterval(fetchSystemData, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  // Manual refresh function
  const handleRefresh = () => {
    fetchSystemData();
  };

  return (
    <div className="flex flex-col h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-indigo-700 text-white p-4 shadow-md">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold">ABrain Dashboard</h1>
            <span className="bg-indigo-600 text-sm px-2 py-1 rounded">v2.0.0</span>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm">
              {lastUpdated ? `Last updated: ${lastUpdated}` : 'Loading...'}
            </span>
            <button 
              className="flex items-center space-x-2 bg-indigo-600 px-3 py-2 rounded hover:bg-indigo-500"
              onClick={handleRefresh}
              disabled={loading}
            >
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
              <span>Refresh</span>
            </button>
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold">CPU Usage Alert</h4>
              <div className="relative inline-block w-12 h-6 border rounded-full">
                <input type="checkbox" className="sr-only" defaultChecked />
                <span className="block absolute left-1 top-1 bg-indigo-600 w-4 h-4 rounded-full transition-transform transform translate-x-6"></span>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span>Alert when CPU usage exceeds</span>
              <input type="number" className="form-input rounded-md w-16 border-gray-300" defaultValue="80" />
              <span>% for</span>
              <input type="number" className="form-input rounded-md w-16 border-gray-300" defaultValue="5" />
              <span>minutes</span>
            </div>
          </div>
          
          <div className="border rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold">Memory Usage Alert</h4>
              <div className="relative inline-block w-12 h-6 border rounded-full">
                <input type="checkbox" className="sr-only" defaultChecked />
                <span className="block absolute left-1 top-1 bg-indigo-600 w-4 h-4 rounded-full transition-transform transform translate-x-6"></span>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span>Alert when memory usage exceeds</span>
              <input type="number" className="form-input rounded-md w-16 border-gray-300" defaultValue="90" />
              <span>% for</span>
              <input type="number" className="form-input rounded-md w-16 border-gray-300" defaultValue="5" />
              <span>minutes</span>
            </div>
          </div>
          
          <div className="border rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold">Agent Failure Alert</h4>
              <div className="relative inline-block w-12 h-6 border rounded-full">
                <input type="checkbox" className="sr-only" defaultChecked />
                <span className="block absolute left-1 top-1 bg-indigo-600 w-4 h-4 rounded-full transition-transform transform translate-x-6"></span>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span>Alert when agent success rate drops below</span>
              <input type="number" className="form-input rounded-md w-16 border-gray-300" defaultValue="75" />
              <span>%</span>
            </div>
          </div>
          
          <div className="flex space-x-3 mt-2">
            <button className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
              Save Configuration
            </button>
            <button className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">
              Test Alerts
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const DocsPanel = ({ data }) => {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">Documentation</h2>
        <div className="flex space-x-3">
          <input type="text" className="form-input rounded-md border-gray-300" placeholder="Search documentation..." />
          <button className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
            Search
          </button>
        </div>
      </div>

      {/* Documentation Overview */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="font-bold mb-4">Welcome to ABrain Documentation</h3>
        <p className="text-gray-600 mb-4">
          This documentation provides comprehensive information about the ABrain system, including
          setup instructions, API references, and best practices for creating and managing agents.
        </p>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          <div className="border rounded-lg p-4 hover:border-indigo-500 cursor-pointer transition-colors">
            <div className="flex items-center mb-2">
              <Book size={20} className="text-indigo-600 mr-2" />
              <h4 className="font-semibold">Getting Started</h4>
            </div>
            <p className="text-sm text-gray-600">
              Learn the basics of ABrain and how to set up your first agents.
            </p>
            <p className="text-indigo-600 text-sm mt-2">Read more →</p>
          </div>
          
          <div className="border rounded-lg p-4 hover:border-indigo-500 cursor-pointer transition-colors">
            <div className="flex items-center mb-2">
              <Code size={20} className="text-indigo-600 mr-2" />
              <h4 className="font-semibold">API Reference</h4>
            </div>
            <p className="text-sm text-gray-600">
              Explore the ABrain API for programmatic interaction with the system.
            </p>
            <p className="text-indigo-600 text-sm mt-2">Read more →</p>
          </div>
          
          <div className="border rounded-lg p-4 hover:border-indigo-500 cursor-pointer transition-colors">
            <div className="flex items-center mb-2">
              <Users size={20} className="text-indigo-600 mr-2" />
              <h4 className="font-semibold">Agent Creation Guide</h4>
            </div>
            <p className="text-sm text-gray-600">
              Best practices for designing and implementing effective agents.
            </p>
            <p className="text-indigo-600 text-sm mt-2">Read more →</p>
          </div>
        </div>
      </div>
      
      {/* Quick Reference */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="font-bold mb-4">Quick Reference</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="font-semibold mb-2">Common Commands</h4>
            <div className="bg-gray-50 p-3 rounded-lg font-mono text-sm">
              <div className="mb-2">
                <span className="text-indigo-600">smolit</span> <span className="text-red-500">login</span>
                <p className="text-gray-500 text-xs mt-1">Authenticate with the system</p>
              </div>
              <div className="mb-2">
                <span className="text-indigo-600">smolit</span> <span className="text-red-500">task</span> <span className="text-green-600">"Task description"</span>
                <p className="text-gray-500 text-xs mt-1">Submit a task for execution</p>
              </div>
              <div className="mb-2">
                <span className="text-indigo-600">smolit</span> <span className="text-red-500">agents</span>
                <p className="text-gray-500 text-xs mt-1">List available agents</p>
              </div>
              <div className="mb-2">
                <span className="text-indigo-600">smolit</span> <span className="text-red-500">metrics</span>
                <p className="text-gray-500 text-xs mt-1">Display system metrics</p>
              </div>
            </div>
          </div>
          
          <div>
            <h4 className="font-semibold mb-2">API Examples</h4>
            <div className="bg-gray-50 p-3 rounded-lg font-mono text-sm">
              <div className="mb-2">
                <p className="text-gray-500">// Submit a task via API</p>
                <span className="text-blue-600">POST</span> <span>/api/v2/tasks</span>
                <pre className="text-xs mt-1 text-green-700">{`{
  "description": "Analyze market trends",
  "domain": "finance",
  "priority": 2
}`}</pre>
              </div>
              <div className="mb-2">
                <p className="text-gray-500">// Get task status</p>
                <span className="text-blue-600">GET</span> <span>/api/v2/tasks/{'{task_id}'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Documentation Table of Contents */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="font-bold mb-4">Documentation Contents</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2">
          <div>
            <h4 className="font-semibold border-b pb-2 mb-2">System Overview</h4>
            <ul className="space-y-1">
              <li className="text-indigo-600 hover:underline cursor-pointer">Architecture</li>
              <li className="text-indigo-600 hover:underline cursor-pointer">Components</li>
              <li className="text-indigo-600 hover:underline cursor-pointer">Security</li>
              <li className="text-indigo-600 hover:underline cursor-pointer">Monitoring</li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-semibold border-b pb-2 mb-2">User Guides</h4>
            <ul className="space-y-1">
              <li className="text-indigo-600 hover:underline cursor-pointer">Installation Guide</li>
              <li className="text-indigo-600 hover:underline cursor-pointer">Configuration</li>
              <li className="text-indigo-600 hover:underline cursor-pointer">Creating Agents</li>
              <li className="text-indigo-600 hover:underline cursor-pointer">Knowledge Management</li>
            </ul>
          </div>
          
          <div className="mt-4">
            <h4 className="font-semibold border-b pb-2 mb-2">API Reference</h4>
            <ul className="space-y-1">
              <li className="text-indigo-600 hover:underline cursor-pointer">Authentication</li>
              <li className="text-indigo-600 hover:underline cursor-pointer">Task Management</li>
              <li className="text-indigo-600 hover:underline cursor-pointer">Agent Management</li>
              <li className="text-indigo-600 hover:underline cursor-pointer">System Management</li>
            </ul>
          </div>
          
          <div className="mt-4">
            <h4 className="font-semibold border-b pb-2 mb-2">Tutorials</h4>
            <ul className="space-y-1">
              <li className="text-indigo-600 hover:underline cursor-pointer">Building Custom Agents</li>
              <li className="text-indigo-600 hover:underline cursor-pointer">Setting Up A/B Tests</li>
              <li className="text-indigo-600 hover:underline cursor-pointer">Integrating External APIs</li>
              <li className="text-indigo-600 hover:underline cursor-pointer">Performance Optimization</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;-center space-x-2">
              <span>Admin</span>
              <div className="w-8 h-8 bg-indigo-500 rounded-full flex items-center justify-center">
                <span>A</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 bg-white shadow-md">
          <nav className="p-4">
            <ul className="space-y-2">
              <li>
                <button 
                  className={`flex items-center space-x-3 w-full p-3 rounded-md ${activeTab === 'system' ? 'bg-indigo-100 text-indigo-700' : 'hover:bg-gray-100'}`}
                  onClick={() => setActiveTab('system')}
                >
                  <Server size={20} />
                  <span>System Overview</span>
                </button>
              </li>
              <li>
                <button 
                  className={`flex items-center space-x-3 w-full p-3 rounded-md ${activeTab === 'agents' ? 'bg-indigo-100 text-indigo-700' : 'hover:bg-gray-100'}`}
                  onClick={() => setActiveTab('agents')}
                >
                  <Users size={20} />
                  <span>Agents</span>
                </button>
              </li>
              <li>
                <button 
                  className={`flex items-center space-x-3 w-full p-3 rounded-md ${activeTab === 'models' ? 'bg-indigo-100 text-indigo-700' : 'hover:bg-gray-100'}`}
                  onClick={() => setActiveTab('models')}
                >
                  <Cpu size={20} />
                  <span>Models</span>
                </button>
              </li>
              <li>
                <button 
                  className={`flex items-center space-x-3 w-full p-3 rounded-md ${activeTab === 'knowledge' ? 'bg-indigo-100 text-indigo-700' : 'hover:bg-gray-100'}`}
                  onClick={() => setActiveTab('knowledge')}
                >
                  <Database size={20} />
                  <span>Knowledge Bases</span>
                </button>
              </li>
              <li>
                <button 
                  className={`flex items-center space-x-3 w-full p-3 rounded-md ${activeTab === 'monitoring' ? 'bg-indigo-100 text-indigo-700' : 'hover:bg-gray-100'}`}
                  onClick={() => setActiveTab('monitoring')}
                >
                  <BarChart size={20} />
                  <span>Monitoring</span>
                </button>
              </li>
              <li>
                <button 
                  className={`flex items-center space-x-3 w-full p-3 rounded-md ${activeTab === 'security' ? 'bg-indigo-100 text-indigo-700' : 'hover:bg-gray-100'}`}
                  onClick={() => setActiveTab('security')}
                >
                  <Shield size={20} />
                  <span>Security</span>
                </button>
              </li>
              <li>
                <button 
                  className={`flex items-center space-x-3 w-full p-3 rounded-md ${activeTab === 'testing' ? 'bg-indigo-100 text-indigo-700' : 'hover:bg-gray-100'}`}
                  onClick={() => setActiveTab('testing')}
                >
                  <GitBranch size={20} />
                  <span>A/B Testing</span>
                </button>
              </li>
              <li>
                <button 
                  className={`flex items-center space-x-3 w-full p-3 rounded-md ${activeTab === 'settings' ? 'bg-indigo-100 text-indigo-700' : 'hover:bg-gray-100'}`}
                  onClick={() => setActiveTab('settings')}
                >
                  <Settings size={20} />
                  <span>Settings</span>
                </button>
              </li>
              <li>
                <button 
                  className={`flex items-center space-x-3 w-full p-3 rounded-md ${activeTab === 'logs' ? 'bg-indigo-100 text-indigo-700' : 'hover:bg-gray-100'}`}
                  onClick={() => setActiveTab('logs')}
                >
                  <AlertTriangle size={20} />
                  <span>Logs & Alerts</span>
                </button>
              </li>
              <li>
                <button 
                  className={`flex items-center space-x-3 w-full p-3 rounded-md ${activeTab === 'docs' ? 'bg-indigo-100 text-indigo-700' : 'hover:bg-gray-100'}`}
                  onClick={() => setActiveTab('docs')}
                >
                  <Book size={20} />
                  <span>Documentation</span>
                </button>
              </li>
            </ul>
          </nav>
        </aside>

        {/* Content Area */}
        <main className="flex-1 overflow-auto p-6">
          {loading && !systemData ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
                <p className="mt-4 text-indigo-600">Loading dashboard data...</p>
              </div>
            </div>
          ) : (
            <>
              {activeTab === 'system' && <SystemOverview data={systemData} />}
              {activeTab === 'agents' && <AgentsPanel data={systemData} />}
              {activeTab === 'models' && <ModelsPanel data={systemData} />}
              {activeTab === 'knowledge' && <KnowledgePanel data={systemData} />}
              {activeTab === 'monitoring' && <MonitoringPanel data={systemData} />}
              {activeTab === 'security' && <SecurityPanel data={systemData} />}
              {activeTab === 'testing' && <TestingPanel data={systemData} />}
              {activeTab === 'settings' && <SettingsPanel data={systemData} />}
              {activeTab === 'logs' && <LogsPanel data={systemData} />}
              {activeTab === 'docs' && <DocsPanel data={systemData} />}
            </>
          )}
        </main>
      </div>
    </div>
  );
};

const SystemOverview = ({ data }) => {
  if (!data) return <div>Loading...</div>;
  
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">System Overview</h2>
        <div className="flex space-x-2">
          <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm flex items-center">
            <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
            System Online
          </span>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center justify-between">
            <h3 className="text-gray-500">CPU Usage</h3>
            <span className="text-green-500">Normal</span>
          </div>
          <p className="text-2xl font-bold mt-2">{data.cpu_usage}%</p>
          <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2">
            <div className="bg-green-500 h-2.5 rounded-full" style={{ width: `${data.cpu_usage}%` }}></div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center justify-between">
            <h3 className="text-gray-500">Memory Usage</h3>
            <span className="text-yellow-500">Warning</span>
          </div>
          <p className="text-2xl font-bold mt-2">{data.memory_usage}%</p>
          <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2">
            <div className="bg-yellow-500 h-2.5 rounded-full" style={{ width: `${data.memory_usage}%` }}></div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center justify-between">
            <h3 className="text-gray-500">GPU Usage</h3>
            <span className="text-green-500">Normal</span>
          </div>
          <p className="text-2xl font-bold mt-2">{data.gpu_usage}%</p>
          <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2">
            <div className="bg-green-500 h-2.5 rounded-full" style={{ width: `${data.gpu_usage}%` }}></div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center justify-between">
            <h3 className="text-gray-500">Disk Space</h3>
            <span className="text-green-500">Normal</span>
          </div>
          <p className="text-2xl font-bold mt-2">{data.disk_usage}%</p>
          <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2">
            <div className="bg-green-500 h-2.5 rounded-full" style={{ width: `${data.disk_usage}%` }}></div>
          </div>
        </div>
      </div>

      {/* Active Tasks & Components */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="font-bold mb-4">Active Tasks</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="bg-gray-50">
                  <th className="p-2 text-left">ID</th>
                  <th className="p-2 text-left">Type</th>
                  <th className="p-2 text-left">Agent</th>
                  <th className="p-2 text-left">Status</th>
                  <th className="p-2 text-left">Duration</th>
                </tr>
              </thead>
              <tbody>
                {data.activeTasks.map((task, index) => (
                  <tr key={task.id} className="border-t">
                    <td className="p-2">{agent.tasks.toLocaleString()}</td>
                  <td className="p-2">
                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                      <div className="bg-indigo-500 h-2.5 rounded-full" style={{ width: `${(agent.tasks / data.agents.reduce((max, a) => Math.max(max, a.tasks), 0)) * 100}%` }}></div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      {/* Alerts & Notifications */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="font-bold mb-4">Recent Alerts</h3>
        <div className="space-y-3">
          <div className="flex items-start p-3 border rounded-lg bg-yellow-50">
            <AlertTriangle size={20} className="text-yellow-600 mr-3 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-medium">High Memory Usage Detected</p>
              <p className="text-sm text-gray-600">Memory usage has reached {data.memory_usage}%, which exceeds the warning threshold of 75%.</p>
              <p className="text-xs text-gray-500 mt-1">Today at {new Date().toLocaleTimeString()}</p>
            </div>
          </div>
          
          <div className="flex items-start p-3 border rounded-lg">
            <Info size={20} className="text-blue-600 mr-3 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-medium">Daily System Backup Completed</p>
              <p className="text-sm text-gray-600">The daily system backup was successfully completed.</p>
              <p className="text-xs text-gray-500 mt-1">Today at 2:00 AM</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const SecurityPanel = ({ data }) => {
  if (!data) return <div>Loading...</div>;
  
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">Security Management</h2>
        <button className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
          Security Audit
        </button>
      </div>

      {/* Security Overview */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="font-bold mb-4">Security Overview</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="border rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold">Security Status</h4>
              <Shield size={18} className="text-green-600" />
            </div>
            <p className="inline-flex items-center bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm">
              <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
              Secure
            </p>
          </div>
          
          <div className="border rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold">Last Security Scan</h4>
              <Shield size={18} className="text-indigo-600" />
            </div>
            <p className="text-sm">Today at 6:00 AM</p>
            <p className="text-xs text-green-600 mt-1">No issues found</p>
          </div>
          
          <div className="border rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold">Security Updates</h4>
              <Shield size={18} className="text-indigo-600" />
            </div>
            <p className="text-sm">All components up to date</p>
            <p className="text-xs text-green-600 mt-1">Last checked: Today at 6:00 AM</p>
          </div>
        </div>
      </div>
      
      {/* Recent Security Events */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="font-bold mb-4">Recent Security Events</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="p-2 text-left">Event Type</th>
                <th className="p-2 text-left">Timestamp</th>
                <th className="p-2 text-left">Details</th>
                <th className="p-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.securityEvents.map((event, index) => (
                <tr key={index} className="border-t">
                  <td className="p-2 font-medium">{event.type}</td>
                  <td className="p-2">{new Date(event.timestamp).toLocaleString()}</td>
                  <td className="p-2">{event.details}</td>
                  <td className="p-2">
                    <button className="px-2 py-1 bg-indigo-100 text-indigo-700 rounded text-xs">
                      View Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      {/* Access Control */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="font-bold mb-4">Access Control</h3>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Authentication Method</label>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="border rounded-lg p-3 bg-indigo-50 border-indigo-200">
              <div className="flex items-center">
                <input type="radio" name="auth-method" checked className="mr-2" />
                <div>
                  <p className="font-medium">JWT Token</p>
                  <p className="text-xs text-gray-600">Token-based authentication with 24h expiry</p>
                </div>
              </div>
            </div>
            
            <div className="border rounded-lg p-3">
              <div className="flex items-center">
                <input type="radio" name="auth-method" className="mr-2" />
                <div>
                  <p className="font-medium">OAuth 2.0</p>
                  <p className="text-xs text-gray-600">Integration with external OAuth providers</p>
                </div>
              </div>
            </div>
            
            <div className="border rounded-lg p-3">
              <div className="flex items-center">
                <input type="radio" name="auth-method" className="mr-2" />
                <div>
                  <p className="font-medium">API Key</p>
                  <p className="text-xs text-gray-600">Simple API key based authentication</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Access Policies</label>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="bg-gray-50">
                  <th className="p-2 text-left">Role</th>
                  <th className="p-2 text-left">Permissions</th>
                  <th className="p-2 text-left">Users</th>
                  <th className="p-2 text-left">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-t">
                  <td className="p-2 font-medium">Administrator</td>
                  <td className="p-2">Full access to all features</td>
                  <td className="p-2">2</td>
                  <td className="p-2">
                    <button className="px-2 py-1 bg-indigo-100 text-indigo-700 rounded text-xs">
                      Edit
                    </button>
                  </td>
                </tr>
                <tr className="border-t">
                  <td className="p-2 font-medium">Manager</td>
                  <td className="p-2">View and manage agents, knowledge bases</td>
                  <td className="p-2">5</td>
                  <td className="p-2">
                    <button className="px-2 py-1 bg-indigo-100 text-indigo-700 rounded text-xs">
                      Edit
                    </button>
                  </td>
                </tr>
                <tr className="border-t">
                  <td className="p-2 font-medium">User</td>
                  <td className="p-2">Submit tasks and view results</td>
                  <td className="p-2">28</td>
                  <td className="p-2">
                    <button className="px-2 py-1 bg-indigo-100 text-indigo-700 rounded text-xs">
                      Edit
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        
        <button className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
          Manage Users & Roles
        </button>
      </div>
    </div>
  );
};

const TestingPanel = ({ data }) => {
  if (!data) return <div>Loading...</div>;
  
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">A/B Testing</h2>
        <button className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
          Create New Test
        </button>
      </div>

      {/* Test Overview */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="font-bold mb-4">Test Results</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="p-2 text-left">Name</th>
                <th className="p-2 text-left">Status</th>
                <th className="p-2 text-left">Variants</th>
                <th className="p-2 text-left">Winner</th>
                <th className="p-2 text-left">Improvement</th>
                <th className="p-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.testResults.map((test, index) => (
                <tr key={index} className="border-t">
                  <td className="p-2 font-medium">{test.name}</td>
                  <td className="p-2">
                    <span className={`px-2 py-1 rounded text-xs ${
                      test.status === 'completed' ? 'bg-green-100 text-green-800' : 
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {test.status === 'completed' ? 'Completed' : 'In Progress'}
                    </span>
                  </td>
                  <td className="p-2">{test.variants}</td>
                  <td className="p-2">{test.winner}</td>
                  <td className="p-2">{test.improvement}</td>
                  <td className="p-2">
                    <div className="flex space-x-2">
                      <button className="p-1 text-gray-500 hover:text-indigo-600">View</button>
                      {test.status !== 'completed' && (
                        <button className="p-1 text-gray-500 hover:text-red-600">Stop</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      {/* Test Details */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-bold">Test Details: Prompt Optimization</h3>
          <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">Completed</span>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="font-semibold mb-2">Variant A (Baseline)</h4>
            <div className="border rounded-lg p-3 bg-gray-50">
              <p className="text-sm font-mono">Analyze the following financial data and provide insights on investment opportunities.</p>
            </div>
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span>Success Rate</span>
                <span>78.5%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div className="bg-blue-500 h-2.5 rounded-full" style={{ width: '78.5%' }}></div>
              </div>
              <div className="flex justify-between text-sm">
                <span>Avg Response Time</span>
                <span>1.8s</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div className="bg-blue-500 h-2.5 rounded-full" style={{ width: '60%' }}></div>
              </div>
            </div>
          </div>
          
          <div>
            <h4 className="font-semibold mb-2">Variant B (Winner)</h4>
            <div className="border rounded-lg p-3 bg-green-50 border-green-200">
              <p className="text-sm font-mono">Given the financial data below, identify potential investment opportunities, considering risk tolerance and expected returns.</p>
            </div>
            <div className="mt-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span>Success Rate</span>
                <span>91.0%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div className="bg-green-500 h-2.5 rounded-full" style={{ width: '91%' }}></div>
              </div>
              <div className="flex justify-between text-sm">
                <span>Avg Response Time</span>
                <span>1.5s</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div className="bg-green-500 h-2.5 rounded-full" style={{ width: '50%' }}></div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Create Test Form */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="font-bold mb-4">Create New Test</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Test Name</label>
            <input type="text" className="form-input rounded-md w-full border-gray-300" placeholder="E.g., Prompt Optimization" />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Test Type</label>
            <select className="form-select rounded-md w-full border-gray-300">
              <option>Prompt Comparison</option>
              <option>Model Comparison</option>
              <option>Parameter Tuning</option>
              <option>Knowledge Source Comparison</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Variants</label>
            <div className="space-y-2">
              <div className="border rounded-lg p-3">
                <h4 className="font-semibold mb-2">Variant A (Baseline)</h4>
                <textarea className="form-textarea rounded-md w-full border-gray-300" rows="3" placeholder="Enter baseline prompt or configuration"></textarea>
              </div>
              
              <div className="border rounded-lg p-3">
                <h4 className="font-semibold mb-2">Variant B</h4>
                <textarea className="form-textarea rounded-md w-full border-gray-300" rows="3" placeholder="Enter test prompt or configuration"></textarea>
              </div>
              
              <button className="text-indigo-600 hover:text-indigo-800 text-sm">
                + Add Another Variant
              </button>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Metrics to Track</label>
            <div className="space-y-2">
              <div className="flex items-center">
                <input type="checkbox" checked className="mr-2" />
                <span>Success Rate</span>
              </div>
              <div className="flex items-center">
                <input type="checkbox" checked className="mr-2" />
                <span>Response Time</span>
              </div>
              <div className="flex items-center">
                <input type="checkbox" className="mr-2" />
                <span>User Satisfaction</span>
              </div>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Test Duration</label>
            <select className="form-select rounded-md w-full border-gray-300">
              <option>1 day</option>
              <option>3 days</option>
              <option>7 days</option>
              <option>14 days</option>
              <option>30 days</option>
            </select>
          </div>
          
          <div className="flex space-x-3">
            <button className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
              Start Test
            </button>
            <button className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">
              Save Draft
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const SettingsPanel = ({ data }) => {
  if (!data) return <div>Loading...</div>;
  
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">System Settings</h2>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
            Save Changes
          </button>
          <button className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">
            Reset to Defaults
          </button>
        </div>
      </div>

      {/* Settings Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b">
          <nav className="flex">
            <button className="px-6 py-3 font-medium border-b-2 border-indigo-600 text-indigo-600">
              General
            </button>
            <button className="px-6 py-3 font-medium text-gray-500 hover:text-gray-700">
              Performance
            </button>
            <button className="px-6 py-3 font-medium text-gray-500 hover:text-gray-700">
              Security
            </button>
            <button className="px-6 py-3 font-medium text-gray-500 hover:text-gray-700">
              Backup
            </button>
            <button className="px-6 py-3 font-medium text-gray-500 hover:text-gray-700">
              Integration
            </button>
          </nav>
        </div>
        
        {/* General Settings */}
        <div className="p-4">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">System Name</label>
              <input type="text" className="form-input rounded-md w-full border-gray-300" defaultValue="ABrain Production" />
              <p className="text-xs text-gray-500 mt-1">Displayed in emails, reports, and notifications.</p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Timezone</label>
              <select className="form-select rounded-md w-full border-gray-300">
                <option>UTC (Coordinated Universal Time)</option>
                <option>America/New_York (Eastern Time)</option>
                <option>America/Chicago (Central Time)</option>
                <option>America/Denver (Mountain Time)</option>
                <option>America/Los_Angeles (Pacific Time)</option>
                <option>Europe/London (Greenwich Mean Time)</option>
                <option>Europe/Berlin (Central European Time)</option>
                <option>Asia/Tokyo (Japan Standard Time)</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">Used for reporting and scheduling tasks.</p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Default Language</label>
              <select className="form-select rounded-md w-full border-gray-300">
                <option>English (en-US)</option>
                <option>German (de-DE)</option>
                <option>French (fr-FR)</option>
                <option>Spanish (es-ES)</option>
                <option>Japanese (ja-JP)</option>
                <option>Chinese (zh-CN)</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Log Level</label>
              <select className="form-select rounded-md w-full border-gray-300">
                <option>ERROR - Only errors and critical issues</option>
                <option>WARNING - Warnings and errors</option>
                <option selected>INFO - General information plus warnings and errors</option>
                <option>DEBUG - Detailed debug information</option>
                <option>TRACE - Extremely verbose debugging</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">Higher levels produce more detailed logs but affect performance.</p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Log Retention</label>
              <select className="form-select rounded-md w-full border-gray-300">
                <option>7 days</option>
                <option>14 days</option>
                <option>30 days</option>
                <option>90 days</option>
                <option>365 days</option>
              </select>
            </div>
            
            <div className="pt-4 border-t">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium">Automatic Updates</h4>
                  <p className="text-sm text-gray-500">Receive and install updates automatically</p>
                </div>
                <div className="relative inline-block w-12 h-6 border rounded-full">
                  <input type="checkbox" className="sr-only" defaultChecked />
                  <span className="block absolute left-1 top-1 bg-indigo-600 w-4 h-4 rounded-full transition-transform transform translate-x-6"></span>
                </div>
              </div>
            </div>
            
            <div className="pt-2">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium">Usage Analytics</h4>
                  <p className="text-sm text-gray-500">Share anonymous usage data to improve the system</p>
                </div>
                <div className="relative inline-block w-12 h-6 border rounded-full">
                  <input type="checkbox" className="sr-only" defaultChecked />
                  <span className="block absolute left-1 top-1 bg-indigo-600 w-4 h-4 rounded-full transition-transform transform translate-x-6"></span>
                </div>
              </div>
            </div>
            
            <div className="pt-2">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium">Email Notifications</h4>
                  <p className="text-sm text-gray-500">Receive system alerts via email</p>
                </div>
                <div className="relative inline-block w-12 h-6 border rounded-full">
                  <input type="checkbox" className="sr-only" defaultChecked />
                  <span className="block absolute left-1 top-1 bg-indigo-600 w-4 h-4 rounded-full transition-transform transform translate-x-6"></span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const LogsPanel = ({ data }) => {
  if (!data) return <div>Loading...</div>;
  
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">Logs & Alerts</h2>
        <div className="flex items-center space-x-3">
          <select className="form-select rounded-md border-gray-300">
            <option>All Levels</option>
            <option>ERROR</option>
            <option>WARNING</option>
            <option>INFO</option>
            <option>DEBUG</option>
          </select>
          <button className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
            Export Logs
          </button>
        </div>
      </div>

      {/* Log Viewer */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-bold">System Logs</h3>
          <div className="flex items-center space-x-2">
            <input type="text" className="form-input rounded-md border-gray-300" placeholder="Search logs..." />
            <button className="px-3 py-2 bg-gray-100 rounded-md">
              <Search size={18} />
            </button>
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="p-2 text-left">Timestamp</th>
                <th className="p-2 text-left">Level</th>
                <th className="p-2 text-left">Message</th>
                <th className="p-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.logs.map((log, index) => (
                <tr key={index} className="border-t">
                  <td className="p-2 text-sm">{new Date(log.timestamp).toLocaleString()}</td>
                  <td className="p-2">
                    <span className={`px-2 py-1 rounded text-xs ${
                      log.level === 'ERROR' ? 'bg-red-100 text-red-800' : 
                      log.level === 'WARNING' ? 'bg-yellow-100 text-yellow-800' : 
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {log.level}
                    </span>
                  </td>
                  <td className="p-2">{log.message}</td>
                  <td className="p-2">
                    <button className="px-2 py-1 bg-indigo-100 text-indigo-700 rounded text-xs">
                      Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        <div className="flex justify-between items-center mt-4">
          <div className="text-sm text-gray-500">
            Showing 4 of 1,284 logs
          </div>
          <div className="flex space-x-2">
            <button className="px-3 py-1 bg-gray-100 rounded-md text-sm">Previous</button>
            <button className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-md text-sm">1</button>
            <button className="px-3 py-1 bg-gray-100 rounded-md text-sm">2</button>
            <button className="px-3 py-1 bg-gray-100 rounded-md text-sm">3</button>
            <button className="px-3 py-1 bg-gray-100 rounded-md text-sm">Next</button>
          </div>
        </div>
      </div>
      
      {/* Alert Configuration */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="font-bold mb-4">Alert Configuration</h3>
        <div className="space-y-4">
          <div className="border rounded-lg p-4">
            <div className="flex items-2">{task.id}</td>
                    <td className="p-2">{task.type}</td>
                    <td className="p-2">{task.agent}</td>
                    <td className="p-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        task.status === 'running' ? 'bg-yellow-100 text-yellow-800' : 
                        task.status === 'completed' ? 'bg-green-100 text-green-800' : 
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {task.status === 'running' ? 'Running' : 
                         task.status === 'completed' ? 'Completed' : 'Queued'}
                      </span>
                    </td>
                    <td className="p-2">{task.duration}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="font-bold mb-4">System Components</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="bg-gray-50">
                  <th className="p-2 text-left">Component</th>
                  <th className="p-2 text-left">Status</th>
                  <th className="p-2 text-left">Version</th>
                  <th className="p-2 text-left">Last Updated</th>
                </tr>
              </thead>
              <tbody>
                {data.systemComponents.map((component, index) => (
                  <tr key={index} className="border-t">
                    <td className="p-2">{component.name}</td>
                    <td className="p-2">
                      <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">
                        {component.status === 'online' ? 'Online' : 'Offline'}
                      </span>
                    </td>
                    <td className="p-2">{component.version}</td>
                    <td className="p-2">{component.lastUpdated}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* System Configuration */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="font-bold mb-4">System Configuration</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Maximum Concurrent Tasks</label>
              <div className="flex items-center">
                <input type="number" className="form-input rounded-md w-24 border-gray-300" defaultValue="10" />
                <button className="ml-2 px-3 py-1 bg-indigo-100 text-indigo-700 rounded text-sm">Update</button>
              </div>
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Task Timeout (seconds)</label>
              <div className="flex items-center">
                <input type="number" className="form-input rounded-md w-24 border-gray-300" defaultValue="300" />
                <button className="ml-2 px-3 py-1 bg-indigo-100 text-indigo-700 rounded text-sm">Update</button>
              </div>
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Logging Level</label>
              <div className="flex items-center">
                <select className="form-select rounded-md w-36 border-gray-300">
                  <option>INFO</option>
                  <option>DEBUG</option>
                  <option>WARNING</option>
                  <option>ERROR</option>
                </select>
                <button className="ml-2 px-3 py-1 bg-indigo-100 text-indigo-700 rounded text-sm">Update</button>
              </div>
            </div>
          </div>
          <div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Cache Size (MB)</label>
              <div className="flex items-center">
                <input type="number" className="form-input rounded-md w-24 border-gray-300" defaultValue="1024" />
                <button className="ml-2 px-3 py-1 bg-indigo-100 text-indigo-700 rounded text-sm">Update</button>
              </div>
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Monitoring Interval (seconds)</label>
              <div className="flex items-center">
                <input type="number" className="form-input rounded-md w-24 border-gray-300" defaultValue="60" />
                <button className="ml-2 px-3 py-1 bg-indigo-100 text-indigo-700 rounded text-sm">Update</button>
              </div>
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Backup Interval (seconds)</label>
              <div className="flex items-center">
                <input type="number" className="form-input rounded-md w-24 border-gray-300" defaultValue="86400" />
                <button className="ml-2 px-3 py-1 bg-indigo-100 text-indigo-700 rounded text-sm">Update</button>
              </div>
            </div>
          </div>
        </div>

        <div className="flex space-x-3 mt-4">
          <button className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">Save All Changes</button>
          <button className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300">Reset to Defaults</button>
          <button className="px-4 py-2 bg-red-100 text-red-700 rounded-md hover:bg-red-200">Clear Cache</button>
        </div>
      </div>
    </div>
  );
};

const AgentsPanel = ({ data }) => {
  const [selectedTab, setSelectedTab] = useState('active');
  
  if (!data) return <div>Loading...</div>;
  
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">Agent Management</h2>
        <button className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 flex items-center space-x-2">
          <span>Create New Agent</span>
        </button>
      </div>

      <div className="bg-white rounded-lg shadow">
        <nav className="flex border-b">
          <button 
            className={`px-6 py-3 font-medium ${selectedTab === 'active' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-gray-500 hover:text-gray-700'}`}
            onClick={() => setSelectedTab('active')}
          >
            Active Agents
          </button>
          <button 
            className={`px-6 py-3 font-medium ${selectedTab === 'custom' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-gray-500 hover:text-gray-700'}`}
            onClick={() => setSelectedTab('custom')}
          >
            Custom Agents
          </button>
          <button 
            className={`px-6 py-3 font-medium ${selectedTab === 'templates' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-gray-500 hover:text-gray-700'}`}
            onClick={() => setSelectedTab('templates')}
          >
            Agent Templates
          </button>
          <button 
            className={`px-6 py-3 font-medium ${selectedTab === 'stats' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-gray-500 hover:text-gray-700'}`}
            onClick={() => setSelectedTab('stats')}
          >
            Performance Stats
          </button>
        </nav>

        {selectedTab === 'active' && (
          <div className="p-4">
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="p-2 text-left">Name</th>
                    <th className="p-2 text-left">Domain</th>
                    <th className="p-2 text-left">Status</th>
                    <th className="p-2 text-left">Tasks</th>
                    <th className="p-2 text-left">Success Rate</th>
                    <th className="p-2 text-left">Avg Response</th>
                    <th className="p-2 text-left">Last Active</th>
                    <th className="p-2 text-left">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.agents.map((agent, index) => (
                    <tr key={index} className="border-t">
                      <td className="p-2 font-medium">{agent.name}</td>
                      <td className="p-2">{agent.domain}</td>
                      <td className="p-2">
                        <span className={`px-2 py-1 rounded text-xs ${
                          agent.status === 'active' ? 'bg-green-100 text-green-800' : 
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {agent.status === 'active' ? 'Active' : 'Idle'}
                        </span>
                      </td>
                      <td className="p-2">{agent.tasks.toLocaleString()}</td>
                      <td className="p-2">{agent.successRate}%</td>
                      <td className="p-2">{agent.avgResponse}s</td>
                      <td className="p-2">{agent.lastActive}</td>
                      <td className="p-2">
                        <div className="flex space-x-2">
                          <button className="p-1 text-gray-500 hover:text-indigo-600">Edit</button>
                          <button className="p-1 text-gray-500 hover:text-red-600">Disable</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {selectedTab === 'custom' && (
          <div className="p-4">
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="p-2 text-left">Name</th>
                    <th className="p-2 text-left">Domain</th>
                    <th className="p-2 text-left">Created</th>
                    <th className="p-2 text-left">Status</th>
                    <th className="p-2 text-left">Base Model</th>
                    <th className="p-2 text-left">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-t">
                    <td className="p-2 font-medium">Healthcare Agent</td>
                    <td className="p-2">Healthcare</td>
                    <td className="p-2">3 days ago</td>
                    <td className="p-2"><span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">Active</span></td>
                    <td className="p-2">gpt-4</td>
                    <td className="p-2">
                      <div className="flex space-x-2">
                        <button className="p-1 text-gray-500 hover:text-indigo-600">Edit</button>
                        <button className="p-1 text-gray-500 hover:text-red-600">Delete</button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}

        {selectedTab === 'templates' && (
          <div className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="border rounded-lg p-4">
                <h3 className="font-bold">Finance Specialist</h3>
                <p className="text-sm text-gray-600 mt-2">Specialized in financial analysis, investment strategies, and market trends.</p>
                <div className="mt-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Base Model</span>
                    <span>gpt-4</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Knowledge Base</span>
                    <span>Finance</span>
                  </div>
                </div>
                <button className="mt-4 w-full py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">Use Template</button>
              </div>

              <div className="border rounded-lg p-4">
                <h3 className="font-bold">Tech Specialist</h3>
                <p className="text-sm text-gray-600 mt-2">Specialized in programming, system architecture, and technical troubleshooting.</p>
                <div className="mt-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Base Model</span>
                    <span>claude-3</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Knowledge Base</span>
                    <span>Technology</span>
                  </div>
                </div>
                <button className="mt-4 w-full py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">Use Template</button>
              </div>
              
              <div className="border rounded-lg p-4">
                <h3 className="font-bold">Marketing Specialist</h3>
                <p className="text-sm text-gray-600 mt-2">Specialized in digital marketing, brand development, and market research.</p>
                <div className="mt-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Base Model</span>
                    <span>llama-3</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Knowledge Base</span>
                    <span>Marketing</span>
                  </div>
                </div>
                <button className="mt-4 w-full py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">Use Template</button>
              </div>
            </div>
          </div>
        )}

        {selectedTab === 'stats' && (
          <div className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="border rounded-lg p-4">
                <h3 className="font-bold">Agent Success Rate</h3>
                <div className="mt-4 space-y-4">
                  {data.agents.map((agent, index) => (
                    <div key={index}>
                      <div className="flex justify-between mb-1">
                        <span>{agent.name}</span>
                        <span>{agent.successRate}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div className={`${
                          agent.successRate > 90 ? 'bg-green-500' : 
                          agent.successRate > 80 ? 'bg-yellow-500' : 'bg-red-500'
                        } h-2.5 rounded-full`} style={{ width: `${agent.successRate}%` }}></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              
              <div className="border rounded-lg p-4">
                <h3 className="font-bold">Average Response Time</h3>
                <div className="mt-4 space-y-4">
                  {data.agents.map((agent, index) => (
                    <div key={index}>
                      <div className="flex justify-between mb-1">
                        <span>{agent.name}</span>
                        <span>{agent.avgResponse}s</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div className={`${
                          agent.avgResponse < 1.0 ? 'bg-green-500' : 
                          agent.avgResponse < 2.0 ? 'bg-yellow-500' : 'bg-red-500'
                        } h-2.5 rounded-full`} style={{ width: `${Math.min(100, agent.avgResponse * 33)}%` }}></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const ModelsPanel = ({ data }) => {
  if (!data) return <div>Loading...</div>;
  
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">Model Management</h2>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200">Import Model</button>
          <button className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">Add New Model</button>
        </div>
      </div>

      {/* Model List */}
      <div className="bg-white p-4 rounded-lg shadow overflow-hidden">
        <h3 className="font-bold mb-4">Available Models</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="p-2 text-left">Name</th>
                <th className="p-2 text-left">Type</th>
                <th className="p-2 text-left">Source</th>
                <th className="p-2 text-left">Version</th>
                <th className="p-2 text-left">Status</th>
                <th className="p-2 text-left">Usage</th>
                <th className="p-2 text-left">Avg Latency</th>
                <th className="p-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.models.map((model, index) => (
                <tr key={index} className="border-t">
                  <td className="p-2 font-medium">{model.name}</td>
                  <td className="p-2">{model.type}</td>
                  <td className="p-2">{model.source}</td>
                  <td className="p-2">{model.version}</td>
                  <td className="p-2">
                    <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">
                      {model.status === 'active' ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="p-2">{model.requests.toLocaleString()} requests</td>
                  <td className="p-2">{model.latency}s</td>
                  <td className="p-2">
                    <div className="flex space-x-2">
                      <button className="p-1 text-gray-500 hover:text-indigo-600">Configure</button>
                      <button className="p-1 text-gray-500 hover:text-red-600">Disable</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      {/* Model Performance */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="font-bold mb-4">Model Performance</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="border rounded-lg p-4">
            <h4 className="font-bold">Response Time Comparison</h4>
            <div className="mt-4 h-64 flex items-end space-x-4 pb-6 px-2">
              {data.models.map((model, index) => (
                <div key={index} className="flex flex-col items-center flex-grow">
                  <div 
                    className={`w-full bg-indigo-600 rounded-t-md ${
                      model.source === 'OpenAI' ? 'bg-green-500' : 
                      model.source === 'Anthropic' ? 'bg-blue-500' : 'bg-purple-500'
                    }`} 
                    style={{ height: `${Math.max(5, 100 - (model.latency * 30))}%` }}
                  ></div>
                  <div className="text-xs mt-2 truncate w-full text-center">{model.name}</div>
                  <div className="text-xs text-gray-500">{model.latency}s</div>
                </div>
              ))}
            </div>
          </div>
          
          <div className="border rounded-lg p-4">
            <h4 className="font-bold">Model Usage</h4>
            <div className="mt-4 h-64 flex items-center justify-center">
              <div className="relative w-48 h-48">
                {/* This would be a pie chart in a real implementation */}
                <div className="absolute inset-0 border-4 border-green-500 rounded-full" style={{ clipPath: 'polygon(50% 50%, 0 0, 0 50%, 0 100%, 50% 100%)' }}></div>
                <div className="absolute inset-0 border-4 border-blue-500 rounded-full" style={{ clipPath: 'polygon(50% 50%, 0 0, 50% 0, 100% 0, 100% 50%)' }}></div>
                <div className="absolute inset-0 border-4 border-purple-500 rounded-full" style={{ clipPath: 'polygon(50% 50%, 100% 50%, 100% 100%, 50% 100%)' }}></div>
                <div className="absolute inset-0 flex items-center justify-center font-bold text-lg">
                  {data.models.reduce((total, model) => total + model.requests, 0).toLocaleString()}
                </div>
              </div>
              <div className="ml-8 space-y-4">
                {data.models.map((model, index) => (
                  <div key={index} className="flex items-center">
                    <div className={`w-4 h-4 rounded-full ${
                      model.source === 'OpenAI' ? 'bg-green-500' : 
                      model.source === 'Anthropic' ? 'bg-blue-500' : 'bg-purple-500'
                    }`}></div>
                    <span className="ml-2">{model.name}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Model Settings */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="font-bold mb-4">Global Model Settings</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Default Model</label>
              <div className="flex items-center">
                <select className="form-select rounded-md w-48 border-gray-300">
                  {data.models.map((model, index) => (
                    <option key={index}>{model.name}</option>
                  ))}
                </select>
                <button className="ml-2 px-3 py-1 bg-indigo-100 text-indigo-700 rounded text-sm">Update</button>
              </div>
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">API Key Management</label>
              <div className="flex items-center">
                <button className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded text-sm">Manage API Keys</button>
              </div>
            </div>
          </div>
          <div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Model Cache TTL (seconds)</label>
              <div className="flex items-center">
                <input type="number" className="form-input rounded-md w-24 border-gray-300" defaultValue="3600" />
                <button className="ml-2 px-3 py-1 bg-indigo-100 text-indigo-700 rounded text-sm">Update</button>
              </div>
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Maximum Tokens</label>
              <div className="flex items-center">
                <input type="number" className="form-input rounded-md w-24 border-gray-300" defaultValue="4096" />
                <button className="ml-2 px-3 py-1 bg-indigo-100 text-indigo-700 rounded text-sm">Update</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const KnowledgePanel = ({ data }) => {
  if (!data) return <div>Loading...</div>;
  
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">Knowledge Base Management</h2>
        <div className="flex space-x-3">
          <button className="px-4 py-2 bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200 flex items-center">
            <UploadCloud size={18} className="mr-2" />
            Import Documents
          </button>
          <button className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 flex items-center">
            <Database size={18} className="mr-2" />
            New Knowledge Base
          </button>
        </div>
      </div>

      {/* Knowledge Bases */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="font-bold mb-4">Knowledge Bases</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="p-2 text-left">Name</th>
                <th className="p-2 text-left">Documents</th>
                <th className="p-2 text-left">Size</th>
                <th className="p-2 text-left">Last Updated</th>
                <th className="p-2 text-left">Status</th>
                <th className="p-2 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.knowledgeBases.map((kb, index) => (
                <tr key={index} className="border-t">
                  <td className="p-2 font-medium">{kb.name}</td>
                  <td className="p-2">{kb.documents.toLocaleString()}</td>
                  <td className="p-2">{kb.size}</td>
                  <td className="p-2">{kb.lastUpdated}</td>
                  <td className="p-2">
                    <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs">
                      {kb.status === 'active' ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="p-2">
                    <div className="flex space-x-2">
                      <button className="p-1 text-gray-500 hover:text-indigo-600">Browse</button>
                      <button className="p-1 text-gray-500 hover:text-blue-600">Update</button>
                      <button className="p-1 text-gray-500 hover:text-red-600">Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      {/* Document Upload */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="font-bold mb-4">Document Upload</h3>
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
          <div className="mx-auto w-12 h-12 rounded-full bg-indigo-100 flex items-center justify-center mb-3">
            <UploadCloud size={24} className="text-indigo-600" />
          </div>
          <h4 className="font-semibold mb-2">Drag and drop files here</h4>
          <p className="text-gray-500 text-sm mb-4">or click to browse files</p>
          <div>
            <label className="cursor-pointer px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
              Browse Files
              <input type="file" multiple className="hidden" />
            </label>
          </div>
          <p className="text-gray-500 text-xs mt-4">Supported formats: PDF, DOCX, TXT, CSV, MD, HTML</p>
        </div>
      </div>
      
      {/* Knowledge Base Metrics */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="font-bold mb-4">Knowledge Base Metrics</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="border rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold">Total Documents</h4>
              <FileText size={18} className="text-indigo-600" />
            </div>
            <p className="text-2xl font-bold">
              {data.knowledgeBases.reduce((total, kb) => total + kb.documents, 0).toLocaleString()}
            </p>
          </div>
          
          <div className="border rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold">Total Storage</h4>
              <HardDrive size={18} className="text-indigo-600" />
            </div>
            <p className="text-2xl font-bold">
              {data.knowledgeBases.reduce((total, kb) => {
                const size = parseFloat(kb.size.replace(' GB', ''));
                return total + size;
              }, 0).toFixed(1)} GB
            </p>
          </div>
          
          <div className="border rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold">Last Update</h4>
              <RefreshCw size={18} className="text-indigo-600" />
            </div>
            <p className="text-xl font-bold">
              {data.knowledgeBases
                .sort((a, b) => {
                  // Sort by most recent
                  const getHours = (str) => parseInt(str.split(' ')[0]);
                  if (str.includes('hour')) return getHours(a.lastUpdated) - getHours(b.lastUpdated);
                  if (str.includes('day')) return getHours(a.lastUpdated) * 24 - getHours(b.lastUpdated) * 24;
                  return 0;
                })[0].lastUpdated}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

const MonitoringPanel = ({ data }) => {
  if (!data) return <div>Loading...</div>;
  
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">System Monitoring</h2>
        <div className="flex space-x-3">
          <select className="form-select rounded-md border-gray-300">
            <option>Last 1 hour</option>
            <option>Last 24 hours</option>
            <option>Last 7 days</option>
            <option>Last 30 days</option>
          </select>
          <button className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
            Export Data
          </button>
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center justify-between">
            <h3 className="text-gray-500">CPU Usage</h3>
            <Cpu size={18} className="text-indigo-600" />
          </div>
          <p className="text-2xl font-bold mt-2">{data.cpu_usage}%</p>
          <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2">
            <div className="bg-green-500 h-2.5 rounded-full" style={{ width: `${data.cpu_usage}%` }}></div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center justify-between">
            <h3 className="text-gray-500">Memory Usage</h3>
            <Server size={18} className="text-indigo-600" />
          </div>
          <p className="text-2xl font-bold mt-2">{data.memory_usage}%</p>
          <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2">
            <div className="bg-yellow-500 h-2.5 rounded-full" style={{ width: `${data.memory_usage}%` }}></div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center justify-between">
            <h3 className="text-gray-500">Active Agents</h3>
            <Users size={18} className="text-indigo-600" />
          </div>
          <p className="text-2xl font-bold mt-2">{data.active_agents}</p>
          <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2">
            <div className="bg-blue-500 h-2.5 rounded-full" style={{ width: `${data.active_agents * 20}%` }}></div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center justify-between">
            <h3 className="text-gray-500">Avg Response Time</h3>
            <Network size={18} className="text-indigo-600" />
          </div>
          <p className="text-2xl font-bold mt-2">{data.avg_response_time}s</p>
          <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2">
            <div className="bg-green-500 h-2.5 rounded-full" style={{ width: `${data.avg_response_time * 50}%` }}></div>
          </div>
        </div>
      </div>
      
      {/* Time Series Charts (Placeholder) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="font-bold mb-4">CPU & Memory Usage Over Time</h3>
          <div className="h-64 border rounded flex items-center justify-center text-gray-500">
            Time series chart would be displayed here
          </div>
        </div>
        
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="font-bold mb-4">Response Time & Request Volume</h3>
          <div className="h-64 border rounded flex items-center justify-center text-gray-500">
            Time series chart would be displayed here
          </div>
        </div>
      </div>
      
      {/* Agent Performance */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="font-bold mb-4">Agent Performance</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="p-2 text-left">Agent</th>
                <th className="p-2 text-left">Response Time</th>
                <th className="p-2 text-left">Success Rate</th>
                <th className="p-2 text-left">Tasks Completed</th>
                <th className="p-2 text-left">Resource Usage</th>
              </tr>
            </thead>
            <tbody>
              {data.agents.map((agent, index) => (
                <tr key={index} className="border-t">
                  <td className="p-2 font-medium">{agent.name}</td>
                  <td className="p-2">{agent.avgResponse}s</td>
                  <td className="p-2">{agent.successRate}%</td>
                  <td className="p
