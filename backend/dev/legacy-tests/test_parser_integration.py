#!/usr/bin/env python3
"""
Test parser integration and registry functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.parsers.registry import parser_registry, initialize_parsers
from app.parsers.pdf_parser import PDFParser
from app.parsers.csv_parser import CSVParser

def test_parser_integration():
    """Test parser integration with registry."""
    
    print("🔧 Testing Parser Integration")
    print("=" * 50)
    
    # Initialize parsers
    print("\n📋 Initializing Parser Registry...")
    initialize_parsers()
    
    # Check registered parsers
    parsers = parser_registry.list_parsers()
    print(f"✅ Registered parsers: {parsers}")
    
    # Test PDF parser registration
    print("\n📄 Testing PDF Parser:")
    pdf_parser = parser_registry.get_parser("pdf_parser")
    if pdf_parser:
        print(f"✅ PDF parser found: {pdf_parser.__class__.__name__}")
        print(f"   Supported extensions: {pdf_parser.config.supported_extensions}")
        print(f"   MIME types: {pdf_parser.config.mime_types}")
        
        # Test ČSOB methods exist
        csob_methods = [
            '_parse_csob_date',
            '_parse_csob_amount', 
            '_split_csob_merchant_location',
            '_parse_csob_exchange_info',
            '_detect_csob_transaction_type',
            '_clean_csob_business_name'
        ]
        
        for method in csob_methods:
            if hasattr(pdf_parser, method):
                print(f"   ✅ ČSOB method: {method}")
            else:
                print(f"   ❌ Missing ČSOB method: {method}")
    else:
        print("❌ PDF parser not found")
    
    # Test CSV parser registration
    print("\n📊 Testing CSV Parser:")
    csv_parser = parser_registry.get_parser("csv_parser")
    if csv_parser:
        print(f"✅ CSV parser found: {csv_parser.__class__.__name__}")
        print(f"   Supported extensions: {csv_parser.config.supported_extensions}")
        print(f"   MIME types: {csv_parser.config.mime_types}")
    else:
        print("❌ CSV parser not found")
    
    # Test file type detection
    print("\n🔍 Testing File Type Detection:")
    test_files = [
        ("statement.pdf", "pdf_parser"),
        ("transactions.csv", "csv_parser"),
        ("data.xlsx", None),  # Not supported yet
        ("unknown.txt", None)
    ]
    
    for filename, expected_parser in test_files:
        found_parser = parser_registry.find_parser(filename)
        if expected_parser:
            if found_parser and found_parser.config.name == expected_parser:
                print(f"   ✅ {filename} -> {found_parser.config.name}")
            else:
                print(f"   ❌ {filename} -> {found_parser.config.name if found_parser else 'None'} (expected: {expected_parser})")
        else:
            if found_parser is None:
                print(f"   ✅ {filename} -> None (no parser available)")
            else:
                print(f"   ⚠️  {filename} -> {found_parser.config.name} (unexpected)")
    
    # Test supported formats
    print("\n📋 Testing Supported Formats:")
    extensions = parser_registry.get_supported_extensions()
    mime_types = parser_registry.get_supported_mime_types()
    
    print(f"   Extensions: {sorted(extensions)}")
    print(f"   MIME types: {sorted(mime_types)}")
    
    # Verify expected formats
    expected_extensions = ['.pdf', '.csv']
    expected_mimes = ['application/pdf', 'text/csv']
    
    for ext in expected_extensions:
        if ext in extensions:
            print(f"   ✅ Extension {ext} supported")
        else:
            print(f"   ❌ Extension {ext} missing")
    
    for mime in expected_mimes:
        if mime in mime_types:
            print(f"   ✅ MIME type {mime} supported")
        else:
            print(f"   ❌ MIME type {mime} missing")
    
    print("\n🎉 Parser Integration Test Complete!")

def test_configuration_loading():
    """Test configuration loading."""
    
    print("\n🔧 Testing Configuration Loading")
    print("=" * 30)
    
    from app.parsers.config import config_manager
    
    # Test loading ČSOB config
    csob_config = config_manager.load_bank_config("csob_slovakia")
    if csob_config:
        print("✅ ČSOB Slovakia config loaded")
        print(f"   Bank name: {csob_config.get('name')}")
        
        if 'pdf_config' in csob_config:
            pdf_config = csob_config['pdf_config']
            print("   PDF config sections:")
            for key in pdf_config.keys():
                print(f"     • {key}")
        
        if 'csv_config' in csob_config:
            print("   ✅ CSV config available")
    else:
        print("❌ ČSOB Slovakia config not found")
    
    # Test other bank configs
    bank_configs = config_manager.list_bank_configs()
    print(f"\n📋 Available bank configs: {bank_configs}")

if __name__ == "__main__":
    test_parser_integration()
    test_configuration_loading()