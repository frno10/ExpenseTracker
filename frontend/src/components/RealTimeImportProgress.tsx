/**
 * Real-time import progress component
 */
import React, { useState, useEffect } from 'react'
import { useRealTimeImportProgress } from '../contexts/WebSocketContext'
import { Progress } from './ui/progress'
import { CheckCircle, AlertCircle, Upload, X } from 'lucide-react'

interface ImportProgressProps {
  importId: string
  onComplete?: (result: any) => void
  onCancel?: () => void
}

interface ImportState {
  progress: number
  status: string
  isComplete: boolean
  result?: any
  error?: string
}

export const RealTimeImportProgress: React.FC<ImportProgressProps> = ({
  importId,
  onComplete,
  onCancel
}) => {
  const [importState, setImportState] = useState<ImportState>({
    progress: 0,
    status: 'Starting...',
    isComplete: false
  })

  const handleProgress = (progress: number, status: string) => {
    setImportState(prev => ({
      ...prev,
      progress,
      status,
      error: undefined
    }))
  }

  const handleComplete = (result: any) => {
    setImportState(prev => ({
      ...prev,
      progress: 100,
      status: 'Completed',
      isComplete: true,
      result
    }))

    onComplete?.(result)
  }

  // Use the real-time import progress hook
  useRealTimeImportProgress(importId, handleProgress, handleComplete)

  const getStatusColor = () => {
    if (importState.error) return 'text-red-600'
    if (importState.isComplete) return 'text-green-600'
    return 'text-blue-600'
  }

  const getProgressColor = () => {
    if (importState.error) return 'bg-red-500'
    if (importState.isComplete) return 'bg-green-500'
    return 'bg-blue-500'
  }

  return (
    <div className="bg-white rounded-lg shadow-lg border p-6 max-w-md mx-auto">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          {importState.isComplete ? (
            <CheckCircle className="h-6 w-6 text-green-500 mr-2" />
          ) : importState.error ? (
            <AlertCircle className="h-6 w-6 text-red-500 mr-2" />
          ) : (
            <Upload className="h-6 w-6 text-blue-500 mr-2 animate-pulse" />
          )}
          <h3 className="text-lg font-semibold">Import Progress</h3>
        </div>
        
        {onCancel && !importState.isComplete && (
          <button
            onClick={onCancel}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      <div className="space-y-4">
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className={getStatusColor()}>{importState.status}</span>
            <span className="text-gray-500">{importState.progress}%</span>
          </div>
          
          <Progress 
            value={importState.progress} 
            className="h-2"
          />
        </div>

        {/* Import Details */}
        {importState.result && (
          <div className="bg-gray-50 rounded-lg p-4 space-y-2">
            <h4 className="font-medium text-gray-900">Import Summary</h4>
            
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Transactions Imported:</span>
                <span className="ml-2 font-medium text-green-600">
                  {importState.result.imported_count || 0}
                </span>
              </div>
              
              <div>
                <span className="text-gray-600">Duplicates Skipped:</span>
                <span className="ml-2 font-medium text-yellow-600">
                  {importState.result.skipped_count || 0}
                </span>
              </div>
              
              <div>
                <span className="text-gray-600">Total Amount:</span>
                <span className="ml-2 font-medium">
                  ${importState.result.total_amount?.toFixed(2) || '0.00'}
                </span>
              </div>
              
              <div>
                <span className="text-gray-600">Categories:</span>
                <span className="ml-2 font-medium">
                  {importState.result.categories_count || 0}
                </span>
              </div>
            </div>

            {importState.result.errors && importState.result.errors.length > 0 && (
              <div className="mt-3">
                <h5 className="text-sm font-medium text-red-600 mb-1">Errors:</h5>
                <ul className="text-xs text-red-600 space-y-1">
                  {importState.result.errors.slice(0, 3).map((error: string, index: number) => (
                    <li key={index}>• {error}</li>
                  ))}
                  {importState.result.errors.length > 3 && (
                    <li>• ... and {importState.result.errors.length - 3} more</li>
                  )}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Error Display */}
        {importState.error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center">
              <AlertCircle className="h-5 w-5 text-red-500 mr-2" />
              <span className="text-red-700 font-medium">Import Failed</span>
            </div>
            <p className="text-red-600 text-sm mt-1">{importState.error}</p>
          </div>
        )}

        {/* Action Buttons */}
        {importState.isComplete && (
          <div className="flex justify-end space-x-2">
            <button
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
            >
              Close
            </button>
            
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors"
            >
              View Expenses
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// Hook for managing import progress state
export const useImportProgress = (importId: string) => {
  const [state, setState] = useState<ImportState>({
    progress: 0,
    status: 'Initializing...',
    isComplete: false
  })

  useRealTimeImportProgress(
    importId,
    (progress, status) => {
      setState(prev => ({ ...prev, progress, status }))
    },
    (result) => {
      setState(prev => ({ ...prev, isComplete: true, result, progress: 100, status: 'Completed' }))
    }
  )

  return state
}

// Simplified progress indicator for inline use
export const ImportProgressIndicator: React.FC<{ importId: string; className?: string }> = ({
  importId,
  className = ''
}) => {
  const state = useImportProgress(importId)

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      {state.isComplete ? (
        <CheckCircle className="h-4 w-4 text-green-500" />
      ) : (
        <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-500 border-t-transparent" />
      )}
      
      <span className="text-sm text-gray-600">
        {state.status} ({state.progress}%)
      </span>
      
      {!state.isComplete && (
        <div className="w-16 bg-gray-200 rounded-full h-1">
          <div
            className="bg-blue-500 h-1 rounded-full transition-all duration-300"
            style={{ width: `${state.progress}%` }}
          />
        </div>
      )}
    </div>
  )
}