/**
 * WebSocket context for real-time features
 */
import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { useWebSocket, WebSocketMessage } from '../hooks/useWebSocket'

interface WebSocketContextType {
  isConnected: boolean
  isConnecting: boolean
  error: string | null
  lastMessage: WebSocketMessage | null
  sendMessage: (message: any) => boolean
  subscribe: (topic: string) => void
  unsubscribe: (topic: string) => void
  connect: () => void
  disconnect: () => void
}

const WebSocketContext = createContext<WebSocketContextType | null>(null)

interface WebSocketProviderProps {
  children: ReactNode
  apiUrl?: string
  token?: string
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({
  children,
  apiUrl = 'ws://localhost:8000',
  token
}) => {
  const [notifications, setNotifications] = useState<WebSocketMessage[]>([])

  const handleMessage = (message: WebSocketMessage) => {
    console.log('WebSocket message received:', message)

    // Handle different message types
    switch (message.type) {
      case 'expense_created':
        // Show notification for new expense
        showNotification('New expense added', 'success')
        break
      
      case 'expense_updated':
        // Show notification for updated expense
        showNotification('Expense updated', 'info')
        break
      
      case 'expense_deleted':
        // Show notification for deleted expense
        showNotification('Expense deleted', 'info')
        break
      
      case 'budget_alert':
        // Show budget alert notification
        const alertType = message.data?.alert_type
        const budgetName = message.data?.budget?.name
        
        if (alertType === 'exceeded') {
          showNotification(`Budget "${budgetName}" exceeded!`, 'error')
        } else if (alertType === 'warning') {
          showNotification(`Budget "${budgetName}" warning`, 'warning')
        }
        break
      
      case 'budget_updated':
        // Show notification for budget update
        showNotification('Budget updated', 'info')
        break
      
      case 'import_progress':
        // Handle import progress updates
        const progress = message.data?.progress
        const status = message.data?.status
        console.log(`Import progress: ${progress}% - ${status}`)
        break
      
      case 'import_completed':
        // Show notification for completed import
        const result = message.data?.result
        const importedCount = result?.imported_count || 0
        showNotification(`Import completed: ${importedCount} transactions imported`, 'success')
        break
      
      case 'analytics_updated':
        // Handle analytics updates
        console.log('Analytics updated:', message.data)
        break
      
      case 'notification':
        // Handle general notifications
        const notification = message.data
        showNotification(notification?.message || 'Notification', notification?.type || 'info')
        break
      
      case 'heartbeat':
        // Handle heartbeat - no action needed
        break
      
      case 'error':
        // Handle error messages
        showNotification(message.data?.message || 'WebSocket error', 'error')
        break
      
      default:
        console.log('Unknown WebSocket message type:', message.type)
    }

    // Store the message for components that need it
    setNotifications(prev => [...prev.slice(-9), message]) // Keep last 10 messages
  }

  const showNotification = (message: string, type: 'success' | 'error' | 'warning' | 'info') => {
    // This would integrate with your notification system
    // For now, just log to console
    console.log(`[${type.toUpperCase()}] ${message}`)
    
    // You could dispatch to a notification context or use a toast library
    // Example with a hypothetical toast system:
    // toast[type](message)
  }

  const handleConnect = () => {
    console.log('WebSocket connected')
    showNotification('Connected to real-time updates', 'success')
  }

  const handleDisconnect = () => {
    console.log('WebSocket disconnected')
    showNotification('Disconnected from real-time updates', 'warning')
  }

  const handleError = (error: Event) => {
    console.error('WebSocket error:', error)
    showNotification('Connection error', 'error')
  }

  const webSocket = useWebSocket({
    url: `${apiUrl}/api/ws`,
    token,
    clientType: 'web',
    clientVersion: '1.0.0',
    onMessage: handleMessage,
    onConnect: handleConnect,
    onDisconnect: handleDisconnect,
    onError: handleError
  })

  // Auto-subscribe to common topics when connected
  useEffect(() => {
    if (webSocket.isConnected) {
      webSocket.subscribe('expenses')
      webSocket.subscribe('budgets')
      webSocket.subscribe('analytics')
    }
  }, [webSocket.isConnected])

  const contextValue: WebSocketContextType = {
    isConnected: webSocket.isConnected,
    isConnecting: webSocket.isConnecting,
    error: webSocket.error,
    lastMessage: webSocket.lastMessage,
    sendMessage: webSocket.sendMessage,
    subscribe: webSocket.subscribe,
    unsubscribe: webSocket.unsubscribe,
    connect: webSocket.connect,
    disconnect: webSocket.disconnect
  }

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  )
}

export const useWebSocketContext = (): WebSocketContextType => {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider')
  }
  return context
}

// Hook for subscribing to specific WebSocket message types
export const useWebSocketSubscription = (
  messageType: string,
  callback: (data: any) => void,
  dependencies: any[] = []
) => {
  const { lastMessage } = useWebSocketContext()

  useEffect(() => {
    if (lastMessage?.type === messageType) {
      callback(lastMessage.data)
    }
  }, [lastMessage, messageType, ...dependencies])
}

// Hook for real-time expense updates
export const useRealTimeExpenses = (onExpenseUpdate: (expense: any) => void) => {
  useWebSocketSubscription('expense_created', onExpenseUpdate)
  useWebSocketSubscription('expense_updated', onExpenseUpdate)
  useWebSocketSubscription('expense_deleted', (data) => onExpenseUpdate({ deleted: true, id: data.expense_id }))
}

// Hook for real-time budget alerts
export const useRealTimeBudgetAlerts = (onBudgetAlert: (alert: any) => void) => {
  useWebSocketSubscription('budget_alert', onBudgetAlert)
}

// Hook for real-time import progress
export const useRealTimeImportProgress = (
  importId: string,
  onProgress: (progress: number, status: string) => void,
  onComplete: (result: any) => void
) => {
  const { lastMessage, subscribe, unsubscribe } = useWebSocketContext()

  useEffect(() => {
    const topic = `import_${importId}`
    subscribe(topic)

    return () => {
      unsubscribe(topic)
    }
  }, [importId, subscribe, unsubscribe])

  useEffect(() => {
    if (lastMessage?.type === 'import_progress' && lastMessage.data?.import_id === importId) {
      onProgress(lastMessage.data.progress, lastMessage.data.status)
    } else if (lastMessage?.type === 'import_completed' && lastMessage.data?.import_id === importId) {
      onComplete(lastMessage.data.result)
    }
  }, [lastMessage, importId, onProgress, onComplete])
}