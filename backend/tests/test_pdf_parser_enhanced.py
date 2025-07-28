"""
Enhanced tests for PDF parser with ČSOB Slovakia integration.
"""
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.parsers.pdf_parser import PDFParser
from app.parsers.base import ParsedTransaction, ParseResult
from app.parsers.config import config_manager


class TestPDFParserEnhanced:
    """Test enhanced PDF parser functionality."""
    
    def test_pdf_parser_initialization(self):
        """Test PDF parser initialization."""
        parser = PDFParser()
        assert parser.config.name == "pdf_parser"
        assert ".pdf" in parser.config.supported_extensions
        assert "application/pdf" in parser.config.mime_types
    
    def test_pdf_parser_can_parse(self):
        """Test PDF parser file detection."""
        parser = PDFParser()
        
        # Test with PDF extension
        assert parser.can_parse("test.pdf")
        assert parser.can_parse("statement.PDF")
        
        # Test with unsupported extension
        assert not parser.can_parse("test.csv")
        assert not parser.can_parse("test.txt")
    
    @pytest.mark.asyncio
    async def test_pdf_parser_with_mock_text(self):
        """Test PDF parser with mocked text extraction."""
        parser = PDFParser()
        
        # Mock text content that resembles ČSOB format
        mock_text = '''VÝPIS Z ÚČTU | ACCOUNT STATEMENT
Obdobie: 1. 5. 2025 - 31. 5. 2025
Účet číslo: 4014293949/7500

2. 5. Čerpanie úveru plat.kartou -12,90
Ref. platiteľa: /VS205000121/SS3600268562/KS6178
Miesto: SUPERMARKET FRESH KOSICE
Suma: 12.9 EUR 30.04.2025 Kurz:

5. 5. Čerpanie úveru plat.kartou -11,49
Ref. platiteľa: /VS205000122/SS3600268563/KS6178
Miesto: Netflix.com Los Gatos
Suma: 11.49 EUR 01.05.2025 Kurz:'''
        
        # Mock the text extraction
        with patch.object(parser, '_extract_text', return_value=mock_text):
            result = await parser.parse("mock.pdf")
            
            assert result.success
            assert len(result.transactions) >= 2
            
            # Check first transaction
            tx1 = result.transactions[0]
            assert tx1.date == date(2025, 5, 2)
            assert tx1.amount == Decimal("-12.90")
            assert "SUPERMARKET FRESH" in str(tx1.merchant or tx1.description)
            
            # Check second transaction
            tx2 = result.transactions[1]
            assert tx2.date == date(2025, 5, 5)
            assert tx2.amount == Decimal("-11.49")
            assert "Netflix" in str(tx2.merchant or tx2.description)
    
    def test_csob_date_parsing(self):
        """Test ČSOB-specific date parsing."""
        parser = PDFParser()
        
        # Test Slovak date format "2. 5." (day. month.)
        test_cases = [
            ("2. 5.", date(2025, 5, 2)),  # Assuming current year 2025
            ("15. 12.", date(2025, 12, 15)),
            ("1. 1.", date(2025, 1, 1)),
        ]
        
        for date_str, expected_date in test_cases:
            parsed_date = parser._parse_csob_date(date_str)
            assert parsed_date == expected_date
    
    def test_csob_amount_parsing(self):
        """Test ČSOB-specific amount parsing."""
        parser = PDFParser()
        
        test_cases = [
            ("-12,90", Decimal("-12.90")),
            ("1 300,54", Decimal("1300.54")),
            ("-1,99", Decimal("-1.99")),
            ("25,00", Decimal("25.00")),
        ]
        
        for amount_str, expected_amount in test_cases:
            parsed_amount = parser._parse_csob_amount(amount_str)
            assert parsed_amount == expected_amount
    
    def test_csob_merchant_location_splitting(self):
        """Test splitting merchant names and locations for ČSOB."""
        parser = PDFParser()
        
        test_cases = [
            ("SUPERMARKET FRESH KOSICE", ("SUPERMARKET FRESH", "KOSICE")),
            ("Netflix.com Los Gatos", ("Netflix.com Los Gatos", None)),
            ("KAUFLAND 1520,KE Popra KOSICE", ("KAUFLAND 1520,KE Popra", "KOSICE")),
            ("H&B SLOVAKIA S.R.O. KOSICE", ("H&B SLOVAKIA", "KOSICE")),
        ]
        
        for merchant_info, expected_result in test_cases:
            merchant, location = parser._split_csob_merchant_location(merchant_info)
            assert merchant == expected_result[0]
            assert location == expected_result[1]
    
    def test_csob_exchange_rate_parsing(self):
        """Test parsing exchange rate information."""
        parser = PDFParser()
        
        test_cases = [
            ("Suma: 12.9 EUR 30.04.2025 Kurz:", (Decimal("12.9"), "EUR", None)),
            ("Suma: 4.83 PLN 02.05.2025 Kurz: 4,2", (Decimal("4.83"), "PLN", Decimal("4.2"))),
            ("Suma: 100.00 USD 15.05.2025 Kurz: 0,92", (Decimal("100.00"), "USD", Decimal("0.92"))),
        ]
        
        for line, expected_result in test_cases:
            result = parser._parse_csob_exchange_info(line)
            if expected_result[2] is None:
                assert result[0] == expected_result[0]
                assert result[1] == expected_result[1]
                assert result[2] is None
            else:
                assert result == expected_result
    
    @pytest.mark.asyncio
    async def test_csob_configuration_loading(self):
        """Test loading ČSOB-specific configuration."""
        # Load ČSOB configuration
        csob_config = config_manager.load_bank_config("csob_slovakia")
        assert csob_config is not None
        assert csob_config["name"] == "ČSOB Slovakia"
        assert "pdf_config" in csob_config
        
        # Test parser with ČSOB config
        parser = PDFParser()
        if "pdf_config" in csob_config:
            parser.config.settings.update(csob_config["pdf_config"])
        
        # Verify configuration was applied
        assert parser.config.settings.get("custom_processing", {}).get("default_year") == 2025
        assert parser.config.settings.get("custom_processing", {}).get("extract_merchant_from_location") is True
    
    def test_csob_ignore_patterns(self):
        """Test ČSOB-specific ignore patterns."""
        parser = PDFParser()
        
        # Load ČSOB config
        csob_config = config_manager.load_bank_config("csob_slovakia")
        if csob_config and "pdf_config" in csob_config:
            parser.config.settings.update(csob_config["pdf_config"])
        
        ignore_patterns = parser.config.settings.get("ignore_patterns", [])
        
        test_lines = [
            "VÝPIS Z ÚČTU | ACCOUNT STATEMENT",
            "Obdobie: 1. 5. 2025 - 31. 5. 2025",
            "Účet číslo: 4014293949/7500",
            "Strana: 1/10",
            "Ref. platiteľa: /VS205000121",
            "2. 5. Čerpanie úveru plat.kartou -12,90",  # This should NOT be ignored
        ]
        
        for line in test_lines:
            should_ignore = any(re.match(pattern, line, re.IGNORECASE) for pattern in ignore_patterns)
            if "Čerpanie úveru" in line:
                assert not should_ignore, f"Transaction line should not be ignored: {line}"
            elif any(keyword in line for keyword in ["VÝPIS", "Obdobie", "Účet číslo", "Strana", "Ref. platiteľa"]):
                assert should_ignore, f"Header line should be ignored: {line}"
    
    @pytest.mark.asyncio
    async def test_pdf_parser_error_handling(self):
        """Test PDF parser error handling."""
        parser = PDFParser()
        
        # Test with non-existent file
        result = await parser.parse("non_existent_file.pdf")
        assert not result.success
        assert len(result.errors) > 0
        
        # Test with invalid PDF content
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pdf') as f:
            f.write("This is not a valid PDF file")
            temp_path = f.name
        
        try:
            result = await parser.parse(temp_path)
            # Should handle gracefully - either succeed with no transactions or fail with error
            assert isinstance(result, ParseResult)
            if not result.success:
                assert len(result.errors) > 0
        finally:
            Path(temp_path).unlink()
    
    def test_pdf_parser_transaction_validation(self):
        """Test transaction validation in PDF parser."""
        parser = PDFParser()
        
        # Test valid transaction creation
        transaction = parser._create_transaction(
            date=date(2025, 5, 2),
            description="Test Transaction",
            amount=Decimal("-12.90"),
            merchant="Test Merchant",
            location="Test Location"
        )
        
        assert transaction.date == date(2025, 5, 2)
        assert transaction.description == "Test Transaction"
        assert transaction.amount == Decimal("-12.90")
        assert transaction.merchant == "Test Merchant"
        
        # Test transaction with missing required fields
        with pytest.raises((ValueError, TypeError)):
            parser._create_transaction(
                date=None,  # Missing required date
                description="Test",
                amount=Decimal("10.00")
            )
    
    def test_pdf_parser_performance_patterns(self):
        """Test performance with various pattern matching scenarios."""
        parser = PDFParser()
        
        # Test with large text content
        large_text = "\\n".join([
            f"{i % 30 + 1}. {(i % 12) + 1}. Čerpanie úveru plat.kartou -{i % 100 + 1}.{i % 100:02d}"
            for i in range(1000)
        ])
        
        # This should complete in reasonable time
        import time
        start_time = time.time()
        
        transactions = parser._extract_csob_transactions(large_text)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should process 1000 lines in under 5 seconds
        assert processing_time < 5.0
        assert len(transactions) > 0
    
    @pytest.mark.asyncio
    async def test_pdf_parser_integration_with_registry(self):
        """Test PDF parser integration with parser registry."""
        from app.parsers.registry import parser_registry, initialize_parsers
        
        # Initialize parsers
        initialize_parsers()
        
        # Get PDF parser from registry
        pdf_parser = parser_registry.get_parser("pdf_parser")
        assert pdf_parser is not None
        assert isinstance(pdf_parser, PDFParser)
        
        # Test finding parser for PDF file
        found_parser = parser_registry.find_parser("test.pdf")
        assert found_parser is not None
        assert found_parser.config.name == "pdf_parser"


class TestCSObSpecificFeatures:
    """Test ČSOB Slovakia specific parsing features."""
    
    def test_csob_transaction_types(self):
        """Test ČSOB transaction type detection."""
        parser = PDFParser()
        
        test_cases = [
            ("Čerpanie úveru plat.kartou", "card_payment"),
            ("Splatka istiny Ing. Michal Lukac", "payment"),
            ("Prevod na účet", "transfer"),
            ("Unknown transaction type", "unknown"),
        ]
        
        for description, expected_type in test_cases:
            tx_type = parser._detect_csob_transaction_type(description)
            assert tx_type == expected_type
    
    def test_csob_reference_extraction(self):
        """Test extracting reference numbers from ČSOB statements."""
        parser = PDFParser()
        
        test_cases = [
            ("Ref. platiteľa: /VS205000121/SS3600268562/KS6178", "/VS205000121/SS3600268562/KS6178"),
            ("Ref. platiteľa: /VS205000122", "/VS205000122"),
            ("No reference here", None),
        ]
        
        for line, expected_ref in test_cases:
            reference = parser._extract_csob_reference(line)
            assert reference == expected_ref
    
    def test_csob_multi_currency_handling(self):
        """Test handling multiple currencies in ČSOB statements."""
        parser = PDFParser()
        
        # Mock transaction data with different currencies
        mock_transactions = [
            {
                "amount": Decimal("-12.90"),
                "original_amount": Decimal("12.9"),
                "original_currency": "EUR",
                "exchange_rate": None
            },
            {
                "amount": Decimal("-1.15"),
                "original_amount": Decimal("4.83"),
                "original_currency": "PLN",
                "exchange_rate": Decimal("4.2")
            },
            {
                "amount": Decimal("-25.50"),
                "original_amount": Decimal("27.75"),
                "original_currency": "USD",
                "exchange_rate": Decimal("0.92")
            }
        ]
        
        for tx_data in mock_transactions:
            # Test currency conversion validation
            if tx_data["exchange_rate"] and tx_data["original_currency"] != "EUR":
                expected_eur_amount = tx_data["original_amount"] * tx_data["exchange_rate"]
                # Allow for small rounding differences
                assert abs(abs(tx_data["amount"]) - expected_eur_amount) < Decimal("0.01")
    
    def test_csob_business_name_cleanup(self):
        """Test cleaning up Slovak business names."""
        parser = PDFParser()
        
        test_cases = [
            ("H&B SLOVAKIA S.R.O. KOSICE", "H&B SLOVAKIA"),
            ("KAUFLAND SLOVENSKO A.S.", "KAUFLAND SLOVENSKO"),
            ("TESCO STORES SK A.S. BRATISLAVA", "TESCO STORES SK"),
            ("Simple Name", "Simple Name"),
        ]
        
        for original_name, expected_clean in test_cases:
            cleaned_name = parser._clean_csob_business_name(original_name)
            assert cleaned_name == expected_clean


class TestPDFParserConfiguration:
    """Test PDF parser configuration management."""
    
    def test_default_configuration(self):
        """Test default PDF parser configuration."""
        parser = PDFParser()
        config = parser.get_default_config()
        
        assert config.name == "pdf_parser"
        assert ".pdf" in config.supported_extensions
        assert "application/pdf" in config.mime_types
        
        # Check default settings
        settings = config.settings
        assert "extraction_method" in settings
        assert "date_patterns" in settings
        assert "amount_patterns" in settings
        assert "transaction_patterns" in settings
        assert "ignore_patterns" in settings
        assert "date_formats" in settings
    
    def test_configuration_update(self):
        """Test updating parser configuration."""
        parser = PDFParser()
        
        # Update configuration
        new_settings = {
            "extraction_method": "pypdf2",
            "custom_processing": {
                "default_year": 2024,
                "extract_merchant_from_location": False
            }
        }
        
        parser.config.settings.update(new_settings)
        
        assert parser.config.settings["extraction_method"] == "pypdf2"
        assert parser.config.settings["custom_processing"]["default_year"] == 2024
        assert parser.config.settings["custom_processing"]["extract_merchant_from_location"] is False
    
    def test_bank_specific_configuration_loading(self):
        """Test loading bank-specific configurations."""
        # Test loading different bank configurations
        bank_configs = ["csob_slovakia", "chase", "bank_of_america"]
        
        for bank_name in bank_configs:
            config = config_manager.load_bank_config(bank_name)
            if config:  # Config might not exist for all banks
                assert "name" in config
                # Should have either csv_config or pdf_config or both
                assert "csv_config" in config or "pdf_config" in config


if __name__ == "__main__":
    pytest.main([__file__])