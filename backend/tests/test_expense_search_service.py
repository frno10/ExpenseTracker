import pytest
from decimal import Decimal
from datetime import datetime, date, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch

from app.services.expense_search_service import ExpenseSearchService
from app.models.expense import ExpenseTable
from app.models.attachment import AttachmentTable, AttachmentType
from app.core.exceptions import ValidationError


class TestExpenseSearchService:
    """Test cases for ExpenseSearchService."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_db):
        """ExpenseSearchService instance with mocked dependencies."""
        return ExpenseSearchService(mock_db)
    
    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID."""
        return uuid4()
    
    @pytest.fixture
    def sample_expense(self, sample_user_id):
        """Sample expense instance."""
        expense = Mock(spec=ExpenseTable)
        expense.id = uuid4()
        expense.user_id = sample_user_id
        expense.amount = Decimal('25.99')
        expense.description = "Coffee shop purchase"
        expense.notes = "Meeting with client, discussed project requirements"
        expense.expense_date = date.today()
        expense.created_at = datetime.utcnow()
        expense.updated_at = datetime.utcnow()
        
        # Mock relationships
        expense.category = Mock()
        expense.category.name = "Food & Dining"
        expense.merchant = Mock()
        expense.merchant.name = "Starbucks"
        expense.payment_method = Mock()
        expense.payment_method.name = "Credit Card"
        expense.account = Mock()
        expense.account.name = "Chase Checking"
        expense.attachments = []
        
        return expense
    
    @pytest.fixture
    def sample_attachment(self, sample_user_id):
        """Sample attachment instance."""
        attachment = Mock(spec=AttachmentTable)
        attachment.id = uuid4()
        attachment.user_id = sample_user_id
        attachment.expense_id = uuid4()
        attachment.filename = "receipt_starbucks.jpg"
        attachment.original_filename = "IMG_001.jpg"
        attachment.attachment_type = AttachmentType.RECEIPT
        attachment.file_size = 1024000
        attachment.mime_type = "image/jpeg"
        
        return attachment
    
    # ===== SEARCH VALIDATION TESTS =====
    
    @pytest.mark.asyncio
    async def test_search_expenses_empty_search_term(self, service, sample_user_id):
        """Test search with empty search term raises validation error."""
        with pytest.raises(ValidationError, match="Search term must be at least 2 characters"):
            await service.search_expenses(sample_user_id, "")
    
    @pytest.mark.asyncio
    async def test_search_expenses_short_search_term(self, service, sample_user_id):
        """Test search with short search term raises validation error."""
        with pytest.raises(ValidationError, match="Search term must be at least 2 characters"):
            await service.search_expenses(sample_user_id, "a")
    
    @pytest.mark.asyncio
    async def test_search_expenses_whitespace_only(self, service, sample_user_id):
        """Test search with whitespace-only search term raises validation error."""
        with pytest.raises(ValidationError, match="Search term must be at least 2 characters"):
            await service.search_expenses(sample_user_id, "   ")
    
    # ===== BASIC SEARCH TESTS =====
    
    @pytest.mark.asyncio
    async def test_search_expenses_basic_success(self, service, sample_user_id, sample_expense):
        """Test basic expense search functionality."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [sample_expense]
        
        service.db.query.return_value = mock_query
        
        # Mock the statistics calculation
        service._calculate_search_statistics = Mock(return_value={
            'total_amount': Decimal('25.99'),
            'average_amount': Decimal('25.99'),
            'date_range': {'earliest': date.today(), 'latest': date.today()},
            'category_breakdown': [{'category': 'Food & Dining', 'count': 1}],
            'merchant_breakdown': [{'merchant': 'Starbucks', 'count': 1}],
            'field_match_counts': {'description': 1, 'notes': 0, 'attachments': 0}
        })
        
        # Execute
        result = await service.search_expenses(sample_user_id, "coffee")
        
        # Verify
        assert result['total_count'] == 1
        assert result['returned_count'] == 1
        assert result['search_term'] == "coffee"
        assert len(result['expenses']) == 1
        assert result['expenses'][0] == sample_expense
        
        # Verify query was called correctly
        service.db.query.assert_called_with(ExpenseTable)
    
    @pytest.mark.asyncio
    async def test_search_expenses_with_filters(self, service, sample_user_id, sample_expense):
        """Test expense search with additional filters."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [sample_expense]
        
        service.db.query.return_value = mock_query
        
        # Mock the statistics calculation
        service._calculate_search_statistics = Mock(return_value={
            'total_amount': Decimal('25.99'),
            'average_amount': Decimal('25.99'),
            'date_range': {'earliest': date.today(), 'latest': date.today()},
            'category_breakdown': [],
            'merchant_breakdown': [],
            'field_match_counts': {}
        })
        
        category_id = uuid4()
        date_from = date.today() - timedelta(days=30)
        date_to = date.today()
        
        # Execute
        result = await service.search_expenses(
            sample_user_id, 
            "coffee",
            category_ids=[category_id],
            date_from=date_from,
            date_to=date_to,
            amount_min=Decimal('10.00'),
            amount_max=Decimal('50.00')
        )
        
        # Verify
        assert result['total_count'] == 1
        assert result['filters_applied']['category_ids'] == [category_id]
        assert result['filters_applied']['date_from'] == date_from
        assert result['filters_applied']['date_to'] == date_to
        assert result['filters_applied']['amount_min'] == Decimal('10.00')
        assert result['filters_applied']['amount_max'] == Decimal('50.00')
    
    @pytest.mark.asyncio
    async def test_search_expenses_with_pagination(self, service, sample_user_id, sample_expense):
        """Test expense search with pagination."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.count.return_value = 100  # Total count
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_expense]  # One result per page
        
        service.db.query.return_value = mock_query
        
        # Mock the statistics calculation
        service._calculate_search_statistics = Mock(return_value={
            'total_amount': Decimal('25.99'),
            'average_amount': Decimal('25.99'),
            'date_range': {'earliest': date.today(), 'latest': date.today()},
            'category_breakdown': [],
            'merchant_breakdown': [],
            'field_match_counts': {}
        })
        
        # Execute
        result = await service.search_expenses(
            sample_user_id, 
            "coffee",
            limit=10,
            offset=20
        )
        
        # Verify
        assert result['total_count'] == 100
        assert result['returned_count'] == 1
        
        # Verify pagination was applied
        mock_query.offset.assert_called_with(20)
        mock_query.limit.assert_called_with(10)
    
    # ===== SEARCH FIELD TESTS =====
    
    @pytest.mark.asyncio
    async def test_search_expenses_description_only(self, service, sample_user_id, sample_expense):
        """Test search in description field only."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [sample_expense]
        
        service.db.query.return_value = mock_query
        
        # Mock the statistics calculation
        service._calculate_search_statistics = Mock(return_value={
            'total_amount': Decimal('25.99'),
            'average_amount': Decimal('25.99'),
            'date_range': {'earliest': date.today(), 'latest': date.today()},
            'category_breakdown': [],
            'merchant_breakdown': [],
            'field_match_counts': {'description': 1}
        })
        
        # Execute
        result = await service.search_expenses(
            sample_user_id, 
            "coffee",
            search_fields=['description']
        )
        
        # Verify
        assert result['search_fields'] == ['description']
        assert result['search_statistics']['field_match_counts']['description'] == 1
    
    @pytest.mark.asyncio
    async def test_search_expenses_notes_only(self, service, sample_user_id, sample_expense):
        """Test search in notes field only."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [sample_expense]
        
        service.db.query.return_value = mock_query
        
        # Mock the statistics calculation
        service._calculate_search_statistics = Mock(return_value={
            'total_amount': Decimal('25.99'),
            'average_amount': Decimal('25.99'),
            'date_range': {'earliest': date.today(), 'latest': date.today()},
            'category_breakdown': [],
            'merchant_breakdown': [],
            'field_match_counts': {'notes': 1}
        })
        
        # Execute
        result = await service.search_expenses(
            sample_user_id, 
            "client",
            search_fields=['notes']
        )
        
        # Verify
        assert result['search_fields'] == ['notes']
        assert result['search_statistics']['field_match_counts']['notes'] == 1
    
    # ===== NOTES SEARCH TESTS =====
    
    @pytest.mark.asyncio
    async def test_search_expenses_with_notes_success(self, service, sample_user_id, sample_expense):
        """Test searching expenses specifically in notes field."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_expense]
        
        service.db.query.return_value = mock_query
        
        # Execute
        result = await service.search_expenses_with_notes(sample_user_id, "client")
        
        # Verify
        assert len(result) == 1
        assert result[0] == sample_expense
        
        # Verify query was filtered for notes
        mock_query.filter.assert_called()
    
    @pytest.mark.asyncio
    async def test_search_expenses_with_notes_validation_error(self, service, sample_user_id):
        """Test notes search with invalid search term."""
        with pytest.raises(ValidationError, match="Search term must be at least 2 characters"):
            await service.search_expenses_with_notes(sample_user_id, "a")
    
    # ===== ATTACHMENT SEARCH TESTS =====
    
    @pytest.mark.asyncio
    async def test_search_expenses_by_attachment_content(self, service, sample_user_id, sample_attachment):
        """Test searching expenses by attachment content."""
        # Setup
        mock_expense = Mock()
        mock_expense.id = sample_attachment.expense_id
        mock_expense.amount = Decimal('25.99')
        mock_expense.expense_date = date.today()
        
        sample_attachment.expense = mock_expense
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.all.return_value = [sample_attachment]
        
        service.db.query.return_value = mock_query
        
        # Execute
        result = await service.search_expenses_by_attachment_content(sample_user_id, "receipt")
        
        # Verify
        assert len(result) == 1
        assert result[0]['expense'] == mock_expense
        assert len(result[0]['matching_attachments']) == 1
        assert result[0]['matching_attachments'][0] == sample_attachment
    
    @pytest.mark.asyncio
    async def test_search_expenses_by_attachment_validation_error(self, service, sample_user_id):
        """Test attachment search with invalid search term."""
        with pytest.raises(ValidationError, match="Search term must be at least 2 characters"):
            await service.search_expenses_by_attachment_content(sample_user_id, "")
    
    # ===== SEARCH SUGGESTIONS TESTS =====
    
    @pytest.mark.asyncio
    async def test_get_search_suggestions_descriptions(self, service, sample_user_id):
        """Test getting search suggestions for descriptions."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [("Coffee shop purchase",), ("Coffee meeting",)]
        
        service.db.query.return_value = mock_query
        
        # Execute
        result = await service.get_search_suggestions(sample_user_id, "coffee", "descriptions")
        
        # Verify
        assert 'descriptions' in result
        assert len(result['descriptions']) == 2
        assert "Coffee shop purchase" in result['descriptions']
        assert "Coffee meeting" in result['descriptions']
    
    @pytest.mark.asyncio
    async def test_get_search_suggestions_notes(self, service, sample_user_id):
        """Test getting search suggestions for notes."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [("Meeting with client about project requirements",)]
        
        service.db.query.return_value = mock_query
        
        # Execute
        result = await service.get_search_suggestions(sample_user_id, "client", "notes")
        
        # Verify
        assert 'notes' in result
        assert len(result['notes']) == 1
        # Should contain snippet with the search term
        assert any("client" in snippet.lower() for snippet in result['notes'])
    
    @pytest.mark.asyncio
    async def test_get_search_suggestions_empty_term(self, service, sample_user_id):
        """Test getting search suggestions with empty term."""
        result = await service.get_search_suggestions(sample_user_id, "", "all")
        assert result == {}
    
    # ===== STATISTICS CALCULATION TESTS =====
    
    @pytest.mark.asyncio
    async def test_calculate_search_statistics_empty_results(self, service, sample_user_id):
        """Test statistics calculation with empty results."""
        result = await service._calculate_search_statistics(sample_user_id, "test", ['description'], [])
        
        assert result['total_amount'] == Decimal('0.00')
        assert result['average_amount'] == Decimal('0.00')
        assert result['date_range'] is None
        assert result['category_breakdown'] == []
        assert result['merchant_breakdown'] == []
        assert result['field_match_counts'] == {}
    
    @pytest.mark.asyncio
    async def test_calculate_search_statistics_with_results(self, service, sample_user_id, sample_expense):
        """Test statistics calculation with results."""
        # Setup additional expense
        expense2 = Mock(spec=ExpenseTable)
        expense2.amount = Decimal('15.50')
        expense2.expense_date = date.today() - timedelta(days=1)
        expense2.description = "Coffee shop visit"
        expense2.notes = None
        expense2.category = Mock()
        expense2.category.name = "Food & Dining"
        expense2.merchant = Mock()
        expense2.merchant.name = "Local Cafe"
        expense2.attachments = []
        
        expenses = [sample_expense, expense2]
        
        # Execute
        result = await service._calculate_search_statistics(
            sample_user_id, "coffee", ['description', 'notes'], expenses
        )
        
        # Verify
        assert result['total_amount'] == Decimal('41.49')  # 25.99 + 15.50
        assert result['average_amount'] == Decimal('20.745')  # 41.49 / 2
        assert result['date_range'] is not None
        assert len(result['category_breakdown']) == 1
        assert result['category_breakdown'][0]['category'] == 'Food & Dining'
        assert result['category_breakdown'][0]['count'] == 2
        assert len(result['merchant_breakdown']) == 2
        
        # Check field match counts
        assert 'description' in result['field_match_counts']
        assert 'notes' in result['field_match_counts']
    
    # ===== SORTING TESTS =====
    
    @pytest.mark.asyncio
    async def test_search_expenses_sort_by_amount_asc(self, service, sample_user_id, sample_expense):
        """Test search with sorting by amount ascending."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [sample_expense]
        
        service.db.query.return_value = mock_query
        
        # Mock the statistics calculation
        service._calculate_search_statistics = Mock(return_value={
            'total_amount': Decimal('25.99'),
            'average_amount': Decimal('25.99'),
            'date_range': {'earliest': date.today(), 'latest': date.today()},
            'category_breakdown': [],
            'merchant_breakdown': [],
            'field_match_counts': {}
        })
        
        # Execute
        result = await service.search_expenses(
            sample_user_id, 
            "coffee",
            sort_by="amount",
            sort_order="asc"
        )
        
        # Verify
        assert result['total_count'] == 1
        # Verify order_by was called (exact call verification would depend on mock setup)
        mock_query.order_by.assert_called()
    
    # ===== ATTACHMENT FILTER TESTS =====
    
    @pytest.mark.asyncio
    async def test_search_expenses_with_attachments_filter(self, service, sample_user_id, sample_expense):
        """Test search with has_attachments filter."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [sample_expense]
        
        service.db.query.return_value = mock_query
        
        # Mock the statistics calculation
        service._calculate_search_statistics = Mock(return_value={
            'total_amount': Decimal('25.99'),
            'average_amount': Decimal('25.99'),
            'date_range': {'earliest': date.today(), 'latest': date.today()},
            'category_breakdown': [],
            'merchant_breakdown': [],
            'field_match_counts': {}
        })
        
        # Execute
        result = await service.search_expenses(
            sample_user_id, 
            "coffee",
            has_attachments=True
        )
        
        # Verify
        assert result['filters_applied']['has_attachments'] == True
        # Verify additional filter was applied
        assert mock_query.filter.call_count > 1  # Base filter + attachment filter
    
    @pytest.mark.asyncio
    async def test_search_expenses_without_attachments_filter(self, service, sample_user_id, sample_expense):
        """Test search with has_attachments=False filter."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [sample_expense]
        
        service.db.query.return_value = mock_query
        
        # Mock the statistics calculation
        service._calculate_search_statistics = Mock(return_value={
            'total_amount': Decimal('25.99'),
            'average_amount': Decimal('25.99'),
            'date_range': {'earliest': date.today(), 'latest': date.today()},
            'category_breakdown': [],
            'merchant_breakdown': [],
            'field_match_counts': {}
        })
        
        # Execute
        result = await service.search_expenses(
            sample_user_id, 
            "coffee",
            has_attachments=False
        )
        
        # Verify
        assert result['filters_applied']['has_attachments'] == False
        # Verify additional filter was applied
        assert mock_query.filter.call_count > 1  # Base filter + attachment filter