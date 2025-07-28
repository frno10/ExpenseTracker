"""
Simple test for Task 8 functionality.
"""
import asyncio
import tempfile
import os
from app.services.file_security_service import FileSecurityService
from app.services.statement_import_service import StatementImportService


async def test_file_security():
    """Test file security service."""
    print("Testing File Security Service...")
    
    # Create a temporary CSV file
    content = """Date,Description,Amount,Category
2024-01-15,Coffee Shop Purchase,-4.50,Food
2024-01-16,Gas Station,-45.00,Transportation
2024-01-17,Grocery Store,-87.32,Food"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(content)
        temp_path = f.name
    
    try:
        service = FileSecurityService()
        
        # Test file validation
        is_valid, errors = await service.validate_file(temp_path, "test.csv")
        print(f"File validation: {'PASS' if is_valid else 'FAIL'}")
        if errors:
            print(f"Validation errors: {errors}")
        
        # Test file hash calculation
        file_hash = service.calculate_file_hash(temp_path)
        print(f"File hash calculated: {'PASS' if file_hash else 'FAIL'}")
        
        # Test file metadata
        metadata = service.get_file_metadata(temp_path, "test.csv")
        print(f"File metadata: {'PASS' if metadata['file_size'] > 0 else 'FAIL'}")
        
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)


async def test_statement_import():
    """Test statement import service."""
    print("\nTesting Statement Import Service...")
    
    service = StatementImportService()
    
    # Test upload record creation
    upload_id = await service.create_upload_record(
        user_id="test-user-123",
        filename="test.csv",
        file_size=1000,
        file_path=None,  # No actual file for this test
        detected_parser="csv_parser",
        bank_hint="Test Bank",
        validation_errors=[]
    )
    
    print(f"Upload record created: {'PASS' if upload_id else 'FAIL'}")
    
    # Test getting upload record
    record = await service.get_upload_record(upload_id, "test-user-123")
    print(f"Upload record retrieved: {'PASS' if record else 'FAIL'}")
    
    # Test security - different user shouldn't access
    record_other = await service.get_upload_record(upload_id, "other-user")
    print(f"Security test: {'PASS' if record_other is None else 'FAIL'}")


async def main():
    """Run all tests."""
    print("=== Task 8: Statement Import Workflow Tests ===\n")
    
    await test_file_security()
    await test_statement_import()
    
    print("\n=== Tests completed ===")


if __name__ == "__main__":
    asyncio.run(main())