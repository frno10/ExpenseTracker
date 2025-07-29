import pytest
import csv
import json
import io
from decimal import Decimal
from datetime import datetime, date, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch

from app.services.export_service import ExportService
from app.models.expense import ExpenseTable
from app.core.exceptions import ValidationError


class TestExportService:
    """Test cases for ExportService."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_db):
        """ExportService instance with mocked dependencies."""
        return ExportService(mock_db)
    
    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID."""
        return uuid4()
    
    @pytest.fixture
    def sample_expenses(self, sample_user_id):
        """Sample expense instances."""
        expenses = []
        
        # Expense 1
        expense1 = Mock(spec=ExpenseTable)
        expense1.id = uuid4()
        expense1.user_id = sample_user_id
        expense1.amount = Decimal('25.99')
        expense1.description = "Coffee shop purchase"
        expense1.notes = "Meeting with client"
        expense1.expense_date = date.today()
        expense1.created_at = datetime.utcnow()
        expense1.updated_at = datetime.utcnow()
        
        # Mock relationships
        expense1.category = Mock()
        expense1.category.id = uuid4()
        expense1.category.name = "Food & Dining"
        expense1.merchant = Mock()
        expense1.merchant.id = uuid4()
        expense1.merchant.name = "Starbucks"
        expense1.payment_method = Mock()
        expense1.payment_method.id = uuid4()
        expense1.payment_method.name = "Credit Card"
        expense1.account = Mock()
        expense1.account.id = uuid4()
        expense1.account.name = "Chase Checking"
        expense1.attachments = []
        
        expenses.append(expense1)
        
        # Expense 2
        expense2 = Mock(spec=ExpenseTable)
        expense2.id = uuid4()
        expense2.user_id = sample_user_id
        expense2.amount = Decimal('150.00')
        expense2.description = "Office supplies"
        expense2.notes = "Printer paper and ink"
        expense2.expense_date = date.today() - timedelta(days=1)
        expense2.created_at = datetime.utcnow()
        expense2.updated_at = datetime.utcnow()
        
        # Mock relationships
        expense2.category = Mock()
        expense2.category.id = uuid4()
        expense2.category.name = "Office Supplies"
        expense2.merchant = Mock()
        expense2.merchant.id = uuid4()
        expense2.merchant.name = "Office Depot"
        expense2.payment_method = Mock()
        expense2.payment_method.id = uuid4()
        expense2.payment_method.name = "Debit Card"
        expense2.account = Mock()
        expense2.account.id = uuid4()
        expense2.account.name = "Business Checking"
        expense2.attachments = []
        
        expenses.append(expense2)
        
        return expenses
    
    # ===== CSV EXPORT TESTS =====
    
    @pytest.mark.asyncio
    async def test_export_expenses_csv_success(self, service, sample_user_id, sample_expenses):
        """Test successful CSV export."""
        # Setup
        service._get_filtered_expenses = Mock(return_value=sample_expenses)
        
        # Execute
        csv_data = await service.export_expenses_csv(sample_user_id)
        
        # Verify
        assert isinstance(csv_data, bytes)
        
        # Parse CSV to verify content
        csv_content = csv_data.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        # Check header
        assert len(rows) >= 1
        header = rows[0]
        assert "Date" in header
        assert "Amount" in header
        assert "Description" in header
        assert "Category" in header
        assert "Merchant" in header
        
        # Check data rows
        assert len(rows) == 3  # Header + 2 expenses
        
        # Verify first expense data
        expense1_row = rows[1]
        assert expense1_row[1] == "25.99"  # Amount
        assert expense1_row[2] == "Coffee shop purchase"  # Description
        assert expense1_row[3] == "Food & Dining"  # Category
        assert expense1_row[4] == "Starbucks"  # Merchant
    
    @pytest.mark.asyncio
    async def test_export_expenses_csv_with_filters(self, service, sample_user_id, sample_expenses):
        """Test CSV export with date and category filters."""
        # Setup
        service._get_filtered_expenses = Mock(return_value=sample_expenses)
        
        date_from = date.today() - timedelta(days=7)
        date_to = date.today()
        category_ids = [uuid4()]
        
        # Execute
        csv_data = await service.export_expenses_csv(
            sample_user_id,
            date_from=date_from,
            date_to=date_to,
            category_ids=category_ids
        )
        
        # Verify
        assert isinstance(csv_data, bytes)
        
        # Verify _get_filtered_expenses was called with correct parameters
        service._get_filtered_expenses.assert_called_once_with(
            sample_user_id, date_from, date_to, category_ids, None
        )
    
    @pytest.mark.asyncio
    async def test_export_expenses_csv_with_attachments(self, service, sample_user_id, sample_expenses):
        """Test CSV export including attachment information."""
        # Setup
        service._get_filtered_expenses = Mock(return_value=sample_expenses)
        
        # Execute
        csv_data = await service.export_expenses_csv(
            sample_user_id,
            include_attachments=True
        )
        
        # Verify
        csv_content = csv_data.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        # Check that attachment columns are included
        header = rows[0]
        assert "Attachment Count" in header
        assert "Attachment Files" in header
    
    @pytest.mark.asyncio
    async def test_export_expenses_csv_without_notes(self, service, sample_user_id, sample_expenses):
        """Test CSV export excluding notes."""
        # Setup
        service._get_filtered_expenses = Mock(return_value=sample_expenses)
        
        # Execute
        csv_data = await service.export_expenses_csv(
            sample_user_id,
            include_notes=False
        )
        
        # Verify
        csv_content = csv_data.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        # Check that notes column is not included
        header = rows[0]
        assert "Notes" not in header
    
    # ===== JSON EXPORT TESTS =====
    
    @pytest.mark.asyncio
    async def test_export_expenses_json_success(self, service, sample_user_id, sample_expenses):
        """Test successful JSON export."""
        # Setup
        service._get_filtered_expenses = Mock(return_value=sample_expenses)
        
        # Execute
        json_data = await service.export_expenses_json(sample_user_id)
        
        # Verify
        assert isinstance(json_data, bytes)
        
        # Parse JSON to verify content
        json_content = json.loads(json_data.decode('utf-8'))
        
        # Check structure
        assert "export_metadata" in json_content
        assert "expenses" in json_content
        
        # Check metadata
        metadata = json_content["export_metadata"]
        assert "generated_at" in metadata
        assert "user_id" in metadata
        assert "total_expenses" in metadata
        assert metadata["total_expenses"] == 2
        
        # Check expenses
        expenses = json_content["expenses"]
        assert len(expenses) == 2
        
        # Verify first expense
        expense1 = expenses[0]
        assert "id" in expense1
        assert "amount" in expense1
        assert "description" in expense1
        assert "category" in expense1
        assert "merchant" in expense1
        assert expense1["amount"] == 25.99
        assert expense1["description"] == "Coffee shop purchase"
    
    @pytest.mark.asyncio
    async def test_export_expenses_json_without_metadata(self, service, sample_user_id, sample_expenses):
        """Test JSON export without metadata."""
        # Setup
        service._get_filtered_expenses = Mock(return_value=sample_expenses)
        
        # Execute
        json_data = await service.export_expenses_json(
            sample_user_id,
            include_metadata=False
        )
        
        # Verify
        json_content = json.loads(json_data.decode('utf-8'))
        
        # Check that metadata is None
        assert json_content["export_metadata"] is None
        assert "expenses" in json_content
        assert len(json_content["expenses"]) == 2
    
    # ===== EXCEL EXPORT TESTS =====
    
    @pytest.mark.asyncio
    async def test_export_expenses_excel_success(self, service, sample_user_id, sample_expenses):
        """Test successful Excel export."""
        # Setup
        service._get_filtered_expenses = Mock(return_value=sample_expenses)
        
        # Mock xlsxwriter components
        with patch('app.services.export_service.xlsxwriter.Workbook') as mock_workbook_class:
            mock_workbook = Mock()
            mock_workbook_class.return_value = mock_workbook
            
            mock_worksheet = Mock()
            mock_workbook.add_worksheet.return_value = mock_worksheet
            mock_workbook.add_format.return_value = Mock()
            
            # Execute
            excel_data = await service.export_expenses_excel(sample_user_id)
            
            # Verify
            assert isinstance(excel_data, bytes)
            
            # Verify workbook was created and closed
            mock_workbook_class.assert_called_once()
            mock_workbook.close.assert_called_once()
    
    # ===== PDF EXPORT TESTS =====
    
    @pytest.mark.asyncio
    async def test_export_expenses_pdf_success(self, service, sample_user_id, sample_expenses):
        """Test successful PDF export."""
        # Setup
        service._get_filtered_expenses = Mock(return_value=sample_expenses)
        
        # Mock reportlab components
        with patch('app.services.export_service.SimpleDocTemplate') as mock_doc_class:
            mock_doc = Mock()
            mock_doc_class.return_value = mock_doc
            
            # Execute
            pdf_data = await service.export_expenses_pdf(sample_user_id)
            
            # Verify
            assert isinstance(pdf_data, bytes)
            
            # Verify document was created and built
            mock_doc_class.assert_called_once()
            mock_doc.build.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_export_expenses_pdf_with_custom_title(self, service, sample_user_id, sample_expenses):
        """Test PDF export with custom title."""
        # Setup
        service._get_filtered_expenses = Mock(return_value=sample_expenses)
        
        with patch('app.services.export_service.SimpleDocTemplate') as mock_doc_class:
            mock_doc = Mock()
            mock_doc_class.return_value = mock_doc
            
            # Execute
            pdf_data = await service.export_expenses_pdf(
                sample_user_id,
                report_title="Custom Expense Report"
            )
            
            # Verify
            assert isinstance(pdf_data, bytes)
            mock_doc.build.assert_called_once()
    
    # ===== TAX EXPORT TESTS =====
    
    @pytest.mark.asyncio
    async def test_export_tax_report_pdf(self, service, sample_user_id, sample_expenses):
        """Test tax report export in PDF format."""
        # Setup
        service._get_filtered_expenses = Mock(return_value=sample_expenses)
        
        with patch('app.services.export_service.SimpleDocTemplate') as mock_doc_class:
            mock_doc = Mock()
            mock_doc_class.return_value = mock_doc
            
            # Execute
            tax_data = await service.export_tax_report(
                sample_user_id,
                tax_year=2024,
                format_type="pdf"
            )
            
            # Verify
            assert isinstance(tax_data, bytes)
            mock_doc.build.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_export_tax_report_csv(self, service, sample_user_id, sample_expenses):
        """Test tax report export in CSV format."""
        # Setup
        service._get_filtered_expenses = Mock(return_value=sample_expenses)
        
        # Execute
        tax_data = await service.export_tax_report(
            sample_user_id,
            tax_year=2024,
            format_type="csv"
        )
        
        # Verify
        assert isinstance(tax_data, bytes)
        
        # Parse CSV to verify tax category grouping
        csv_content = tax_data.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        # Check header includes tax category
        header = rows[0]
        assert "Tax Category" in header
    
    @pytest.mark.asyncio
    async def test_export_tax_report_with_custom_categories(self, service, sample_user_id, sample_expenses):
        """Test tax report with custom tax categories."""
        # Setup
        service._get_filtered_expenses = Mock(return_value=sample_expenses)
        
        custom_tax_categories = {
            "Business Meals": ["Food & Dining"],
            "Business Supplies": ["Office Supplies"]
        }
        
        # Execute
        tax_data = await service.export_tax_report(
            sample_user_id,
            tax_year=2024,
            tax_categories=custom_tax_categories,
            format_type="csv"
        )
        
        # Verify
        assert isinstance(tax_data, bytes)
        
        # Parse and verify custom categories are used
        csv_content = tax_data.decode('utf-8')
        assert "Business Meals" in csv_content or "Business Supplies" in csv_content
    
    # ===== HELPER METHOD TESTS =====
    
    @pytest.mark.asyncio
    async def test_get_filtered_expenses_no_filters(self, service, sample_user_id):
        """Test getting expenses without any filters."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        
        service.db.query.return_value = mock_query
        
        # Execute
        result = await service._get_filtered_expenses(sample_user_id)
        
        # Verify
        assert result == []
        service.db.query.assert_called_once()
        mock_query.filter.assert_called()  # At least user_id filter
    
    @pytest.mark.asyncio
    async def test_get_filtered_expenses_with_date_filters(self, service, sample_user_id):
        """Test getting expenses with date filters."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        
        service.db.query.return_value = mock_query
        
        date_from = date.today() - timedelta(days=30)
        date_to = date.today()
        
        # Execute
        result = await service._get_filtered_expenses(
            sample_user_id,
            date_from=date_from,
            date_to=date_to
        )
        
        # Verify
        assert result == []
        # Should have multiple filter calls (user_id, date_from, date_to)
        assert mock_query.filter.call_count >= 3
    
    def test_get_csv_headers_default(self, service):
        """Test getting default CSV headers."""
        headers = service._get_csv_headers()
        
        expected_headers = [
            "Date", "Amount", "Description", "Category", "Merchant", 
            "Payment Method", "Account", "Notes"
        ]
        
        assert headers == expected_headers
    
    def test_get_csv_headers_with_attachments(self, service):
        """Test getting CSV headers with attachments."""
        headers = service._get_csv_headers(include_attachments=True)
        
        assert "Attachment Count" in headers
        assert "Attachment Files" in headers
    
    def test_get_csv_headers_without_notes(self, service):
        """Test getting CSV headers without notes."""
        headers = service._get_csv_headers(include_notes=False)
        
        assert "Notes" not in headers
        assert "Date" in headers
        assert "Amount" in headers
    
    def test_format_expense_for_csv(self, service, sample_expenses):
        """Test formatting expense for CSV row."""
        expense = sample_expenses[0]
        
        row = service._format_expense_for_csv(expense)
        
        # Verify row structure
        assert len(row) >= 7  # At least basic fields
        assert row[1] == "25.99"  # Amount
        assert row[2] == "Coffee shop purchase"  # Description
        assert row[3] == "Food & Dining"  # Category
        assert row[4] == "Starbucks"  # Merchant
    
    def test_format_expense_for_csv_with_attachments(self, service, sample_expenses):
        """Test formatting expense for CSV with attachments."""
        expense = sample_expenses[0]
        
        row = service._format_expense_for_csv(expense, include_attachments=True)
        
        # Should include attachment count and files columns
        assert len(row) >= 9  # Basic fields + attachment fields
        assert row[-2] == "0"  # Attachment count (no attachments in mock)
        assert row[-1] == ""  # Attachment files (empty)
    
    def test_group_expenses_for_tax_default_categories(self, service, sample_expenses):
        """Test grouping expenses for tax with default categories."""
        grouped = service._group_expenses_for_tax(sample_expenses)
        
        # Should have grouped expenses
        assert isinstance(grouped, dict)
        assert "Uncategorized" in grouped
        
        # Check if expenses were categorized
        total_expenses = sum(len(expenses) for expenses in grouped.values())
        assert total_expenses == len(sample_expenses)
    
    def test_group_expenses_for_tax_custom_categories(self, service, sample_expenses):
        """Test grouping expenses for tax with custom categories."""
        custom_categories = {
            "Business Meals": ["Food & Dining"],
            "Office Expenses": ["Office Supplies"]
        }
        
        grouped = service._group_expenses_for_tax(sample_expenses, custom_categories)
        
        # Should use custom categories
        assert "Business Meals" in grouped
        assert "Office Expenses" in grouped
        
        # Verify expenses are properly grouped
        business_meals = grouped.get("Business Meals", [])
        office_expenses = grouped.get("Office Expenses", [])
        
        # Should have at least one expense in each category based on sample data
        assert len(business_meals) > 0 or len(office_expenses) > 0
    
    # ===== ERROR HANDLING TESTS =====
    
    @pytest.mark.asyncio
    async def test_export_with_no_expenses(self, service, sample_user_id):
        """Test export when no expenses match filters."""
        # Setup
        service._get_filtered_expenses = Mock(return_value=[])
        
        # Execute
        csv_data = await service.export_expenses_csv(sample_user_id)
        
        # Verify
        assert isinstance(csv_data, bytes)
        
        # Should still have header row
        csv_content = csv_data.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        assert len(rows) == 1  # Only header row
        assert "Date" in rows[0]
    
    @pytest.mark.asyncio
    async def test_export_handles_none_values(self, service, sample_user_id):
        """Test export handles expenses with None values gracefully."""
        # Setup expense with None values
        expense = Mock(spec=ExpenseTable)
        expense.id = uuid4()
        expense.amount = Decimal('10.00')
        expense.description = None  # None description
        expense.notes = None  # None notes
        expense.expense_date = date.today()
        expense.created_at = datetime.utcnow()
        expense.updated_at = datetime.utcnow()
        
        # None relationships
        expense.category = None
        expense.merchant = None
        expense.payment_method = None
        expense.account = None
        expense.attachments = []
        
        service._get_filtered_expenses = Mock(return_value=[expense])
        
        # Execute
        csv_data = await service.export_expenses_csv(sample_user_id)
        
        # Verify - should not raise exception
        assert isinstance(csv_data, bytes)
        
        # Parse and verify empty strings for None values
        csv_content = csv_data.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        assert len(rows) == 2  # Header + 1 expense
        expense_row = rows[1]
        
        # None values should be converted to empty strings
        assert expense_row[2] == ""  # Description
        assert expense_row[3] == ""  # Category
        assert expense_row[4] == ""  # Merchant