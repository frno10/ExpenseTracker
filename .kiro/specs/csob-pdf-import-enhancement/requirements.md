# Requirements Document

## Introduction

This feature creates a web-based configuration interface for managing PDF parsing patterns and algorithms, with specific focus on improving ČSOB Slovakia bank statement parsing. The system already has a flexible configuration system with YAML-based bank configurations, but lacks a user-friendly interface for editing these configurations and testing them against specific PDF files. This enhancement will provide a visual interface for tweaking parsing algorithms and immediately testing them against uploaded documents.

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want to access a web-based configuration interface for PDF parsing patterns, so that I can create, edit, and manage bank-specific parsing configurations without modifying code.

#### Acceptance Criteria

1. WHEN I navigate to the parsing configuration page THEN the system SHALL display a list of all available bank configurations
2. WHEN I select a bank configuration THEN the system SHALL show all parsing patterns, date formats, and custom settings in an editable form
3. WHEN I modify a configuration THEN the system SHALL validate the changes and save them to the YAML configuration file
4. WHEN I create a new bank configuration THEN the system SHALL provide templates and validation for required fields

### Requirement 2

**User Story:** As a user testing parsing configurations, I want to upload a PDF file and test it against different parsing configurations, so that I can see which configuration works best for my specific bank statement format.

#### Acceptance Criteria

1. WHEN I upload a PDF file in the configuration interface THEN the system SHALL extract and display the raw text content
2. WHEN I select a parsing configuration THEN the system SHALL apply it to the uploaded PDF and show the extracted transactions
3. WHEN parsing fails or produces incorrect results THEN the system SHALL display detailed error messages and parsing logs
4. WHEN I modify a configuration THEN the system SHALL allow me to re-test it immediately against the same PDF file

### Requirement 3

**User Story:** As a user configuring parsing patterns, I want a visual pattern editor with syntax highlighting and validation, so that I can create and modify regex patterns without making syntax errors.

#### Acceptance Criteria

1. WHEN I edit a regex pattern THEN the system SHALL provide syntax highlighting for regex components
2. WHEN I enter an invalid regex pattern THEN the system SHALL show an error message with the specific issue
3. WHEN I test a pattern against sample text THEN the system SHALL highlight matching groups and show extracted values
4. WHEN I save a pattern THEN the system SHALL validate it can be compiled and used by the parser

### Requirement 4

**User Story:** As a user improving ČSOB parsing, I want to enhance the existing ČSOB Slovakia configuration to properly handle the specific format in my PDF statement, so that all transactions are extracted correctly.

#### Acceptance Criteria

1. WHEN the system processes a ČSOB statement with format "1. 3. Transakcia platobnou kartou -2,04" THEN it SHALL extract the date as March 1st, description as "Transakcia platobnou kartou", and amount as -2.04
2. WHEN a transaction contains "Miesto: SUPERMARKET FRESH PLU KOSICE" THEN the system SHALL extract "SUPERMARKET FRESH PLU" as the merchant name
3. WHEN multi-line transactions span across "Ref. platiteľa:", "Miesto:", and "Suma:" lines THEN the system SHALL combine them into a single transaction record
4. WHEN foreign currency information is present like "Suma: 2.13 USD 25.02.2023 Kurz: 1,044117" THEN the system SHALL preserve both EUR and original currency amounts

### Requirement 5

**User Story:** As a user managing parsing configurations, I want to export and import configuration files, so that I can share working configurations with other users or backup my customizations.

#### Acceptance Criteria

1. WHEN I have a working configuration THEN the system SHALL allow me to export it as a YAML file
2. WHEN I want to use someone else's configuration THEN the system SHALL allow me to import a YAML configuration file
3. WHEN I import a configuration THEN the system SHALL validate it and show any errors before saving
4. WHEN I export a configuration THEN the system SHALL include all patterns, settings, and metadata

### Requirement 6

**User Story:** As a user debugging parsing issues, I want detailed parsing logs and step-by-step execution information, so that I can understand why certain transactions are not being extracted correctly.

#### Acceptance Criteria

1. WHEN I test a configuration THEN the system SHALL show which patterns matched which lines of text
2. WHEN a pattern fails to match THEN the system SHALL explain why it didn't match and suggest improvements
3. WHEN parsing encounters errors THEN the system SHALL display the exact line that caused the error and the error details
4. WHEN parsing succeeds THEN the system SHALL show statistics about matched patterns and extracted data

### Requirement 7

**User Story:** As a user with a working configuration, I want to apply it to the regular import process, so that my customized parsing rules are used when I import statements through the normal workflow.

#### Acceptance Criteria

1. WHEN I have a custom configuration for my bank THEN the system SHALL automatically detect and use it during PDF import
2. WHEN I upload a PDF in the regular import flow THEN the system SHALL apply the best matching configuration based on detected patterns
3. WHEN multiple configurations could apply THEN the system SHALL allow me to choose which one to use
4. WHEN I'm satisfied with parsing results THEN the system SHALL proceed with the normal import workflow using the extracted transactions