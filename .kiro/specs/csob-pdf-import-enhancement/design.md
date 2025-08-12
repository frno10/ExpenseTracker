# Design Document

## Overview

This design creates a comprehensive web-based interface for managing PDF parsing configurations, allowing users to create, edit, test, and deploy custom parsing patterns for different bank statement formats. The system leverages the existing YAML-based configuration infrastructure while providing an intuitive visual interface for non-technical users.

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │  Configuration  │
│   React UI      │◄──►│   FastAPI       │◄──►│   YAML Files    │
│                 │    │                 │    │                 │
│ • Config Editor │    │ • Config CRUD   │    │ • Bank Configs  │
│ • Pattern Test  │    │ • PDF Testing   │    │ • Parser Rules  │
│ • File Upload   │    │ • Validation    │    │ • Templates     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  PDF Parser     │
                       │  Engine         │
                       │                 │
                       │ • Pattern Match │
                       │ • Text Extract  │
                       │ • Transaction   │
                       │   Assembly      │
                       └─────────────────┘
```

### Component Architecture

1. **Configuration Management Layer**
   - Extends existing `ConfigManager` class
   - Handles YAML file operations
   - Provides validation and templating

2. **API Layer**
   - New FastAPI endpoints for configuration management
   - PDF testing and validation endpoints
   - Real-time pattern testing

3. **Frontend Layer**
   - React-based configuration interface
   - Monaco Editor for pattern editing
   - Real-time preview and testing

4. **Parser Integration**
   - Enhanced PDF parser with debugging
   - Configuration hot-reloading
   - Detailed logging and metrics

## Components and Interfaces

### Backend Components

#### 1. Configuration API (`/api/parser-config`)

```python
class ParserConfigAPI:
    """API endpoints for parser configuration management."""
    
    # Configuration CRUD
    GET    /api/parser-config/banks                    # List all bank configs
    GET    /api/parser-config/banks/{bank_name}        # Get specific config
    POST   /api/parser-config/banks/{bank_name}        # Create/update config
    DELETE /api/parser-config/banks/{bank_name}        # Delete config
    
    # Testing endpoints
    POST   /api/parser-config/test                     # Test config against PDF
    POST   /api/parser-config/validate                 # Validate config
    
    # Import/Export
    POST   /api/parser-config/import                   # Import config file
    GET    /api/parser-config/export/{bank_name}       # Export config file
    
    # Templates and suggestions
    GET    /api/parser-config/templates                # Get config templates
    POST   /api/parser-config/suggest                  # Suggest patterns from PDF
```

#### 2. Enhanced Configuration Manager

```python
class EnhancedConfigManager(ConfigManager):
    """Extended configuration manager with testing capabilities."""
    
    async def test_config_against_pdf(
        self, 
        config: Dict[str, Any], 
        pdf_path: str
    ) -> ConfigTestResult
    
    def validate_patterns(
        self, 
        patterns: List[str]
    ) -> ValidationResult
    
    def suggest_patterns_from_text(
        self, 
        text: str
    ) -> List[PatternSuggestion]
    
    def create_config_template(
        self, 
        template_type: str
    ) -> Dict[str, Any]
```

#### 3. PDF Testing Service

```python
class PDFTestingService:
    """Service for testing PDF parsing configurations."""
    
    async def extract_text_with_metadata(
        self, 
        pdf_path: str
    ) -> TextExtractionResult
    
    async def test_patterns_against_text(
        self, 
        patterns: List[str], 
        text: str
    ) -> PatternTestResult
    
    async def parse_with_debug_info(
        self, 
        config: Dict[str, Any], 
        pdf_path: str
    ) -> DebugParseResult
```

### Frontend Components

#### 1. Configuration Dashboard

```typescript
interface ConfigurationDashboard {
  // Main dashboard showing all bank configurations
  bankConfigs: BankConfig[]
  selectedBank: string | null
  
  // Actions
  createNewConfig(): void
  editConfig(bankName: string): void
  deleteConfig(bankName: string): void
  importConfig(file: File): void
  exportConfig(bankName: string): void
}
```

#### 2. Pattern Editor

```typescript
interface PatternEditor {
  // Monaco editor for regex patterns
  patterns: string[]
  selectedPattern: number
  
  // Validation and testing
  validationErrors: ValidationError[]
  testResults: PatternTestResult[]
  
  // Actions
  updatePattern(index: number, pattern: string): void
  testPattern(pattern: string, sampleText: string): void
  addPattern(): void
  removePattern(index: number): void
}
```

#### 3. PDF Testing Interface

```typescript
interface PDFTestingInterface {
  // File upload and text display
  uploadedFile: File | null
  extractedText: string
  
  // Configuration testing
  selectedConfig: BankConfig
  parseResults: ParseResult[]
  debugInfo: DebugInfo
  
  // Actions
  uploadPDF(file: File): void
  testConfiguration(config: BankConfig): void
  applyConfiguration(): void
}
```

### Data Models

#### Configuration Models

```python
class BankConfig(BaseModel):
    name: str
    description: Optional[str]
    pdf_config: PDFConfig
    csv_config: Optional[CSVConfig]
    created_at: datetime
    updated_at: datetime

class PDFConfig(BaseModel):
    transaction_patterns: List[str]
    date_formats: List[str]
    amount_patterns: List[str]
    ignore_patterns: List[str]
    custom_processing: Dict[str, Any]

class PatternTestResult(BaseModel):
    pattern: str
    matches: List[PatternMatch]
    errors: List[str]
    success_rate: float

class ConfigTestResult(BaseModel):
    config_name: str
    success: bool
    transactions_found: int
    sample_transactions: List[Dict[str, Any]]
    errors: List[str]
    warnings: List[str]
    debug_info: DebugInfo
```

## Data Models

### Database Schema Extensions

```sql
-- Configuration testing history
CREATE TABLE parser_config_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    config_name VARCHAR(255) NOT NULL,
    pdf_filename VARCHAR(255) NOT NULL,
    test_results JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Configuration versions for tracking changes
CREATE TABLE parser_config_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_name VARCHAR(255) NOT NULL,
    version_number INTEGER NOT NULL,
    config_data JSONB NOT NULL,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### File System Structure

```
backend/config/parsers/
├── settings.yaml                 # Global parser settings
├── banks/                        # Bank-specific configurations
│   ├── csob_slovakia.yaml
│   ├── chase.yaml
│   └── ...
├── templates/                    # Configuration templates
│   ├── basic_pdf.yaml
│   ├── multi_currency.yaml
│   └── ...
└── user_configs/                 # User-created configurations
    ├── {user_id}/
    │   ├── my_custom_bank.yaml
    │   └── ...
```

## Error Handling

### Configuration Validation

```python
class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Configuration validation failed: {', '.join(errors)}")

class PatternValidationError(Exception):
    """Raised when regex pattern validation fails."""
    
    def __init__(self, pattern: str, error: str):
        self.pattern = pattern
        self.error = error
        super().__init__(f"Pattern '{pattern}' is invalid: {error}")
```

### Error Response Format

```json
{
  "error": "validation_failed",
  "message": "Configuration validation failed",
  "details": {
    "field": "transaction_patterns",
    "errors": [
      "Pattern at index 0 is invalid: unterminated character set",
      "Pattern at index 2 contains unsupported regex feature"
    ]
  }
}
```

## Testing Strategy

### Unit Testing

1. **Configuration Manager Tests**
   - YAML file operations
   - Validation logic
   - Pattern compilation

2. **API Endpoint Tests**
   - CRUD operations
   - File upload handling
   - Error responses

3. **Pattern Testing**
   - Regex validation
   - Pattern matching accuracy
   - Performance testing

### Integration Testing

1. **End-to-End Configuration Flow**
   - Create config → Test against PDF → Apply to import
   - Configuration export/import cycle
   - Multi-user configuration management

2. **PDF Processing Pipeline**
   - Text extraction → Pattern matching → Transaction assembly
   - Error handling and recovery
   - Performance with large PDFs

### User Acceptance Testing

1. **Configuration Interface**
   - Ease of pattern editing
   - Visual feedback and validation
   - Import/export functionality

2. **PDF Testing Workflow**
   - Upload and test cycle
   - Debug information clarity
   - Configuration refinement process

## Performance Considerations

### Caching Strategy

```python
class ConfigCache:
    """Cache for compiled configurations and patterns."""
    
    def __init__(self):
        self._compiled_patterns: Dict[str, re.Pattern] = {}
        self._config_cache: Dict[str, BankConfig] = {}
        self._cache_ttl = 3600  # 1 hour
    
    def get_compiled_pattern(self, pattern: str) -> re.Pattern:
        """Get compiled regex pattern with caching."""
        
    def invalidate_config(self, config_name: str) -> None:
        """Invalidate cached configuration."""
```

### Optimization Strategies

1. **Pattern Compilation Caching**
   - Cache compiled regex patterns
   - Invalidate on configuration changes
   - Memory-efficient pattern storage

2. **PDF Text Extraction Caching**
   - Cache extracted text for uploaded PDFs
   - Enable rapid pattern testing iterations
   - Automatic cleanup of old cache entries

3. **Async Processing**
   - Non-blocking PDF processing
   - Background pattern testing
   - Real-time progress updates

## Security Considerations

### File Upload Security

```python
class SecurePDFUpload:
    """Secure PDF file upload handling."""
    
    ALLOWED_MIME_TYPES = ['application/pdf']
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    def validate_upload(self, file: UploadFile) -> ValidationResult:
        """Validate uploaded PDF file."""
        
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize uploaded filename."""
```

### Configuration Security

1. **Access Control**
   - User-specific configuration isolation
   - Admin-only system configuration access
   - Configuration sharing permissions

2. **Input Validation**
   - Regex pattern safety checks
   - YAML injection prevention
   - File path traversal protection

3. **Audit Logging**
   - Configuration change tracking
   - User action logging
   - Security event monitoring

## Deployment Strategy

### Development Environment

```yaml
# docker-compose.dev.yml additions
services:
  backend:
    volumes:
      - ./backend/config:/app/config
      - ./backend/temp:/app/temp
    environment:
      - PARSER_CONFIG_DIR=/app/config/parsers
      - TEMP_UPLOAD_DIR=/app/temp/uploads
```

### Production Considerations

1. **Configuration Backup**
   - Automated YAML file backups
   - Version control integration
   - Disaster recovery procedures

2. **Monitoring**
   - Configuration usage metrics
   - Pattern performance monitoring
   - Error rate tracking

3. **Scaling**
   - Configuration caching across instances
   - Load balancing for PDF processing
   - Database connection pooling
