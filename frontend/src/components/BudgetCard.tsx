import { useState } from 'react'
import { MoreHorizontal, Edit, Trash2, AlertTriangle, TrendingUp, Calendar } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { Progress } from './ui/progress'

interface Budget {
  id: string
  name: string
  period: string
  total_limit?: number
  start_date: string
  end_date?: string
  is_active: boolean
  category_budgets: CategoryBudget[]
}

interface CategoryBudget {
  id: string
  limit_amount: number
  spent_amount: number
  category_id: string
  category?: {
    id: string
    name: string
    color: string
  }
}

interface BudgetAlert {
  budget_id: string
  category_id?: string
  alert_type: 'warning' | 'exceeded'
  message: string
  percentage_used: number
  amount_spent: number
  amount_limit: number
  amount_remaining: number
}

interface BudgetCardProps {
  budget: Budget
  alerts: BudgetAlert[]
  onBudgetUpdated: (budget: Budget) => void
  onBudgetDeleted: (budgetId: string) => void
}

export function BudgetCard({ budget, alerts, onBudgetUpdated, onBudgetDeleted }: BudgetCardProps) {
  const [showMenu, setShowMenu] = useState(false)
  const [loading, setLoading] = useState(false)

  const getTotalSpent = () => {
    return budget.category_budgets.reduce((sum, cb) => sum + cb.spent_amount, 0)
  }

  const getTotalLimit = () => {
    return budget.total_limit || budget.category_budgets.reduce((sum, cb) => sum + cb.limit_amount, 0)
  }

  const getOverallProgress = () => {
    const totalLimit = getTotalLimit()
    if (totalLimit === 0) return 0
    return (getTotalSpent() / totalLimit) * 100
  }

  const getProgressColor = (percentage: number) => {
    if (percentage >= 100) return 'bg-destructive'
    if (percentage >= 80) return 'bg-orange-500'
    return 'bg-primary'
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  }

  const getPeriodDisplay = () => {
    const period = budget.period.charAt(0).toUpperCase() + budget.period.slice(1)
    if (budget.end_date) {
      return `${period} (${formatDate(budget.start_date)} - ${formatDate(budget.end_date)})`
    }
    return `${period} (from ${formatDate(budget.start_date)})`
  }

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete the budget "${budget.name}"? This action cannot be undone.`)) {
      return
    }

    setLoading(true)
    try {
      const response = await fetch(`/api/budgets/${budget.id}`, {
        method: 'DELETE',
        headers: {
          // Add auth headers when authentication is implemented
        }
      })

      if (response.ok) {
        onBudgetDeleted(budget.id)
      } else {
        throw new Error('Failed to delete budget')
      }
    } catch (error) {
      console.error('Error deleting budget:', error)
      alert('Failed to delete budget. Please try again.')
    } finally {
      setLoading(false)
      setShowMenu(false)
    }
  }

  const overallProgress = getOverallProgress()
  const hasAlerts = alerts.length > 0
  const hasExceededAlerts = alerts.some(alert => alert.alert_type === 'exceeded')

  return (
    <Card className={`relative ${hasExceededAlerts ? 'border-destructive' : hasAlerts ? 'border-orange-500' : ''}`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle className="text-lg flex items-center gap-2">
              {budget.name}
              {!budget.is_active && (
                <Badge variant="secondary" className="text-xs">
                  Inactive
                </Badge>
              )}
              {hasExceededAlerts && (
                <Badge variant="destructive" className="text-xs">
                  <AlertTriangle className="h-3 w-3 mr-1" />
                  Over Budget
                </Badge>
              )}
              {hasAlerts && !hasExceededAlerts && (
                <Badge variant="outline" className="text-xs text-orange-600 border-orange-600">
                  <AlertTriangle className="h-3 w-3 mr-1" />
                  Warning
                </Badge>
              )}
            </CardTitle>
            <CardDescription className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {getPeriodDisplay()}
            </CardDescription>
          </div>
          
          <div className="relative">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowMenu(!showMenu)}
              disabled={loading}
            >
              <MoreHorizontal className="h-4 w-4" />
            </Button>
            
            {showMenu && (
              <div className="absolute right-0 top-8 z-10 bg-background border rounded-md shadow-lg py-1 min-w-[120px]">
                <button
                  className="w-full px-3 py-2 text-left text-sm hover:bg-muted flex items-center gap-2"
                  onClick={() => {
                    setShowMenu(false)
                    // TODO: Open edit dialog
                  }}
                >
                  <Edit className="h-3 w-3" />
                  Edit
                </button>
                <button
                  className="w-full px-3 py-2 text-left text-sm hover:bg-muted text-destructive flex items-center gap-2"
                  onClick={handleDelete}
                  disabled={loading}
                >
                  <Trash2 className="h-3 w-3" />
                  Delete
                </button>
              </div>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Overall Progress */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">Overall Progress</span>
            <span className={overallProgress >= 100 ? 'text-destructive font-medium' : ''}>
              {formatCurrency(getTotalSpent())} / {formatCurrency(getTotalLimit())}
            </span>
          </div>
          <div className="relative">
            <Progress 
              value={Math.min(overallProgress, 100)} 
              className="h-2"
            />
            <div 
              className={`absolute top-0 left-0 h-2 rounded-full transition-all ${getProgressColor(overallProgress)}`}
              style={{ width: `${Math.min(overallProgress, 100)}%` }}
            />
          </div>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{overallProgress.toFixed(1)}% used</span>
            <span>
              {overallProgress >= 100 
                ? `$${(getTotalSpent() - getTotalLimit()).toFixed(2)} over budget`
                : `$${(getTotalLimit() - getTotalSpent()).toFixed(2)} remaining`
              }
            </span>
          </div>
        </div>

        {/* Category Breakdown */}
        {budget.category_budgets.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-medium">Categories</h4>
            <div className="space-y-2">
              {budget.category_budgets.slice(0, 3).map((categoryBudget) => {
                const percentage = (categoryBudget.spent_amount / categoryBudget.limit_amount) * 100
                const categoryAlert = alerts.find(alert => alert.category_id === categoryBudget.category_id)
                
                return (
                  <div key={categoryBudget.id} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">
                          {categoryBudget.category?.name || 'Unknown Category'}
                        </span>
                        {categoryAlert && (
                          <AlertTriangle className={`h-3 w-3 ${
                            categoryAlert.alert_type === 'exceeded' ? 'text-destructive' : 'text-orange-500'
                          }`} />
                        )}
                      </div>
                      <span className={percentage >= 100 ? 'text-destructive' : ''}>
                        {formatCurrency(categoryBudget.spent_amount)} / {formatCurrency(categoryBudget.limit_amount)}
                      </span>
                    </div>
                    <div className="relative">
                      <Progress 
                        value={Math.min(percentage, 100)} 
                        className="h-1"
                      />
                      <div 
                        className={`absolute top-0 left-0 h-1 rounded-full transition-all ${getProgressColor(percentage)}`}
                        style={{ width: `${Math.min(percentage, 100)}%` }}
                      />
                    </div>
                  </div>
                )
              })}
              
              {budget.category_budgets.length > 3 && (
                <div className="text-xs text-muted-foreground text-center pt-1">
                  +{budget.category_budgets.length - 3} more categories
                </div>
              )}
            </div>
          </div>
        )}

        {/* Alerts Summary */}
        {alerts.length > 0 && (
          <div className="pt-2 border-t">
            <div className="text-xs text-muted-foreground">
              {alerts.length} alert{alerts.length !== 1 ? 's' : ''} • 
              {alerts.filter(a => a.alert_type === 'exceeded').length} exceeded • 
              {alerts.filter(a => a.alert_type === 'warning').length} warnings
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}