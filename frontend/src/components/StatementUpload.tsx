import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, AlertCircle, CheckCircle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { Progress } from './ui/progress'

interface FileUploadResponse {
  upload_id: string
  filename: string
  file_size: number
  file_type: string
  supported_format: boolean
  detected_parser?: string
  validation_errors: string[]
}

interface StatementUploadProps {
  onUploadComplete: (response: FileUploadResponse) => void
  onError: (error: string) => void
}

export function StatementUpload({ onUploadComplete, onError }: StatementUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [bankHint, setBankHint] = useState('')

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return

    const file = acceptedFiles[0]
    setUploading(true)
    setUploadProgress(0)

    try {
      const formData = new FormData()
      formData.append('file', file)
      if (bankHint) {
        formData.append('bank_hint', bankHint)
      }

      // Simulate progress for better UX
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 10, 90))
      }, 200)

      const response = await fetch('/api/statement-import/upload', {
        method: 'POST',
        body: formData,
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
      })

      clearInterval(progressInterval)
      setUploadProgress(100)

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Upload failed')
      }

      const result: FileUploadResponse = await response.json()
      onUploadComplete(result)
    } catch (error) {
      onError(error instanceof Error ? error.message : 'Upload failed')
    } finally {
      setUploading(false)
      setUploadProgress(0)
    }
  }, [bankHint, onUploadComplete, onError])

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/csv': ['.csv'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/x-ofx': ['.ofx'],
      'text/plain': ['.txt', '.qif']
    },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024, // 50MB
    disabled: uploading
  })

  const getSupportedFormats = () => [
    'PDF', 'CSV', 'Excel (XLS/XLSX)', 'OFX', 'QIF', 'Text'
  ]

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Upload className="h-5 w-5" />
          Upload Bank Statement
        </CardTitle>
        <CardDescription>
          Upload your bank statement to automatically import transactions
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Bank Hint Input */}
        <div className="space-y-2">
          <label htmlFor="bank-hint" className="text-sm font-medium">
            Bank Name (Optional)
          </label>
          <input
            id="bank-hint"
            type="text"
            placeholder="e.g., Chase, Bank of America, Wells Fargo"
            value={bankHint}
            onChange={(e) => setBankHint(e.target.value)}
            className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm"
            disabled={uploading}
          />
          <p className="text-xs text-muted-foreground">
            Providing your bank name helps us choose the best parser for your statement
          </p>
        </div>

        {/* Upload Area */}
        <div
          {...getRootProps()}
          className={`
            border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
            ${isDragActive && !isDragReject ? 'border-primary bg-primary/5' : ''}
            ${isDragReject ? 'border-destructive bg-destructive/5' : ''}
            ${uploading ? 'cursor-not-allowed opacity-50' : 'hover:border-primary/50'}
            ${!isDragActive && !isDragReject ? 'border-border' : ''}
          `}
        >
          <input {...getInputProps()} />

          {uploading ? (
            <div className="space-y-4">
              <div className="animate-spin mx-auto h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
              <div className="space-y-2">
                <p className="text-sm font-medium">Uploading...</p>
                <Progress value={uploadProgress} className="w-full max-w-xs mx-auto" />
                <p className="text-xs text-muted-foreground">{uploadProgress}%</p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
              <div className="space-y-2">
                <p className="text-lg font-medium">
                  {isDragActive
                    ? isDragReject
                      ? 'File type not supported'
                      : 'Drop your statement here'
                    : 'Drag & drop your statement here'}
                </p>
                <p className="text-sm text-muted-foreground">
                  or click to browse files
                </p>
              </div>
              <Button variant="outline" size="sm" disabled={uploading}>
                Choose File
              </Button>
            </div>
          )}
        </div>

        {/* Supported Formats */}
        <div className="space-y-3">
          <h4 className="text-sm font-medium">Supported Formats:</h4>
          <div className="flex flex-wrap gap-2">
            {getSupportedFormats().map((format) => (
              <Badge key={format} variant="secondary" className="text-xs">
                {format}
              </Badge>
            ))}
          </div>
          <div className="flex items-start gap-2 p-3 bg-muted/50 rounded-md">
            <AlertCircle className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
            <div className="text-xs text-muted-foreground">
              <p className="font-medium mb-1">File Requirements:</p>
              <ul className="space-y-1">
                <li>• Maximum file size: 50MB</li>
                <li>• Files are scanned for security</li>
                <li>• Temporary files are automatically deleted</li>
              </ul>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}