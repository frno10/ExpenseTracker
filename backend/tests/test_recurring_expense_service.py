import pytest
from decimal import Decimal
from datetime import datetime, date, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch, AsyncMock

from app.services.recurring_expense_service import RecurringExpenseService
from app.models.recurring_expense import (
    RecurringExpenseTable, RecurringExpenseHistoryTable, RecurringExpenseNotificationTable,
    RecurrenceFrequency, RecurrenceStatus
)
from app.core.exceptions import ValidationError, NotFoundError, BusinessLogicError


class TestRecurringExpenseService:
    """Test cases for RecurringExpenseService."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def mock_repository(self):
        """Mock recurring expense repository."""
        return Mock()
    
    @pytest.fixture
    def mock_expense_service(self):
        """Mock expense service."""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_db, mock_repository, mock_expense_service):
        """RecurringExpenseService instance with mocked dependencies."""
        service = RecurringExpenseService(mock_db)
        service.repository = mock_repository
        service.expense_service = mock_expense_service
        return service
    
    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID."""
        return uuid4()
    
    @pytest.fixture
    def sample_recurring_expense_data(self):
        """Sample recurring expense data."""
        return {
            'name': 'Netflix Subscription',
            'description': 'Monthly streaming service',
            'amount': Decimal('15.99'),
            'frequency': RecurrenceFrequency.MONTHLY,
            'interval': 1,
            'start_date': date.today(),
            'category_id': uuid4(),
            'payment_method_id': uuid4(),
            'is_auto_create': True,
            'notify_before_days': 1
        }
    
    @pytest.fixture
    def sample_recurring_expense(self, sample_user_id):
        """Sample recurring expense instance."""
        return RecurringExpenseTable(
            id=uuid4(),
            user_id=sample_user_id,
            name='Netflix Subscription',
            description='Monthly streaming service',
            amount=Decimal('15.99'),
            frequency=RecurrenceFrequency.MONTHLY,
            interval=1,
            start_date=date.today(),
            next_due_date=date.today(),
            max_occurrences=None,
            current_occurrences=0,
            status=RecurrenceStatus.ACTIVE,
            is_auto_create=True,
            notify_before_days=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    # ===== CREATE RECURRING EXPENSE TESTS =====
    
    @pytest.mark.asyncio
    async def test_create_recurring_expense_success(
        self, service, sample_user_id, sample_recurring_expense_data, sample_recurring_expense
    ):
        """Test successful recurring expense creation."""
        # Setup
        service.repository.create_recurring_expense.return_value = sample_recurring_expense
        
        # Execute
        result = await service.create_recurring_expense(sample_user_id, sample_recurring_expense_data)
        
        # Verify
        assert result == sample_recurring_expense
        service.repository.create_recurring_expense.assert_called_once()
        
        # Check that user_id was added and next_due_date was set
        call_args = service.repository.create_recurring_expense.call_args[0][0]
        assert call_args['user_id'] == sample_user_id
        assert 'next_due_date' in call_args
    
    @pytest.mark.asyncio
    async def test_create_recurring_expense_validation_error(
        self, service, sample_user_id
    ):
        """Test recurring expense creation with invalid data."""
        # Setup - invalid data (missing required fields)
        invalid_data = {'description': 'Missing required fields'}
        
        # Execute & Verify
        with pytest.raises(ValidationError, match="Missing required field: name"):
            await service.create_recurring_expense(sample_user_id, invalid_data)
    
    @pytest.mark.asyncio
    async def test_create_recurring_expense_invalid_amount(
        self, service, sample_user_id
    ):
        """Test recurring expense creation with invalid amount."""
        # Setup
        invalid_data = {
            'name': 'Test Expense',
            'amount': Decimal('-10.00'),  # Negative amount
            'frequency': RecurrenceFrequency.MONTHLY,
            'start_date': date.today()
        }
        
        # Execute & Verify
        with pytest.raises(ValidationError, match="Amount must be positive"):
            await service.create_recurring_expense(sample_user_id, invalid_data)
    
    @pytest.mark.asyncio
    async def test_create_recurring_expense_invalid_frequency(
        self, service, sample_user_id
    ):
        """Test recurring expense creation with invalid frequency."""
        # Setup
        invalid_data = {
            'name': 'Test Expense',
            'amount': Decimal('10.00'),
            'frequency': 'invalid_frequency',
            'start_date': date.today()
        }
        
        # Execute & Verify
        with pytest.raises(ValidationError, match="Invalid frequency"):
            await service.create_recurring_expense(sample_user_id, invalid_data)
    
    @pytest.mark.asyncio
    async def test_create_recurring_expense_invalid_date_range(
        self, service, sample_user_id
    ):
        """Test recurring expense creation with invalid date range."""
        # Setup
        start_date = date.today()
        end_date = start_date - timedelta(days=1)  # End before start
        
        invalid_data = {
            'name': 'Test Expense',
            'amount': Decimal('10.00'),
            'frequency': RecurrenceFrequency.MONTHLY,
            'start_date': start_date,
            'end_date': end_date
        }
        
        # Execute & Verify
        with pytest.raises(ValidationError, match="End date must be after start date"):
            await service.create_recurring_expense(sample_user_id, invalid_data)
    
    # ===== GET RECURRING EXPENSE TESTS =====
    
    @pytest.mark.asyncio
    async def test_get_recurring_expense_success(
        self, service, sample_user_id, sample_recurring_expense
    ):
        """Test successful recurring expense retrieval."""
        # Setup
        recurring_expense_id = sample_recurring_expense.id
        service.repository.get_recurring_expense_by_id.return_value = sample_recurring_expense
        
        # Execute
        result = await service.get_recurring_expense(recurring_expense_id, sample_user_id)
        
        # Verify
        assert result == sample_recurring_expense
        service.repository.get_recurring_expense_by_id.assert_called_once_with(
            recurring_expense_id, sample_user_id
        )
    
    @pytest.mark.asyncio
    async def test_get_recurring_expense_not_found(
        self, service, sample_user_id
    ):
        """Test recurring expense retrieval when not found."""
        # Setup
        recurring_expense_id = uuid4()
        service.repository.get_recurring_expense_by_id.return_value = None
        
        # Execute & Verify
        with pytest.raises(NotFoundError, match=f"Recurring expense {recurring_expense_id} not found"):
            await service.get_recurring_expense(recurring_expense_id, sample_user_id)
    
    # ===== UPDATE RECURRING EXPENSE TESTS =====
    
    @pytest.mark.asyncio
    async def test_update_recurring_expense_success(
        self, service, sample_user_id, sample_recurring_expense
    ):
        """Test successful recurring expense update."""
        # Setup
        recurring_expense_id = sample_recurring_expense.id
        update_data = {'name': 'Updated Name', 'amount': Decimal('20.00')}
        
        service.repository.get_recurring_expense_by_id.return_value = sample_recurring_expense
        service.repository.update_recurring_expense.return_value = sample_recurring_expense
        
        # Execute
        result = await service.update_recurring_expense(recurring_expense_id, sample_user_id, update_data)
        
        # Verify
        assert result == sample_recurring_expense
        service.repository.update_recurring_expense.assert_called_once_with(
            recurring_expense_id, sample_user_id, update_data
        )
    
    @pytest.mark.asyncio
    async def test_update_recurring_expense_frequency_change(
        self, service, sample_user_id, sample_recurring_expense
    ):
        """Test recurring expense update with frequency change."""
        # Setup
        recurring_expense_id = sample_recurring_expense.id
        update_data = {'frequency': RecurrenceFrequency.WEEKLY}
        
        service.repository.get_recurring_expense_by_id.return_value = sample_recurring_expense
        service.repository.update_recurring_expense.return_value = sample_recurring_expense
        
        # Execute
        await service.update_recurring_expense(recurring_expense_id, sample_user_id, update_data)
        
        # Verify that next_due_date was recalculated
        call_args = service.repository.update_recurring_expense.call_args[0][2]
        assert 'next_due_date' in call_args
    
    # ===== EXPENSE GENERATION TESTS =====
    
    @pytest.mark.asyncio
    async def test_create_expense_from_recurring_success(
        self, service, sample_user_id, sample_recurring_expense
    ):
        """Test successful expense creation from recurring expense."""
        # Setup
        recurring_expense_id = sample_recurring_expense.id
        expense_date = date.today()
        
        mock_expense = Mock()
        mock_expense.id = uuid4()
        
        service.repository.get_recurring_expense_by_id.return_value = sample_recurring_expense
        service.expense_service.create_expense = AsyncMock(return_value=mock_expense)
        
        # Execute
        result = await service.create_expense_from_recurring(
            recurring_expense_id, sample_user_id, expense_date
        )
        
        # Verify
        assert result == mock_expense
        service.expense_service.create_expense.assert_called_once()
        
        # Check expense data
        call_args = service.expense_service.create_expense.call_args[0]
        expense_data = call_args[1]
        assert expense_data['amount'] == sample_recurring_expense.amount
        assert expense_data['expense_date'] == expense_date
        assert expense_data['recurring_expense_id'] == sample_recurring_expense.id
        assert expense_data['is_recurring'] == True
        
        # Verify history entry was created
        service.repository.create_history_entry.assert_called_once()
        
        # Verify occurrence count was incremented
        service.repository.increment_occurrence_count.assert_called_once_with(
            sample_recurring_expense.id
        )
        
        # Verify next due date was updated
        service.repository.update_next_due_date.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_due_recurring_expenses_success(
        self, service, sample_user_id
    ):
        """Test processing due recurring expenses."""
        # Setup
        due_expenses = [sample_recurring_expense]
        service.repository.get_due_recurring_expenses.return_value = due_expenses
        
        # Mock the _process_single_recurring_expense method
        service._process_single_recurring_expense = AsyncMock(return_value=True)
        
        # Execute
        results = await service.process_due_recurring_expenses(sample_user_id)
        
        # Verify
        assert results['processed'] == 1
        assert results['created'] == 1
        assert results['failed'] == 0
        assert len(results['errors']) == 0
        
        service._process_single_recurring_expense.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_single_recurring_expense_auto_create(
        self, service, sample_user_id, sample_recurring_expense
    ):
        """Test processing a single recurring expense with auto-create enabled."""
        # Setup
        sample_recurring_expense.is_auto_create = True
        sample_recurring_expense.is_completed = False
        due_date = date.today()
        
        mock_expense = Mock()
        mock_expense.id = uuid4()
        
        service.expense_service.create_expense = AsyncMock(return_value=mock_expense)
        
        # Execute
        result = await service._process_single_recurring_expense(sample_recurring_expense, due_date)
        
        # Verify
        assert result == True
        service.expense_service.create_expense.assert_called_once()
        service.repository.create_history_entry.assert_called_once()
        service.repository.increment_occurrence_count.assert_called_once()
        service.repository.update_next_due_date.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_single_recurring_expense_no_auto_create(
        self, service, sample_user_id, sample_recurring_expense
    ):
        """Test processing a single recurring expense with auto-create disabled."""
        # Setup
        sample_recurring_expense.is_auto_create = False
        sample_recurring_expense.is_completed = False
        due_date = date.today()
        
        # Execute
        result = await service._process_single_recurring_expense(sample_recurring_expense, due_date)
        
        # Verify
        assert result == False
        service.expense_service.create_expense.assert_not_called()
        service.repository.create_history_entry.assert_called_once()
        service.repository.increment_occurrence_count.assert_called_once()
        service.repository.update_next_due_date.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_single_recurring_expense_completed(
        self, service, sample_user_id, sample_recurring_expense
    ):
        """Test processing a completed recurring expense."""
        # Setup
        sample_recurring_expense.is_completed = True
        due_date = date.today()
        
        # Execute
        result = await service._process_single_recurring_expense(sample_recurring_expense, due_date)
        
        # Verify
        assert result == False
        service.repository.update_recurring_expense.assert_called_once_with(
            sample_recurring_expense.id,
            sample_recurring_expense.user_id,
            {'status': RecurrenceStatus.COMPLETED}
        )
    
    # ===== UPCOMING EXPENSES TESTS =====
    
    @pytest.mark.asyncio
    async def test_get_upcoming_recurring_expenses(
        self, service, sample_user_id, sample_recurring_expense
    ):
        """Test getting upcoming recurring expenses."""
        # Setup
        days_ahead = 30
        sample_recurring_expense.get_upcoming_dates = Mock(return_value=[
            date.today() + timedelta(days=1),
            date.today() + timedelta(days=8),
            date.today() + timedelta(days=15)
        ])
        
        # Mock category and merchant
        sample_recurring_expense.category = Mock()
        sample_recurring_expense.category.name = "Subscriptions"
        sample_recurring_expense.merchant = Mock()
        sample_recurring_expense.merchant.name = "Netflix"
        
        service.repository.get_upcoming_recurring_expenses.return_value = [sample_recurring_expense]
        
        # Execute
        result = await service.get_upcoming_recurring_expenses(sample_user_id, days_ahead)
        
        # Verify
        assert len(result) == 3
        assert all(item['recurring_expense_id'] == str(sample_recurring_expense.id) for item in result)
        assert all(item['name'] == sample_recurring_expense.name for item in result)
        assert all(item['amount'] == sample_recurring_expense.amount for item in result)
        assert all(item['category_name'] == "Subscriptions" for item in result)
        assert all(item['merchant_name'] == "Netflix" for item in result)
        
        # Check dates are sorted
        dates = [item['due_date'] for item in result]
        assert dates == sorted(dates)
    
    # ===== STATUS MANAGEMENT TESTS =====
    
    @pytest.mark.asyncio
    async def test_pause_recurring_expense(
        self, service, sample_user_id, sample_recurring_expense
    ):
        """Test pausing a recurring expense."""
        # Setup
        recurring_expense_id = sample_recurring_expense.id
        service.repository.get_recurring_expense_by_id.return_value = sample_recurring_expense
        service.repository.update_recurring_expense.return_value = sample_recurring_expense
        
        # Execute
        result = await service.pause_recurring_expense(recurring_expense_id, sample_user_id)
        
        # Verify
        assert result == sample_recurring_expense
        service.repository.update_recurring_expense.assert_called_once_with(
            recurring_expense_id, sample_user_id, {'status': RecurrenceStatus.PAUSED}
        )
    
    @pytest.mark.asyncio
    async def test_resume_recurring_expense(
        self, service, sample_user_id, sample_recurring_expense
    ):
        """Test resuming a recurring expense."""
        # Setup
        recurring_expense_id = sample_recurring_expense.id
        service.repository.get_recurring_expense_by_id.return_value = sample_recurring_expense
        service.repository.update_recurring_expense.return_value = sample_recurring_expense
        
        # Execute
        result = await service.resume_recurring_expense(recurring_expense_id, sample_user_id)
        
        # Verify
        assert result == sample_recurring_expense
        service.repository.update_recurring_expense.assert_called_once_with(
            recurring_expense_id, sample_user_id, {'status': RecurrenceStatus.ACTIVE}
        )
    
    @pytest.mark.asyncio
    async def test_cancel_recurring_expense(
        self, service, sample_user_id, sample_recurring_expense
    ):
        """Test cancelling a recurring expense."""
        # Setup
        recurring_expense_id = sample_recurring_expense.id
        service.repository.get_recurring_expense_by_id.return_value = sample_recurring_expense
        service.repository.update_recurring_expense.return_value = sample_recurring_expense
        
        # Execute
        result = await service.cancel_recurring_expense(recurring_expense_id, sample_user_id)
        
        # Verify
        assert result == sample_recurring_expense
        service.repository.update_recurring_expense.assert_called_once_with(
            recurring_expense_id, sample_user_id, {'status': RecurrenceStatus.CANCELLED}
        )
    
    # ===== NOTIFICATION TESTS =====
    
    @pytest.mark.asyncio
    async def test_create_upcoming_notifications(
        self, service, sample_user_id
    ):
        """Test creating upcoming notifications."""
        # Setup
        sample_recurring_expense.next_due_date = date.today() + timedelta(days=1)
        sample_recurring_expense.notify_before_days = 1
        sample_recurring_expense.last_notification_sent = None
        
        service.repository.get_due_recurring_expenses.return_value = [sample_recurring_expense]
        
        # Execute
        result = await service.create_upcoming_notifications(sample_user_id)
        
        # Verify
        assert result == 1
        service.repository.create_notification.assert_called_once()
        service.repository.update_last_notification_sent.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_upcoming_notifications_already_sent(
        self, service, sample_user_id, sample_recurring_expense
    ):
        """Test that notifications are not sent twice on the same day."""
        # Setup
        sample_recurring_expense.next_due_date = date.today() + timedelta(days=1)
        sample_recurring_expense.notify_before_days = 1
        sample_recurring_expense.last_notification_sent = datetime.now()  # Already sent today
        
        service.repository.get_due_recurring_expenses.return_value = [sample_recurring_expense]
        
        # Execute
        result = await service.create_upcoming_notifications(sample_user_id)
        
        # Verify
        assert result == 0
        service.repository.create_notification.assert_not_called()
    
    # ===== ANALYTICS TESTS =====
    
    @pytest.mark.asyncio
    async def test_get_recurring_expense_summary(
        self, service, sample_user_id
    ):
        """Test getting recurring expense summary."""
        # Setup
        summary_data = {
            'total_active': 5,
            'total_monthly_equivalent': Decimal('150.00'),
            'frequency_breakdown': {
                'monthly': {'count': 3, 'amount': Decimal('100.00')},
                'weekly': {'count': 2, 'amount': Decimal('50.00')}
            },
            'due_count': 2,
            'overdue_count': 1,
            'recent_successful_creations': 8,
            'recent_failed_creations': 1,
            'success_rate': 88.9
        }
        service.repository.get_recurring_expense_summary.return_value = summary_data
        
        # Execute
        result = await service.get_recurring_expense_summary(sample_user_id)
        
        # Verify
        assert result == summary_data
        service.repository.get_recurring_expense_summary.assert_called_once_with(sample_user_id)
    
    @pytest.mark.asyncio
    async def test_get_recurring_expenses_by_category(
        self, service, sample_user_id
    ):
        """Test getting recurring expenses grouped by category."""
        # Setup
        category_data = [
            {
                'category_id': str(uuid4()),
                'category_name': 'Subscriptions',
                'count': 3,
                'total_amount': Decimal('45.00')
            },
            {
                'category_id': str(uuid4()),
                'category_name': 'Utilities',
                'count': 2,
                'total_amount': Decimal('200.00')
            }
        ]
        service.repository.get_recurring_expenses_by_category.return_value = category_data
        
        # Execute
        result = await service.get_recurring_expenses_by_category(sample_user_id)
        
        # Verify
        assert result == category_data
        service.repository.get_recurring_expenses_by_category.assert_called_once_with(sample_user_id)


class TestRecurringExpenseModel:
    """Test cases for RecurringExpenseTable model methods."""
    
    @pytest.fixture
    def sample_recurring_expense(self):
        """Sample recurring expense for testing."""
        return RecurringExpenseTable(
            id=uuid4(),
            user_id=uuid4(),
            name='Test Expense',
            amount=Decimal('10.00'),
            frequency=RecurrenceFrequency.MONTHLY,
            interval=1,
            start_date=date(2025, 1, 1),
            next_due_date=date(2025, 1, 1),
            max_occurrences=None,
            current_occurrences=0,
            status=RecurrenceStatus.ACTIVE,
            is_auto_create=True,
            notify_before_days=1
        )
    
    def test_is_active_property(self, sample_recurring_expense):
        """Test is_active property."""
        assert sample_recurring_expense.is_active == True
        
        sample_recurring_expense.status = RecurrenceStatus.PAUSED
        assert sample_recurring_expense.is_active == False
    
    def test_is_due_property(self, sample_recurring_expense):
        """Test is_due property."""
        # Set due date to today
        sample_recurring_expense.next_due_date = date.today()
        assert sample_recurring_expense.is_due == True
        
        # Set due date to tomorrow
        sample_recurring_expense.next_due_date = date.today() + timedelta(days=1)
        assert sample_recurring_expense.is_due == False
        
        # Inactive expense should not be due
        sample_recurring_expense.status = RecurrenceStatus.PAUSED
        sample_recurring_expense.next_due_date = date.today()
        assert sample_recurring_expense.is_due == False
    
    def test_is_completed_property(self, sample_recurring_expense):
        """Test is_completed property."""
        # Not completed by default
        assert sample_recurring_expense.is_completed == False
        
        # Completed by max occurrences
        sample_recurring_expense.max_occurrences = 5
        sample_recurring_expense.current_occurrences = 5
        assert sample_recurring_expense.is_completed == True
        
        # Reset for end date test
        sample_recurring_expense.max_occurrences = None
        sample_recurring_expense.current_occurrences = 0
        
        # Completed by end date
        sample_recurring_expense.end_date = date.today() - timedelta(days=1)
        assert sample_recurring_expense.is_completed == True
    
    def test_remaining_occurrences_property(self, sample_recurring_expense):
        """Test remaining_occurrences property."""
        # No max occurrences
        assert sample_recurring_expense.remaining_occurrences is None
        
        # With max occurrences
        sample_recurring_expense.max_occurrences = 10
        sample_recurring_expense.current_occurrences = 3
        assert sample_recurring_expense.remaining_occurrences == 7
        
        # All occurrences used
        sample_recurring_expense.current_occurrences = 10
        assert sample_recurring_expense.remaining_occurrences == 0
    
    def test_frequency_description_property(self, sample_recurring_expense):
        """Test frequency_description property."""
        # Interval of 1
        assert sample_recurring_expense.frequency_description == "Monthly"
        
        # Interval greater than 1
        sample_recurring_expense.interval = 2
        assert sample_recurring_expense.frequency_description == "Every 2 monthlys"
    
    def test_calculate_next_due_date_daily(self, sample_recurring_expense):
        """Test calculating next due date for daily frequency."""
        sample_recurring_expense.frequency = RecurrenceFrequency.DAILY
        sample_recurring_expense.interval = 1
        
        from_date = date(2025, 1, 1)
        next_date = sample_recurring_expense.calculate_next_due_date(from_date)
        
        assert next_date == date(2025, 1, 2)
    
    def test_calculate_next_due_date_weekly(self, sample_recurring_expense):
        """Test calculating next due date for weekly frequency."""
        sample_recurring_expense.frequency = RecurrenceFrequency.WEEKLY
        sample_recurring_expense.interval = 1
        
        from_date = date(2025, 1, 1)  # Wednesday
        next_date = sample_recurring_expense.calculate_next_due_date(from_date)
        
        assert next_date == date(2025, 1, 8)  # Next Wednesday
    
    def test_calculate_next_due_date_monthly(self, sample_recurring_expense):
        """Test calculating next due date for monthly frequency."""
        sample_recurring_expense.frequency = RecurrenceFrequency.MONTHLY
        sample_recurring_expense.interval = 1
        
        from_date = date(2025, 1, 15)
        next_date = sample_recurring_expense.calculate_next_due_date(from_date)
        
        assert next_date == date(2025, 2, 15)
    
    def test_calculate_next_due_date_monthly_with_day_of_month(self, sample_recurring_expense):
        """Test calculating next due date for monthly frequency with specific day."""
        sample_recurring_expense.frequency = RecurrenceFrequency.MONTHLY
        sample_recurring_expense.interval = 1
        sample_recurring_expense.day_of_month = 1  # First of month
        
        from_date = date(2025, 1, 15)
        next_date = sample_recurring_expense.calculate_next_due_date(from_date)
        
        assert next_date == date(2025, 2, 1)
    
    def test_calculate_next_due_date_annually(self, sample_recurring_expense):
        """Test calculating next due date for annual frequency."""
        sample_recurring_expense.frequency = RecurrenceFrequency.ANNUALLY
        sample_recurring_expense.interval = 1
        
        from_date = date(2025, 1, 15)
        next_date = sample_recurring_expense.calculate_next_due_date(from_date)
        
        assert next_date == date(2026, 1, 15)
    
    def test_get_upcoming_dates(self, sample_recurring_expense):
        """Test getting upcoming dates."""
        sample_recurring_expense.frequency = RecurrenceFrequency.WEEKLY
        sample_recurring_expense.interval = 1
        sample_recurring_expense.next_due_date = date(2025, 1, 1)
        
        upcoming_dates = sample_recurring_expense.get_upcoming_dates(3)
        
        assert len(upcoming_dates) == 3
        assert upcoming_dates[0] == date(2025, 1, 1)
        assert upcoming_dates[1] == date(2025, 1, 8)
        assert upcoming_dates[2] == date(2025, 1, 15)
    
    def test_get_upcoming_dates_with_max_occurrences(self, sample_recurring_expense):
        """Test getting upcoming dates with max occurrences limit."""
        sample_recurring_expense.frequency = RecurrenceFrequency.WEEKLY
        sample_recurring_expense.interval = 1
        sample_recurring_expense.next_due_date = date(2025, 1, 1)
        sample_recurring_expense.max_occurrences = 2
        sample_recurring_expense.current_occurrences = 1
        
        upcoming_dates = sample_recurring_expense.get_upcoming_dates(5)
        
        # Should only return 1 date (2 max - 1 current = 1 remaining)
        assert len(upcoming_dates) == 1
        assert upcoming_dates[0] == date(2025, 1, 1)
    
    def test_get_upcoming_dates_with_end_date(self, sample_recurring_expense):
        """Test getting upcoming dates with end date limit."""
        sample_recurring_expense.frequency = RecurrenceFrequency.WEEKLY
        sample_recurring_expense.interval = 1
        sample_recurring_expense.next_due_date = date(2025, 1, 1)
        sample_recurring_expense.end_date = date(2025, 1, 10)  # Before third occurrence
        
        upcoming_dates = sample_recurring_expense.get_upcoming_dates(5)
        
        # Should only return 2 dates (within end date)
        assert len(upcoming_dates) == 2
        assert upcoming_dates[0] == date(2025, 1, 1)
        assert upcoming_dates[1] == date(2025, 1, 8)