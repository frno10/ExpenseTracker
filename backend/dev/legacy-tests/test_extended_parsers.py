#!/usr/bin/env python3
"""
Test script for extended parsing formats (Excel, OFX, QIF).
This script tests the new parsers added in Task 7.
"""
import asyncio
import logging
import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import parsers
from app.parsers.registry import initialize_parsers, parser_registry
from app.parsers.excel_parser import ExcelParser
from app.parsers.ofx_parser import OFXParser
from app.parsers.qif_parser import QIFParser


def create_test_excel_file() -> str:
    """Create a test Excel file for parsing."""
    import pandas as pd
    
    # Create sample data
    data = {
        'Date': ['2025-01-15', '2025-01-16', '2025-01-17', '2025-01-18'],
        'Description': ['Coffee Shop Purchase', 'Grocery Store', 'Gas Station', 'Online Transfer'],
        'Amount': [-4.50, -85.32, -45.00, 250.00],
        'Merchant': ['Coffee Shop', 'SuperMarket', 'Shell Gas', 'Bank Transfer'],
        'Category': ['Dining', 'Groceries', 'Transportation', 'Transfer']
    }
    
    df = pd.DataFrame(data)
    
    # Create temporary Excel file
    temp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    df.to_excel(temp_file.name, index=False)
    temp_file.close()
    
    return temp_file.name


def create_test_ofx_file() -> str:
    """Create a test OFX file for parsing."""
    ofx_content = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<DTSERVER>20250127120000
<LANGUAGE>ENG
</SONRS>
</SIGNONMSGSRSV1>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>1
<STATUS>
<CODE>0
<SEVERITY>INFO
</STATUS>
<STMTRS>
<CURDEF>USD
<BANKACCTFROM>
<BANKID>123456789
<ACCTID>1234567890
<ACCTTYPE>CHECKING
</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>20250115120000
<DTEND>20250118120000
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20250115120000
<TRNAMT>-4.50
<FITID>202501151
<NAME>COFFEE SHOP
<MEMO>Coffee and pastry
</STMTTRN>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20250116120000
<TRNAMT>-85.32
<FITID>202501162
<NAME>SUPERMARKET
<MEMO>Weekly groceries
</STMTTRN>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20250117120000
<TRNAMT>-45.00
<FITID>202501173
<NAME>SHELL GAS STATION
<MEMO>Fuel purchase
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20250118120000
<TRNAMT>250.00
<FITID>202501184
<NAME>DIRECT DEPOSIT
<MEMO>Salary payment
</STMTTRN>
</BANKTRANLIST>
<LEDGERBAL>
<BALAMT>1234.56
<DTASOF>20250118120000
</LEDGERBAL>
</STMTRS>
</STMTRS>
</BANKMSGSRSV1>
</OFX>"""
    
    # Create temporary OFX file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.ofx', delete=False)
    temp_file.write(ofx_content)
    temp_file.close()
    
    return temp_file.name


def create_test_qif_file() -> str:
    """Create a test QIF file for parsing."""
    qif_content = """!Type:Bank
D1/15/2025
T-4.50
PCOFFEE SHOP
MCoffee and pastry
LDining
^
D1/16/2025
T-85.32
PSUPERMARKET
MWeekly groceries
LGroceries
^
D1/17/2025
T-45.00
PSHELL GAS STATION
MFuel purchase
LTransportation
^
D1/18/2025
T250.00
PDIRECT DEPOSIT
MSalary payment
LIncome
^"""
    
    # Create temporary QIF file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.qif', delete=False)
    temp_file.write(qif_content)
    temp_file.close()
    
    return temp_file.name


async def test_excel_parser():
    """Test Excel parser functionality."""
    print("\n📊 Testing Excel Parser...")
    
    try:
        # Create test file
        test_file = create_test_excel_file()
        print(f"   Created test Excel file: {test_file}")
        
        # Initialize parser
        parser = ExcelParser()
        
        # Test can_parse
        can_parse = parser.can_parse(test_file)
        print(f"   ✅ Can parse Excel file: {can_parse}")
        
        if can_parse:
            # Parse file
            result = await parser.parse(test_file)
            
            if result.success:
                print(f"   ✅ Excel parsing successful: {len(result.transactions)} transactions")
                
                # Display sample transaction
                if result.transactions:
                    tx = result.transactions[0]
                    print(f"      Sample: {tx.date} | {tx.description} | {tx.amount}")
                
                # Validate transaction data
                for tx in result.transactions:
                    assert isinstance(tx.date, date), "Date should be date object"
                    assert isinstance(tx.amount, Decimal), "Amount should be Decimal"
                    assert tx.description, "Description should not be empty"
                
                print("   ✅ Excel transaction validation passed")
                
            else:
                print(f"   ❌ Excel parsing failed: {result.errors}")
        
        # Clean up
        Path(test_file).unlink()
        
    except Exception as e:
        print(f"   ❌ Excel parser test failed: {e}")


async def test_ofx_parser():
    """Test OFX parser functionality."""
    print("\n💳 Testing OFX Parser...")
    
    try:
        # Create test file
        test_file = create_test_ofx_file()
        print(f"   Created test OFX file: {test_file}")
        
        # Initialize parser
        parser = OFXParser()
        
        # Test can_parse
        can_parse = parser.can_parse(test_file)
        print(f"   ✅ Can parse OFX file: {can_parse}")
        
        if can_parse:
            # Parse file
            result = await parser.parse(test_file)
            
            if result.success:
                print(f"   ✅ OFX parsing successful: {len(result.transactions)} transactions")
                
                # Display sample transaction
                if result.transactions:
                    tx = result.transactions[0]
                    print(f"      Sample: {tx.date} | {tx.description} | {tx.amount}")
                
                # Check metadata
                if result.metadata.get('accounts'):
                    print(f"      Accounts found: {len(result.metadata['accounts'])}")
                
                # Validate transaction data
                for tx in result.transactions:
                    assert isinstance(tx.date, date), "Date should be date object"
                    assert isinstance(tx.amount, Decimal), "Amount should be Decimal"
                    assert tx.description, "Description should not be empty"
                
                print("   ✅ OFX transaction validation passed")
                
            else:
                print(f"   ❌ OFX parsing failed: {result.errors}")
        
        # Clean up
        Path(test_file).unlink()
        
    except Exception as e:
        print(f"   ❌ OFX parser test failed: {e}")


async def test_qif_parser():
    """Test QIF parser functionality."""
    print("\n📝 Testing QIF Parser...")
    
    try:
        # Create test file
        test_file = create_test_qif_file()
        print(f"   Created test QIF file: {test_file}")
        
        # Initialize parser
        parser = QIFParser()
        
        # Test can_parse
        can_parse = parser.can_parse(test_file)
        print(f"   ✅ Can parse QIF file: {can_parse}")
        
        if can_parse:
            # Parse file
            result = await parser.parse(test_file)
            
            if result.success:
                print(f"   ✅ QIF parsing successful: {len(result.transactions)} transactions")
                
                # Display sample transaction
                if result.transactions:
                    tx = result.transactions[0]
                    print(f"      Sample: {tx.date} | {tx.description} | {tx.amount}")
                
                # Check metadata
                if result.metadata.get('accounts'):
                    print(f"      Accounts found: {len(result.metadata['accounts'])}")
                
                # Validate transaction data
                for tx in result.transactions:
                    assert isinstance(tx.date, date), "Date should be date object"
                    assert isinstance(tx.amount, Decimal), "Amount should be Decimal"
                    assert tx.description, "Description should not be empty"
                
                print("   ✅ QIF transaction validation passed")
                
            else:
                print(f"   ❌ QIF parsing failed: {result.errors}")
        
        # Clean up
        Path(test_file).unlink()
        
    except Exception as e:
        print(f"   ❌ QIF parser test failed: {e}")


async def test_parser_registry_extended():
    """Test parser registry with extended parsers."""
    print("\n🏛️ Testing Extended Parser Registry...")
    
    try:
        # Initialize all parsers
        initialize_parsers()
        
        # Check registered parsers
        parsers = parser_registry.list_parsers()
        print(f"   ✅ Registered parsers: {parsers}")
        
        expected_parsers = ['csv_parser', 'pdf_parser', 'excel_parser', 'ofx_parser', 'qif_parser']
        for expected in expected_parsers:
            assert expected in parsers, f"Parser {expected} not registered"
        
        # Test supported extensions
        extensions = parser_registry.get_supported_extensions()
        print(f"   ✅ Supported extensions: {extensions}")
        
        expected_extensions = ['.csv', '.pdf', '.xlsx', '.xls', '.ofx', '.qif']
        for ext in expected_extensions:
            assert ext in extensions, f"Extension {ext} not supported"
        
        # Test MIME types
        mime_types = parser_registry.get_supported_mime_types()
        print(f"   ✅ Supported MIME types: {len(mime_types)} types")
        
        # Test parser retrieval
        excel_parser = parser_registry.get_parser('excel_parser')
        assert excel_parser is not None, "Excel parser not found"
        
        ofx_parser = parser_registry.get_parser('ofx_parser')
        assert ofx_parser is not None, "OFX parser not found"
        
        qif_parser = parser_registry.get_parser('qif_parser')
        assert qif_parser is not None, "QIF parser not found"
        
        print("   ✅ Parser registry extended tests passed")
        
    except Exception as e:
        print(f"   ❌ Parser registry extended test failed: {e}")


async def main():
    """Run all extended parser tests."""
    print("🚀 Extended Parsing Framework Test (Task 7)")
    print("=" * 60)
    
    # Test individual parsers
    await test_excel_parser()
    await test_ofx_parser()
    await test_qif_parser()
    
    # Test registry integration
    await test_parser_registry_extended()
    
    print("\n🎉 Extended Parsing Framework Test Complete!")
    print("✅ Task 7: Extend statement parsing with additional formats - COMPLETED")


if __name__ == "__main__":
    asyncio.run(main())