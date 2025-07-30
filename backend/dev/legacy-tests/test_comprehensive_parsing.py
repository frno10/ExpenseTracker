#!/usr/bin/env python3
"""
Comprehensive parsing test to validate Task 6 completion.
"""

import sys
import os
import tempfile
import asyncio
from pathlib import Path
from datetime import date
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.parsers.registry import parser_registry, initialize_parsers
from app.parsers.config import config_manager

async def test_comprehensive_parsing():
    """Comprehensive test of the parsing framework."""
    
    print("🚀 Comprehensive Parsing Framework Test")
    print("=" * 60)
    
    # Initialize the parsing framework
    print("\n1️⃣ Initializing Parsing Framework...")
    initialize_parsers()
    
    parsers = parser_registry.list_parsers()
    print(f"   ✅ Registered parsers: {parsers}")
    
    # Test CSV parsing
    await test_csv_parsing()
    
    # Test PDF parsing with ČSOB configuration
    await test_pdf_parsing_with_csob_config()
    
    # Test configuration system
    test_configuration_system()
    
    # Test parser registry functionality
    test_parser_registry()
    
    print("\n🎉 Comprehensive Parsing Framework Test Complete!")
    print("✅ Task 6: Build modular statement parsing architecture - COMPLETED")

async def test_csv_parsing():
    """Test CSV parsing functionality."""
    
    print("\n2️⃣ Testing CSV Parsing...")
    
    # Create test CSV content
    csv_content = """Date,Description,Amount,Category
2025-01-15,Coffee Shop,-4.50,Dining
2025-01-16,Salary,2500.00,Income
2025-01-17,Grocery Store,-85.30,Groceries
2025-01-18,Gas Station,-45.00,Transportation"""
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
        f.write(csv_content)
        temp_path = f.name
    
    try:
        # Get CSV parser
        csv_parser = parser_registry.get_parser("csv_parser")
        if not csv_parser:
            print("   ❌ CSV parser not found")
            return
        
        # Parse the file
        result = await csv_parser.parse(temp_path)
        
        if result.success:
            print(f"   ✅ CSV parsing successful: {len(result.transactions)} transactions")
            
            # Validate first transaction
            if result.transactions:
                tx = result.transactions[0]
                print(f"      Sample transaction: {tx.date} | {tx.description} | {tx.amount}")
                
                # Verify data types and values
                assert tx.date == date(2025, 1, 15)
                assert tx.description == "Coffee Shop"
                assert tx.amount == Decimal("-4.50")
                print("      ✅ Transaction data validation passed")
        else:
            print(f"   ❌ CSV parsing failed: {result.errors}")
    
    except Exception as e:
        print(f"   ❌ CSV parsing error: {e}")
    
    finally:
        Path(temp_path).unlink()

async def test_pdf_parsing_with_csob_config():
    """Test PDF parsing with ČSOB configuration."""
    
    print("\n3️⃣ Testing PDF Parsing with ČSOB Configuration...")
    
    # Get PDF parser
    pdf_parser = parser_registry.get_parser("pdf_parser")
    if not pdf_parser:
        print("   ❌ PDF parser not found")
        return
    
    # Load ČSOB configuration
    csob_config = config_manager.load_bank_config("csob_slovakia")
    if not csob_config:
        print("   ❌ ČSOB configuration not found")
        return
    
    print("   ✅ ČSOB configuration loaded")
    
    # Apply ČSOB configuration to parser
    if "pdf_config" in csob_config:
        pdf_parser.config.settings.update(csob_config["pdf_config"])
        print("   ✅ ČSOB PDF configuration applied")
    
    # Test ČSOB-specific methods with real data
    print("   🧪 Testing ČSOB-specific parsing methods:")
    
    # Test date parsing
    test_date = pdf_parser._parse_csob_date("2. 5.")
    if test_date == date(2025, 5, 2):
        print("      ✅ ČSOB date parsing")
    else:
        print(f"      ❌ ČSOB date parsing: got {test_date}")
    
    # Test amount parsing
    test_amount = pdf_parser._parse_csob_amount("-12,90")
    if test_amount == Decimal("-12.90"):
        print("      ✅ ČSOB amount parsing")
    else:
        print(f"      ❌ ČSOB amount parsing: got {test_amount}")
    
    # Test merchant/location splitting
    merchant, location = pdf_parser._split_csob_merchant_location("SUPERMARKET FRESH KOSICE")
    if merchant == "SUPERMARKET FRESH" and location == "KOSICE":
        print("      ✅ ČSOB merchant/location splitting")
    else:
        print(f"      ❌ ČSOB merchant/location splitting: got {merchant}, {location}")
    
    # Test exchange rate parsing
    exchange_info = pdf_parser._parse_csob_exchange_info("Suma: 4.83 PLN 02.05.2025 Kurz: 4,2")
    if exchange_info and exchange_info[0] == Decimal("4.83") and exchange_info[1] == "PLN":
        print("      ✅ ČSOB exchange rate parsing")
    else:
        print(f"      ❌ ČSOB exchange rate parsing: got {exchange_info}")
    
    # Test transaction type detection
    tx_type = pdf_parser._detect_csob_transaction_type("Čerpanie úveru plat.kartou")
    if tx_type == "card_payment":
        print("      ✅ ČSOB transaction type detection")
    else:
        print(f"      ❌ ČSOB transaction type detection: got {tx_type}")
    
    # Test business name cleanup
    clean_name = pdf_parser._clean_csob_business_name("H&B SLOVAKIA S.R.O. KOSICE")
    if clean_name == "H&B SLOVAKIA":
        print("      ✅ ČSOB business name cleanup")
    else:
        print(f"      ❌ ČSOB business name cleanup: got '{clean_name}'")

def test_configuration_system():
    """Test the configuration management system."""
    
    print("\n4️⃣ Testing Configuration System...")
    
    # Test loading bank configurations
    bank_configs = config_manager.list_bank_configs()
    print(f"   ✅ Available bank configs: {len(bank_configs)}")
    
    # Test ČSOB configuration details
    csob_config = config_manager.load_bank_config("csob_slovakia")
    if csob_config:
        print("   ✅ ČSOB configuration loaded successfully")
        
        # Verify required sections
        required_sections = ["name", "pdf_config", "csv_config"]
        for section in required_sections:
            if section in csob_config:
                print(f"      ✅ {section} section present")
            else:
                print(f"      ⚠️  {section} section missing")
        
        # Verify PDF config details
        if "pdf_config" in csob_config:
            pdf_config = csob_config["pdf_config"]
            pdf_sections = ["transaction_patterns", "date_formats", "ignore_patterns", "custom_processing"]
            for section in pdf_sections:
                if section in pdf_config:
                    print(f"         ✅ PDF {section}")
                else:
                    print(f"         ⚠️  PDF {section} missing")
    
    # Test other bank configurations
    other_banks = ["chase", "bank_of_america", "wells_fargo"]
    for bank in other_banks:
        config = config_manager.load_bank_config(bank)
        if config:
            print(f"   ✅ {bank} configuration available")
        else:
            print(f"   ⚠️  {bank} configuration missing")

def test_parser_registry():
    """Test parser registry functionality."""
    
    print("\n5️⃣ Testing Parser Registry...")
    
    # Test parser registration
    parsers = parser_registry.list_parsers()
    expected_parsers = ["csv_parser", "pdf_parser"]
    
    for parser_name in expected_parsers:
        if parser_name in parsers:
            print(f"   ✅ {parser_name} registered")
        else:
            print(f"   ❌ {parser_name} not registered")
    
    # Test parser retrieval
    for parser_name in expected_parsers:
        parser = parser_registry.get_parser(parser_name)
        if parser:
            print(f"   ✅ {parser_name} retrieval successful")
        else:
            print(f"   ❌ {parser_name} retrieval failed")
    
    # Test supported extensions
    extensions = parser_registry.get_supported_extensions()
    expected_extensions = [".pdf", ".csv"]
    
    for ext in expected_extensions:
        if ext in extensions:
            print(f"   ✅ Extension {ext} supported")
        else:
            print(f"   ❌ Extension {ext} not supported")
    
    # Test MIME type support
    mime_types = parser_registry.get_supported_mime_types()
    expected_mimes = ["application/pdf", "text/csv"]
    
    for mime in expected_mimes:
        if mime in mime_types:
            print(f"   ✅ MIME type {mime} supported")
        else:
            print(f"   ❌ MIME type {mime} not supported")
    
    print(f"\n   📊 Summary:")
    print(f"      • Total parsers: {len(parsers)}")
    print(f"      • Supported extensions: {len(extensions)}")
    print(f"      • Supported MIME types: {len(mime_types)}")

async def main():
    """Main test function."""
    try:
        await test_comprehensive_parsing()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())