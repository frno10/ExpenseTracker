"""
Tests for advanced analytics service functionality.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.services.advanced_analytics_service import (
    AdvancedAnalyticsService, 
    AdvancedAnomaly, 
    TrendForecast, 
    CustomDashboard, 
    VisualizationData
)
from app.models.expense import ExpenseTable
from app.models.category import CategoryTable
from app.models.merchant import MerchantTable


@pytest.fixture
def advanced_analytics_service():
    """Advanced analytics service fixture."""
    return AdvancedAnalyticsService()


@pytest.fixture
def sample_user_id():
    """Sample user ID."""
    return uuid4()


@pytest.fixture
def sample_expenses_with_anomaly():
    """Sample expense data with anomalies for testing."""
    expenses = []
    
    # Create mock categories and merchants
    food_category = MagicMock()
    food_category.id = uuid4()
    food_category.name = "Food"
    
    restaurant_merchant = MagicMock()
    restaurant_merchant.id = uuid4()
    restaurant_merchant.name = "Restaurant ABC"
    
    # Create normal expenses
    for i in range(10):
        expense = MagicMock()
        expense.id = uuid4()
        expense.amount = Decimal("25.00")  # Normal amount
        expense.date = date.today() - timedelta(days=i)
        expense.description = f"Normal expense {i}"
        expense.category = food_category
        expense.merchant = restaurant_merchant
        expenses.append(expense)
    
    # Add an anomalous expense
    anomaly_expense = MagicMock()
    anomaly_expense.id = uuid4()
    anomaly_expense.amount = Decimal("500.00")  # Anomalously high
    anomaly_expense.date = date.today()
    anomaly_expense.description = "Expensive dinner"
    anomaly_expense.category = food_category
    anomaly_expense.merchant = restaurant_merchant
    expenses.append(anomaly_expense)
    
    return expenses


@pytest.fixture
def sample_historical_expenses():
    """Sample historical expense data."""
    expenses = []
    
    food_category = MagicMock()
    food_category.id = uuid4()
    food_category.name = "Food"
    
    restaurant_merchant = MagicMock()
    restaurant_merchant.id = uuid4()
    restaurant_merchant.name = "Restaurant ABC"
    
    # Create consistent historical expenses
    for i in range(30):
        expense = MagicMock()
        expense.id = uuid4()
        expense.amount = Decimal("20.00")  # Consistent historical amount
        expense.date = date.today() - timedelta(days=30 + i)
        expense.description = f"Historical expense {i}"
        expense.category = food_category
        expense.merchant = restaurant_merchant
        expenses.append(expense)
    
    return expenses


@pytest.fixture
def mock_db():
    """Mock database session."""
    return MagicMock()


class TestAdvancedAnalyticsService:
    """Test advanced analytics service functionality."""
    
    @pytest.mark.asyncio
    async def test_detect_advanced_anomalies(
        self, 
        advanced_analytics_service, 
        mock_db, 
        sample_user_id, 
        sample_expenses_with_anomaly, 
        sample_historical_expenses
    ):
        """Test advanced anomaly detection."""
        
        # Mock the _get_expenses_with_relationships method
        advanced_analytics_service._get_expenses_with_relationships = AsyncMock()
        advanced_analytics_service._get_expenses_with_relationships.side_effect = [
            sample_expenses_with_anomaly,  # Current expenses
            sample_historical_expenses     # Historical expenses
        ]
        
        # Test anomaly detection
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()
        
        result = await advanced_analytics_service.detect_advanced_anomalies(
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
        assert isinstance(anomaly, AdvancedAnomaly)
        assert anomaly.anomaly_type == "statistical"
        assert anomaly.severity in ["low", "medium", "high", "critical"]
        assert 0.0 <= anomaly.confidence_score <= 1.0
        assert len(anomaly.contributing_factors) > 0
        assert len(anomaly.suggested_actions) > 0
        assert isinstance(anomaly.historical_context, dict)
    
    @pytest.mark.asyncio
    async def test_analyze_trends_and_forecast(
        self, 
        advanced_analytics_service, 
        mock_db, 
        sample_user_id
    ):
        """Test trend analysis and forecasting."""
        
        # Create mock expenses with trend
        expenses = []
        food_category = MagicMock()
        food_category.name = "Food"
        
        # Create increasing trend over 12 months
        for i in range(12):
            expense = MagicMock()
            expense.id = uuid4()
            expense.amount = Decimal(f"{100 + i * 10}.00")  # Increasing trend
            expense.date = date.today() - timedelta(days=30 * (11 - i))
            expense.category = food_category
            expenses.append(expense)
        
        # Mock the _get_expenses_with_relationships method
        advanced_analytics_service._get_expenses_with_relationships = AsyncMock(
            return_value=expenses
        )
        
        # Test trend analysis
        result = await advanced_analytics_service.analyze_trends_and_forecast(
            db=mock_db,
            user_id=sample_user_id,
            forecast_periods=6
        )
        
        # Verify results
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check forecast properties
        forecast = result[0]
        assert isinstance(forecast, TrendForecast)
        assert forecast.category == "Food"
        assert forecast.current_trend in ["increasing", "decreasing", "stable", "volatile", "insufficient_data"]
        assert 0.0 <= forecast.trend_strength <= 1.0
        assert isinstance(forecast.seasonal_pattern, dict)
        assert len(forecast.forecast_periods) == 6
        assert isinstance(forecast.confidence_interval, tuple)
        assert len(forecast.confidence_interval) == 2
        assert isinstance(forecast.key_insights, list)
    
    @pytest.mark.asyncio
    async def test_create_custom_dashboard(
        self, 
        advanced_analytics_service, 
        sample_user_id
    ):
        """Test custom dashboard creation."""
        
        # Test dashboard creation
        dashboard = await advanced_analytics_service.create_custom_dashboard(
            user_id=sample_user_id,
            name="My Custom Dashboard",
            description="Test dashboard",
            is_public=False
        )
        
        # Verify results
        assert isinstance(dashboard, CustomDashboard)
        assert dashboard.user_id == sample_user_id
        assert dashboard.name == "My Custom Dashboard"
        assert dashboard.description == "Test dashboard"
        assert dashboard.is_public == False
        assert isinstance(dashboard.layout, dict)
        assert isinstance(dashboard.widgets, list)
        assert isinstance(dashboard.filters, dict)
        assert dashboard.id is not None
    
    @pytest.mark.asyncio
    async def test_get_user_dashboards(
        self, 
        advanced_analytics_service, 
        sample_user_id
    ):
        """Test getting user dashboards."""
        
        # Create a test dashboard first
        await advanced_analytics_service.create_custom_dashboard(
            user_id=sample_user_id,
            name="Test Dashboard",
            description="Test"
        )
        
        # Get user dashboards
        result = await advanced_analytics_service.get_user_dashboards(
            user_id=sample_user_id
        )
        
        # Verify results
        assert isinstance(result, list)
        assert len(result) > 0
        
        dashboard = result[0]
        assert isinstance(dashboard, CustomDashboard)
        assert dashboard.user_id == sample_user_id
        assert dashboard.name == "Test Dashboard"
    
    @pytest.mark.asyncio
    async def test_update_custom_dashboard(
        self, 
        advanced_analytics_service, 
        sample_user_id
    ):
        """Test updating custom dashboard."""
        
        # Create a dashboard first
        dashboard = await advanced_analytics_service.create_custom_dashboard(
            user_id=sample_user_id,
            name="Original Name",
            description="Original description"
        )
        
        # Update the dashboard
        updated_dashboard = await advanced_analytics_service.update_custom_dashboard(
            dashboard_id=dashboard.id,
            user_id=sample_user_id,
            updates={
                "name": "Updated Name",
                "description": "Updated description"
            }
        )
        
        # Verify results
        assert updated_dashboard is not None
        assert updated_dashboard.name == "Updated Name"
        assert updated_dashboard.description == "Updated description"
        assert updated_dashboard.id == dashboard.id
    
    @pytest.mark.asyncio
    async def test_delete_custom_dashboard(
        self, 
        advanced_analytics_service, 
        sample_user_id
    ):
        """Test deleting custom dashboard."""
        
        # Create a dashboard first
        dashboard = await advanced_analytics_service.create_custom_dashboard(
            user_id=sample_user_id,
            name="To Delete",
            description="Will be deleted"
        )
        
        # Delete the dashboard
        success = await advanced_analytics_service.delete_custom_dashboard(
            dashboard_id=dashboard.id,
            user_id=sample_user_id
        )
        
        # Verify deletion
        assert success == True
        
        # Verify it's no longer accessible
        dashboards = await advanced_analytics_service.get_user_dashboards(
            user_id=sample_user_id
        )
        dashboard_ids = [d.id for d in dashboards]
        assert dashboard.id not in dashboard_ids
    
    @pytest.mark.asyncio
    async def test_generate_visualizations(
        self, 
        advanced_analytics_service, 
        mock_db, 
        sample_user_id, 
        sample_expenses_with_anomaly
    ):
        """Test visualization generation."""
        
        # Mock the _get_expenses_with_relationships method
        advanced_analytics_service._get_expenses_with_relationships = AsyncMock(
            return_value=sample_expenses_with_anomaly
        )
        
        # Test visualization generation
        visualization_types = ["spending_heatmap", "category_treemap", "trend_line_chart"]
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        
        result = await advanced_analytics_service.generate_visualizations(
            db=mock_db,
            user_id=sample_user_id,
            visualization_types=visualization_types,
            start_date=start_date,
            end_date=end_date
        )
        
        # Verify results
        assert isinstance(result, list)
        assert len(result) == len(visualization_types)
        
        for viz in result:
            assert isinstance(viz, VisualizationData)
            assert viz.type in ["heatmap", "treemap", "line"]
            assert isinstance(viz.title, str)
            assert isinstance(viz.data, list)
            assert isinstance(viz.config, dict)
            assert isinstance(viz.insights, list)
    
    @pytest.mark.asyncio
    async def test_export_analytics_data(
        self, 
        advanced_analytics_service, 
        mock_db, 
        sample_user_id, 
        sample_expenses_with_anomaly
    ):
        """Test analytics data export."""
        
        # Mock dependencies
        advanced_analytics_service._get_expenses_with_relationships = AsyncMock(
            return_value=sample_expenses_with_anomaly
        )
        
        # Mock analytics service import
        from unittest.mock import patch
        with patch('app.services.advanced_analytics_service.analytics_service') as mock_analytics:
            mock_analytics.get_category_spending_trends = AsyncMock(return_value=[])
            
            # Test data export
            start_date = date.today() - timedelta(days=30)
            end_date = date.today()
            
            result = await advanced_analytics_service.export_analytics_data(
                db=mock_db,
                user_id=sample_user_id,
                export_type="json",
                data_types=["expenses", "anomalies"],
                start_date=start_date,
                end_date=end_date
            )
            
            # Verify results
            assert isinstance(result, dict)
            assert "metadata" in result
            assert "data" in result
            
            # Check metadata
            metadata = result["metadata"]
            assert metadata["user_id"] == str(sample_user_id)
            assert metadata["export_type"] == "json"
            assert "expenses" in metadata["data_types"]
            assert "anomalies" in metadata["data_types"]
            
            # Check data
            data = result["data"]
            assert "expenses" in data
            assert "anomalies" in data
            assert isinstance(data["expenses"], list)
            assert isinstance(data["anomalies"], list)
    
    def test_calculate_severity(self, advanced_analytics_service):
        """Test severity calculation."""
        
        thresholds = [2.0, 2.5, 3.0, 4.0]
        
        # Test different severity levels
        assert advanced_analytics_service._calculate_severity(1.5, thresholds) == "low"
        assert advanced_analytics_service._calculate_severity(2.2, thresholds) == "medium"
        assert advanced_analytics_service._calculate_severity(3.2, thresholds) == "high"
        assert advanced_analytics_service._calculate_severity(4.5, thresholds) == "critical"
    
    def test_get_default_layout(self, advanced_analytics_service):
        """Test default layout generation."""
        
        layout = advanced_analytics_service._get_default_layout()
        
        # Verify layout structure
        assert isinstance(layout, dict)
        assert "grid" in layout
        assert "widgets" in layout
        
        # Check grid configuration
        grid = layout["grid"]
        assert "columns" in grid
        assert "rows" in grid
        assert "gap" in grid
        
        # Check widgets configuration
        widgets = layout["widgets"]
        assert isinstance(widgets, list)
        assert len(widgets) > 0
        
        for widget in widgets:
            assert "id" in widget
            assert "x" in widget
            assert "y" in widget
            assert "w" in widget
            assert "h" in widget
    
    def test_get_default_widgets(self, advanced_analytics_service):
        """Test default widgets generation."""
        
        widgets = advanced_analytics_service._get_default_widgets()
        
        # Verify widgets structure
        assert isinstance(widgets, list)
        assert len(widgets) > 0
        
        for widget in widgets:
            assert "id" in widget
            assert "type" in widget
            assert "title" in widget
            assert "config" in widget
            assert isinstance(widget["config"], dict)
    
    @pytest.mark.asyncio
    async def test_detect_statistical_anomalies(
        self, 
        advanced_analytics_service, 
        sample_expenses_with_anomaly, 
        sample_historical_expenses
    ):
        """Test statistical anomaly detection algorithm."""
        
        # Test statistical anomaly detection
        result = await advanced_analytics_service._detect_statistical_anomalies(
            sample_expenses_with_anomaly,
            sample_historical_expenses,
            "medium"
        )
        
        # Verify results
        assert isinstance(result, list)
        assert len(result) > 0  # Should detect the high-value anomaly
        
        # Check anomaly properties
        anomaly = result[0]
        assert anomaly.anomaly_type == "statistical"
        assert anomaly.amount == Decimal("500.00")  # The anomalous amount
        assert anomaly.severity in ["low", "medium", "high", "critical"]
        assert "Z-score" in anomaly.contributing_factors[0]
    
    @pytest.mark.asyncio
    async def test_detect_behavioral_anomalies(
        self, 
        advanced_analytics_service, 
        sample_expenses_with_anomaly, 
        sample_historical_expenses
    ):
        """Test behavioral anomaly detection algorithm."""
        
        # Create expenses with frequency anomaly
        current_expenses = []
        historical_expenses = []
        
        # Mock merchant
        merchant = MagicMock()
        merchant.name = "Test Merchant"
        
        # Current period: high frequency (10 transactions)
        for i in range(10):
            expense = MagicMock()
            expense.id = uuid4()
            expense.amount = Decimal("25.00")
            expense.date = date.today() - timedelta(days=i)
            expense.merchant = merchant
            expense.category = MagicMock()
            expense.category.name = "Food"
            current_expenses.append(expense)
        
        # Historical period: low frequency (2 transactions)
        for i in range(2):
            expense = MagicMock()
            expense.id = uuid4()
            expense.amount = Decimal("25.00")
            expense.date = date.today() - timedelta(days=30 + i)
            expense.merchant = merchant
            expense.category = MagicMock()
            expense.category.name = "Food"
            historical_expenses.append(expense)
        
        # Test behavioral anomaly detection
        result = await advanced_analytics_service._detect_behavioral_anomalies(
            current_expenses,
            historical_expenses,
            "medium"
        )
        
        # Verify results
        assert isinstance(result, list)
        assert len(result) > 0  # Should detect the frequency anomaly
        
        # Check anomaly properties
        anomaly = result[0]
        assert anomaly.anomaly_type == "behavioral"
        assert "frequency" in anomaly.description.lower()
        assert "Test Merchant" in anomaly.merchant
    
    @pytest.mark.asyncio
    async def test_analyze_category_trend_insufficient_data(
        self, 
        advanced_analytics_service
    ):
        """Test trend analysis with insufficient data."""
        
        # Create minimal expense data (less than 6 months)
        expenses = []
        for i in range(3):  # Only 3 expenses
            expense = MagicMock()
            expense.date = date.today() - timedelta(days=30 * i)
            expense.amount = Decimal("100.00")
            expenses.append(expense)
        
        # Test trend analysis
        result = await advanced_analytics_service._analyze_category_trend(
            "Food", expenses, 6
        )
        
        # Verify results
        assert isinstance(result, TrendForecast)
        assert result.category == "Food"
        assert result.current_trend == "insufficient_data"
        assert result.trend_strength == 0.0
        assert len(result.forecast_periods) == 0
        assert "Insufficient data" in result.key_insights[0]
    
    @pytest.mark.asyncio
    async def test_analyze_category_trend_increasing(
        self, 
        advanced_analytics_service
    ):
        """Test trend analysis with increasing trend."""
        
        # Create expenses with increasing trend
        expenses = []
        for i in range(12):  # 12 months of data
            expense = MagicMock()
            expense.date = date.today() - timedelta(days=30 * (11 - i))
            expense.amount = Decimal(f"{100 + i * 20}.00")  # Increasing trend
            expenses.append(expense)
        
        # Test trend analysis
        result = await advanced_analytics_service._analyze_category_trend(
            "Food", expenses, 6
        )
        
        # Verify results
        assert isinstance(result, TrendForecast)
        assert result.category == "Food"
        assert result.current_trend == "increasing"
        assert result.trend_strength > 0
        assert len(result.forecast_periods) == 6
        assert len(result.key_insights) > 0
        assert "increasing" in result.key_insights[0].lower()
    
    @pytest.mark.asyncio
    async def test_visualization_generation_methods(
        self, 
        advanced_analytics_service, 
        sample_expenses_with_anomaly
    ):
        """Test individual visualization generation methods."""
        
        # Test heatmap generation
        heatmap = await advanced_analytics_service._generate_spending_heatmap(
            sample_expenses_with_anomaly
        )
        assert heatmap.type == "heatmap"
        assert "Heatmap" in heatmap.title
        assert isinstance(heatmap.data, list)
        
        # Test treemap generation
        treemap = await advanced_analytics_service._generate_category_treemap(
            sample_expenses_with_anomaly
        )
        assert treemap.type == "treemap"
        assert "Treemap" in treemap.title
        assert isinstance(treemap.data, list)
        
        # Test line chart generation
        line_chart = await advanced_analytics_service._generate_trend_line_chart(
            sample_expenses_with_anomaly
        )
        assert line_chart.type == "line"
        assert "Trend" in line_chart.title
        assert isinstance(line_chart.data, list)
        
        # Test scatter plot generation
        scatter = await advanced_analytics_service._generate_merchant_scatter_plot(
            sample_expenses_with_anomaly
        )
        assert scatter.type == "scatter"
        assert "Merchant" in scatter.title
        assert isinstance(scatter.data, list)
        
        # Test seasonal pattern generation
        seasonal = await advanced_analytics_service._generate_seasonal_pattern_chart(
            sample_expenses_with_anomaly
        )
        assert seasonal.type == "bar"
        assert "Seasonal" in seasonal.title
        assert isinstance(seasonal.data, list)
        
        # Test distribution generation
        distribution = await advanced_analytics_service._generate_spending_distribution(
            sample_expenses_with_anomaly
        )
        assert distribution.type == "histogram"
        assert "Distribution" in distribution.title
        assert isinstance(distribution.data, list)