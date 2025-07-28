import React, { useState, useEffect } from 'react'
import { CheckCircle, AlertTriangle, RefreshCw, Download, Undo } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'

interface ImportConfirmRequest {
  upload_id: string
  selected_transactions?: number[]
  category_mappings?: Record<string, string>
  merchant_mappings?: Record<string, string>
}

interface ImportConfirmResponse {
  import_id: string
  success: boolean
  imported_count: number
  skipped_count: number
  duplicate_count: number
  errors: string[]
}

interface DuplicateAnalysis {
  upload_id: string
  total_transactions: number
  likely_duplicates: number
  analysis: Array<{
    transaction_index: number
    transaction: {
      date: string
      description: string
      amount: number
      merchant: string
    }
    is_likely_duplicate: boolean
    confidence_score: number
    potential_duplicates: Array<{
      expense_id: string
      match_score: number
      match_reasons: string[]
    }>
  }>
}

interface ImportConfirmationProps {
  uploadId: string
  transactionCount: number
  onImportComplete: (response: ImportConfirmResponse) => void
  onError: (error: string) => void
  onBack: () => void
}

export function ImportConfirmation({ 
  uploadId, 
  transactionCount, 
  onImportComplete, 
  onError, 
  onBack 
}: ImportConfirmationProps) {
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(true)
  const [duplicateAnalysis, setDuplicateAnalysis] = useState<DuplicateAnalysis | null>(null)
  const [selectedTransactions, setSelectedTransactions] = useState<number[]>([])
  const [categoryMappings, setCategoryMappings] = useState<Record<string, string>>({})
  const [merchantMappings, setMerchantMappings] = useState<Record<string, string>>({})

  useEffect(() => {
    analyzeDuplicates()
  }, [uploadId])

  const analyzeDuplicates = async () => {
    setAnalyzing(true)
    try {
      const response = await fetch(`/api/statement-import/analyze-duplicates/${uploadId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // Add auth headers here when authentication is implemented
        }
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Duplicate analysis failed')
      }

      const result: DuplicateAnalysis = await response.json()
      setDuplicateAnalysis(result)
      
      // Pre-select non-duplicate transactions
      const nonDuplicates = result.analysis
        .filter(item => !item.is_likely_duplicate)
        .map(item => item.transaction_index)
      setSelectedTransactions(nonDuplicates)
      
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Duplicate analysis failed')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleImport = async () => {
    setLoading(true)
    try {
      const request: ImportConfirmRequest = {
        upload_id: uploadId,
        selected_transactions: selectedTransactions.length > 0 ? selectedTransactions : undefined,
        category_mappings: Object.keys(categoryMappings).length > 0 ? categoryMappings : undefined,
        merchant_mappings: Object.keys(merchantMappings).length > 0 ? merchantMappings : undefined
      }

      const response = await fetch(`/api/statement-import/confirm/${uploadId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // Add auth headers here when authentication is implemented
        },
        body: JSON.stringify(request)
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Import failed')
      }

      const result: ImportConfirmResponse = await response.json()
      onImportComplete(result)
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Import failed')
    } finally {
      setLoading(false)
    }
  }

  const toggleTransaction = (index: number) => {
    setSelectedTransactions(prev => 
      prev.includes(index) 
        ? prev.filter(i => i !== index)
        : [...prev, index]
    )
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

  if (analyzing) {
    return (
      <Card className="w-full max-w-4xl mx-auto">
        <CardContent className="flex items-center justify-center py-12">
          <div className="text-center space-y-4">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto text-primary" />
            <div>
              <p className="font-medium">Analyzing Transactions</p>
              <p className="text-sm text-muted-foreground">
                Checking for potential duplicates in your existing expenses...
              </p>
            </div>
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
              <CheckCircle className="h-5 w-5 text-primary" />
              <div>
                <CardTitle>Confirm Import</CardTitle>
                <CardDescription>
                  Review and confirm which transactions to import
                </CardDescription>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-muted/50 rounded-lg">
              <p className="text-2xl font-bold text-primary">{transactionCount}</p>
              <p className="text-sm text-muted-foreground">Total Transactions</p>
            </div>
            <div className="text-center p-4 bg-muted/50 rounded-lg">
              <p className="text-2xl font-bold text-green-600">{selectedTransactions.length}</p>
              <p className="text-sm text-muted-foreground">Selected to Import</p>
            </div>
            <div className="text-center p-4 bg-muted/50 rounded-lg">
              <p className="text-2xl font-bold text-orange-600">
                {duplicateAnalysis?.likely_duplicates || 0}
              </p>
              <p className="text-sm text-muted-foreground">Likely Duplicates</p>
            </div>
            <div className="text-center p-4 bg-muted/50 rounded-lg">
              <p className="text-2xl font-bold text-muted-foreground">
                {transactionCount - selectedTransactions.length}
              </p>
              <p className="text-sm text-muted-foreground">Will be Skipped</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Transaction Selection */}
      {duplicateAnalysis && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg">Transaction Selection</CardTitle>
                <CardDescription>
                  Select which transactions to import. Likely duplicates are deselected by default.
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setSelectedTransactions(
                    duplicateAnalysis.analysis.map((_, index) => index)
                  )}
                >
                  Select All
                </Button>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setSelectedTransactions([])}
                >
                  Select None
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {duplicateAnalysis.analysis.map((item) => (
                <div 
                  key={item.transaction_index}
                  className={`
                    flex items-center gap-4 p-3 border rounded-lg cursor-pointer transition-colors
                    ${selectedTransactions.includes(item.transaction_index) 
                      ? 'bg-primary/5 border-primary' 
                      : 'hover:bg-muted/50'
                    }
                    ${item.is_likely_duplicate ? 'border-orange-200 bg-orange-50/50' : ''}
                  `}
                  onClick={() => toggleTransaction(item.transaction_index)}
                >
                  <input
                    type="checkbox"
                    checked={selectedTransactions.includes(item.transaction_index)}
                    onChange={() => toggleTransaction(item.transaction_index)}
                    className="h-4 w-4"
                  />
                  
                  <div className="flex-1 grid grid-cols-1 md:grid-cols-4 gap-2">
                    <div>
                      <p className="text-sm font-medium">
                        {formatDate(item.transaction.date)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium">
                        {item.transaction.description}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {item.transaction.merchant}
                      </p>
                    </div>
                    <div>
                      <p className={`text-sm font-medium ${
                        item.transaction.amount < 0 ? 'text-destructive' : 'text-green-600'
                      }`}>
                        {item.transaction.amount < 0 ? '-' : '+'}
                        {formatCurrency(item.transaction.amount)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {item.is_likely_duplicate && (
                        <Badge variant="outline" className="text-xs text-orange-600">
                          <AlertTriangle className="h-3 w-3 mr-1" />
                          Likely Duplicate
                        </Badge>
                      )}
                      <Badge variant="secondary" className="text-xs">
                        {Math.round(item.confidence_score * 100)}% confidence
                      </Badge>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="flex justify-between">
        <Button onClick={onBack} variant="outline">
          Back to Preview
        </Button>
        
        <div className="flex gap-2">
          <Button onClick={analyzeDuplicates} variant="outline" disabled={analyzing}>
            <RefreshCw className={`h-4 w-4 mr-2 ${analyzing ? 'animate-spin' : ''}`} />
            Re-analyze
          </Button>
          
          <Button 
            onClick={handleImport} 
            disabled={loading || selectedTransactions.length === 0}
          >
            {loading ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Importing...
              </>
            ) : (
              <>
                Import {selectedTransactions.length} Transaction{selectedTransactions.length !== 1 ? 's' : ''}
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}