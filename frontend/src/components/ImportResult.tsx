import React, { useState } from 'react'
import { CheckCircle, AlertTriangle, Undo, Download, Home } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'

interface ImportConfirmResponse {
  import_id: string
  success: boolean
  imported_count: number
  skipped_count: number
  duplicate_count: number
  errors: string[]
}

interface ImportResultProps {
  result: ImportConfirmResponse
  rollbackToken?: string
  onRollback?: () => void
  onNewImport: () => void
  onGoToDashboard: () => void
}

export function ImportResult({ 
  result, 
  rollbackToken, 
  onRollback, 
  onNewImport, 
  onGoToDashboard 
}: ImportResultProps) {
  const [rollingBack, setRollingBack] = useState(false)

  const handleRollback = async () => {
    if (!rollbackToken || !onRollback) return

    setRollingBack(true)
    try {
      const response = await fetch(`/api/statement-import/rollback/${rollbackToken}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // Add auth headers here when authentication is implemented
        }
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Rollback failed')
      }

      onRollback()
    } catch (error) {
      console.error('Rollback failed:', error)
      // You might want to show an error toast here
    } finally {
      setRollingBack(false)
    }
  }

  const getTotalProcessed = () => {
    return result.imported_count + result.skipped_count + result.duplicate_count
  }

  const getSuccessRate = () => {
    const total = getTotalProcessed()
    if (total === 0) return 0
    return Math.round((result.imported_count / total) * 100)
  }

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {result.success ? (
                <CheckCircle className="h-6 w-6 text-green-600" />
              ) : (
                <AlertTriangle className="h-6 w-6 text-destructive" />
              )}
              <div>
                <CardTitle>
                  {result.success ? 'Import Completed' : 'Import Failed'}
                </CardTitle>
                <CardDescription>
                  {result.success 
                    ? 'Your transactions have been successfully imported'
                    : 'There were issues importing your transactions'
                  }
                </CardDescription>
              </div>
            </div>
            <Badge variant={result.success ? "default" : "destructive"} className="text-sm">
              {result.success ? `${getSuccessRate()}% Success` : 'Failed'}
            </Badge>
          </div>
        </CardHeader>
      </Card>

      {/* Statistics */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Import Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-2xl font-bold text-green-600">{result.imported_count}</p>
              <p className="text-sm text-green-700">Successfully Imported</p>
            </div>
            
            <div className="text-center p-4 bg-orange-50 border border-orange-200 rounded-lg">
              <p className="text-2xl font-bold text-orange-600">{result.duplicate_count}</p>
              <p className="text-sm text-orange-700">Duplicates Skipped</p>
            </div>
            
            <div className="text-center p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <p className="text-2xl font-bold text-gray-600">{result.skipped_count}</p>
              <p className="text-sm text-gray-700">Other Skipped</p>
            </div>
            
            <div className="text-center p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-2xl font-bold text-blue-600">{getTotalProcessed()}</p>
              <p className="text-sm text-blue-700">Total Processed</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Success Details */}
      {result.success && result.imported_count > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              Import Successful
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-green-800 font-medium">
                {result.imported_count} transaction{result.imported_count !== 1 ? 's' : ''} 
                {result.imported_count === 1 ? ' has' : ' have'} been added to your expense tracker.
              </p>
              <p className="text-green-700 text-sm mt-1">
                You can now view and manage these expenses in your dashboard.
              </p>
            </div>

            {result.duplicate_count > 0 && (
              <div className="p-4 bg-orange-50 border border-orange-200 rounded-lg">
                <p className="text-orange-800 font-medium">
                  {result.duplicate_count} potential duplicate{result.duplicate_count !== 1 ? 's were' : ' was'} automatically skipped.
                </p>
                <p className="text-orange-700 text-sm mt-1">
                  These transactions appear to already exist in your expense tracker.
                </p>
              </div>
            )}

            {rollbackToken && (
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-blue-800 font-medium">Rollback Available</p>
                <p className="text-blue-700 text-sm mt-1">
                  If you notice any issues with the imported transactions, you can undo this import.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Errors */}
      {result.errors.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-5 w-5" />
              Import Errors ({result.errors.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {result.errors.map((error, index) => (
                <div key={index} className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                  <p className="text-destructive text-sm">{error}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-4 justify-between">
        <div className="flex gap-2">
          <Button onClick={onNewImport} variant="outline">
            Import Another Statement
          </Button>
          
          {rollbackToken && onRollback && (
            <Button 
              onClick={handleRollback} 
              variant="outline"
              disabled={rollingBack}
              className="text-destructive hover:text-destructive"
            >
              {rollingBack ? (
                <>
                  <div className="animate-spin h-4 w-4 mr-2 border-2 border-destructive border-t-transparent rounded-full" />
                  Rolling Back...
                </>
              ) : (
                <>
                  <Undo className="h-4 w-4 mr-2" />
                  Undo Import
                </>
              )}
            </Button>
          )}
        </div>

        <div className="flex gap-2">
          {result.success && result.imported_count > 0 && (
            <Button onClick={onGoToDashboard}>
              <Home className="h-4 w-4 mr-2" />
              View Dashboard
            </Button>
          )}
        </div>
      </div>

      {/* Import ID for reference */}
      <Card>
        <CardContent className="pt-6">
          <div className="text-center text-sm text-muted-foreground">
            <p>Import ID: <code className="bg-muted px-2 py-1 rounded text-xs">{result.import_id}</code></p>
            <p className="mt-1">Keep this ID for your records</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}