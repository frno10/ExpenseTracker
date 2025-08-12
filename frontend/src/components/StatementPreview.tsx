import React, { useState, useEffect } from 'react'
import { Eye, AlertTriangle, CheckCircle, RefreshCw, Download } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'

interface ParsedTransaction {
  index: number
  date: string
  description: string
  amount: number
  merchant: string
  category: string
  account: string
  reference: string
}

interface ParsePreviewResponse {
  upload_id: string
  success: boolean
  transaction_count: number
  sample_transactions: ParsedTransaction[]
  errors: string[]
  warnings: string[]
  metadata: Record<string, any>
}

interface StatementPreviewProps {
  uploadId: string
  onPreviewComplete: (response: ParsePreviewResponse) => void
  onError: (error: string) => void
  onBack: () => void
}

export function StatementPreview({ uploadId, onPreviewComplete, onError, onBack }: StatementPreviewProps) {
  const [loading, setLoading] = useState(true)
  const [preview, setPreview] = useState<ParsePreviewResponse | null>(null)

  useEffect(() => {
    loadPreview()
  }, [uploadId])

  const loadPreview = async () => {
    setLoading(true)
    try {
      const response = await fetch(`http://localhost:8000/api/statement-import/preview/${uploadId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Preview failed')
      }

      const result: ParsePreviewResponse = await response.json()
      setPreview(result)
      onPreviewComplete(result)
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Preview failed')
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(Math.abs(amount))
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  if (loading) {
    return (
      <Card className="w-full max-w-4xl mx-auto">
        <CardContent className="flex items-center justify-center py-12">
          <div className="text-center space-y-4">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto text-primary" />
            <div>
              <p className="font-medium">Processing Statement</p>
              <p className="text-sm text-muted-foreground">
                Analyzing your file and extracting transactions...
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!preview) {
    return (
      <Card className="w-full max-w-4xl mx-auto">
        <CardContent className="flex items-center justify-center py-12">
          <div className="text-center space-y-4">
            <AlertTriangle className="h-8 w-8 text-destructive mx-auto" />
            <div>
              <p className="font-medium">Preview Failed</p>
              <p className="text-sm text-muted-foreground">
                Unable to load statement preview
              </p>
            </div>
            <Button onClick={onBack} variant="outline">
              Go Back
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Eye className="h-5 w-5" />
              <div>
                <CardTitle>Statement Preview</CardTitle>
                <CardDescription>
                  Review the extracted transactions before importing
                </CardDescription>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={preview.success ? "default" : "destructive"}>
                {preview.success ? (
                  <>
                    <CheckCircle className="h-3 w-3 mr-1" />
                    Parsed Successfully
                  </>
                ) : (
                  <>
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    Parse Failed
                  </>
                )}
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-4 bg-muted/50 rounded-lg">
              <p className="text-2xl font-bold text-primary">{preview.transaction_count}</p>
              <p className="text-sm text-muted-foreground">Transactions Found</p>
            </div>
            <div className="text-center p-4 bg-muted/50 rounded-lg">
              <p className="text-2xl font-bold text-orange-600">{preview.warnings.length}</p>
              <p className="text-sm text-muted-foreground">Warnings</p>
            </div>
            <div className="text-center p-4 bg-muted/50 rounded-lg">
              <p className="text-2xl font-bold text-destructive">{preview.errors.length}</p>
              <p className="text-sm text-muted-foreground">Errors</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Metadata */}
      {Object.keys(preview.metadata).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Statement Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(preview.metadata).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="font-medium capitalize">
                    {key.replace(/_/g, ' ')}:
                  </span>
                  <span className="text-muted-foreground">{String(value)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Errors and Warnings */}
      {(preview.errors.length > 0 || preview.warnings.length > 0) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Issues Found</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {preview.errors.length > 0 && (
              <div className="space-y-2">
                <h4 className="font-medium text-destructive flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  Errors ({preview.errors.length})
                </h4>
                <ul className="space-y-1">
                  {preview.errors.map((error, index) => (
                    <li key={index} className="text-sm text-destructive bg-destructive/10 p-2 rounded">
                      {error}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {preview.warnings.length > 0 && (
              <div className="space-y-2">
                <h4 className="font-medium text-orange-600 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  Warnings ({preview.warnings.length})
                </h4>
                <ul className="space-y-1">
                  {preview.warnings.map((warning, index) => (
                    <li key={index} className="text-sm text-orange-600 bg-orange-50 p-2 rounded">
                      {warning}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Sample Transactions */}
      {preview.sample_transactions.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg">Sample Transactions</CardTitle>
                <CardDescription>
                  Preview of the first {preview.sample_transactions.length} transactions
                  {preview.transaction_count > preview.sample_transactions.length && 
                    ` (${preview.transaction_count - preview.sample_transactions.length} more will be imported)`
                  }
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-2 font-medium">Date</th>
                    <th className="text-left p-2 font-medium">Description</th>
                    <th className="text-left p-2 font-medium">Amount</th>
                    <th className="text-left p-2 font-medium">Merchant</th>
                    <th className="text-left p-2 font-medium">Category</th>
                    <th className="text-left p-2 font-medium">Account</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.sample_transactions.map((transaction) => (
                    <tr key={transaction.index} className="border-b hover:bg-muted/50">
                      <td className="p-2 text-sm">
                        {formatDate(transaction.date)}
                      </td>
                      <td className="p-2 text-sm font-medium">
                        {transaction.description}
                      </td>
                      <td className={`p-2 text-sm font-medium ${
                        transaction.amount < 0 ? 'text-destructive' : 'text-green-600'
                      }`}>
                        {transaction.amount < 0 ? '-' : '+'}
                        {formatCurrency(transaction.amount)}
                      </td>
                      <td className="p-2 text-sm text-muted-foreground">
                        {transaction.merchant || '-'}
                      </td>
                      <td className="p-2 text-sm">
                        {transaction.category && (
                          <Badge variant="secondary" className="text-xs">
                            {transaction.category}
                          </Badge>
                        )}
                      </td>
                      <td className="p-2 text-sm text-muted-foreground">
                        {transaction.account || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="flex justify-between">
        <Button onClick={onBack} variant="outline">
          Upload Different File
        </Button>
        
        <div className="flex gap-2">
          <Button onClick={loadPreview} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh Preview
          </Button>
          
          {preview.success && preview.transaction_count > 0 && (
            <Button onClick={() => onPreviewComplete(preview)}>
              Continue to Import
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}