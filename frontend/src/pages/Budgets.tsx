import React, { useState, useEffect } from 'react'
import { Plus, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Progress } from '../components/ui/progress'
import { BudgetCreateDialog } from '../components/BudgetCreateDialog'
import { BudgetCard } from '../components/BudgetCard'
import { BudgetAlerts } from '../components/BudgetAlerts'

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

export function Budgets() {
  const [budgets, setBudgets] = useState<Budget[]>([])
  const [alerts, setAlerts] = useState<BudgetAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [activeOnly, setActiveOnly] = useState(true)

  useEffect(() => {
    loadBudgets()
    loadAlerts()
  }, [activeOnly])

  const loadBudgets = async () => {
    try {
      const response = await fetch(`/api/budgets?active_only=${activeOnly}`, {
        headers: {
          // Add auth headers when authentication is implemented
        }
      })

      if (response.ok) {
        const data = await response.json()
        setBudgets(data)
      }
    } catch (error) {
      console.error('Failed to load budgets:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadAlerts = async () => {
    try {
      const response = await fetch('/api/budgets/alerts/', {
        headers: {
          // Add auth headers when authentication is implemented
        }
      })

      if (response.ok) {
        const data = await response.json()
        setAlerts(data)
      }
    } catch (error) {
      console.error('Failed to load budget alerts:', error)
    }
  }

  const handleBudgetCreated = (newBudget: Budget) => {
    setBudgets(prev => [newBudget, ...prev])
    setShowCreateDialog(false)
    loadAlerts() // Refresh alerts
  }

  const handleBudgetUpdated = (updatedBudget: Budget) => {
    setBudgets(prev => prev.map(b => b.id === updatedBudget.id ? updatedBudget : b))
    loadAlerts() // Refresh alerts
  }

  const handleBudgetDeleted = (budgetId: string) => {
    setBudgets(prev => prev.filter(b => b.id !== budgetId))
    loadAlerts() // Refresh alerts
  }

  const getTotalBudgetAmount = () => {
    return budgets.reduce((total, budget) => total + (budget.total_limit || 0), 0)
  }

  const getTotalSpentAmount = () => {
    return budgets.reduce((total, budget) => {
      const spent = budget.category_budgets.reduce((sum, cb) => sum + cb.spent_amount, 0)
      return total + spent
    }, 0)
  }

  const getActiveAlertsCount = () => {
    return alerts.length
  }

  const getExceededBudgetsCount = () => {
    return alerts.filter(alert => alert.alert_type === 'exceeded').length
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Budget Management</h2>
          <p className="text-muted-foreground">
            Track your spending limits and financial goals
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={activeOnly ? "default" : "outline"}
            onClick={() => setActiveOnly(!activeOnly)}
            size="sm"
          >
            {activeOnly ? "Active Only" : "All Budgets"}
          </Button>
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create Budget
          </Button>
        </div>
      </div>

      {/* Budget Alerts */}
      {alerts.length > 0 && (
        <BudgetAlerts alerts={alerts} onAlertDismissed={loadAlerts} />
      )}

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Budget</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${getTotalBudgetAmount().toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">
              Across {budgets.length} budget{budgets.length !== 1 ? 's' : ''}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Spent</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${getTotalSpentAmount().toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">
              {getTotalBudgetAmount() > 0 
                ? `${((getTotalSpentAmount() / getTotalBudgetAmount()) * 100).toFixed(1)}% of total budget`
                : 'No budget set'
              }
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Alerts</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {getActiveAlertsCount()}
            </div>
            <p className="text-xs text-muted-foreground">
              Budget warnings and overages
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Exceeded Budgets</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">
              {getExceededBudgetsCount()}
            </div>
            <p className="text-xs text-muted-foreground">
              Budgets over their limit
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Budget List */}
      {budgets.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <TrendingUp className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No budgets found</h3>
            <p className="text-muted-foreground text-center mb-4">
              {activeOnly 
                ? "You don't have any active budgets. Create your first budget to start tracking your spending."
                : "You haven't created any budgets yet. Create your first budget to start tracking your spending."
              }
            </p>
            <Button onClick={() => setShowCreateDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Your First Budget
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {budgets.map((budget) => (
            <BudgetCard
              key={budget.id}
              budget={budget}
              alerts={alerts.filter(alert => alert.budget_id === budget.id)}
              onBudgetUpdated={handleBudgetUpdated}
              onBudgetDeleted={handleBudgetDeleted}
            />
          ))}
        </div>
      )}

      {/* Create Budget Dialog */}
      <BudgetCreateDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onBudgetCreated={handleBudgetCreated}
      />
    </div>
  )
}