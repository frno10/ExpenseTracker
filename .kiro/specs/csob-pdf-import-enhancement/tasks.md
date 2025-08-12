# Implementation Plan

- [x] 1. Fix ČSOB-specific parsing issues in PDF parser


  - Implement proper date parsing for Slovak format "1. 3." with default year 2025
  - Fix amount parsing to handle comma decimal separator correctly (e.g., "-2,04" → -2.04)
  - Implement multi-line transaction parsing to combine main transaction line with "Miesto:" and "Suma:" lines
  - Add merchant extraction from "Miesto:" lines with location cleanup
  - _Requirements: 4.1, 4.2, 4.3, 4.4_








- [ ] 2. Enhance PDF parser with ČSOB-specific methods
  - Update `_parse_csob_date` method to handle current year properly
  - Fix `_parse_csob_amount` method to handle comma decimal separator
  - Implement `_extract_csob_transactions` method for multi-line parsing
  - Add merchant name cleaning for Slovak business names
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 3. Create configuration management API endpoints
  - Implement `/api/parser-config/banks` endpoints for CRUD operations
  - Add `/api/parser-config/test` endpoint for testing configurations against PDFs
  - Create `/api/parser-config/validate` endpoint for configuration validation
  - Add import/export endpoints for configuration files
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 5.1, 5.2, 5.3, 5.4_

- [ ] 4. Build PDF testing service
  - Create `PDFTestingService` class for configuration testing
  - Implement text extraction with metadata for debugging
  - Add pattern testing against extracted text
  - Create debug parsing with detailed logging
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 6.1, 6.2, 6.3, 6.4_

- [ ] 5. Create configuration dashboard frontend
  - Build React component for listing all bank configurations
  - Add configuration editor with form validation
  - Implement create/edit/delete operations for configurations
  - Add import/export functionality for configuration files
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 5.1, 5.2, 5.3, 5.4_

- [ ] 6. Build pattern editor with syntax highlighting
  - Integrate Monaco Editor for regex pattern editing
  - Add regex syntax highlighting and validation
  - Implement real-time pattern testing against sample text
  - Create pattern compilation and error reporting
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 7. Create PDF testing interface
  - Build file upload component for PDF testing
  - Add text extraction display with formatting
  - Implement configuration testing with results display
  - Create debug information panel with parsing logs
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 6.1, 6.2, 6.3, 6.4_

- [ ] 8. Integrate custom configurations with import workflow
  - Update statement import service to detect custom configurations
  - Add configuration selection during PDF upload
  - Implement automatic configuration matching based on patterns
  - Ensure custom configurations work with existing import flow
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 9. Add configuration testing and validation
  - Create unit tests for ČSOB-specific parsing methods
  - Add integration tests for configuration API endpoints
  - Implement end-to-end tests for PDF testing workflow
  - Create performance tests for large PDF processing
  - _Requirements: All requirements validation_

- [ ] 10. Create database schema for configuration management
  - Add `parser_config_tests` table for testing history
  - Create `parser_config_versions` table for version tracking
  - Implement configuration caching and invalidation
  - Add audit logging for configuration changes
  - _Requirements: 6.1, 6.2, 6.3, 6.4_