import { useState } from 'react'
import { StatementUpload } from '../components/StatementUpload'
import { StatementPreview } from '../components/StatementPreview'
import { ImportConfirmation } from '../components/ImportConfirmation'
import { ImportResult } from '../components/ImportResult'

type ImportStep = 'upload' | 'preview' | 'confirm' | 'result'

interface FileUploadResponse {
  upload_id: string
  filename: string
  file_size: number
  file_type: string
  supported_format: boolean
  detected_parser?: string
  validation_errors: string[]
}

interface ParsePreviewResponse {
  upload_id: string
  success: boolean
  transaction_count: number
  sample_transactions: any[]
  errors: string[]
  warnings: string[]
  metadata: Record<string, any>
}

interface ImportConfirmResponse {
  import_id: string
  success: boolean
  imported_count: number
  skipped_count: number
  duplicate_count: number
  errors: string[]
}

export function StatementImport() {
  const [currentStep, setCurrentStep] = useState<ImportStep>('upload')
  const [uploadResponse, setUploadResponse] = useState<FileUploadResponse | null>(null)
  const [previewResponse, setPreviewResponse] = useState<ParsePreviewResponse | null>(null)
  const [importResponse, setImportResponse] = useState<ImportConfirmResponse | null>(null)
  const [rollbackToken, setRollbackToken] = useState<string | undefined>()
  const [error, setError] = useState<string | null>(null)

  const handleUploadComplete = (response: FileUploadResponse) => {
    setUploadResponse(response)
    setError(null)
    
    if (response.validation_errors.length > 0) {
      setError(`Upload validation failed: ${response.validation_errors.join(', ')}`)
      return
    }
    
    setCurrentStep('preview')
  }

  const handlePreviewComplete = (response: ParsePreviewResponse) => {
    setPreviewResponse(response)
    setError(null)
    
    if (!response.success) {
      setError(`Statement parsing failed: ${response.errors.join(', ')}`)
      return
    }
    
    if (response.transaction_count === 0) {
      setError('No transactions found in the statement')
      return
    }
    
    setCurrentStep('confirm')
  }

  const handleImportComplete = (response: ImportConfirmResponse) => {
    setImportResponse(response)
    setError(null)
    
    // Extract rollback token from response if available
    // Note: This would need to be added to the API response
    // setRollbackToken(response.rollback_token)
    
    setCurrentStep('result')
  }

  const handleError = (errorMessage: string) => {
    setError(errorMessage)
  }

  const handleRollback = () => {
    // Reset to upload step after successful rollback
    setCurrentStep('upload')
    setUploadResponse(null)
    setPreviewResponse(null)
    setImportResponse(null)
    setRollbackToken(undefined)
    setError(null)
  }

  const handleNewImport = () => {
    // Reset everything for a new import
    setCurrentStep('upload')
    setUploadResponse(null)
    setPreviewResponse(null)
    setImportResponse(null)
    setRollbackToken(undefined)
    setError(null)
  }

  const handleGoToDashboard = () => {
    // Navigate to dashboard - this would use React Router in a real app
    window.location.href = '/'
  }

  const getStepTitle = () => {
    switch (currentStep) {
      case 'upload':
        return 'Upload Statement'
      case 'preview':
        return 'Preview Transactions'
      case 'confirm':
        return 'Confirm Import'
      case 'result':
        return 'Import Complete'
      default:
        return 'Statement Import'
    }
  }

  const getStepDescription = () => {
    switch (currentStep) {
      case 'upload':
        return 'Upload your bank statement file to get started'
      case 'preview':
        return 'Review the extracted transactions before importing'
      case 'confirm':
        return 'Select which transactions to import and check for duplicates'
      case 'result':
        return 'Review the import results and next steps'
      default:
        return 'Import transactions from your bank statement'
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">{getStepTitle()}</h1>
              <p className="text-muted-foreground mt-1">{getStepDescription()}</p>
            </div>
            
            {/* Step Indicator */}
            <div className="hidden md:flex items-center space-x-4">
              {(['upload', 'preview', 'confirm', 'result'] as const).map((step, index) => {
                const isActive = currentStep === step
                const isCompleted = ['upload', 'preview', 'confirm', 'result'].indexOf(currentStep) > index
                
                return (
                  <div key={step} className="flex items-center">
                    <div className={`
                      flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium
                      ${isActive ? 'bg-primary text-primary-foreground' : ''}
                      ${isCompleted ? 'bg-green-600 text-white' : ''}
                      ${!isActive && !isCompleted ? 'bg-muted text-muted-foreground' : ''}
                    `}>
                      {isCompleted ? '✓' : index + 1}
                    </div>
                    {index < 3 && (
                      <div className={`
                        w-12 h-0.5 mx-2
                        ${isCompleted ? 'bg-green-600' : 'bg-muted'}
                      `} />
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="container mx-auto px-4 py-4">
          <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
            <div className="flex items-center gap-2">
              <div className="h-4 w-4 text-destructive">⚠</div>
              <p className="text-destructive font-medium">Error</p>
            </div>
            <p className="text-destructive text-sm mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        {currentStep === 'upload' && (
          <StatementUpload
            onUploadComplete={handleUploadComplete}
            onError={handleError}
          />
        )}

        {currentStep === 'preview' && uploadResponse && (
          <StatementPreview
            uploadId={uploadResponse.upload_id}
            onPreviewComplete={handlePreviewComplete}
            onError={handleError}
            onBack={() => setCurrentStep('upload')}
          />
        )}

        {currentStep === 'confirm' && uploadResponse && previewResponse && (
          <ImportConfirmation
            uploadId={uploadResponse.upload_id}
            transactionCount={previewResponse.transaction_count}
            onImportComplete={handleImportComplete}
            onError={handleError}
            onBack={() => setCurrentStep('preview')}
          />
        )}

        {currentStep === 'result' && importResponse && (
          <ImportResult
            result={importResponse}
            rollbackToken={rollbackToken}
            onRollback={rollbackToken ? handleRollback : undefined}
            onNewImport={handleNewImport}
            onGoToDashboard={handleGoToDashboard}
          />
        )}
      </div>
    </div>
  )
}