import React, { useState, useEffect } from 'react'
import { Plus, X, Calendar, DollarSign } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'

interface Category {
  id: string
  name: string
  color: string
}

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
  category?: Category
}

interface BudgetCreateDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onBudgetCreated: (budget: Budget) => void
}

interface CategoryBudgetForm {
  category_id: string
  limit_amount: string
}

export function BudgetCreateDialog({ open, onOpenChange, onBudgetCreated }: BudgetCreateDialogProps) {
  const [loading, setLoading] = useState(false)
  const [categories, setCategories] = useState<Category[]>([])
  
  // Form state
  const [name, setName] = useState('')
  const [period, setPeriod] = useState('monthly')
  const [totalLimit, setTotalLimit] = useState('')
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0])
  const [endDate, setEndDate] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [categoryBudgets, setCategoryBudgets] = useState<CategoryBudgetForm[]>([])

  useEffect(() => {
    if (open) {
      loadCategories()
      resetForm()
    }
  }, [open])

  const loadCategories = async () => {
    try {
      const response = await fetch('/api/categories', {
        headers: {
          // Add auth headers when authentication is implemented
        }
      })

      if (response.ok) {
        const data = await response.json()
        setCategories(data)
      }
    } catch (error) {
      console.error('Failed to load categories:', error)
    }
  }

  const resetForm = () => {
    setName('')
    setPeriod('monthly')
    setTotalLimit('')
    setStartDate(new Date().toISOString().split('T')[0])
    setEndDate('')
    setIsActive(true)
    setCategoryBudgets([])
  }

  const addCategoryBudget = () => {
    setCategoryBudgets(prev => [...prev, { category_id: '', limit_amount: '' }])
  }

  const removeCategoryBudget = (index: number) => {
    setCategoryBudgets(prev => prev.filter((_, i) => i !== index))
  }

  const updateCategoryBudget = (index: number, field: keyof CategoryBudgetForm, value: string) => {
    setCategoryBudgets(prev => prev.map((cb, i) => 
      i === index ? { ...cb, [field]: value } : cb
    ))
  }

  const getUsedCategories = () => {
    return new Set(categoryBudgets.map(cb => cb.category_id).filter(Boolean))
  }

  const getAvailableCategories = () => {
    const usedCategories = getUsedCategories()
    return categories.filter(category => !usedCategories.has(category.id))
  }

  const calculateTotalCategoryBudgets = () => {
    return categoryBudgets.reduce((sum, cb) => {
      const amount = parseFloat(cb.limit_amount) || 0
      return sum + amount
    }, 0)
  }

  const validateForm = () => {
    if (!name.trim()) return 'Budget name is required'
    if (!startDate) return 'Start date is required'
    if (endDate && new Date(endDate) <= new Date(startDate)) {
      return 'End date must be after start date'
    }
    
    // Validate category budgets
    for (let i = 0; i < categoryBudgets.length; i++) {
      const cb = categoryBudgets[i]
      if (!cb.category_id) return `Category is required for budget ${i + 1}`
      if (!cb.limit_amount || parseFloat(cb.limit_amount) <= 0) {
        return `Valid amount is required for budget ${i + 1}`
      }
    }

    // Check for duplicate categories
    const categoryIds = categoryBudgets.map(cb => cb.category_id).filter(Boolean)
    const uniqueIds = new Set(categoryIds)
    if (categoryIds.length !== uniqueIds.size) {
      return 'Each category can only have one budget'
    }

    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    const validationError = validateForm()
    if (validationError) {
      alert(validationError)
      return
    }

    setLoading(true)
    try {
      const budgetData = {
        name: name.trim(),
        period,
        total_limit: totalLimit ? parseFloat(totalLimit) : null,
        start_date: startDate,
        end_date: endDate || null,
        is_active: isActive,
        user_id: '00000000-0000-0000-0000-000000000000' // Will be set by backend
      }

      const categoryBudgetsData = categoryBudgets.map(cb => ({
        limit_amount: parseFloat(cb.limit_amount),
        budget_id: '00000000-0000-0000-0000-000000000000', // Will be set by backend
        category_id: cb.category_id
      }))

      const response = await fetch('/api/budgets/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // Add auth headers when authentication is implemented
        },
        body: JSON.stringify({
          budget: budgetData,
          category_budgets: categoryBudgetsData.length > 0 ? categoryBudgetsData : null
        })
      })

      if (response.ok) {
        const newBudget = await response.json()
        onBudgetCreated(newBudget)
        onOpenChange(false)
      } else {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to create budget')
      }
    } catch (error) {
      console.error('Error creating budget:', error)
      alert(`Failed to create budget: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setLoading(false)
    }
  }

  if (!open) return null

  const totalCategoryBudgets = calculateTotalCategoryBudgets()
  const totalBudgetAmount = totalLimit ? parseFloat(totalLimit) : 0

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Create New Budget</CardTitle>
              <CardDescription>
                Set spending limits for your categories and track your financial goals
              </CardDescription>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Information */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Basic Information</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label htmlFor="name" className="text-sm font-medium">
                    Budget Name *
                  </label>
                  <input
                    id="name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g., Monthly Budget, Q1 2024"
                    className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                    required
                    disabled={loading}
                  />
                </div>

                <div className="space-y-2">
                  <label htmlFor="period" className="text-sm font-medium">
                    Period
                  </label>
                  <select
                    id="period"
                    value={period}
                    onChange={(e) => setPeriod(e.target.value)}
                    className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                    disabled={loading}
                  >
                    <option value="monthly">Monthly</option>
                    <option value="quarterly">Quarterly</option>
                    <option value="yearly">Yearly</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label htmlFor="startDate" className="text-sm font-medium">
                    Start Date *
                  </label>
                  <input
                    id="startDate"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                    required
                    disabled={loading}
                  />
                </div>

                <div className="space-y-2">
                  <label htmlFor="endDate" className="text-sm font-medium">
                    End Date {period === 'custom' && '*'}
                  </label>
                  <input
                    id="endDate"
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
                    required={period === 'custom'}
                    disabled={loading}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label htmlFor="totalLimit" className="text-sm font-medium">
                  Total Budget Limit (Optional)
                </label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <input
                    id="totalLimit"
                    type="number"
                    step="0.01"
                    min="0"
                    value={totalLimit}
                    onChange={(e) => setTotalLimit(e.target.value)}
                    placeholder="0.00"
                    className="w-full pl-10 pr-3 py-2 border border-input rounded-md bg-background text-sm"
                    disabled={loading}
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Leave empty to use the sum of category budgets as the total limit
                </p>
              </div>

              <div className="flex items-center space-x-2">
                <input
                  id="isActive"
                  type="checkbox"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="h-4 w-4"
                  disabled={loading}
                />
                <label htmlFor="isActive" className="text-sm font-medium">
                  Active budget
                </label>
              </div>
            </div>

            {/* Category Budgets */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Category Budgets</h3>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addCategoryBudget}
                  disabled={loading || getAvailableCategories().length === 0}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Category
                </Button>
              </div>

              {categoryBudgets.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <p>No category budgets added yet.</p>
                  <p className="text-sm">Add category budgets to track spending by category.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {categoryBudgets.map((categoryBudget, index) => (
                    <div key={index} className="flex items-center gap-3 p-3 border rounded-lg">
                      <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-3">
                        <select
                          value={categoryBudget.category_id}
                          onChange={(e) => updateCategoryBudget(index, 'category_id', e.target.value)}
                          className="px-3 py-2 border border-input rounded-md bg-background text-sm"
                          required
                          disabled={loading}
                        >
                          <option value="">Select category...</option>
                          {getAvailableCategories().map(category => (
                            <option key={category.id} value={category.id}>
                              {category.name}
                            </option>
                          ))}
                          {categoryBudget.category_id && !getAvailableCategories().find(c => c.id === categoryBudget.category_id) && (
                            <option value={categoryBudget.category_id}>
                              {categories.find(c => c.id === categoryBudget.category_id)?.name || 'Unknown'}
                            </option>
                          )}
                        </select>

                        <div className="relative">
                          <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            value={categoryBudget.limit_amount}
                            onChange={(e) => updateCategoryBudget(index, 'limit_amount', e.target.value)}
                            placeholder="0.00"
                            className="w-full pl-10 pr-3 py-2 border border-input rounded-md bg-background text-sm"
                            required
                            disabled={loading}
                          />
                        </div>
                      </div>

                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeCategoryBudget(index)}
                        disabled={loading}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}

              {/* Budget Summary */}
              {(totalCategoryBudgets > 0 || totalBudgetAmount > 0) && (
                <div className="p-3 bg-muted/50 rounded-lg space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span>Category Budgets Total:</span>
                    <span className="font-medium">${totalCategoryBudgets.toFixed(2)}</span>
                  </div>
                  {totalBudgetAmount > 0 && (
                    <div className="flex items-center justify-between text-sm">
                      <span>Total Budget Limit:</span>
                      <span className="font-medium">${totalBudgetAmount.toFixed(2)}</span>
                    </div>
                  )}
                  {totalBudgetAmount > 0 && totalCategoryBudgets > totalBudgetAmount && (
                    <div className="text-xs text-orange-600">
                      ⚠️ Category budgets exceed total limit by ${(totalCategoryBudgets - totalBudgetAmount).toFixed(2)}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 pt-4 border-t">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={loading}>
                {loading ? (
                  <>
                    <div className="animate-spin h-4 w-4 mr-2 border-2 border-primary-foreground border-t-transparent rounded-full" />
                    Creating...
                  </>
                ) : (
                  'Create Budget'
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}