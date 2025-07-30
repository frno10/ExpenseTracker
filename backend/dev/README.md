# Development Files Directory

This directory contains development, debugging, and legacy files that are not part of the main application but are useful for development and historical reference.

## 📁 Directory Structure

### `parsers/`
Development and debugging files for statement parsers:
- `analyze_csob_structure.py` - ČSOB bank statement structure analysis
- `analyze_pdf.py` - PDF parsing analysis and debugging
- `debug_qif.py` - QIF format debugging utilities
- `enhanced_csob_parser.py` - Enhanced ČSOB parser development
- `final_csob_parser.py` - Final ČSOB parser implementation
- `simple_pdf_test.py` - Simple PDF parsing tests

### `test-data/`
Sample data files and parsing results used during development:
- `*.json` - Parsed statement results and test data
- `*.txt` - Sample text extractions and debugging output
- Bank statement samples for parser testing

### `legacy-tests/`
Legacy test files from development phases:
- `test_comprehensive_parsing.py` - Comprehensive parsing tests
- `test_csob_*.py` - ČSOB-specific parser tests
- `test_enhanced_csob.py` - Enhanced ČSOB parser tests
- `test_extended_parsers.py` - Extended parser format tests
- `test_parser_integration.py` - Parser integration tests
- `test_pdf_parsing.py` - PDF parsing tests
- `test_statement_import*.py` - Statement import workflow tests
- `test_task8_*.py` - Task 8 specific tests

## 🚨 Important Notes

- **These files are for development reference only**
- **Do not use these files in production**
- **The main test suite is in `../tests/`**
- **Active parser implementations are in `../app/parsers/`**

## 🧹 Maintenance

These files can be safely removed if:
- You don't need development history
- Disk space is a concern
- You want to clean up the repository

However, they may be useful for:
- Understanding parser development evolution
- Debugging parser issues
- Reference for similar parser implementations
- Historical context of development decisions