# ABrain UI v1.1.0 🚀

A modern, responsive web interface for managing AI agents with enhanced UX/UI design, built with React, TypeScript, and Tailwind CSS.

## ✨ Features

### 🎨 Modern Design System
- **Dark/Light Mode Support** - Seamless theme switching with system preference detection
- **Responsive Design** - Optimized for desktop, tablet, and mobile devices  
- **Glass Morphism Effects** - Modern blur and transparency effects
- **Smooth Animations** - Framer Motion powered transitions and micro-interactions
- **Custom Component Library** - Reusable UI components with consistent styling

### 🤖 Agent Management
- **Real-time Agent Monitoring** - Live status updates and performance metrics
- **Task Queue Management** - Visual task progression with priority handling
- **Agent Configuration** - Easy setup and management of AI agents
- **Performance Analytics** - Detailed metrics and success rate tracking

### 💬 Enhanced Chat Interface
- **Multi-Session Support** - Multiple chat sessions with history
- **Task Type Selection** - Specialized agents for different use cases
- **File Upload Support** - Drag & drop file attachments
- **Real-time Typing Indicators** - Live response feedback
- **Message Status Tracking** - Delivery confirmation and error handling

### 📊 Advanced Dashboard
- **System Health Monitoring** - CPU, memory, and network usage
- **Real-time Metrics** - Live performance charts and graphs
- **Activity Feed** - Recent system events and notifications
- **Quick Actions** - One-click access to common tasks

### ⚙️ Comprehensive Settings
- **API Configuration** - OpenAI, Anthropic, and local model setup
- **Security Settings** - SSL, authentication, and rate limiting
- **Agent Parameters** - Timeout, retry, and concurrency settings
- **Advanced Options** - Debug mode, telemetry, and backup configuration

### 🔐 Security & Performance
- **PWA Support** - Progressive Web App with offline capabilities
- **Security Headers** - CORS, CSP, and security best practices
- **Code Splitting** - Optimized bundle loading for faster performance
- **Caching Strategy** - Intelligent caching for API responses and assets

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ 
- npm 8+ or yarn 1.22+

### Installation

```bash
# Clone the repository
git clone https://github.com/EcoSphereNetwork/Agent-NN.git
cd Agent-NN/frontend/agent-ui

# Install dependencies
npm install

# Copy environment configuration
cp .env.local.example .env.local

# Start development server
npm run dev
```

### Environment Configuration

Create a `.env.local` file with your configuration:

```env
# API Configuration
VITE_API_URL=http://localhost:8000

# Optional: Feature Flags
VITE_ENABLE_PWA=true
VITE_ENABLE_ANALYTICS=false
VITE_DEBUG_MODE=false

# Optional: Branding
VITE_APP_NAME="ABrain"
VITE_APP_VERSION="2.0.0"
```

## 📁 Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── ui/             # Base UI components (Button, Input, etc.)
│   ├── layout/         # Layout components (Header, Sidebar)
│   └── features/       # Feature-specific components
├── pages/              # Page components
├── hooks/              # Custom React hooks
├── store/              # State management (Zustand)
├── utils/              # Utility functions
├── types/              # TypeScript type definitions
├── styles/             # Global styles and Tailwind config
└── assets/             # Static assets
```

## 🎨 Component Library

### Basic Components
```tsx
import { Button, Input, Card, Badge, Modal } from '@/components/ui'

// Example usage
<Button variant="primary" size="lg" loading={isLoading}>
  Save Changes
</Button>

<Input 
  label="API Key" 
  type="password" 
  error={errors.apiKey}
  icon={<KeyIcon />}
/>

<Card title="System Status" hover>
  <Badge variant="success">Online</Badge>
</Card>
```

### Advanced Components
```tsx
import { Toast, LoadingSpinner, ProgressBar } from '@/components/ui'

// Toast notifications
<Toast 
  type="success" 
  message="Settings saved successfully!" 
  onClose={handleClose}
/>

// Progress tracking
<ProgressBar 
  value={75} 
  color="blue" 
  showLabel 
  className="mb-4"
/>
```

## 🔧 Configuration

### Tailwind CSS Customization

The project uses an extended Tailwind configuration with:
- Custom color palette
- Enhanced animations
- Glass morphism utilities
- Component classes
- Typography system

### API Integration

Configure your backend API endpoints:

```typescript
// In your API service
const API_BASE_URL = import.meta.env.VITE_API_URL

// Example API calls
export const agentService = {
  getAgents: () => fetch(`${API_BASE_URL}/agents`),
  createTask: (task) => fetch(`${API_BASE_URL}/tasks`, {
    method: 'POST',
    body: JSON.stringify(task)
  })
}
```

## 📱 PWA Features

The application is configured as a Progressive Web App with:
- **Offline Support** - Core functionality works without internet
- **App Installation** - Can be installed on mobile and desktop
- **Background Sync** - Automatic data synchronization
- **Push Notifications** - Real-time updates (when configured)

## 🎯 Performance Optimizations

- **Code Splitting** - Lazy loading of routes and components
- **Bundle Analysis** - Optimized chunk sizes
- **Image Optimization** - WebP support and lazy loading
- **Caching Strategy** - Service worker for offline support
- **Tree Shaking** - Unused code elimination

## 🧪 Testing

```bash
# Run type checking
npm run type-check

# Lint code
npm run lint

# Automatically fix lint issues
npm run lint:fix

# Format code
npm run format

# Build for production
npm run build

# Preview production build
npm run preview
```

The project uses **ESLint** with a flat configuration and **Prettier** for code formatting. Configuration is defined in `eslint.config.js`.

## 🚀 Deployment

### Build for Production

```bash
npm run build
```

### Deploy to Static Hosting

The built files in `dist/` can be deployed to any static hosting service:
- Netlify
- Vercel  
- AWS S3 + CloudFront
- GitHub Pages
- Firebase Hosting

### Docker Deployment

```dockerfile
FROM nginx:alpine
COPY dist/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 🎨 Theming & Customization

### Color Scheme

```css
/* Custom CSS variables */
:root {
  --primary-500: #3b82f6;
  --primary-600: #2563eb;
  --success-500: #10b981;
  --warning-500: #f59e0b;
  --error-500: #ef4444;
}
```

### Component Styling

```tsx
// Using Tailwind classes
<div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
  <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
    Dashboard
  </h2>
</div>

// Using component classes
<div className="card card-hover">
  <button className="btn btn-primary">
    Action
  </button>
</div>
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow TypeScript best practices
- Use semantic commit messages
- Add tests for new features
- Update documentation as needed
- Ensure responsive design compliance

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: central project docs in the main repository
- **Issues**: use the main repository issue tracker
- **Discussions**: use the main repository discussion channel when available

## 🙏 Acknowledgments

- [React](https://reactjs.org/) - UI library
- [TypeScript](https://www.typescriptlang.org/) - Type safety
- [Tailwind CSS](https://tailwindcss.com/) - Styling framework
- [Vite](https://vitejs.dev/) - Build tool
- [Framer Motion](https://www.framer.com/motion/) - Animations
- [Heroicons](https://heroicons.com/) - Icon library

---

Built with ❤️ by the ABrain team
