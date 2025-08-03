import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// Debug environment variables
console.log('🔧 Environment Variables Debug:')
console.log('VITE_API_URL:', import.meta.env.VITE_API_URL)
console.log('VITE_SUPABASE_URL:', import.meta.env.VITE_SUPABASE_URL)
console.log('VITE_SUPABASE_ANON_KEY:', import.meta.env.VITE_SUPABASE_ANON_KEY ? '✅ Present' : '❌ Missing')
console.log('VITE_WS_URL:', import.meta.env.VITE_WS_URL)
console.log('VITE_NODE_ENV:', import.meta.env.VITE_NODE_ENV)
console.log('All env vars:', import.meta.env)

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)