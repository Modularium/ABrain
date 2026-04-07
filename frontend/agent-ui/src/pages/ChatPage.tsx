import { useRef, useState, useEffect } from 'react'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  status?: 'sending' | 'sent' | 'error'
  metadata?: {
    agent?: string
    taskType?: string
    executionTime?: number
    tokens?: number
  }
}

interface ChatSession {
  id: string
  title: string
  createdAt: Date
  messageCount: number
}

const taskTypes = [
  { value: 'default', label: 'General Chat', icon: '💬', description: 'General purpose conversation' },
  { value: 'docker', label: 'Docker Operations', icon: '🐳', description: 'Container management and deployment' },
  { value: 'container_ops', label: 'Container Management', icon: '📦', description: 'Advanced container operations' },
  { value: 'analysis', label: 'Data Analysis', icon: '📊', description: 'Data processing and analytics' },
  { value: 'coding', label: 'Code Generation', icon: '💻', description: 'Programming assistance and code review' },
  { value: 'security', label: 'Security Scan', icon: '🔒', description: 'Security analysis and vulnerability assessment' },
]

const mockSessions: ChatSession[] = [
  { id: '1', title: 'Docker Deployment Setup', createdAt: new Date(Date.now() - 86400000), messageCount: 12 },
  { id: '2', title: 'Code Review Session', createdAt: new Date(Date.now() - 172800000), messageCount: 8 },
  { id: '3', title: 'Data Pipeline Configuration', createdAt: new Date(Date.now() - 259200000), messageCount: 15 },
]

export default function EnhancedChatPage() {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'system',
      content: 'Welcome to ABrain. I\'m your AI assistant and can help with planning, development, analysis and other task types from the tabs above.',
      timestamp: new Date(Date.now() - 60000)
    }
  ])
  const [taskType, setTaskType] = useState('default')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [sessions, setSessions] = useState<ChatSession[]>(mockSessions)
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 120)}px`
    }
  }, [input])

  const generateResponse = (userMessage: string, type: string): string => {
    const responses = {
      docker: `I'll help you with Docker operations. For "${userMessage}", I recommend checking your container configuration and ensuring all dependencies are properly defined in your Dockerfile.`,
      coding: `Here's my analysis of your code request: "${userMessage}". I suggest implementing best practices for error handling and adding proper type annotations.`,
      analysis: `Based on your data analysis request: "${userMessage}", I recommend starting with data validation and exploratory analysis to understand the dataset structure.`,
      security: `For your security query: "${userMessage}", I'll perform a comprehensive scan and check for common vulnerabilities like SQL injection, XSS, and authentication issues.`,
      default: `I understand you're asking about "${userMessage}". Let me provide you with a comprehensive response based on the context and available information.`
    }
    
    return responses[type as keyof typeof responses] || responses.default
  }

  const sendMessage = async () => {
    if (!input.trim()) return
    
    const userMessage: Message = { 
      id: Date.now().toString(),
      role: 'user', 
      content: input.trim(),
      timestamp: new Date(),
      status: 'sending'
    }
    
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)
    setError('')
    setIsTyping(true)
    
    try {
      // Update message status to sent
      setMessages(prev => 
        prev.map(msg => 
          msg.id === userMessage.id 
            ? { ...msg, status: 'sent' } 
            : msg
        )
      )

      // Simulate API call with realistic delay
      await new Promise(resolve => setTimeout(resolve, 1500 + Math.random() * 1000))
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: generateResponse(userMessage.content, taskType),
        timestamp: new Date(),
        metadata: {
          agent: taskTypes.find(t => t.value === taskType)?.label || 'General Assistant',
          taskType,
          executionTime: Math.round(Math.random() * 2000 + 500),
          tokens: Math.round(Math.random() * 150 + 50)
        }
      }
      
      setMessages(prev => [...prev, assistantMessage])
    } catch (err) {
      setError('Failed to send message. Please try again.')
      setMessages(prev => 
        prev.map(msg => 
          msg.id === userMessage.id 
            ? { ...msg, status: 'error' } 
            : msg
        )
      )
    } finally {
      setLoading(false)
      setIsTyping(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handleFileUpload = () => {
    fileInputRef.current?.click()
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const newSession = () => {
    const session: ChatSession = {
      id: Date.now().toString(),
      title: `New Session ${sessions.length + 1}`,
      createdAt: new Date(),
      messageCount: 0
    }
    setSessions(prev => [session, ...prev])
    setCurrentSessionId(session.id)
    setMessages([{
      id: '1',
      role: 'system',
      content: 'New session started. How can I help you today?',
      timestamp: new Date()
    }])
  }

  const currentTaskType = taskTypes.find(t => t.value === taskType)

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      {/* Session Sidebar */}
      <div className={`${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} sm:translate-x-0 w-80 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 fixed sm:static h-full z-30 transition-transform duration-300`}>
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={newSession}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Session
          </button>
        </div>
        
        <div className="p-4">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">Recent Sessions</h3>
          <div className="space-y-2">
            {sessions.map(session => (
              <button
                key={session.id}
                onClick={() => setCurrentSessionId(session.id)}
                className={`w-full text-left p-3 rounded-lg transition-colors ${
                  currentSessionId === session.id
                    ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-700'
                }`}
              >
                <div className="font-medium text-gray-900 dark:text-white text-sm truncate">
                  {session.title}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center justify-between mt-1">
                  <span>{session.messageCount} messages</span>
                  <span>{formatTime(session.createdAt)}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                className="sm:hidden p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                onClick={() => setSidebarOpen(!sidebarOpen)}
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center">
                  <span className="text-white text-xl">{currentTaskType?.icon}</span>
                </div>
                <div>
                  <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {currentTaskType?.label}
                  </h1>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {currentTaskType?.description}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 px-3 py-1 bg-green-100 dark:bg-green-900 rounded-full">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm text-green-700 dark:text-green-300 font-medium">Online</span>
              </div>
            </div>
          </div>

          {/* Task Type Tabs */}
          <div className="mt-4 flex overflow-x-auto space-x-1 pb-2">
            {taskTypes.map((type) => (
              <button
                key={type.value}
                onClick={() => setTaskType(type.value)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                  taskType === type.value
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-700'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                <span>{type.icon}</span>
                <span>{type.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {messages.map((message) => (
            <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`flex gap-3 max-w-4xl ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                {/* Avatar */}
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  message.role === 'user' 
                    ? 'bg-gradient-to-br from-purple-500 to-pink-600' 
                    : message.role === 'system'
                    ? 'bg-gradient-to-br from-gray-500 to-gray-600'
                    : 'bg-gradient-to-br from-blue-500 to-indigo-600'
                }`}>
                  <span className="text-white text-sm">
                    {message.role === 'user' ? '👤' : message.role === 'system' ? '⚙️' : '🤖'}
                  </span>
                </div>
                
                {/* Message Bubble */}
                <div className={`group ${message.role === 'user' ? 'text-right' : 'text-left'}`}>
                  <div className={`inline-block px-4 py-3 rounded-2xl shadow-sm max-w-2xl ${
                    message.role === 'user'
                      ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white'
                      : message.role === 'system'
                      ? 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600'
                      : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-800 dark:text-gray-200'
                  }`}>
                    <p className="whitespace-pre-wrap break-words">{message.content}</p>
                    
                    {/* Message Status */}
                    {message.role === 'user' && message.status && (
                      <div className="flex items-center justify-end mt-2">
                        {message.status === 'sending' && (
                          <div className="flex items-center gap-1 text-blue-200">
                            <div className="w-2 h-2 bg-blue-200 rounded-full animate-bounce"></div>
                            <span className="text-xs">Sending...</span>
                          </div>
                        )}
                        {message.status === 'sent' && (
                          <span className="text-blue-200 text-xs">✓</span>
                        )}
                        {message.status === 'error' && (
                          <span className="text-red-200 text-xs">Failed</span>
                        )}
                      </div>
                    )}
                  </div>
                  
                  {/* Message Metadata */}
                  <div className={`flex items-center gap-3 mt-2 text-xs text-gray-500 dark:text-gray-400 ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}>
                    <span>{formatTime(message.timestamp)}</span>
                    {message.metadata && (
                      <>
                        <span>•</span>
                        <span>{message.metadata.agent}</span>
                        {message.metadata.executionTime && (
                          <>
                            <span>•</span>
                            <span>{message.metadata.executionTime}ms</span>
                          </>
                        )}
                        {message.metadata.tokens && (
                          <>
                            <span>•</span>
                            <span>{message.metadata.tokens} tokens</span>
                          </>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
          
          {/* Typing indicator */}
          {isTyping && (
            <div className="flex justify-start">
              <div className="flex gap-3 max-w-4xl">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center">
                  <span className="text-white text-sm">🤖</span>
                </div>
                <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl px-4 py-3 shadow-sm">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Error Display */}
        {error && (
          <div className="px-6 py-2">
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3 flex items-center gap-3">
              <span className="text-red-500">⚠️</span>
              <span className="text-red-700 dark:text-red-300 text-sm">{error}</span>
              <button 
                onClick={() => setError('')}
                className="ml-auto text-red-500 hover:text-red-700 dark:hover:text-red-300"
              >
                ✕
              </button>
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-6 py-4">
          <div className="flex items-end gap-3">
            {/* File Upload */}
            <button
              onClick={handleFileUpload}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title="Attach file"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
            </button>
            
            {/* Text Input */}
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                className="w-full px-4 py-3 pr-12 border border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:shadow-focus focus:border-transparent outline-none transition-all resize-none"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
                disabled={loading}
                rows={1}
                style={{ minHeight: '48px', maxHeight: '120px' }}
              />
              
              {/* Character count */}
              <div className="absolute bottom-2 right-3 text-xs text-gray-400">
                {input.length}/2000
              </div>
            </div>
            
            {/* Send Button */}
            <button
              className="px-6 py-3 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-xl font-medium hover:from-blue-600 hover:to-indigo-700 focus:outline-none focus:shadow-focus disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-blue-500/25 flex items-center gap-2"
              onClick={sendMessage}
              disabled={loading || !input.trim()}
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                  Send
                </>
              )}
            </button>
          </div>
          
          {/* Quick Actions */}
          <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
            <div className="flex items-center gap-2">
              <button className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 px-2 py-1 rounded">
                Clear Chat
              </button>
              <button className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 px-2 py-1 rounded">
                Export
              </button>
            </div>
            
            <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
              <span>Messages: {messages.length}</span>
              <span>•</span>
              <span>Model: {currentTaskType?.label}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept=".txt,.pdf,.doc,.docx,.csv,.json"
        onChange={(e) => {
          // Handle file upload
          console.log('File selected:', e.target.files?.[0])
        }}
      />

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-20 sm:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  )
}
