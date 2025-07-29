"""Unit tests for budget service."""
import pytest
from decimal import Decimal
from datetime import date, datetime
from uuid import uuid4
from unittest.mock import AsyncMock, Mock, patch

from app.services.budget_service import BudgetService
from app.models.budget import BudgetCreate, BudgetUpdate
from app.repositories.budget import budget_repository
from app.repositories.expense import expense_repository
from tests.conftest import AsyncTestCase


class TestBudgetService(AsyncTestCase):
    """Test cases for BudgetService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.budget_service = BudgetService()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_budget_success(self, db_session, test_user):
        """Test successful budget creation."""
        budget_data = BudgetCreate(
            name="Monthly Food Budget",
            total_limit=Decimal("500.00"),
            period="monthly",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        with patch.object(budget_repository, 'create') as mock_create:
            mock_budget = Mock()
            mock_budget.id = uuid4()
            mock_budget.name = budget_data.name
            mock_budget.total_limit = budget_data.total_limit
            mock_budget.period = budget_data.period
            mock_budget.start_date = budget_data.start_date
            mock_budget.end_date = budget_data.end_date
            mock_budget.created_at = datetime.utcnow()
            
            mock_create.return_value = mock_budget
            
            result = await self.budget_service.create_budget(
                db_session, budget_data, test_user.id
            )
            
            assert result == mock_budget
            mock_create.assert_called_once_with(db_session, budget_data, test_user.id)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_budget_invalid_dates(self, db_session, test_user):
        """Test budget creation with invalid date range."""
        budget_data = BudgetCreate(
            name="Invalid Budget",
            total_limit=Decimal("500.00"),
            period="monthly",
            start_date=date(2024, 1, 31),  # Start after end
            end_date=date(2024, 1, 1)
        )
        
        with pytest.raises(ValueError, match="Start date must be before end date"):
            await self.budget_service.create_budget(
                db_session, budget_data, test_user.id
            )
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_budget_invalid_limit(self, db_session, test_user):
        """Test budget creation with invalid limit."""
        budget_data = BudgetCreate(
            name="Invalid Budget",
            total_limit=Decimal("-100.00"),  # Negative limit
            period="monthly",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        with pytest.raises(ValueError, match="Budget limit must be positive"):
            await self.budget_service.create_budget(
                db_session, budget_data, test_user.id
            )
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_budget_by_id_success(self, db_session, test_user):
        """Test successful budget retrieval by ID."""
        budget_id = uuid4()
        
        with patch.object(budget_repository, 'get') as mock_get:
            mock_budget = Mock()
            mock_budget.id = budget_id
            mock_budget.user_id = test_user.id
            mock_get.return_value = mock_budget
            
            result = await self.budget_service.get_budget_by_id(
                db_session, budget_id, test_user.id
            )
            
            assert result == mock_budget
            mock_get.assert_called_once_with(db_session, budget_id)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_budget_by_id_unauthorized(self, db_session, test_user):
        """Test budget retrieval for unauthorized user."""
        budget_id = uuid4()
        other_user_id = uuid4()
        
        with patch.object(budget_repository, 'get') as mock_get:
            mock_budget = Mock()
            mock_budget.id = budget_id
            mock_budget.user_id = other_user_id  # Different user
            mock_get.return_value = mock_budget
            
            with pytest.raises(PermissionError, match="Access denied"):
                await self.budget_service.get_budget_by_id(
                    db_session, budget_id, test_user.id
                )
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_budget_success(self, db_session, test_user):
        """Test successful budget update."""
        budget_id = uuid4()
        update_data = BudgetUpdate(
            name="Updated Budget",
            total_limit=Decimal("600.00")
        )
        
        with patch.object(budget_repository, 'get') as mock_get, \
             patch.object(budget_repository, 'update') as mock_update:
            
            # Mock existing budget
            mock_budget = Mock()
            mock_budget.id = budget_id
            mock_budget.user_id = test_user.id
            mock_budget.name = "Original Budget"
            mock_budget.total_limit = Decimal("500.00")
            mock_get.return_value = mock_budget
            
            # Mock updated budget
            mock_updated_budget = Mock()
            mock_updated_budget.id = budget_id
            mock_updated_budget.name = update_data.name
            mock_updated_budget.total_limit = update_data.total_limit
            mock_update.return_value = mock_updated_budget
            
            result = await self.budget_service.update_budget(
                db_session, budget_id, update_data, test_user.id
            )
            
            assert result == mock_updated_budget
            mock_get.assert_called_once_with(db_session, budget_id)
            mock_update.assert_called_once_with(db_session, budget_id, update_data)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_budget_success(self, db_session, test_user):
        """Test successful budget deletion."""
        budget_id = uuid4()
        
        with patch.object(budget_repository, 'get') as mock_get, \
             patch.object(budget_repository, 'delete') as mock_delete:
            
            # Mock existing budget
            mock_budget = Mock()
            mock_budget.id = budget_id
            mock_budget.user_id = test_user.id
            mock_get.return_value = mock_budget
            
            mock_delete.return_value = True
            
            result = await self.budget_service.delete_budget(
                db_session, budget_id, test_user.id
            )
            
            assert result is True
            mock_get.assert_called_once_with(db_session, budget_id)
            mock_delete.assert_called_once_with(db_session, budget_id)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calculate_budget_usage_success(self, db_session, test_user):
        """Test successful budget usage calculation."""
        budget_id = uuid4()
        
        with patch.object(budget_repository, 'get') as mock_get_budget, \
             patch.object(expense_repository, 'get_by_budget_period') as mock_get_expenses:
            
            # Mock budget
            mock_budget = Mock()
            mock_budget.id = budget_id
            mock_budget.user_id = test_user.id
            mock_budget.total_limit = Decimal("500.00")
            mock_budget.start_date = date(2024, 1, 1)
            mock_budget.end_date = date(2024, 1, 31)
            mock_get_budget.return_value = mock_budget
            
            # Mock expenses
            mock_expenses = [
                Mock(amount=Decimal("150.00")),
                Mock(amount=Decimal("75.50")),
                Mock(amount=Decimal("25.00"))
            ]
            mock_get_expenses.return_value = mock_expenses
            
            result = await self.budget_service.calculate_budget_usage(
                db_session, budget_id, test_user.id
            )
            
            assert result["budget_limit"] == Decimal("500.00")
            assert result["total_spent"] == Decimal("250.50")
            assert result["remaining"] == Decimal("249.50")
            assert result["usage_percentage"] == 50.1
            assert result["is_over_budget"] is False
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calculate_budget_usage_over_budget(self, db_session, test_user):
        """Test budget usage calculation when over budget."""
        budget_id = uuid4()
        
        with patch.object(budget_repository, 'get') as mock_get_budget, \
             patch.object(expense_repository, 'get_by_budget_period') as mock_get_expenses:
            
            # Mock budget
            mock_budget = Mock()
            mock_budget.id = budget_id
            mock_budget.user_id = test_user.id
            mock_budget.total_limit = Decimal("500.00")
            mock_budget.start_date = date(2024, 1, 1)
            mock_budget.end_date = date(2024, 1, 31)
            mock_get_budget.return_value = mock_budget
            
            # Mock expenses that exceed budget
            mock_expenses = [
                Mock(amount=Decimal("300.00")),
                Mock(amount=Decimal("250.00"))
            ]
            mock_get_expenses.return_value = mock_expenses
            
            result = await self.budget_service.calculate_budget_usage(
                db_session, budget_id, test_user.id
            )
            
            assert result["budget_limit"] == Decimal("500.00")
            assert result["total_spent"] == Decimal("550.00")
            assert result["remaining"] == Decimal("-50.00")
            assert result["usage_percentage"] == 110.0
            assert result["is_over_budget"] is True
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_budget_alerts_success(self, db_session, test_user):
        """Test successful budget alerts retrieval."""
        with patch.object(budget_repository, 'get_by_user') as mock_get_budgets, \
             patch.object(self.budget_service, 'calculate_budget_usage') as mock_calc_usage:
            
            # Mock budgets
            mock_budgets = [
                Mock(id=uuid4(), name="Budget 1", alert_threshold=0.8),
                Mock(id=uuid4(), name="Budget 2", alert_threshold=0.9)
            ]
            mock_get_budgets.return_value = mock_budgets
            
            # Mock usage calculations
            mock_calc_usage.side_effect = [
                {"usage_percentage": 85.0, "is_over_budget": False},  # Over threshold
                {"usage_percentage": 75.0, "is_over_budget": False}   # Under threshold
            ]
            
            result = await self.budget_service.get_budget_alerts(
                db_session, test_user.id
            )
            
            assert len(result) == 1  # Only one budget over threshold
            assert result[0]["budget_name"] == "Budget 1"
            assert result[0]["usage_percentage"] == 85.0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_budget_limits_success(self, db_session, test_user):
        """Test successful budget limits checking."""
        expense_amount = Decimal("100.00")
        category_id = uuid4()
        
        with patch.object(budget_repository, 'get_active_budgets_for_category') as mock_get_budgets, \
             patch.object(self.budget_service, 'calculate_budget_usage') as mock_calc_usage:
            
            # Mock active budgets
            mock_budgets = [
                Mock(id=uuid4(), name="Food Budget", total_limit=Decimal("500.00"))
            ]
            mock_get_budgets.return_value = mock_budgets
            
            # Mock usage calculation
            mock_calc_usage.return_value = {
                "total_spent": Decimal("400.00"),
                "remaining": Decimal("100.00"),
                "is_over_budget": False
            }
            
            result = await self.budget_service.check_budget_limits(
                db_session, test_user.id, expense_amount, category_id
            )
            
            assert result["can_add_expense"] is True
            assert result["warnings"] == []
            assert result["would_exceed_budgets"] == []