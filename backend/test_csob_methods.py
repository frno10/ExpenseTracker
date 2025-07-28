#!/usr/bin/env python3
"""
Simple test for ČSOB parser methods without pytest dependencies.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import date
from decimal import Decimal
from app.parsers.pdf_parser import PDFParser

def test_csob_methods():
    """Test ČSOB-specific methods."""
    
    parser = PDFParser()
    
    print("🧪 Testing ČSOB Parser Methods")
    print("=" * 50)
    
    # Test date parsing
    print("\n📅 Testing Date Parsing:")
    test_dates = [
        ("2. 5.", date(2025, 5, 2)),
        ("15. 12.", date(2025, 12, 15)),
        ("1. 1.", date(2025, 1, 1)),
    ]
    
    for date_str, expected in test_dates:
        result = parser._parse_csob_date(date_str)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{date_str}' -> {result} (expected: {expected})")
    
    # Test amount parsing
    print("\n💰 Testing Amount Parsing:")
    test_amounts = [
        ("-12,90", Decimal("-12.90")),
        ("1 300,54", Decimal("1300.54")),
        ("-1,99", Decimal("-1.99")),
        ("25,00", Decimal("25.00")),
    ]
    
    for amount_str, expected in test_amounts:
        result = parser._parse_csob_amount(amount_str)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{amount_str}' -> {result} (expected: {expected})")
    
    # Test merchant/location splitting
    print("\n🏪 Testing Merchant/Location Splitting:")
    test_merchants = [
        ("SUPERMARKET FRESH KOSICE", ("SUPERMARKET FRESH", "KOSICE")),
        ("Netflix.com Los Gatos", ("Netflix.com Los Gatos", None)),
        ("KAUFLAND 1520,KE Popra KOSICE", ("KAUFLAND 1520,KE Popra", "KOSICE")),
        ("H&B SLOVAKIA S.R.O. KOSICE", ("H&B SLOVAKIA S.R.O.", "KOSICE")),
    ]
    
    for merchant_info, expected in test_merchants:
        result = parser._split_csob_merchant_location(merchant_info)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{merchant_info}' -> {result}")
        print(f"      Expected: {expected}")
    
    # Test exchange rate parsing
    print("\n💱 Testing Exchange Rate Parsing:")
    test_exchanges = [
        ("Suma: 12.9 EUR 30.04.2025 Kurz:", (Decimal("12.9"), "EUR", None)),
        ("Suma: 4.83 PLN 02.05.2025 Kurz: 4,2", (Decimal("4.83"), "PLN", Decimal("4.2"))),
        ("Suma: 100.00 USD 15.05.2025 Kurz: 0,92", (Decimal("100.00"), "USD", Decimal("0.92"))),
    ]
    
    for line, expected in test_exchanges:
        result = parser._parse_csob_exchange_info(line)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{line[:30]}...' -> {result}")
        if result != expected:
            print(f"      Expected: {expected}")
    
    # Test transaction type detection
    print("\n🔍 Testing Transaction Type Detection:")
    test_types = [
        ("Čerpanie úveru plat.kartou", "card_payment"),
        ("Splatka istiny Ing. Michal Lukac", "payment"),
        ("Prevod na účet", "transfer"),
        ("Unknown transaction type", "unknown"),
    ]
    
    for description, expected in test_types:
        result = parser._detect_csob_transaction_type(description)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{description}' -> '{result}' (expected: '{expected}')")
    
    # Test business name cleanup
    print("\n🧹 Testing Business Name Cleanup:")
    test_cleanups = [
        ("H&B SLOVAKIA S.R.O. KOSICE", "H&B SLOVAKIA"),
        ("KAUFLAND SLOVENSKO A.S.", "KAUFLAND SLOVENSKO"),
        ("TESCO STORES SK A.S. BRATISLAVA", "TESCO STORES SK"),
        ("Simple Name", "Simple Name"),
    ]
    
    for original, expected in test_cleanups:
        result = parser._clean_csob_business_name(original)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{original}' -> '{result}' (expected: '{expected}')")
    
    print("\n🎉 ČSOB Parser Methods Test Complete!")

if __name__ == "__main__":
    test_csob_methods()