"""
Tests for analytics service functionality.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.services.analytics_service import AnalyticsService, TimeSeriesPoint, CategoryAnalysis, SpendingTrend
from app.models.expense import ExpenseTable
from app.models.category import CategoryTable
from app.models.merchant import MerchantTable


@pytest.fixture
def analytics_service():
    """Analytics service fixture."""
    return AnalyticsService()


@pytest.fixture
def sample_user_id():
    """Sample user ID."""
    return uuid4()


@pytest.fixture
def sample_expenses():
    """Sample expense data for testing."""
    expenses = []
    
    # Create mock categories
    food_category = MagicMock()
    food_category.id = uuid4()
    food_category.name = "Food"
    
    transport_category = MagicMock()
    transport_category.id = uuid4()
    transport_category.name = "Transport"
    
    # Create mock merchants
    restaurant_merchant = MagicMock()
    restaurant_merchant.id = uuid4()
    restaurant_merchant.name = "Restaurant ABC"
    
    gas_merchant = MagicMock()
    gas_merchant.id = uuid4()
    gas_merchant.name = "Gas Station XYZ"
    
    # Create sample expenses
    for i in range(10):
        expense = MagicMock()
        expense.id = uuid4()
        expense.amount = Decimal(f"{20 + i * 5}.00")
        expense.date = date.today() - timedelta(days=i)
        expense.description = f"Test expense {i}"
        
        # Alternate categories and merchants
        if i % 2 == 0:
            expense.category = food_category
            expense.merchant = restaurant_merchant
        else:
            expense.category = transport_category
            expense.merchant = gas_merchant
        
        expenses.append(expense)
    
    return expenses


@pytest.fixture
def mock_db():
    """Mock database session."""
    return MagicMock()


class TestAnalyticsService:
    """Test analytics service functionality."""
    
    @pytest.mark.asyncio
    async def test_get_spending_time_series_daily(
        self, 
        analytics_service, 
        mock_db, 
        sample_user_id, 
        sample_expenses
    ):
        """Test daily time series generation."""
        
        # Mock the database query
        analytics_service.expense_repo = MagicMock()
        
        # Create a mock query chain
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.all = AsyncMock(return_value=sample_expenses)
        
        mock_db.query.return_value = mock_query
        
        # Test daily time series
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()
        
        result = await analytics_service.get_spending_time_series(
            db=mock_db,
            user_id=sample_user_id,
            start_date=start_date,
            end_date=end_date,
            granularity="daily"
        )
        
        # Verify results
        assert isinstance(result, list)
        assert len(result) == 8  # 7 days + 1
        assert all(isinstance(point, TimeSeriesPoint) for point in result)
        
        # Check that we have data points for each day
        dates_in_result = [point.date for point in result]
        expected_dates = []
        current_date = start_date
        while current_date <= end_date:
            expected_dates.append(current_date)
            current_date += timedelta(days=1)
        
        assert set(dates_in_result) == set(expected_dates)
    
    @pytest.mark.asyncio
    async def test_get_category_spending_trends(
        self, 
        analytics_service, 
        mock_db, 
        sample_user_id, 
        sample_expenses
    ):
        """Test category spending trends analysis."""
        
        # Mock the _get_expenses_with_categories method
        analytics_service._get_expenses_with_categories = AsyncMock()
        
        # Current period expenses
        current_expenses = sample_expenses[:5]  # First 5 expenses
        # Previous period expenses (simulate lower spending)
        previous_expenses = sample_expenses[5:8]  # Next 3 expenses
        
        analytics_service._get_expenses_with_categories.side_effect = [
            current_expenses, previous_expenses
        ]
        
        # Test category trends
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        
        result = await analytics_service.get_category_spending_trends(
            db=mock_db,
            user_id=sample_user_id,
            start_date=start_date,
            end_date=end_date,
            limit=10
        )
        
        # Verify results
        assert isinstance(result, list)
        assert len(result) <= 10
        assert all(isinstance(analysis, CategoryAnalysis) for analysis in result)
        
        # Check that we have both categories
        category_names = [analysis.category_name for analysis in result]
        assert "Food" in category_names
        assert "Transport" in category_names
        
        # Verify analysis structure
        for analysis in result:
            assert analysis.total_amount >= 0
            assert analysis.transaction_count >= 0
            assert 0 <= analysis.percentage_of_total <= 100
            assert analysis.trend_direction in ["up", "down", "stable"]
    
    @pytest.mark.asyncio
    async def test_get_period_comparison(
        self, 
        analytics_service, 
        mock_db, 
        sample_user_id
    ):
        """Test period comparison functionality."""
        
        # Mock the _get_period_total method
        analytics_service._get_period_total = AsyncMock()
        
        # Current period: $500, Previous period: $400
        analytics_service._get_period_total.side_effect = [
            Decimal("500.00"),  # Current period
            Decimal("400.00")   # Previous period
        ]
        
        # Test period comparison
        current_start = date.today() - timedelta(days=30)
        current_end = date.today()
        
        result = await analytics_service.get_period_comparison(
            db=mock_db,
            user_id=sample_user_id,
            current_start=current_start,
            current_end=current_end,
            comparison_type="previous_period"
        )
        
        # Verify results
        assert isinstance(result, SpendingTrend)
        assert result.current_amount == Decimal("500.00")
        assert result.previous_amount == Decimal("400.00")
        assert result.change_amount == Decimal("100.00")
        assert result.change_percentage == 25.0  # 25% increase
        assert result.trend_direction == "up"
    
    @pytest.mark.asyncio
    async def test_detect_spending_anomalies(
        self, 
        analytics_service, 
        mock_db, 
        sample_user_id
    ):
        """Test spending anomaly detection."""
        
        # Create expenses with one anomaly
        normal_expenses = []
        for i in range(5):
            expense = MagicMock()
            expense.amount = Decimal("25.00")  # Normal amount
            expense.date = date.today() - timedelta(days=i)
            expense.category = MagicMock()
            expense.category.name = "Food"
            expense.merchant = MagicMock()
            expense.merchant.name = "Restaurant"
            normal_expenses.append(expense)
        
        # Add an anomaly
        anomaly_expense = MagicMock()
        anomaly_expense.amount = Decimal("200.00")  # Unusually high
        anomaly_expense.date = date.today()
        anomaly_expense.category = MagicMock()
        anomaly_expense.category.name = "Food"
        anomaly_expense.merchant = MagicMock()
        anomaly_expense.merchant.name = "Expensive Restaurant"
        
        current_expenses = [anomaly_expense]
        historical_expenses = normal_expenses
        
        # Mock the _get_expenses_with_categories method
        analytics_service._get_expenses_with_categories = AsyncMock()
        analytics_service._get_expenses_with_categories.side_effect = [
            current_expenses, historical_expenses
        ]
        
        # Test anomaly detection
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()
        
        result = await analytics_service.detect_spending_anomalies(
            db=mock_db,
            user_id=sample_user_id,
            start_date=start_date,
            end_date=end_date,
            sensitivity="medium"
        )
        
        # Verify results
        assert isinstance(result, list)
        assert len(result) > 0  # Should detect the anomaly
        
        # Check anomaly properties
        anomaly = result[0]
        assert anomaly.amount == Decimal("200.00")
        assert anomaly.anomaly_type == "high_amount"
        assert anomaly.severity in ["low", "medium", "high"]
    
    @pytest.mark.asyncio
    async def test_get_dashboard_summary(
        self, 
        analytics_service, 
        mock_db, 
        sample_user_id, 
        sample_expenses
    ):
        """Test dashboard summary generation."""
        
        # Mock all the required methods
        analytics_service._get_expenses_with_categories = AsyncMock(return_value=sample_expenses)
        analytics_service.get_period_comparison = AsyncMock()
        analytics_service.detect_spending_anomalies = AsyncMock(return_value=[])
        
        # Mock trend
        mock_trend = MagicMock()
        mock_trend.trend_direction = "up"
        mock_trend.change_amount = Decimal("50.00")
        mock_trend.change_percentage = 10.0
        analytics_service.get_period_comparison.return_value = mock_trend
        
        # Test dashboard summary
        result = await analytics_service.get_dashboard_summary(
            db=mock_db,
            user_id=sample_user_id,
            period_days=30
        )
        
        # Verify results structure
        assert isinstance(result, dict)
        assert "period" in result
        assert "summary" in result
        assert "trend" in result
        assert "category_breakdown" in result
        assert "merchant_breakdown" in result
        assert "anomalies" in result
        assert "insights" in result
        
        # Verify period information
        assert result["period"]["days"] == 30
        assert "start_date" in result["period"]
        assert "end_date" in result["period"]
        
        # Verify summary calculations
        assert result["summary"]["transaction_count"] == len(sample_expenses)
        assert result["summary"]["total_spending"] > 0
        assert result["summary"]["average_transaction"] > 0
    
    def test_group_expenses_by_time_daily(self, analytics_service, sample_expenses):
        """Test grouping expenses by daily periods."""
        
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()
        
        result = analytics_service._group_expenses_by_time(
            sample_expenses, "daily", start_date, end_date
        )
        
        # Verify results
        assert isinstance(result, list)
        assert len(result) == 8  # 7 days + 1
        assert all(isinstance(point, TimeSeriesPoint) for point in result)
        
        # Check that dates are in order
        dates = [point.date for point in result]
        assert dates == sorted(dates)
    
    def test_group_expenses_by_time_weekly(self, analytics_service, sample_expenses):
        """Test grouping expenses by weekly periods."""
        
        start_date = date.today() - timedelta(days=21)  # 3 weeks
        end_date = date.today()
        
        result = analytics_service._group_expenses_by_time(
            sample_expenses, "weekly", start_date, end_date
        )
        
        # Verify results
        assert isinstance(result, list)
        assert all(isinstance(point, TimeSeriesPoint) for point in result)
        
        # Check that all dates are Mondays (start of week)
        for point in result:
            assert point.date.weekday() == 0  # Monday
    
    def test_group_expenses_by_time_monthly(self, analytics_service, sample_expenses):
        """Test grouping expenses by monthly periods."""
        
        start_date = date.today().replace(day=1) - timedelta(days=60)  # ~2 months ago
        end_date = date.today()
        
        result = analytics_service._group_expenses_by_time(
            sample_expenses, "monthly", start_date, end_date
        )
        
        # Verify results
        assert isinstance(result, list)
        assert all(isinstance(point, TimeSeriesPoint) for point in result)
        
        # Check that all dates are first of month
        for point in result:
            assert point.date.day == 1
    
    def test_analyze_categories(self, analytics_service, sample_expenses):
        """Test category analysis functionality."""
        
        # Split expenses into current and previous periods
        current_expenses = sample_expenses[:5]
        previous_expenses = sample_expenses[5:]
        
        result = analytics_service._analyze_categories(
            current_expenses, previous_expenses, limit=10
        )
        
        # Verify results
        assert isinstance(result, list)
        assert len(result) <= 10
        assert all(isinstance(analysis, CategoryAnalysis) for analysis in result)
        
        # Check that results are sorted by amount (descending)
        amounts = [analysis.total_amount for analysis in result]
        assert amounts == sorted(amounts, reverse=True)
        
        # Verify analysis properties
        for analysis in result:
            assert analysis.total_amount >= 0
            assert analysis.transaction_count >= 0
            assert 0 <= analysis.percentage_of_total <= 100
            assert analysis.trend_direction in ["up", "down", "stable"]
    
    def test_get_category_breakdown(self, analytics_service, sample_expenses):
        """Test category breakdown calculation."""
        
        result = analytics_service._get_category_breakdown(sample_expenses)
        
        # Verify results
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check structure
        for category in result:
            assert "category" in category
            assert "amount" in category
            assert "count" in category
            assert "percentage" in category
            assert category["amount"] >= 0
            assert category["count"] >= 0
            assert 0 <= category["percentage"] <= 100
        
        # Check that percentages sum to ~100%
        total_percentage = sum(cat["percentage"] for cat in result)
        assert abs(total_percentage - 100.0) < 0.01  # Allow for rounding errors
    
    def test_get_merchant_breakdown(self, analytics_service, sample_expenses):
        """Test merchant breakdown calculation."""
        
        result = analytics_service._get_merchant_breakdown(sample_expenses)
        
        # Verify results
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check structure
        for merchant in result:
            assert "merchant" in merchant
            assert "amount" in merchant
            assert "count" in merchant
            assert merchant["amount"] >= 0
            assert merchant["count"] >= 0
        
        # Check that results are sorted by amount (descending)
        amounts = [merchant["amount"] for merchant in result]
        assert amounts == sorted(amounts, reverse=True)
    
    def test_generate_insights(self, analytics_service, sample_expenses):
        """Test insight generation."""
        
        # Create mock trend
        mock_trend = MagicMock()
        mock_trend.trend_direction = "up"
        mock_trend.change_percentage = 25.0
        
        # Create mock anomalies
        mock_anomalies = [MagicMock()]
        mock_anomalies[0].severity = "high"
        
        result = analytics_service._generate_insights(
            sample_expenses, mock_trend, mock_anomalies
        )
        
        # Verify results
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(insight, str) for insight in result)
        
        # Check that insights contain relevant information
        insights_text = " ".join(result).lower()
        assert any(keyword in insights_text for keyword in ["spending", "category", "transaction", "average"])