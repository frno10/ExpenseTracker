"""
Tests for the statement parsing framework.
"""
import csv
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.parsers.base import BaseParser, ParsedTransaction, ParseResult, ParserConfig, ParserRegistry
from app.parsers.csv_parser import CSVParser
from app.parsers.detection import FileDetector
from app.parsers.registry import parser_registry, initialize_parsers


class TestParserBase:
    """Test base parser functionality."""
    
    def test_parsed_transaction_validation(self):
        """Test ParsedTransaction validation."""
        # Valid transaction
        transaction = ParsedTransaction(
            date=date(2024, 1, 15),
            description="Test Transaction",
            amount=Decimal("25.50")
        )
        
        assert transaction.date == date(2024, 1, 15)
        assert transaction.description == "Test Transaction"
        assert transaction.amount == Decimal("25.50")
    
    def test_parsed_transaction_amount_validation(self):
        """Test amount validation in ParsedTransaction."""
        # String amount
        transaction = ParsedTransaction(
            date=date(2024, 1, 15),
            description="Test",
            amount="25.50"
        )
        assert transaction.amount == Decimal("25.50")
        
        # Amount with currency symbol
        transaction = ParsedTransaction(
            date=date(2024, 1, 15),
            description="Test",
            amount="$25.50"
        )
        assert transaction.amount == Decimal("25.50")
        
        # Negative amount in parentheses
        transaction = ParsedTransaction(
            date=date(2024, 1, 15),
            description="Test",
            amount="($25.50)"
        )
        assert transaction.amount == Decimal("-25.50")
    
    def test_parsed_transaction_date_validation(self):
        """Test date validation in ParsedTransaction."""
        # String date
        transaction = ParsedTransaction(
            date="2024-01-15",
            description="Test",
            amount=Decimal("25.50")
        )
        assert transaction.date == date(2024, 1, 15)
        
        # Different date format
        transaction = ParsedTransaction(
            date="01/15/2024",
            description="Test",
            amount=Decimal("25.50")
        )
        assert transaction.date == date(2024, 1, 15)
    
    def test_parse_result(self):
        """Test ParseResult functionality."""
        result = ParseResult(success=True)
        
        # Add transactions
        transaction = ParsedTransaction(
            date=date(2024, 1, 15),
            description="Test",
            amount=Decimal("25.50")
        )
        result.transactions.append(transaction)
        
        assert result.transaction_count == 1
        assert not result.has_errors
        assert not result.has_warnings
        
        # Add errors and warnings
        result.errors.append("Test error")
        result.warnings.append("Test warning")
        
        assert result.has_errors
        assert result.has_warnings
    
    def test_parser_registry(self):
        """Test parser registry functionality."""
        registry = ParserRegistry()
        
        # Create a mock parser
        class MockParser(BaseParser):
            def get_default_config(self):
                return ParserConfig(
                    name="mock_parser",
                    description="Mock parser for testing",
                    supported_extensions=[".mock"],
                    mime_types=["application/mock"]
                )
            
            def can_parse(self, file_path, mime_type=None):
                return file_path.endswith(".mock")
            
            async def parse(self, file_path, **kwargs):
                return ParseResult(success=True)
        
        # Register parser
        mock_parser = MockParser()
        registry.register(mock_parser)
        
        assert "mock_parser" in registry.list_parsers()
        assert registry.get_parser("mock_parser") is mock_parser
        
        # Test finding parser
        found_parser = registry.find_parser("test.mock")
        assert found_parser is mock_parser
        
        # Test supported extensions
        extensions = registry.get_supported_extensions()
        assert ".mock" in extensions
        
        # Test supported MIME types
        mime_types = registry.get_supported_mime_types()
        assert "application/mock" in mime_types
        
        # Unregister parser
        registry.unregister("mock_parser")
        assert "mock_parser" not in registry.list_parsers()


class TestFileDetector:
    """Test file detection functionality."""
    
    def test_file_detector_initialization(self):
        """Test FileDetector initialization."""
        detector = FileDetector()
        assert detector is not None
    
    def test_detect_encoding(self):
        """Test encoding detection."""
        detector = FileDetector()
        
        # Create a test file with UTF-8 content
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as f:
            f.write("Test content with UTF-8 encoding: café")
            temp_path = f.name
        
        try:
            encoding = detector.detect_encoding(temp_path)
            assert encoding is not None
            assert encoding.lower() in ['utf-8', 'ascii']
        finally:
            Path(temp_path).unlink()
    
    def test_validate_file(self):
        """Test file validation."""
        detector = FileDetector()
        
        # Test with non-existent file
        is_valid, errors = detector.validate_file("non_existent_file.txt")
        assert not is_valid
        assert len(errors) > 0
        
        # Test with valid file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Test content")
            temp_path = f.name
        
        try:
            is_valid, errors = detector.validate_file(temp_path)
            assert is_valid
            assert len(errors) == 0
        finally:
            Path(temp_path).unlink()
    
    def test_get_file_info(self):
        """Test getting file information."""
        detector = FileDetector()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Test content")
            temp_path = f.name
        
        try:
            info = detector.get_file_info(temp_path)
            
            assert 'path' in info
            assert 'name' in info
            assert 'extension' in info
            assert 'size' in info
            assert info['extension'] == '.txt'
            assert info['size'] > 0
        finally:
            Path(temp_path).unlink()


class TestCSVParser:
    """Test CSV parser functionality."""
    
    def test_csv_parser_initialization(self):
        """Test CSV parser initialization."""
        parser = CSVParser()
        assert parser.config.name == "csv_parser"
        assert ".csv" in parser.config.supported_extensions
        assert "text/csv" in parser.config.mime_types
    
    def test_csv_parser_can_parse(self):
        """Test CSV parser file detection."""
        parser = CSVParser()
        
        # Create temporary CSV file for testing
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            f.write("Date,Description,Amount\n2024-01-15,Test,-10.00")
            csv_path = f.name
        
        try:
            # Test with CSV extension
            assert parser.can_parse(csv_path)
            
            # Test with unsupported extension
            assert not parser.can_parse("test.pdf")
        finally:
            Path(csv_path).unlink()
    
    @pytest.mark.asyncio
    async def test_csv_parser_parse_simple(self):
        """Test parsing a simple CSV file."""
        parser = CSVParser()
        
        # Create test CSV content
        csv_content = """Date,Description,Amount
2024-01-15,Coffee Shop,-4.50
2024-01-16,Salary,2500.00
2024-01-17,Grocery Store,-85.30"""
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            result = await parser.parse(temp_path)
            
            assert result.success
            assert len(result.transactions) == 3
            
            # Check first transaction
            tx1 = result.transactions[0]
            assert tx1.date == date(2024, 1, 15)
            assert tx1.description == "Coffee Shop"
            assert tx1.amount == Decimal("-4.50")
            
            # Check second transaction
            tx2 = result.transactions[1]
            assert tx2.date == date(2024, 1, 16)
            assert tx2.description == "Salary"
            assert tx2.amount == Decimal("2500.00")
            
        finally:
            Path(temp_path).unlink()
    
    @pytest.mark.asyncio
    async def test_csv_parser_parse_with_different_delimiter(self):
        """Test parsing CSV with different delimiter."""
        parser = CSVParser()
        
        # Create test CSV content with semicolon delimiter
        csv_content = """Date;Description;Amount
2024-01-15;Coffee Shop;-4.50
2024-01-16;Salary;2500.00"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            result = await parser.parse(temp_path, delimiter=';')
            
            assert result.success
            assert len(result.transactions) == 2
            
        finally:
            Path(temp_path).unlink()
    
    @pytest.mark.asyncio
    async def test_csv_parser_parse_with_field_mapping(self):
        """Test parsing CSV with custom field mapping."""
        parser = CSVParser()
        
        # Update field mappings
        parser.config.settings["field_mappings"]["date"] = ["Transaction Date"]
        parser.config.settings["field_mappings"]["description"] = ["Memo"]
        parser.config.settings["field_mappings"]["amount"] = ["Transaction Amount"]
        
        csv_content = """Transaction Date,Memo,Transaction Amount
01/15/2024,Coffee Shop,-4.50
01/16/2024,Salary,2500.00"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            result = await parser.parse(temp_path)
            
            assert result.success
            assert len(result.transactions) == 2
            
            tx1 = result.transactions[0]
            assert tx1.date == date(2024, 1, 15)
            assert tx1.description == "Coffee Shop"
            assert tx1.amount == Decimal("-4.50")
            
        finally:
            Path(temp_path).unlink()
    
    @pytest.mark.asyncio
    async def test_csv_parser_parse_debit_credit_columns(self):
        """Test parsing CSV with separate debit/credit columns."""
        parser = CSVParser()
        
        # Configure for separate debit/credit columns
        parser.config.settings["amount_columns"] = {
            "single": False,
            "debit_column": "Debit",
            "credit_column": "Credit",
            "negative_debits": True
        }
        
        csv_content = """Date,Description,Debit,Credit
2024-01-15,Coffee Shop,4.50,
2024-01-16,Salary,,2500.00
2024-01-17,Grocery Store,85.30,"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            result = await parser.parse(temp_path)
            
            assert result.success
            assert len(result.transactions) == 3
            
            # Check debit transaction (should be negative)
            tx1 = result.transactions[0]
            assert tx1.amount == Decimal("-4.50")
            
            # Check credit transaction (should be positive)
            tx2 = result.transactions[1]
            assert tx2.amount == Decimal("2500.00")
            
        finally:
            Path(temp_path).unlink()
    
    def test_csv_parser_merchant_extraction(self):
        """Test merchant name extraction."""
        parser = CSVParser()
        
        # Test basic merchant extraction
        merchant = parser._extract_merchant_name("STARBUCKS #1234 SEATTLE WA")
        assert merchant is not None
        assert "STARBUCKS" in merchant
        
        # Test with date removal
        merchant = parser._extract_merchant_name("GROCERY STORE 01/15/2024 #REF123")
        assert merchant is not None
        assert "01/15/2024" not in merchant
        assert "#REF123" not in merchant
    
    def test_csv_parser_categorization(self):
        """Test transaction categorization."""
        parser = CSVParser()
        
        # Test grocery categorization
        transaction = ParsedTransaction(
            date=date(2024, 1, 15),
            description="SAFEWAY GROCERY STORE",
            amount=Decimal("-50.00")
        )
        category = parser._categorize_transaction(transaction)
        assert category == "Groceries"
        
        # Test gas categorization
        transaction = ParsedTransaction(
            date=date(2024, 1, 15),
            description="SHELL GAS STATION",
            amount=Decimal("-40.00")
        )
        category = parser._categorize_transaction(transaction)
        assert category == "Transportation"


class TestParserIntegration:
    """Test parser integration and registry."""
    
    def test_parser_registry_initialization(self):
        """Test parser registry initialization."""
        # Initialize parsers
        initialize_parsers()
        
        # Check that parsers are registered
        parsers = parser_registry.list_parsers()
        assert "csv_parser" in parsers
        assert "pdf_parser" in parsers
    
    def test_find_parser_for_csv(self):
        """Test finding parser for CSV file."""
        initialize_parsers()
        
        # Create temporary CSV file for testing
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            f.write("Date,Description,Amount\n2024-01-15,Test,-10.00")
            csv_path = f.name
        
        try:
            parser = parser_registry.find_parser(csv_path)
            assert parser is not None
            assert parser.config.name == "csv_parser"
        finally:
            Path(csv_path).unlink()
    
    def test_find_parser_for_pdf(self):
        """Test finding parser for PDF file."""
        initialize_parsers()
        
        # For PDF test, just check extension matching since creating a valid PDF is complex
        # The PDF parser should be able to handle .pdf extension
        pdf_parser = parser_registry.get_parser("pdf_parser")
        assert pdf_parser is not None
        assert ".pdf" in pdf_parser.config.supported_extensions
    
    def test_supported_formats(self):
        """Test getting supported formats."""
        initialize_parsers()
        
        extensions = parser_registry.get_supported_extensions()
        assert ".csv" in extensions
        assert ".pdf" in extensions
        
        mime_types = parser_registry.get_supported_mime_types()
        assert "text/csv" in mime_types
        assert "application/pdf" in mime_types


if __name__ == "__main__":
    pytest.main([__file__])