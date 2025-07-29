/**
 * Real-time notifications component
 */
import React, { useState, useEffect } from 'react'
import { useWebSocketContext } from '../contexts/WebSocketContext'
import { X, CheckCircle, AlertTriangle, Info, AlertCircle } from 'lucide-react'

interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  timestamp: Date
  autoHide?: boolean
  duration?: number
}

export const RealTimeNotifications: React.FC = () => {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const { lastMessage, isConnected } = useWebSocketContext()

  // Handle WebSocket messages and create notifications
  useEffect(() => {
    if (!lastMessage) return

    let notification: Notification | null = null

    switch (lastMessage.type) {
      case 'expense_created':
        notification = {
          id: `expense_created_${Date.now()}`,
          type: 'success',
          title: 'Expense Added',
          message: `New expense: ${lastMessage.data?.description} - $${lastMessage.data?.amount}`,
          timestamp: new Date(),
          autoHide: true,
          duration: 5000
        }
        break

      case 'expense_updated':
        notification = {
          id: `expense_updated_${Date.now()}`,
          type: 'info',
          title: 'Expense Updated',
          message: `Updated: ${lastMessage.data?.description}`,
          timestamp: new Date(),
          autoHide: true,
          duration: 4000
        }
        break

      case 'expense_deleted':
        notification = {
          id: `expense_deleted_${Date.now()}`,
          type: 'info',
          title: 'Expense Deleted',
          message: 'An expense has been deleted',
          timestamp: new Date(),
          autoHide: true,
          duration: 4000
        }
        break

      case 'budget_alert':
        const alertType = lastMessage.data?.alert_type
        const budgetName = lastMessage.data?.budget?.name
        const percentage = lastMessage.data?.budget?.percentage_used

        notification = {
          id: `budget_alert_${Date.now()}`,
          type: alertType === 'exceeded' ? 'error' : 'warning',
          title: alertType === 'exceeded' ? 'Budget Exceeded!' : 'Budget Warning',
          message: `Budget "${budgetName}" is ${percentage?.toFixed(1)}% used`,
          timestamp: new Date(),
          autoHide: alertType !== 'exceeded',
          duration: alertType === 'exceeded' ? undefined : 8000
        }
        break

      case 'budget_updated':
        notification = {
          id: `budget_updated_${Date.now()}`,
          type: 'info',
          title: 'Budget Updated',
          message: `Budget "${lastMessage.data?.name}" has been updated`,
          timestamp: new Date(),
          autoHide: true,
          duration: 4000
        }
        break

      case 'import_completed':
        const result = lastMessage.data?.result
        const importedCount = result?.imported_count || 0
        const skippedCount = result?.skipped_count || 0

        notification = {
          id: `import_completed_${Date.now()}`,
          type: 'success',
          title: 'Import Completed',
          message: `${importedCount} transactions imported${skippedCount > 0 ? `, ${skippedCount} skipped` : ''}`,
          timestamp: new Date(),
          autoHide: true,
          duration: 6000
        }
        break

      case 'analytics_updated':
        notification = {
          id: `analytics_updated_${Date.now()}`,
          type: 'info',
          title: 'Analytics Updated',
          message: 'Your spending analytics have been refreshed',
          timestamp: new Date(),
          autoHide: true,
          duration: 3000
        }
        break

      case 'notification':
        const notificationData = lastMessage.data
        notification = {
          id: `notification_${Date.now()}`,
          type: notificationData?.type || 'info',
          title: notificationData?.title || 'Notification',
          message: notificationData?.message || '',
          timestamp: new Date(),
          autoHide: true,
          duration: 5000
        }
        break

      case 'error':
        notification = {
          id: `error_${Date.now()}`,
          type: 'error',
          title: 'Error',
          message: lastMessage.data?.message || 'An error occurred',
          timestamp: new Date(),
          autoHide: false
        }
        break
    }

    if (notification) {
      setNotifications(prev => [...prev, notification!])

      // Auto-hide notification if specified
      if (notification.autoHide && notification.duration) {
        setTimeout(() => {
          removeNotification(notification!.id)
        }, notification.duration)
      }
    }
  }, [lastMessage])

  // Connection status notification
  useEffect(() => {
    if (isConnected) {
      const notification: Notification = {
        id: `connected_${Date.now()}`,
        type: 'success',
        title: 'Connected',
        message: 'Real-time updates are now active',
        timestamp: new Date(),
        autoHide: true,
        duration: 3000
      }
      setNotifications(prev => [...prev, notification])

      setTimeout(() => {
        removeNotification(notification.id)
      }, notification.duration!)
    }
  }, [isConnected])

  const removeNotification = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id))
  }

  const getIcon = (type: Notification['type']) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />
      case 'warning':
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />
      case 'info':
      default:
        return <Info className="h-5 w-5 text-blue-500" />
    }
  }

  const getBackgroundColor = (type: Notification['type']) => {
    switch (type) {
      case 'success':
        return 'bg-green-50 border-green-200'
      case 'error':
        return 'bg-red-50 border-red-200'
      case 'warning':
        return 'bg-yellow-50 border-yellow-200'
      case 'info':
      default:
        return 'bg-blue-50 border-blue-200'
    }
  }

  if (notifications.length === 0) {
    return null
  }

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm">
      {notifications.map((notification) => (
        <div
          key={notification.id}
          className={`rounded-lg border p-4 shadow-lg transition-all duration-300 ${getBackgroundColor(notification.type)}`}
        >
          <div className="flex items-start">
            <div className="flex-shrink-0">
              {getIcon(notification.type)}
            </div>
            <div className="ml-3 flex-1">
              <h3 className="text-sm font-medium text-gray-900">
                {notification.title}
              </h3>
              <p className="mt-1 text-sm text-gray-600">
                {notification.message}
              </p>
              <p className="mt-1 text-xs text-gray-500">
                {notification.timestamp.toLocaleTimeString()}
              </p>
            </div>
            <div className="ml-4 flex-shrink-0">
              <button
                onClick={() => removeNotification(notification.id)}
                className="inline-flex rounded-md text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                <span className="sr-only">Close</span>
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// Connection status indicator component
export const WebSocketStatus: React.FC = () => {
  const { isConnected, isConnecting, error } = useWebSocketContext()

  if (isConnected) {
    return (
      <div className="flex items-center text-green-600">
        <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
        <span className="text-xs">Live</span>
      </div>
    )
  }

  if (isConnecting) {
    return (
      <div className="flex items-center text-yellow-600">
        <div className="w-2 h-2 bg-yellow-500 rounded-full mr-2 animate-pulse"></div>
        <span className="text-xs">Connecting...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center text-red-600">
        <div className="w-2 h-2 bg-red-500 rounded-full mr-2"></div>
        <span className="text-xs">Offline</span>
      </div>
    )
  }

  return (
    <div className="flex items-center text-gray-400">
      <div className="w-2 h-2 bg-gray-400 rounded-full mr-2"></div>
      <span className="text-xs">Disconnected</span>
    </div>
  )
}