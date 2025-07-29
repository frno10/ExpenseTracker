"""
Tests for budget and expense integration.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.models.budget import BudgetCreate, BudgetPeriod, CategoryBudgetCreate
from app.models.expense import ExpenseCreate
from app.services.expense_service import ExpenseService
from app.services.budget_service import BudgetService


@pytest.fixture
def expense_service():
    """Expense service fixture."""
    return ExpenseService()


@pytest.fixture
def budget_service():
    """Budget service fixture."""
    return BudgetService()


@pytest.fixture
def sample_user_id():
    """Sample user ID."""
    return uuid4()


@pytest.fixture
def sample_category_id():
    """Sample category ID."""
    return uuid4()


@pytest.fixture
def sample_expense_data(sample_user_id, sample_category_id):
    """Sample expense creation data."""
    return ExpenseCreate(
        amount=Decimal("50.00"),
        description="Test expense",
        date=date.today(),
        category_id=sample_category_id,
        user_id=sample_user_id
    )


@pytest.fixture
def sample_budget_data(sample_user_id):
    """Sample budget creation data."""
    return BudgetCreate(
        name="Monthly Budget",
        period=BudgetPeriod.MONTHLY,
        total_limit=Decimal("1000.00"),
        start_date=date.today().replace(day=1),
        is_active=True,
        user_id=sample_user_id
    )


@pytest.fixture
def sample_category_budget(sample_category_id):
    """Sample category budget data."""
    return CategoryBudgetCreate(
        limit_amount=Decimal("200.00"),
        budget_id=uuid4(),
        category_id=sample_category_id
    )


class TestBudgetExpenseIntegration:
    """Test budget and expense integration."""
    
    @pytest.mark.asyncio
    async def test_create_expense_updates_budget(
        self, 
        expense_service, 
        mock_db, 
        sample_expense_data, 
        sample_user_id
    ):
        """Test that creating an expense updates related budgets."""
        
        # Mock expense creation
        mock_expense = MagicMock()
        mock_expense.id = uuid4()
        mock_expense.amount = sample_expense_data.amount
        mock_expense.user_id = sample_user_id
        mock_expense.category = MagicMock()
        mock_expense.category.name = "Food"
        mock_expense.date = sample_expense_data.date
        
        expense_service.expense_repo.create = AsyncMock(return_value=mock_expense)
        
        # Mock budget service methods
        expense_service.budget_service.get_budgets_for_category = AsyncMock(return_value=[])
        
        # Create expense
        result = await expense_service.create_expense(
            mock_db, sample_expense_data, sample_user_id
        )
        
        # Verify expense was created
        assert result == mock_expense
        expense_service.expense_repo.create.assert_called_once()
        
        # Verify budget integration was called
        expense_service.budget_service.get_budgets_for_category.assert_called_once_with(
            mock_db, sample_user_id, "Food", sample_expense_data.date
        )
    
    @pytest.mark.asyncio
    async def test_update_expense_recalculates_budgets(
        self, 
        expense_service, 
        mock_db, 
        sample_user_id
    ):
        """Test that updating an expense recalculates budgets."""
        
        expense_id = uuid4()
        
        # Mock original expense
        mock_original_expense = MagicMock()
        mock_original_expense.user_id = sample_user_id
        mock_original_expense.amount = Decimal("30.00")
        
        # Mock updated expense
        mock_updated_expense = MagicMock()
        mock_updated_expense.user_id = sample_user_id
        mock_updated_expense.amount = Decimal("50.00")
        
        expense_service.expense_repo.get_by_id = AsyncMock(return_value=mock_original_expense)
        expense_service.expense_repo.update = AsyncMock(return_value=mock_updated_expense)
        expense_service.budget_service.recalculate_user_budgets = AsyncMock(return_value=[])
        
        # Update expense with amount change
        from app.models.expense import ExpenseUpdate
        update_data = ExpenseUpdate(amount=Decimal("50.00"))
        
        result = await expense_service.update_expense(
            mock_db, expense_id, update_data, sample_user_id
        )
        
        # Verify expense was updated
        assert result == mock_updated_expense
        expense_service.expense_repo.update.assert_called_once()
        
        # Verify budget recalculation was called
        expense_service.budget_service.recalculate_user_budgets.assert_called_once_with(
            mock_db, sample_user_id
        )
    
    @pytest.mark.asyncio
    async def test_delete_expense_recalculates_budgets(
        self, 
        expense_service, 
        mock_db, 
        sample_user_id
    ):
        """Test that deleting an expense recalculates budgets."""
        
        expense_id = uuid4()
        
        # Mock expense
        mock_expense = MagicMock()
        mock_expense.user_id = sample_user_id
        
        expense_service.expense_repo.get_by_id = AsyncMock(return_value=mock_expense)
        expense_service.expense_repo.delete = AsyncMock(return_value=True)
        expense_service.budget_service.recalculate_user_budgets = AsyncMock(return_value=[])
        
        # Delete expense
        result = await expense_service.delete_expense(
            mock_db, expense_id, sample_user_id
        )
        
        # Verify expense was deleted
        assert result is True
        expense_service.expense_repo.delete.assert_called_once()
        
        # Verify budget recalculation was called
        expense_service.budget_service.recalculate_user_budgets.assert_called_once_with(
            mock_db, sample_user_id
        )
    
    @pytest.mark.asyncio
    async def test_get_budgets_for_category(
        self, 
        budget_service, 
        mock_db, 
        sample_user_id, 
        sample_category_id
    ):
        """Test getting budgets that include a specific category."""
        
        # Mock budget with category
        mock_budget = MagicMock()
        mock_budget.start_date = date.today().replace(day=1)
        mock_budget.end_date = None
        mock_budget.category_budgets = [MagicMock()]
        mock_budget.category_budgets[0].category = MagicMock()
        mock_budget.category_budgets[0].category.name = "Food"
        
        # Mock budget without specific categories (includes all)
        mock_budget_all = MagicMock()
        mock_budget_all.start_date = date.today().replace(day=1)
        mock_budget_all.end_date = None
        mock_budget_all.category_budgets = []
        
        budget_service.budget_repo.get_multi = AsyncMock(
            return_value=[mock_budget, mock_budget_all]
        )
        
        # Get budgets for Food category
        result = await budget_service.get_budgets_for_category(
            mock_db, sample_user_id, "Food", date.today()
        )
        
        # Should return both budgets (one specific, one all-inclusive)
        assert len(result) == 2
        assert mock_budget in result
        assert mock_budget_all in result
    
    @pytest.mark.asyncio
    async def test_recalculate_user_budgets(
        self, 
        budget_service, 
        mock_db, 
        sample_user_id
    ):
        """Test recalculating all budgets for a user."""
        
        # Mock active budgets
        mock_budget1 = MagicMock()
        mock_budget1.id = uuid4()
        mock_budget2 = MagicMock()
        mock_budget2.id = uuid4()
        
        budget_service.budget_repo.get_multi = AsyncMock(
            return_value=[mock_budget1, mock_budget2]
        )
        budget_service._update_budget_spending = AsyncMock()
        budget_service.check_budget_alerts = AsyncMock(return_value=[])
        
        # Recalculate budgets
        result = await budget_service.recalculate_user_budgets(
            mock_db, sample_user_id
        )
        
        # Verify all budgets were processed
        assert len(result) == 2
        assert mock_budget1 in result
        assert mock_budget2 in result
        
        # Verify spending was updated for each budget
        assert budget_service._update_budget_spending.call_count == 2
        assert budget_service.check_budget_alerts.call_count == 2
    
    @pytest.mark.asyncio
    async def test_expense_triggers_budget_alert(
        self, 
        expense_service, 
        mock_db, 
        sample_expense_data, 
        sample_user_id
    ):
        """Test that an expense can trigger budget alerts."""
        
        # Mock expense creation
        mock_expense = MagicMock()
        mock_expense.id = uuid4()
        mock_expense.amount = Decimal("180.00")  # Large amount to trigger alert
        mock_expense.user_id = sample_user_id
        mock_expense.category = MagicMock()
        mock_expense.category.name = "Food"
        mock_expense.date = sample_expense_data.date
        
        # Mock budget that will be affected
        mock_budget = MagicMock()
        mock_budget.id = uuid4()
        
        expense_service.expense_repo.create = AsyncMock(return_value=mock_expense)
        expense_service.budget_service.get_budgets_for_category = AsyncMock(
            return_value=[mock_budget]
        )
        expense_service.budget_service._update_budget_spending = AsyncMock()
        
        # Mock alert generation
        from app.services.budget_service import BudgetAlert
        mock_alert = BudgetAlert(
            budget_id=mock_budget.id,
            category_id=None,
            alert_type="warning",
            message="Budget warning",
            percentage_used=85.0,
            amount_spent=Decimal("170.00"),
            amount_limit=Decimal("200.00"),
            amount_remaining=Decimal("30.00")
        )
        
        expense_service.budget_service.check_budget_alerts = AsyncMock(
            return_value=[mock_alert]
        )
        
        # Create expense
        result = await expense_service.create_expense(
            mock_db, sample_expense_data, sample_user_id
        )
        
        # Verify expense was created
        assert result == mock_expense
        
        # Verify budget was updated and alerts were checked
        expense_service.budget_service._update_budget_spending.assert_called_once_with(
            mock_db, mock_budget
        )
        expense_service.budget_service.check_budget_alerts.assert_called_once_with(
            mock_db, sample_user_id, mock_budget.id
        )