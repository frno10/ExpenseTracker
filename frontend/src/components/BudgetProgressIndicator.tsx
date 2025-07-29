import React, { useState, useEffect } from 'react'
import { AlertTriangle, TrendingUp, DollarSign } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Progress } from './ui/progress'
import { Badge } from './ui/badge'

interface BudgetProgress {
  budget_id: string
  budget_name: string
  current_spent: number
  budget_limit: number
  remaining_amount: number
  spent_percentage: number
  is_over_budget: boolean
  is_warning_threshold_reached: boolean
}

interface BudgetProgressIndicatorProps {
  categoryId?: string
  expenseAmount?: number
  className?: string
}

export function BudgetProgressIndicator({ 
  categoryId, 
  expenseAmount = 0, 
  className = "" 
}: BudgetProgressIndicatorProps) {
  const [budgetProgress, setBudgetProgress] = useState<BudgetProgress[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (categoryId) {
      loadBudgetProgress()
    }
  }, [categoryId])

  const loadBudgetProgress = async () => {
    if (!categoryId) return

    setLoading(true)
    try {
      // Get budgets that include this category
      const response = await fetch(`/api/budgets?active_only=true`, {
        headers: {
          // Add auth headers when authentication is implemented
        }
      })

      if (response.ok) {
        const budgets = await response.json()
        
        // Filter budgets that include this category
        const relevantBudgets = budgets.filter((budget: any) => {
          // If no category budgets specified, it includes all categories
          if (!budget.category_budgets || budget.category_budgets.length === 0) {
            return true
          }
          
          // Check if this category is included in the budget
          return budget.category_budgets.some((cb: any) => cb.category_id === categoryId)
        })

        // Transform to progress format
        const progressData = relevantBudgets.map((budget: any) => {
          const totalSpent = budget.category_budgets.reduce(
            (sum: number, cb: any) => sum + cb.spent_amount, 
            0
          )
          const totalLimit = budget.total_limit || budget.category_budgets.reduce(
            (sum: number, cb: any) => sum + cb.limit_amount, 
            0
          )
          
          return {
            budget_id: budget.id,
            budget_name: budget.name,
            current_spent: totalSpent,
            budget_limit: totalLimit,
            remaining_amount: totalLimit - totalSpent,
            spent_percentage: totalLimit > 0 ? (totalSpent / totalLimit) * 100 : 0,
            is_over_budget: totalSpent > totalLimit,
            is_warning_threshold_reached: totalLimit > 0 && (totalSpent / totalLimit) >= 0.8
          }
        })

        setBudgetProgress(progressData)
      }
    } catch (error) {
      console.error('Failed to load budget progress:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount)
  }

  const getProgressColor = (percentage: number, withExpense: boolean = false) => {
    if (withExpense && percentage >= 100) return 'bg-destructive'
    if (percentage >= 100) return 'bg-destructive'
    if (percentage >= 80) return 'bg-orange-500'
    return 'bg-primary'
  }

  const getImpactMessage = (budget: BudgetProgress) => {
    if (expenseAmount === 0) return null

    const newSpent = budget.current_spent + expenseAmount
    const newPercentage = budget.budget_limit > 0 ? (newSpent / budget.budget_limit) * 100 : 0
    
    if (newPercentage >= 100 && budget.spent_percentage < 100) {
      return {
        type: 'exceeded',
        message: `This expense will put you ${formatCurrency(newSpent - budget.budget_limit)} over budget`
      }
    } else if (newPercentage >= 80 && budget.spent_percentage < 80) {
      return {
        type: 'warning',
        message: `This expense will bring you to ${newPercentage.toFixed(1)}% of your budget`
      }
    } else if (newPercentage > budget.spent_percentage) {
      return {
        type: 'info',
        message: `This will increase your budget usage to ${newPercentage.toFixed(1)}%`
      }
    }

    return null
  }

  if (!categoryId || budgetProgress.length === 0) {
    return null
  }

  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="pt-6">
          <div className="flex items-center justify-center">
            <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
            <span className="ml-2 text-sm text-muted-foreground">Loading budget info...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <TrendingUp className="h-4 w-4" />
          Budget Impact
        </CardTitle>
        <CardDescription className="text-xs">
          How this expense affects your budgets
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {budgetProgress.map((budget) => {
          const impact = getImpactMessage(budget)
          const newSpent = budget.current_spent + expenseAmount
          const newPercentage = budget.budget_limit > 0 ? (newSpent / budget.budget_limit) * 100 : 0

          return (
            <div key={budget.budget_id} className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{budget.budget_name}</span>
                  {budget.is_over_budget && (
                    <Badge variant="destructive" className="text-xs">
                      Over Budget
                    </Badge>
                  )}
                  {budget.is_warning_threshold_reached && !budget.is_over_budget && (
                    <Badge variant="outline" className="text-xs text-orange-600 border-orange-600">
                      Warning
                    </Badge>
                  )}
                </div>
                <span className="text-xs text-muted-foreground">
                  {formatCurrency(budget.current_spent)} / {formatCurrency(budget.budget_limit)}
                </span>
              </div>

              {/* Current Progress */}
              <div className="space-y-1">
                <div className="relative">
                  <Progress 
                    value={Math.min(budget.spent_percentage, 100)} 
                    className="h-2"
                  />
                  <div 
                    className={`absolute top-0 left-0 h-2 rounded-full transition-all ${getProgressColor(budget.spent_percentage)}`}
                    style={{ width: `${Math.min(budget.spent_percentage, 100)}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Current: {budget.spent_percentage.toFixed(1)}%</span>
                  <span>{formatCurrency(budget.remaining_amount)} remaining</span>
                </div>
              </div>

              {/* Impact Preview */}
              {expenseAmount > 0 && (
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">After this expense:</div>
                  <div className="relative">
                    <Progress 
                      value={Math.min(newPercentage, 100)} 
                      className="h-2"
                    />
                    <div 
                      className={`absolute top-0 left-0 h-2 rounded-full transition-all ${getProgressColor(newPercentage, true)}`}
                      style={{ width: `${Math.min(newPercentage, 100)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className={newPercentage >= 100 ? 'text-destructive' : newPercentage >= 80 ? 'text-orange-600' : 'text-muted-foreground'}>
                      New: {newPercentage.toFixed(1)}%
                    </span>
                    <span className={newSpent > budget.budget_limit ? 'text-destructive' : 'text-muted-foreground'}>
                      {formatCurrency(budget.budget_limit - newSpent)} remaining
                    </span>
                  </div>
                </div>
              )}

              {/* Impact Message */}
              {impact && (
                <div className={`flex items-start gap-2 p-2 rounded-md text-xs ${
                  impact.type === 'exceeded' ? 'bg-destructive/10 text-destructive' :
                  impact.type === 'warning' ? 'bg-orange-50 text-orange-700' :
                  'bg-blue-50 text-blue-700'
                }`}>
                  {impact.type === 'exceeded' && <AlertTriangle className="h-3 w-3 mt-0.5 flex-shrink-0" />}
                  {impact.type === 'warning' && <AlertTriangle className="h-3 w-3 mt-0.5 flex-shrink-0" />}
                  {impact.type === 'info' && <DollarSign className="h-3 w-3 mt-0.5 flex-shrink-0" />}
                  <span>{impact.message}</span>
                </div>
              )}
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}