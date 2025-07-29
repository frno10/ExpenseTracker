import React from 'react'
import { AlertTriangle, X, TrendingUp } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'

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

interface BudgetAlertsProps {
  alerts: BudgetAlert[]
  onAlertDismissed?: () => void
}

export function BudgetAlerts({ alerts, onAlertDismissed }: BudgetAlertsProps) {
  if (alerts.length === 0) return null

  const exceededAlerts = alerts.filter(alert => alert.alert_type === 'exceeded')
  const warningAlerts = alerts.filter(alert => alert.alert_type === 'warning')

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount)
  }

  const getAlertIcon = (alertType: string) => {
    return alertType === 'exceeded' ? (
      <AlertTriangle className="h-4 w-4 text-destructive" />
    ) : (
      <AlertTriangle className="h-4 w-4 text-orange-500" />
    )
  }

  const getAlertBadge = (alertType: string) => {
    return alertType === 'exceeded' ? (
      <Badge variant="destructive" className="text-xs">
        Over Budget
      </Badge>
    ) : (
      <Badge variant="outline" className="text-xs text-orange-600 border-orange-600">
        Warning
      </Badge>
    )
  }

  return (
    <div className="space-y-4">
      {/* Exceeded Budgets */}
      {exceededAlerts.length > 0 && (
        <Card className="border-destructive bg-destructive/5">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-destructive" />
                <CardTitle className="text-lg text-destructive">
                  Budget Exceeded ({exceededAlerts.length})
                </CardTitle>
              </div>
              {onAlertDismissed && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onAlertDismissed}
                  className="text-destructive hover:text-destructive"
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
            <CardDescription>
              These budgets have exceeded their limits and need attention
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {exceededAlerts.map((alert, index) => (
                <div
                  key={`${alert.budget_id}-${alert.category_id || 'total'}-${index}`}
                  className="flex items-start justify-between p-3 bg-background rounded-lg border"
                >
                  <div className="flex items-start gap-3">
                    {getAlertIcon(alert.alert_type)}
                    <div className="space-y-1">
                      <p className="text-sm font-medium">{alert.message}</p>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>Spent: {formatCurrency(alert.amount_spent)}</span>
                        <span>Limit: {formatCurrency(alert.amount_limit)}</span>
                        <span>Over by: {formatCurrency(Math.abs(alert.amount_remaining))}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {getAlertBadge(alert.alert_type)}
                    <Badge variant="secondary" className="text-xs">
                      {alert.percentage_used.toFixed(1)}%
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Warning Alerts */}
      {warningAlerts.length > 0 && (
        <Card className="border-orange-500 bg-orange-50/50">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-orange-500" />
                <CardTitle className="text-lg text-orange-700">
                  Budget Warnings ({warningAlerts.length})
                </CardTitle>
              </div>
              {onAlertDismissed && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onAlertDismissed}
                  className="text-orange-500 hover:text-orange-600"
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
            <CardDescription>
              These budgets are approaching their limits (80%+ used)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {warningAlerts.map((alert, index) => (
                <div
                  key={`${alert.budget_id}-${alert.category_id || 'total'}-${index}`}
                  className="flex items-start justify-between p-3 bg-background rounded-lg border"
                >
                  <div className="flex items-start gap-3">
                    {getAlertIcon(alert.alert_type)}
                    <div className="space-y-1">
                      <p className="text-sm font-medium">{alert.message}</p>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>Spent: {formatCurrency(alert.amount_spent)}</span>
                        <span>Limit: {formatCurrency(alert.amount_limit)}</span>
                        <span>Remaining: {formatCurrency(alert.amount_remaining)}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {getAlertBadge(alert.alert_type)}
                    <Badge variant="secondary" className="text-xs">
                      {alert.percentage_used.toFixed(1)}%
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Actions */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Quick Actions</span>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm">
                Adjust Budgets
              </Button>
              <Button variant="outline" size="sm">
                View Analytics
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}