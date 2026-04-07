import { useState } from 'react'
import type { ReactNode } from 'react'

// Button Component
interface ButtonProps {
  children: ReactNode
  variant?: 'primary' | 'secondary' | 'danger' | 'success'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  loading?: boolean
  onClick?: () => void
  className?: string
}

export function Button({ 
  children, 
  variant = 'primary', 
  size = 'md', 
  disabled = false, 
  loading = false, 
  onClick, 
  className = '' 
}: ButtonProps) {
  const baseStyles = 'font-medium rounded-lg transition-all duration-200 focus:ring-2  disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2'
  
  const variants = {
    primary: 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white hover:from-blue-600 hover:to-indigo-700 focus:ring-blue-500 shadow-lg shadow-blue-500/25',
    secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200 focus:ring-gray-500 border border-gray-300',
    danger: 'bg-gradient-to-r from-red-500 to-red-600 text-white hover:from-red-600 hover:to-red-700 focus:ring-red-500 shadow-lg shadow-red-500/25',
    success: 'bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:from-green-600 hover:to-emerald-700 focus:ring-green-500 shadow-lg shadow-green-500/25'
  }
  
  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2',
    lg: 'px-6 py-3 text-lg'
  }

  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled || loading}
      onClick={onClick}
    >
      {loading && (
        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
      )}
      {children}
    </button>
  )
}

// Input Component
interface InputProps {
  label?: string
  placeholder?: string
  value: string
  onChange: (value: string) => void
  type?: 'text' | 'email' | 'password' | 'number'
  disabled?: boolean
  error?: string
  icon?: ReactNode
  className?: string
}

export function Input({ 
  label, 
  placeholder, 
  value, 
  onChange, 
  type = 'text', 
  disabled = false, 
  error, 
  icon, 
  className = '' 
}: InputProps) {
  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label}
        </label>
      )}
      <div className="relative">
        {icon && (
          <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
            {icon}
          </div>
        )}
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className={`w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:shadow-focus focus:border-transparent outline-none transition-all ${
            icon ? 'pl-10' : ''
          } ${error ? 'border-red-500 focus:ring-red-500' : ''} ${
            disabled ? 'bg-gray-50 cursor-not-allowed' : ''
          }`}
        />
      </div>
      {error && (
        <p className="mt-1 text-sm text-red-600">{error}</p>
      )}
    </div>
  )
}

// Card Component
interface CardProps {
  children: ReactNode
  title?: string
  subtitle?: string
  padding?: 'sm' | 'md' | 'lg'
  hover?: boolean
  className?: string
}

export function Card({ 
  children, 
  title, 
  subtitle, 
  padding = 'md', 
  hover = false, 
  className = '' 
}: CardProps) {
  const paddings = {
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8'
  }

  return (
    <div className={`bg-white rounded-xl border border-gray-200 ${paddings[padding]} ${
      hover ? 'hover:shadow-lg transition-shadow duration-200' : 'shadow-sm'
    } ${className}`}>
      {(title || subtitle) && (
        <div className="mb-4">
          {title && <h3 className="text-lg font-semibold text-gray-900">{title}</h3>}
          {subtitle && <p className="text-gray-600">{subtitle}</p>}
        </div>
      )}
      {children}
    </div>
  )
}

// Badge Component
interface BadgeProps {
  children: ReactNode
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info'
  size?: 'sm' | 'md'
  className?: string
}

export function Badge({ 
  children, 
  variant = 'default', 
  size = 'md', 
  className = '' 
}: BadgeProps) {
  const variants = {
    default: 'bg-gray-100 text-gray-800 border-gray-200',
    success: 'bg-green-100 text-green-800 border-green-200',
    warning: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    danger: 'bg-red-100 text-red-800 border-red-200',
    info: 'bg-blue-100 text-blue-800 border-blue-200'
  }
  
  const sizes = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1 text-sm'
  }

  return (
    <span className={`inline-flex items-center font-medium rounded-full border ${variants[variant]} ${sizes[size]} ${className}`}>
      {children}
    </span>
  )
}

// Modal Component
interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

export function Modal({ isOpen, onClose, title, children, size = 'md' }: ModalProps) {
  if (!isOpen) return null

  const sizes = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl'
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 transition-opacity" onClick={onClose}>
          <div className="absolute inset-0 bg-black opacity-50"></div>
        </div>

        <div className={`inline-block align-bottom bg-white rounded-xl text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle w-full ${sizes[size]}`}>
          {title && (
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
                <button
                  onClick={onClose}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          )}
          <div className="px-6 py-4">
            {children}
          </div>
        </div>
      </div>
    </div>
  )
}

// Loading Spinner Component
interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  color?: 'blue' | 'gray' | 'white'
  className?: string
}

export function LoadingSpinner({ size = 'md', color = 'blue', className = '' }: LoadingSpinnerProps) {
  const sizes = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8'
  }
  
  const colors = {
    blue: 'border-blue-500 border-t-transparent',
    gray: 'border-gray-500 border-t-transparent',
    white: 'border-white border-t-transparent'
  }

  return (
    <div className={`${sizes[size]} border-2 ${colors[color]} rounded-full animate-spin ${className}`}></div>
  )
}

// Progress Bar Component
interface ProgressBarProps {
  value: number
  max?: number
  color?: 'blue' | 'green' | 'yellow' | 'red'
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  className?: string
}

export function ProgressBar({ 
  value, 
  max = 100, 
  color = 'blue', 
  size = 'md', 
  showLabel = false, 
  className = '' 
}: ProgressBarProps) {
  const percentage = Math.min((value / max) * 100, 100)
  
  const colors = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500'
  }
  
  const sizes = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3'
  }

  return (
    <div className={className}>
      <div className={`w-full bg-gray-200 rounded-full ${sizes[size]}`}>
        <div 
          className={`${colors[color]} ${sizes[size]} rounded-full transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        ></div>
      </div>
      {showLabel && (
        <div className="flex justify-between text-sm text-gray-600 mt-1">
          <span>{value}</span>
          <span>{max}</span>
        </div>
      )}
    </div>
  )
}

// Demo Component
export default function UIComponentsDemo() {
  const [inputValue, setInputValue] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleLoadingTest = () => {
    setLoading(true)
    setTimeout(() => setLoading(false), 2000)
  }

  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">UI Components Library</h1>
          <p className="text-gray-600 text-lg">Modern, accessible and reusable components for ABrain</p>
        </div>

        {/* Buttons */}
        <Card title="Buttons" subtitle="Various button styles and states">
          <div className="flex flex-wrap gap-4">
            <Button variant="primary">Primary Button</Button>
            <Button variant="secondary">Secondary Button</Button>
            <Button variant="success">Success Button</Button>
            <Button variant="danger">Danger Button</Button>
            <Button variant="primary" size="sm">Small</Button>
            <Button variant="primary" size="lg">Large</Button>
            <Button variant="primary" disabled>Disabled</Button>
            <Button variant="primary" loading={loading} onClick={handleLoadingTest}>
              {loading ? 'Loading...' : 'Test Loading'}
            </Button>
          </div>
        </Card>

        {/* Inputs */}
        <Card title="Input Fields" subtitle="Form inputs with various configurations">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Basic Input"
              placeholder="Enter text..."
              value={inputValue}
              onChange={setInputValue}
            />
            <Input
              label="With Icon"
              placeholder="Search..."
              value=""
              onChange={() => {}}
              icon={
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              }
            />
            <Input
              label="Email Input"
              type="email"
              placeholder="user@example.com"
              value=""
              onChange={() => {}}
            />
            <Input
              label="Error State"
              placeholder="Invalid input"
              value=""
              onChange={() => {}}
              error="This field is required"
            />
          </div>
        </Card>

        {/* Badges */}
        <Card title="Badges" subtitle="Status indicators and labels">
          <div className="flex flex-wrap gap-3">
            <Badge variant="default">Default</Badge>
            <Badge variant="success">✅ Active</Badge>
            <Badge variant="warning">⚠️ Warning</Badge>
            <Badge variant="danger">❌ Error</Badge>
            <Badge variant="info">ℹ️ Info</Badge>
            <Badge variant="success" size="sm">Small Badge</Badge>
          </div>
        </Card>

        {/* Progress Bars */}
        <Card title="Progress Bars" subtitle="Visual progress indicators">
          <div className="space-y-4">
            <div>
              <p className="text-sm text-gray-600 mb-2">Success Rate: 85%</p>
              <ProgressBar value={85} color="green" showLabel />
            </div>
            <div>
              <p className="text-sm text-gray-600 mb-2">CPU Usage: 45%</p>
              <ProgressBar value={45} color="blue" />
            </div>
            <div>
              <p className="text-sm text-gray-600 mb-2">Memory Usage: 78%</p>
              <ProgressBar value={78} color="yellow" />
            </div>
            <div>
              <p className="text-sm text-gray-600 mb-2">Error Rate: 12%</p>
              <ProgressBar value={12} color="red" size="sm" />
            </div>
          </div>
        </Card>

        {/* Loading States */}
        <Card title="Loading States" subtitle="Various loading indicators">
          <div className="flex items-center gap-8">
            <div className="text-center">
              <LoadingSpinner size="sm" />
              <p className="text-sm text-gray-600 mt-2">Small</p>
            </div>
            <div className="text-center">
              <LoadingSpinner size="md" />
              <p className="text-sm text-gray-600 mt-2">Medium</p>
            </div>
            <div className="text-center">
              <LoadingSpinner size="lg" />
              <p className="text-sm text-gray-600 mt-2">Large</p>
            </div>
            <div className="text-center">
              <LoadingSpinner color="gray" />
              <p className="text-sm text-gray-600 mt-2">Gray</p>
            </div>
          </div>
        </Card>

        {/* Modal Demo */}
        <Card title="Modal" subtitle="Overlay dialogs and popups">
          <Button onClick={() => setModalOpen(true)}>
            Open Modal
          </Button>
          
          <Modal 
            isOpen={modalOpen} 
            onClose={() => setModalOpen(false)}
            title="Example Modal"
            size="md"
          >
            <div className="space-y-4">
              <p className="text-gray-600">
                This is an example modal dialog. It can contain any content and is fully accessible.
              </p>
              <Input
                label="Modal Input"
                placeholder="Type something..."
                value=""
                onChange={() => {}}
              />
              <div className="flex gap-3 justify-end">
                <Button variant="secondary" onClick={() => setModalOpen(false)}>
                  Cancel
                </Button>
                <Button variant="primary" onClick={() => setModalOpen(false)}>
                  Save Changes
                </Button>
              </div>
            </div>
          </Modal>
        </Card>

        {/* Cards Showcase */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card title="Hover Card" subtitle="Hover for effect" hover>
            <p className="text-gray-600">This card has hover effects enabled.</p>
          </Card>
          
          <Card padding="sm">
            <div className="text-center">
              <div className="text-3xl mb-2">🚀</div>
              <h4 className="font-semibold">Small Padding</h4>
              <p className="text-sm text-gray-600">Compact card layout</p>
            </div>
          </Card>
          
          <Card padding="lg">
            <div className="text-center">
              <div className="text-3xl mb-2">🎯</div>
              <h4 className="font-semibold">Large Padding</h4>
              <p className="text-sm text-gray-600">Spacious card layout</p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
