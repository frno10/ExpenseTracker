"""
Tests for budget service functionality.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.models.budget import BudgetCreate, BudgetPeriod, CategoryBudgetCreate
from app.services.budget_service import BudgetService


@pytest.fixture
def budget_service():
    """Budget service fixture."""
    return BudgetService()


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def sample_user_id():
    """Sample user ID."""
    return uuid4()


@pytest.fixture
def sample_budget_data(sample_user_id):
    """Sample budget creation data."""
    return BudgetCreate(
        name="Monthly Budget",
        period=BudgetPeriod.MONTHLY,
        total_limit=Decimal("2000.00"),
        start_date=date.today(),
        end_date=None,
        is_active=True,
        user_id=sample_user_id
    )


@pytest.fixture
def sample_category_budgets():
    """Sample category budget data."""
    return [
        CategoryBudgetCreate(
            limit_amount=Decimal("500.00"),
            budget_id=uuid4(),
            category_id=uuid4()
        ),
        CategoryBudgetCreate(
            limit_amount=Decimal("300.00"),
            budget_id=uuid4(),
            category_id=uuid4()
        )
    ]


class TestBudgetService:
    """Test budget service functionality."""
    
    @pytest.mark.asyncio
    async def test_create_budget(self, budget_service, mock_db, sample_budget_data, sample_category_budgets):
        """Test creating a budget with category budgets."""
        # Mock repository responses
        mock_budget = MagicMock()
        mock_budget.id = uuid4()
        mock_budget.name = sample_budget_data.name
        
        budget_service.budget_repo.create = AsyncMock(return_value=mock_budget)
        budget_service.category_budget_repo.create = AsyncMock()
        budget_service.budget_repo.get_by_id = AsyncMock(return_value=mock_budget)
        
        # Create budget
        result = await budget_service.create_budget(mock_db, sample_budget_data, sample_category_budgets)
        
        # Verify calls
        budget_service.budget_repo.create.assert_called_once_with(mock_db, sample_budget_data)
        assert budget_service.category_budget_repo.create.call_count == len(sample_category_budgets)
        budget_service.budget_repo.get_by_id.assert_called_once_with(mock_db, mock_budget.id)
        
        assert result == mock_budget
    
    @pytest.mark.asyncio
    async def test_get_user_budgets_active_only(self, budget_service, mock_db, sample_user_id):
        """Test getting active budgets for a user."""
        # Mock repository response
        mock_budgets = [MagicMock(), MagicMock()]
        for budget in mock_budgets:
            budget.user_id = sample_user_id
        
        budget_service.budget_repo.get_active_budgets = AsyncMock(return_value=mock_budgets)
        
        # Get active budgets
        result = await budget_service.get_user_budgets(mock_db, sample_user_id, active_only=True)
        
        # Verify
        budget_service.budget_repo.get_active_budgets.assert_called_once_with(mock_db)
        assert result == mock_budgets
    
    @pytest.mark.asyncio
    async def test_check_budget_alerts_warning(self, budget_service, mock_db, sample_user_id):
        """Test budget alert generation for 80% threshold."""
        # Mock budget with 80% spending
        mock_budget = MagicMock()
        mock_budget.id = uuid4()
        mock_budget.name = "Test Budget"
        mock_budget.total_limit = Decimal("1000.00")
        mock_budget.user_id = sample_user_id
        
        # Mock category budget with 80% spending
        mock_category_budget = MagicMock()
        mock_category_budget.category_id = uuid4()
        mock_category_budget.limit_amount = Decimal("500.00")
        mock_category_budget.spent_amount = Decimal("400.00")  # 80%
        mock_category_budget.category = MagicMock()
        mock_category_budget.category.name = "Food"
        
        mock_budget.category_budgets = [mock_category_budget]
        
        budget_service.get_user_budgets = AsyncMock(return_value=[mock_budget])
        budget_service._update_budget_spending = AsyncMock()
        
        # Check alerts
        alerts = await budget_service.check_budget_alerts(mock_db, sample_user_id)
        
        # Verify warning alert is generated
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.alert_type == "warning"
        assert alert.percentage_used == 80.0
        assert "Food" in alert.message
    
    @pytest.mark.asyncio
    async def test_check_budget_alerts_exceeded(self, budget_service, mock_db, sample_user_id):
        """Test budget alert generation for exceeded budget."""
        # Mock budget with exceeded spending
        mock_budget = MagicMock()
        mock_budget.id = uuid4()
        mock_budget.name = "Test Budget"
        mock_budget.total_limit = Decimal("1000.00")
        mock_budget.user_id = sample_user_id
        
        # Mock category budget with exceeded spending
        mock_category_budget = MagicMock()
        mock_category_budget.category_id = uuid4()
        mock_category_budget.limit_amount = Decimal("500.00")
        mock_category_budget.spent_amount = Decimal("600.00")  # 120%
        mock_category_budget.category = MagicMock()
        mock_category_budget.category.name = "Food"
        
        mock_budget.category_budgets = [mock_category_budget]
        
        budget_service.get_user_budgets = AsyncMock(return_value=[mock_budget])
        budget_service._update_budget_spending = AsyncMock()
        
        # Check alerts
        alerts = await budget_service.check_budget_alerts(mock_db, sample_user_id)
        
        # Verify exceeded alert is generated
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.alert_type == "exceeded"
        assert alert.percentage_used == 120.0
        assert "exceeded by $100.00" in alert.message
    
    @pytest.mark.asyncio
    async def test_get_budget_progress(self, budget_service, mock_db, sample_user_id):
        """Test getting budget progress information."""
        budget_id = uuid4()
        
        # Mock budget with spending
        mock_budget = MagicMock()
        mock_budget.id = budget_id
        mock_budget.name = "Test Budget"
        mock_budget.period = BudgetPeriod.MONTHLY
        mock_budget.start_date = date.today()
        mock_budget.end_date = None
        mock_budget.total_limit = Decimal("1000.00")
        
        # Mock category budget
        mock_category_budget = MagicMock()
        mock_category_budget.category_id = uuid4()
        mock_category_budget.category = MagicMock()
        mock_category_budget.category.name = "Food"
        mock_category_budget.limit_amount = Decimal("500.00")
        mock_category_budget.spent_amount = Decimal("300.00")
        
        mock_budget.category_budgets = [mock_category_budget]
        
        budget_service.get_budget_with_spending = AsyncMock(return_value=mock_budget)
        
        # Get progress
        progress = await budget_service.get_budget_progress(mock_db, budget_id, sample_user_id)
        
        # Verify progress data
        assert progress is not None
        assert progress["budget_id"] == budget_id
        assert progress["budget_name"] == "Test Budget"
        assert progress["total_spent"] == Decimal("300.00")
        assert progress["total_remaining"] == Decimal("700.00")
        assert progress["total_percentage"] == 30.0
        assert len(progress["categories"]) == 1
        
        category = progress["categories"][0]
        assert category["category_name"] == "Food"
        assert category["percentage_used"] == 60.0
        assert not category["is_over_budget"]
    
    def test_calculate_period_end_date_monthly(self, budget_service):
        """Test calculating end date for monthly period."""
        start_date = date(2024, 1, 15)
        end_date = budget_service._calculate_period_end_date(start_date, BudgetPeriod.MONTHLY)
        
        # Should be last day of January
        assert end_date == date(2024, 1, 31)
    
    def test_calculate_period_end_date_yearly(self, budget_service):
        """Test calculating end date for yearly period."""
        start_date = date(2024, 1, 15)
        end_date = budget_service._calculate_period_end_date(start_date, BudgetPeriod.YEARLY)
        
        # Should be January 14, 2025 (one day before next year)
        assert end_date == date(2025, 1, 14)
    
    def test_calculate_period_end_date_custom(self, budget_service):
        """Test calculating end date for custom period."""
        start_date = date(2024, 1, 15)
        end_date = budget_service._calculate_period_end_date(start_date, BudgetPeriod.CUSTOM)
        
        # Should return None for custom periods
        assert end_date is None
    
    @pytest.mark.asyncio
    async def test_create_recurring_budget(self, budget_service, mock_db, sample_user_id):
        """Test creating a recurring budget."""
        base_budget_id = uuid4()
        next_period_start = date.today() + timedelta(days=30)
        
        # Mock base budget
        mock_base_budget = MagicMock()
        mock_base_budget.id = base_budget_id
        mock_base_budget.name = "Monthly Budget"
        mock_base_budget.period = BudgetPeriod.MONTHLY
        mock_base_budget.total_limit = Decimal("2000.00")
        mock_base_budget.user_id = sample_user_id
        
        # Mock category budget
        mock_category_budget = MagicMock()
        mock_category_budget.limit_amount = Decimal("500.00")
        mock_category_budget.category_id = uuid4()
        mock_base_budget.category_budgets = [mock_category_budget]
        
        # Mock new budget
        mock_new_budget = MagicMock()
        mock_new_budget.id = uuid4()
        
        budget_service.budget_repo.get_by_id = AsyncMock(return_value=mock_base_budget)
        budget_service.create_budget = AsyncMock(return_value=mock_new_budget)
        
        # Create recurring budget
        result = await budget_service.create_recurring_budget(
            mock_db, base_budget_id, sample_user_id, next_period_start
        )
        
        # Verify
        budget_service.budget_repo.get_by_id.assert_called_once_with(mock_db, base_budget_id)
        budget_service.create_budget.assert_called_once()
        
        # Check the create_budget call arguments
        call_args = budget_service.create_budget.call_args
        budget_data = call_args[0][1]  # Second argument (first is db)
        category_budgets_data = call_args[0][2]  # Third argument
        
        assert budget_data.start_date == next_period_start
        assert budget_data.total_limit == Decimal("2000.00")
        assert len(category_budgets_data) == 1
        assert category_budgets_data[0].limit_amount == Decimal("500.00")
        
        assert result == mock_new_budget


if __name__ == "__main__":
    pytest.main([__file__])