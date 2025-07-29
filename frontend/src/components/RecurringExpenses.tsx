import { useState, useEffect } from 'react'
import { 
  Calendar, 
  Plus, 
  Edit, 
  Trash2, 
  Play, 
  Pause, 
  Clock,
  DollarSign,
  Tag,
  AlertTriangle,
  CheckCircle
} from 'lucide-react'

interface RecurringExpense {
  id: string
  name: string
  amount: number
  category: string
  frequency: string
  next_due_date: string
  is_active: boolean
  account?: string
  payment_method?: string
  notes?: string
  created_at: string
  last_processed?: string
}

interface RecurringNotification {
  id: string
  recurring_expense_id: string
  message: string
  type: 'due' | 'overdue' | 'processed'
  created_at: string
  is_read: boolean
  recurring_expense: RecurringExpense
}

export function RecurringExpenses() {
  const [recurringExpenses, setRecurringExpenses] = useState<RecurringExpense[]>([])
  const [notifications, setNotifications] = useState<RecurringNotification[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedTab, setSelectedTab] = useState<'active' | 'inactive' | 'notifications'>('active')

  useEffect(() => {
    loadRecurringExpenses()
    loadNotifications()
  }, [])

  const loadRecurringExpenses = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/recurring-expenses')
      if (response.ok) {
        const data = await response.json()
        setRecurringExpenses(data)
      }
    } catch (error) {
      console.error('Error loading recurring expenses:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadNotifications = async () => {
    try {
      const response = await fetch('/api/recurring-expenses/notifications')
      if (response.ok) {
        const data = await response.json()
        setNotifications(data)
      }
    } catch (error) {
      console.error('Error loading notifications:', error)
    }
  }

  const handleToggleActive = async (id: string, isActive: boolean) => {
    try {
      const response = await fetch(`/api/recurring-expenses/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !isActive })
      })
      
      if (response.ok) {
        loadRecurringExpenses()
      }
    } catch (error) {
      console.error('Error toggling recurring expense:', error)
    }
  }

  const handleProcessNow = async (id: string) => {
    if (confirm('Process this recurring expense now?')) {
      try {
        const response = await fetch(`/api/recurring-expenses/${id}/process`, {
          method: 'POST'
        })
        
        if (response.ok) {
          loadRecurringExpenses()
          loadNotifications()
        }
      } catch (error) {
        console.error('Error processing recurring expense:', error)
      }
    }
  }

  const handleDelete = async (id: string) => {
    if (confirm('Delete this recurring expense? This action cannot be undone.')) {
      try {
        const response = await fetch(`/api/recurring-expenses/${id}`, {
          method: 'DELETE'
        })
        
        if (response.ok) {
          loadRecurringExpenses()
        }
      } catch (error) {
        console.error('Error deleting recurring expense:', error)
      }
    }
  }

  const markNotificationRead = async (notificationId: string) => {
    try {
      await fetch(`/api/recurring-expenses/notifications/${notificationId}/read`, {
        method: 'POST'
      })
      loadNotifications()
    } catch (error) {
      console.error('Error marking notification as read:', error)
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount)
  }

  const getFrequencyDisplay = (frequency: string) => {
    const frequencyMap: { [key: string]: string } = {
      'daily': 'Daily',
      'weekly': 'Weekly',
      'monthly': 'Monthly',
      'quarterly': 'Quarterly',
      'yearly': 'Yearly'
    }
    return frequencyMap[frequency] || frequency
  }

  const getDaysUntilDue = (dueDate: string) => {
    const due = new Date(dueDate)
    const today = new Date()
    const diffTime = due.getTime() - today.getTime()
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    return diffDays
  }

  const getStatusColor = (expense: RecurringExpense) => {
    if (!expense.is_active) return 'text-gray-500'
    
    const daysUntilDue = getDaysUntilDue(expense.next_due_date)
    if (daysUntilDue < 0) return 'text-red-500'
    if (daysUntilDue <= 3) return 'text-amber-500'
    return 'text-green-500'
  }

  const getStatusText = (expense: RecurringExpense) => {
    if (!expense.is_active) return 'Inactive'
    
    const daysUntilDue = getDaysUntilDue(expense.next_due_date)
    if (daysUntilDue < 0) return `Overdue by ${Math.abs(daysUntilDue)} days`
    if (daysUntilDue === 0) return 'Due today'
    if (daysUntilDue === 1) return 'Due tomorrow'
    return `Due in ${daysUntilDue} days`
  }

  const activeExpenses = recurringExpenses.filter(e => e.is_active)
  const inactiveExpenses = recurringExpenses.filter(e => !e.is_active)
  const unreadNotifications = notifications.filter(n => !n.is_read)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Recurring Expenses</h2>
          <p className="text-muted-foreground">
            Manage your recurring expenses and subscriptions
          </p>
        </div>
        <button className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors">
          <Plus className="h-4 w-4 mr-2" />
          Add Recurring Expense
        </button>
      </div>

      {/* Notifications Alert */}
      {unreadNotifications.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-center">
            <AlertTriangle className="h-5 w-5 text-amber-600 mr-2" />
            <h3 className="font-medium text-amber-800">
              {unreadNotifications.length} pending notification{unreadNotifications.length > 1 ? 's' : ''}
            </h3>
          </div>
          <div className="mt-2">
            <button
              onClick={() => setSelectedTab('notifications')}
              className="text-sm text-amber-600 hover:text-amber-800 underline"
            >
              View notifications →
            </button>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="border-b">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setSelectedTab('active')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              selectedTab === 'active'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-gray-300'
            }`}
          >
            Active ({activeExpenses.length})
          </button>
          <button
            onClick={() => setSelectedTab('inactive')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              selectedTab === 'inactive'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-gray-300'
            }`}
          >
            Inactive ({inactiveExpenses.length})
          </button>
          <button
            onClick={() => setSelectedTab('notifications')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              selectedTab === 'notifications'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-gray-300'
            }`}
          >
            Notifications ({unreadNotifications.length})
          </button>
        </nav>
      </div>

      {/* Content */}
      {selectedTab === 'active' && (
        <div className="space-y-4">
          {activeExpenses.length > 0 ? (
            activeExpenses.map((expense) => (
              <div key={expense.id} className="border rounded-lg p-6 bg-card">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold">{expense.name}</h3>
                      <span className={`text-sm font-medium ${getStatusColor(expense)}`}>
                        {getStatusText(expense)}
                      </span>
                    </div>
                    
                    <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-4 text-sm text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <DollarSign className="h-3 w-3" />
                        {formatCurrency(expense.amount)}
                      </div>
                      <div className="flex items-center gap-1">
                        <Tag className="h-3 w-3" />
                        {expense.category}
                      </div>
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {getFrequencyDisplay(expense.frequency)}
                      </div>
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        Next: {new Date(expense.next_due_date).toLocaleDateString()}
                      </div>
                    </div>
                    
                    {expense.notes && (
                      <p className="text-sm text-muted-foreground mt-2">{expense.notes}</p>
                    )}
                    
                    {expense.last_processed && (
                      <p className="text-xs text-muted-foreground mt-2">
                        Last processed: {new Date(expense.last_processed).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2 ml-4">
                    <button
                      onClick={() => handleProcessNow(expense.id)}
                      className="p-2 hover:bg-muted rounded-md transition-colors"
                      title="Process now"
                    >
                      <Play className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleToggleActive(expense.id, expense.is_active)}
                      className="p-2 hover:bg-muted rounded-md transition-colors"
                      title="Pause"
                    >
                      <Pause className="h-4 w-4" />
                    </button>
                    <button className="p-2 hover:bg-muted rounded-md transition-colors">
                      <Edit className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(expense.id)}
                      className="p-2 hover:bg-muted rounded-md transition-colors text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-12">
              <Calendar className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
              <h3 className="text-lg font-semibold mb-2">No active recurring expenses</h3>
              <p className="text-muted-foreground mb-4">
                Set up recurring expenses to automate your regular payments.
              </p>
              <button className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors">
                <Plus className="h-4 w-4 mr-2" />
                Add Recurring Expense
              </button>
            </div>
          )}
        </div>
      )}

      {selectedTab === 'inactive' && (
        <div className="space-y-4">
          {inactiveExpenses.length > 0 ? (
            inactiveExpenses.map((expense) => (
              <div key={expense.id} className="border rounded-lg p-6 bg-card opacity-60">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold">{expense.name}</h3>
                      <span className="text-sm font-medium text-gray-500">Inactive</span>
                    </div>
                    
                    <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3 text-sm text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <DollarSign className="h-3 w-3" />
                        {formatCurrency(expense.amount)}
                      </div>
                      <div className="flex items-center gap-1">
                        <Tag className="h-3 w-3" />
                        {expense.category}
                      </div>
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {getFrequencyDisplay(expense.frequency)}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2 ml-4">
                    <button
                      onClick={() => handleToggleActive(expense.id, expense.is_active)}
                      className="p-2 hover:bg-muted rounded-md transition-colors"
                      title="Activate"
                    >
                      <Play className="h-4 w-4" />
                    </button>
                    <button className="p-2 hover:bg-muted rounded-md transition-colors">
                      <Edit className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(expense.id)}
                      className="p-2 hover:bg-muted rounded-md transition-colors text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-12">
              <Pause className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
              <h3 className="text-lg font-semibold mb-2">No inactive recurring expenses</h3>
              <p className="text-muted-foreground">
                Paused recurring expenses will appear here.
              </p>
            </div>
          )}
        </div>
      )}

      {selectedTab === 'notifications' && (
        <div className="space-y-4">
          {notifications.length > 0 ? (
            notifications.map((notification) => (
              <div 
                key={notification.id} 
                className={`border rounded-lg p-4 ${
                  notification.is_read ? 'bg-card opacity-60' : 'bg-card border-amber-200'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      {notification.type === 'due' && <Clock className="h-4 w-4 text-amber-500" />}
                      {notification.type === 'overdue' && <AlertTriangle className="h-4 w-4 text-red-500" />}
                      {notification.type === 'processed' && <CheckCircle className="h-4 w-4 text-green-500" />}
                      <span className="font-medium">{notification.recurring_expense.name}</span>
                      {!notification.is_read && (
                        <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mb-1">{notification.message}</p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(notification.created_at).toLocaleDateString()} at{' '}
                      {new Date(notification.created_at).toLocaleTimeString()}
                    </p>
                  </div>
                  
                  {!notification.is_read && (
                    <button
                      onClick={() => markNotificationRead(notification.id)}
                      className="text-sm text-primary hover:text-primary/80"
                    >
                      Mark as read
                    </button>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-12">
              <CheckCircle className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
              <h3 className="text-lg font-semibold mb-2">No notifications</h3>
              <p className="text-muted-foreground">
                Notifications about recurring expenses will appear here.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}