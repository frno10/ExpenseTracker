#!/usr/bin/env python3
"""
Test script for statement import workflow.
"""
import asyncio
import json
import tempfile
from datetime import date
from decimal import Decimal

from app.parsers.base import ParsedTransaction, ParseResult
from app.services.duplicate_detection import DuplicateDetectionService, ImportConflictResolver
from app.services.statement_import_service import StatementImportService


def create_test_csv_file() -> str:
    """Create a test CSV file for import testing."""
    csv_content = """Date,Description,Amount,Category
2025-01-15,Coffee Shop Purchase,-4.50,Dining
2025-01-16,Grocery Store,-85.32,Groceries
2025-01-17,Gas Station,-45.00,Transportation
2025-01-18,Online Transfer,250.00,Transfer"""
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    temp_file.write(csv_content)
    temp_file.close()
    
    return temp_file.name


async def test_upload_record_creation():
    """Test upload record creation."""
    print("\n📤 Testing Upload Record Creation...")
    
    service = StatementImportService()
    
    # Create upload record
    upload_id = await service.create_upload_record(
        user_id="test-user-123",
        filename="test_statement.csv",
        file_size=1024,
        file_path=None,
        detected_parser="csv_parser",
        bank_hint="Chase Bank",
        validation_errors=[]
    )
    
    print(f"   ✅ Upload record created: {upload_id}")
    
    # Retrieve upload record
    record = await service.get_upload_record(upload_id, "test-user-123")
    assert record is not None
    assert record.filename == "test_statement.csv"
    assert record.detected_parser == "csv_parser"
    
    print("   ✅ Upload record retrieval successful")
    
    # Test security - different user shouldn't access
    other_record = await service.get_upload_record(upload_id, "other-user")
    assert other_record is None
    
    print("   ✅ User isolation working correctly")


async def test_duplicate_detection():
    """Test duplicate detection functionality."""
    print("\n🔍 Testing Duplicate Detection...")
    
    # Create test transactions
    transaction1 = ParsedTransaction(
        date=date(2025, 1, 15),
        description="Coffee Shop Purchase",
        amount=Decimal("-4.50"),
        merchant="Coffee Shop",
        category="Dining"
    )
    
    transaction2 = ParsedTransaction(
        date=date(2025, 1, 15),
        description="Coffee Shop",
        amount=Decimal("-4.50"),
        merchant="Coffee Shop",
        category="Dining"
    )
    
    transaction3 = ParsedTransaction(
        date=date(2025, 1, 20),
        description="Grocery Store",
        amount=Decimal("-85.32"),
        merchant="Supermarket",
        category="Groceries"
    )
    
    detector = DuplicateDetectionService()
    
    # Test text similarity
    similarity = detector._calculate_text_similarity(
        "Coffee Shop Purchase",
        "Coffee Shop"
    )
    print(f"   ✅ Text similarity: {similarity:.2f}")
    
    # Test transaction similarity
    score = detector._calculate_similarity_score(transaction1, transaction2)
    print(f"   ✅ Transaction similarity score: {score:.2f}")
    
    # Test keyword extraction
    keywords = detector._extract_keywords("Coffee Shop Purchase with card payment")
    print(f"   ✅ Extracted keywords: {keywords}")


async def test_conflict_resolution():
    """Test import conflict resolution."""
    print("\n⚖️ Testing Conflict Resolution...")
    
    # Create test transactions
    transactions = [
        ParsedTransaction(
            date=date(2025, 1, 15),
            description="Coffee Shop Purchase",
            amount=Decimal("-4.50"),
            merchant="Coffee Shop",
            category="Dining"
        ),
        ParsedTransaction(
            date=date(2025, 1, 16),
            description="Grocery Store",
            amount=Decimal("-85.32"),
            merchant="Supermarket",
            category="Groceries"
        ),
        ParsedTransaction(
            date=date(2025, 1, 17),
            description="Gas Station",
            amount=Decimal("-45.00"),
            merchant="Shell",
            category="Transportation"
        )
    ]
    
    resolver = ImportConflictResolver()
    
    # Test conflict resolution (no actual duplicates in this test)
    clean_transactions, conflicts = await resolver.resolve_duplicates(
        transactions, "test-user-123", auto_skip_duplicates=True
    )
    
    print(f"   ✅ Clean transactions: {len(clean_transactions)}")
    print(f"   ✅ Conflicts detected: {len(conflicts)}")
    
    assert len(clean_transactions) == 3  # No duplicates in test data
    assert len(conflicts) == 0


async def test_import_workflow():
    """Test complete import workflow."""
    print("\n🔄 Testing Complete Import Workflow...")
    
    service = StatementImportService()
    
    # Step 1: Create upload record
    test_file = create_test_csv_file()
    
    upload_id = await service.create_upload_record(
        user_id="test-user-123",
        filename="test_statement.csv",
        file_size=1024,
        file_path=test_file,
        detected_parser="csv_parser",
        bank_hint=None,
        validation_errors=[]
    )
    
    print(f"   ✅ Step 1: Upload record created: {upload_id}")
    
    # Step 2: Parse the file (simulate)
    mock_parse_result = ParseResult(
        success=True,
        transactions=[
            ParsedTransaction(
                date=date(2025, 1, 15),
                description="Coffee Shop Purchase",
                amount=Decimal("-4.50"),
                merchant="Coffee Shop",
                category="Dining"
            ),
            ParsedTransaction(
                date=date(2025, 1, 16),
                description="Grocery Store",
                amount=Decimal("-85.32"),
                merchant="Supermarket",
                category="Groceries"
            )
        ],
        metadata={"parser": "csv_parser", "file_size": 1024}
    )
    
    await service.store_parse_result(upload_id, mock_parse_result)
    print("   ✅ Step 2: Parse result stored")
    
    # Step 3: Execute import (simulate - would normally create expenses)
    import_result = await service.execute_import(
        upload_id=upload_id,
        user_id="test-user-123",
        selected_transactions=None,  # Import all
        category_mappings={},
        merchant_mappings={}
    )
    
    print(f"   ✅ Step 3: Import executed")
    print(f"      - Success: {import_result.success}")
    print(f"      - Imported: {import_result.imported_count}")
    print(f"      - Skipped: {import_result.skipped_count}")
    print(f"      - Duplicates: {import_result.duplicate_count}")
    
    # Step 4: Get import history
    history = await service.get_import_history("test-user-123", limit=10)
    print(f"   ✅ Step 4: Import history retrieved: {len(history)} records")
    
    # Clean up
    import os
    if os.path.exists(test_file):
        os.unlink(test_file)


async def test_file_validation():
    """Test file validation logic."""
    print("\n✅ Testing File Validation...")
    
    service = StatementImportService()
    
    # Test with validation errors
    upload_id = await service.create_upload_record(
        user_id="test-user-123",
        filename="large_file.pdf",
        file_size=100 * 1024 * 1024,  # 100MB - too large
        file_path=None,
        detected_parser=None,
        bank_hint=None,
        validation_errors=["File size exceeds 50MB limit", "Unsupported format"]
    )
    
    record = await service.get_upload_record(upload_id, "test-user-123")
    assert record.status == 'failed'
    assert len(record.validation_errors) == 2
    
    print("   ✅ File validation working correctly")
    print(f"      - Status: {record.status}")
    print(f"      - Errors: {record.validation_errors}")


async def main():
    """Run all statement import tests."""
    print("🚀 Statement Import Workflow Tests")
    print("=" * 50)
    
    try:
        await test_upload_record_creation()
        await test_duplicate_detection()
        await test_conflict_resolution()
        await test_import_workflow()
        await test_file_validation()
        
        print("\n🎉 All Statement Import Tests Passed!")
        print("✅ Task 8: Create statement import workflow - Core functionality implemented")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())