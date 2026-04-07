import { useState } from 'react'
import { Button, Card, Input, Badge, ProgressBar, LoadingSpinner, Modal } from './index'

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
