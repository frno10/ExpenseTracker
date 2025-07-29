"""Unit tests for expense service."""
import pytest
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4
from unittest.mock import AsyncMock, Mock, patch

from app.services.expense_service import ExpenseService
from app.models.expense import ExpenseCreate, ExpenseUpdate
from app.repositories.expense import expense_repository
from app.repositories.category import category_repository
from tests.conftest import AsyncTestCase


class TestExpenseService(AsyncTestCase):
    """Test cases for ExpenseService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.expense_service = ExpenseService()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_expense_success(self, db_session, test_user, test_category):
        """Test successful expense creation."""
        expense_data = ExpenseCreate(
            amount=Decimal("25.50"),
            description="Coffee",
            category_id=test_category.id,
            date=date.today()
        )
        
        with patch.object(expense_repository, 'create') as mock_create:
            mock_expense = Mock()
            mock_expense.id = uuid4()
            mock_expense.amount = expense_data.amount
            mock_expense.description = expense_data.description
            mock_expense.category = test_category
            mock_expense.date = expense_data.date
            mock_expense.created_at = datetime.utcnow()
            
            mock_create.return_value = mock_expense
            
            result = await self.expense_service.create_expense(
                db_session, expense_data, test_user.id
            )
            
            assert result == mock_expense
            mock_create.assert_called_once_with(db_session, expense_data, test_user.id)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_expense_invalid_amount(self, db_session, test_user, test_category):
        """Test expense creation with invalid amount."""
        expense_data = ExpenseCreate(
            amount=Decimal("-10.00"),  # Negative amount
            description="Invalid expense",
            category_id=test_category.id,
            date=date.today()
        )
        
        with pytest.raises(ValueError, match="Amount must be positive"):
            await self.expense_service.create_expense(
                db_session, expense_data, test_user.id
            )
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_expense_by_id_success(self, db_session, test_user):
        """Test successful expense retrieval by ID."""
        expense_id = uuid4()
        
        with patch.object(expense_repository, 'get') as mock_get:
            mock_expense = Mock()
            mock_expense.id = expense_id
            mock_expense.user_id = test_user.id
            mock_get.return_value = mock_expense
            
            result = await self.expense_service.get_expense_by_id(
                db_session, expense_id, test_user.id
            )
            
            assert result == mock_expense
            mock_get.assert_called_once_with(db_session, expense_id)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_expense_by_id_not_found(self, db_session, test_user):
        """Test expense retrieval when expense doesn't exist."""
        expense_id = uuid4()
        
        with patch.object(expense_repository, 'get') as mock_get:
            mock_get.return_value = None
            
            result = await self.expense_service.get_expense_by_id(
                db_session, expense_id, test_user.id
            )
            
            assert result is None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_expense_by_id_unauthorized(self, db_session, test_user):
        """Test expense retrieval for unauthorized user."""
        expense_id = uuid4()
        other_user_id = uuid4()
        
        with patch.object(expense_repository, 'get') as mock_get:
            mock_expense = Mock()
            mock_expense.id = expense_id
            mock_expense.user_id = other_user_id  # Different user
            mock_get.return_value = mock_expense
            
            with pytest.raises(PermissionError, match="Access denied"):
                await self.expense_service.get_expense_by_id(
                    db_session, expense_id, test_user.id
                )
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_expense_success(self, db_session, test_user, test_category):
        """Test successful expense update."""
        expense_id = uuid4()
        update_data = ExpenseUpdate(
            amount=Decimal("30.00"),
            description="Updated coffee"
        )
        
        with patch.object(expense_repository, 'get') as mock_get, \
             patch.object(expense_repository, 'update') as mock_update:
            
            # Mock existing expense
            mock_expense = Mock()
            mock_expense.id = expense_id
            mock_expense.user_id = test_user.id
            mock_expense.amount = Decimal("25.50")
            mock_expense.description = "Coffee"
            mock_expense.category_id = test_category.id
            mock_get.return_value = mock_expense
            
            # Mock updated expense
            mock_updated_expense = Mock()
            mock_updated_expense.id = expense_id
            mock_updated_expense.amount = update_data.amount
            mock_updated_expense.description = update_data.description
            mock_update.return_value = mock_updated_expense
            
            result = await self.expense_service.update_expense(
                db_session, expense_id, update_data, test_user.id
            )
            
            assert result == mock_updated_expense
            mock_get.assert_called_once_with(db_session, expense_id)
            mock_update.assert_called_once_with(db_session, expense_id, update_data)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_expense_success(self, db_session, test_user):
        """Test successful expense deletion."""
        expense_id = uuid4()
        
        with patch.object(expense_repository, 'get') as mock_get, \
             patch.object(expense_repository, 'delete') as mock_delete:
            
            # Mock existing expense
            mock_expense = Mock()
            mock_expense.id = expense_id
            mock_expense.user_id = test_user.id
            mock_get.return_value = mock_expense
            
            mock_delete.return_value = True
            
            result = await self.expense_service.delete_expense(
                db_session, expense_id, test_user.id
            )
            
            assert result is True
            mock_get.assert_called_once_with(db_session, expense_id)
            mock_delete.assert_called_once_with(db_session, expense_id)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_user_expenses_with_filters(self, db_session, test_user):
        """Test getting user expenses with filters."""
        filters = {
            "category": "Food",
            "min_amount": 10.0,
            "max_amount": 100.0,
            "date_from": "2024-01-01",
            "date_to": "2024-01-31"
        }
        
        with patch.object(expense_repository, 'get_by_user_with_filters') as mock_get_filtered:
            mock_expenses = [Mock(), Mock(), Mock()]
            mock_get_filtered.return_value = mock_expenses
            
            result = await self.expense_service.get_user_expenses(
                db_session, test_user.id, **filters
            )
            
            assert result == mock_expenses
            mock_get_filtered.assert_called_once_with(
                db_session, test_user.id, **filters
            )
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calculate_expense_statistics_success(self, db_session, test_user):
        """Test successful expense statistics calculation."""
        with patch.object(expense_repository, 'get_by_user_with_filters') as mock_get_filtered:
            mock_expenses = [
                Mock(amount=Decimal("25.50"), date=date(2024, 1, 15)),
                Mock(amount=Decimal("45.00"), date=date(2024, 1, 16)),
                Mock(amount=Decimal("12.75"), date=date(2024, 1, 17))
            ]
            mock_get_filtered.return_value = mock_expenses
            
            result = await self.expense_service.calculate_expense_statistics(
                db_session, test_user.id, date(2024, 1, 1), date(2024, 1, 31)
            )
            
            assert result["total_amount"] == Decimal("83.25")
            assert result["expense_count"] == 3
            assert result["average_amount"] == Decimal("27.75")
            assert result["min_amount"] == Decimal("12.75")
            assert result["max_amount"] == Decimal("45.00")