"""
Advanced analytics service with anomaly detection, forecasting, and custom dashboards.
"""
import logging
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4
from dataclasses import dataclass, asdict
from collections import defaultdict
import statistics
import math

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.models.expense import ExpenseTable
from app.models.category import CategoryTable
from app.models.user import UserTable
from app.repositories.expense import expense_repository
from app.services.analytics_cache_service import analytics_cache_service

logger = logging.getLogger(__name__)


@dataclass
class AdvancedAnomaly:
    """Advanced anomaly detection result."""
    id: str
    expense_id: UUID
    date: date
    amount: Decimal
    category: str
    merchant: str
    anomaly_type: str  # 'statistical', 'behavioral', 'seasonal', 'contextual'
    severity: str  # 'low', 'medium', 'high', 'critical'
    confidence_score: float  # 0.0 to 1.0
    description: str
    contributing_factors: List[str]
    suggested_actions: List[str]
    historical_context: Dict[str, Any]


@dataclass
class TrendForecast:
    """Trend analysis and forecasting result."""
    category: str
    current_trend: str  # 'increasing', 'decreasing', 'stable', 'volatile'
    trend_strength: float  # 0.0 to 1.0
    seasonal_pattern: Dict[str, float]  # month/day -> multiplier
    forecast_periods: List[Dict[str, Any]]  # future predictions
    confidence_interval: Tuple[float, float]
    key_insights: List[str]


@dataclass
class CustomDashboard:
    """Custom dashboard configuration."""
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    layout: Dict[str, Any]  # Widget positions and configurations
    widgets: List[Dict[str, Any]]  # Widget definitions
    filters: Dict[str, Any]  # Default filters
    is_public: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class VisualizationData:
    """Data structure for various visualization types."""
    type: str  # 'line', 'bar', 'pie', 'heatmap', 'scatter', 'treemap'
    title: str
    data: List[Dict[str, Any]]
    config: Dict[str, Any]  # Chart-specific configuration
    insights: List[str]


class AdvancedAnalyticsService:
    """Service for advanced analytics features."""
    
    def __init__(self):
        self.expense_repo = expense_repository
        self.dashboards_cache = {}  # In-memory storage for custom dashboards   
 
    # ===== ADVANCED ANOMALY DETECTION =====
    
    async def detect_advanced_anomalies(
        self,
        db: AsyncSession,
        user_id: UUID,
        start_date: date,
        end_date: date,
        sensitivity: str = "medium",
        anomaly_types: Optional[List[str]] = None
    ) -> List[AdvancedAnomaly]:
        """
        Advanced anomaly detection with multiple algorithms.
        
        Args:
            db: Database session
            user_id: User ID
            start_date: Analysis start date
            end_date: Analysis end date
            sensitivity: Detection sensitivity
            anomaly_types: Types of anomalies to detect
            
        Returns:
            List of advanced anomalies
        """
        logger.info(f"Running advanced anomaly detection for user {user_id}")
        
        # Check cache first
        cache_key_params = {
            "start_date": start_date,
            "end_date": end_date,
            "sensitivity": sensitivity,
            "anomaly_types": anomaly_types or []
        }
        cached_result = analytics_cache_service.get_cached_result(
            "advanced_anomalies", user_id, **cache_key_params
        )
        if cached_result:
            return [AdvancedAnomaly(**anomaly) for anomaly in cached_result]
        
        # Get expenses for analysis
        expenses = await self._get_expenses_with_relationships(
            db, user_id, start_date, end_date
        )
        
        # Get historical data for baseline (6 months)
        historical_start = start_date - timedelta(days=180)
        historical_expenses = await self._get_expenses_with_relationships(
            db, user_id, historical_start, start_date - timedelta(days=1)
        )
        
        anomalies = []
        
        # Statistical anomalies (Z-score, IQR)
        if not anomaly_types or "statistical" in anomaly_types:
            anomalies.extend(await self._detect_statistical_anomalies(
                expenses, historical_expenses, sensitivity
            ))
        
        # Behavioral anomalies (pattern changes)
        if not anomaly_types or "behavioral" in anomaly_types:
            anomalies.extend(await self._detect_behavioral_anomalies(
                expenses, historical_expenses, sensitivity
            ))
        
        # Sort by severity and confidence
        anomalies.sort(key=lambda x: (
            {"critical": 4, "high": 3, "medium": 2, "low": 1}[x.severity],
            x.confidence_score
        ), reverse=True)
        
        # Cache the result
        anomaly_dicts = [asdict(anomaly) for anomaly in anomalies]
        analytics_cache_service.cache_result(
            "advanced_anomalies", user_id, anomaly_dicts, **cache_key_params
        )
        
        logger.info(f"Detected {len(anomalies)} advanced anomalies")
        return anomalies
    
    # ===== TREND ANALYSIS AND FORECASTING =====
    
    async def analyze_trends_and_forecast(
        self,
        db: AsyncSession,
        user_id: UUID,
        forecast_periods: int = 6,  # months
        categories: Optional[List[str]] = None
    ) -> List[TrendForecast]:
        """
        Analyze spending trends and generate forecasts.
        
        Args:
            db: Database session
            user_id: User ID
            forecast_periods: Number of periods to forecast
            categories: Specific categories to analyze
            
        Returns:
            List of trend forecasts
        """
        logger.info(f"Analyzing trends and forecasting for user {user_id}")
        
        # Check cache first
        cache_key_params = {
            "forecast_periods": forecast_periods,
            "categories": categories or []
        }
        cached_result = analytics_cache_service.get_cached_result(
            "trend_forecast", user_id, **cache_key_params
        )
        if cached_result:
            return [TrendForecast(**forecast) for forecast in cached_result]
        
        # Get 2 years of historical data for trend analysis
        end_date = date.today()
        start_date = end_date - timedelta(days=730)  # 2 years
        
        expenses = await self._get_expenses_with_relationships(
            db, user_id, start_date, end_date
        )
        
        # Group by category
        category_expenses = defaultdict(list)
        for expense in expenses:
            category_name = expense.category.name if expense.category else "Uncategorized"
            if not categories or category_name in categories:
                category_expenses[category_name].append(expense)
        
        forecasts = []
        for category_name, cat_expenses in category_expenses.items():
            if len(cat_expenses) < 12:  # Need at least 12 data points
                continue
            
            forecast = await self._analyze_category_trend(
                category_name, cat_expenses, forecast_periods
            )
            forecasts.append(forecast)
        
        # Cache the result
        forecast_dicts = [asdict(forecast) for forecast in forecasts]
        analytics_cache_service.cache_result(
            "trend_forecast", user_id, forecast_dicts, **cache_key_params
        )
        
        logger.info(f"Generated {len(forecasts)} trend forecasts")
        return forecasts 
   
    # ===== CUSTOM DASHBOARD BUILDER =====
    
    async def create_custom_dashboard(
        self,
        user_id: UUID,
        name: str,
        description: Optional[str] = None,
        layout: Optional[Dict[str, Any]] = None,
        widgets: Optional[List[Dict[str, Any]]] = None,
        filters: Optional[Dict[str, Any]] = None,
        is_public: bool = False
    ) -> CustomDashboard:
        """
        Create a custom dashboard configuration.
        
        Args:
            user_id: User ID
            name: Dashboard name
            description: Dashboard description
            layout: Widget layout configuration
            widgets: Widget definitions
            filters: Default filters
            is_public: Whether dashboard is publicly shareable
            
        Returns:
            Created custom dashboard
        """
        logger.info(f"Creating custom dashboard '{name}' for user {user_id}")
        
        dashboard = CustomDashboard(
            id=uuid4(),
            user_id=user_id,
            name=name,
            description=description,
            layout=layout or self._get_default_layout(),
            widgets=widgets or self._get_default_widgets(),
            filters=filters or {},
            is_public=is_public,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Store in cache (in production, this would be in database)
        self.dashboards_cache[str(dashboard.id)] = dashboard
        
        logger.info(f"Created custom dashboard {dashboard.id}")
        return dashboard
    
    async def get_user_dashboards(
        self,
        user_id: UUID,
        include_public: bool = False
    ) -> List[CustomDashboard]:
        """Get user's custom dashboards."""
        
        dashboards = []
        for dashboard in self.dashboards_cache.values():
            if dashboard.user_id == user_id or (include_public and dashboard.is_public):
                dashboards.append(dashboard)
        
        return sorted(dashboards, key=lambda x: x.updated_at, reverse=True)
    
    async def update_custom_dashboard(
        self,
        dashboard_id: UUID,
        user_id: UUID,
        updates: Dict[str, Any]
    ) -> Optional[CustomDashboard]:
        """Update a custom dashboard."""
        
        dashboard = self.dashboards_cache.get(str(dashboard_id))
        if not dashboard or dashboard.user_id != user_id:
            return None
        
        # Update fields
        for key, value in updates.items():
            if hasattr(dashboard, key):
                setattr(dashboard, key, value)
        
        dashboard.updated_at = datetime.utcnow()
        self.dashboards_cache[str(dashboard_id)] = dashboard
        
        return dashboard
    
    async def delete_custom_dashboard(
        self,
        dashboard_id: UUID,
        user_id: UUID
    ) -> bool:
        """Delete a custom dashboard."""
        
        dashboard = self.dashboards_cache.get(str(dashboard_id))
        if not dashboard or dashboard.user_id != user_id:
            return False
        
        del self.dashboards_cache[str(dashboard_id)]
        return True    

    # ===== MULTIPLE VISUALIZATION TYPES =====
    
    async def generate_visualizations(
        self,
        db: AsyncSession,
        user_id: UUID,
        visualization_types: List[str],
        start_date: date,
        end_date: date,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VisualizationData]:
        """
        Generate multiple types of visualizations.
        
        Args:
            db: Database session
            user_id: User ID
            visualization_types: Types of visualizations to generate
            start_date: Data start date
            end_date: Data end date
            filters: Additional filters
            
        Returns:
            List of visualization data
        """
        logger.info(f"Generating {len(visualization_types)} visualizations for user {user_id}")
        
        expenses = await self._get_expenses_with_relationships(
            db, user_id, start_date, end_date
        )
        
        visualizations = []
        
        for viz_type in visualization_types:
            if viz_type == "spending_heatmap":
                viz = await self._generate_spending_heatmap(expenses)
            elif viz_type == "category_treemap":
                viz = await self._generate_category_treemap(expenses)
            elif viz_type == "trend_line_chart":
                viz = await self._generate_trend_line_chart(expenses)
            elif viz_type == "merchant_scatter_plot":
                viz = await self._generate_merchant_scatter_plot(expenses)
            elif viz_type == "seasonal_pattern_chart":
                viz = await self._generate_seasonal_pattern_chart(expenses)
            elif viz_type == "spending_distribution":
                viz = await self._generate_spending_distribution(expenses)
            else:
                continue
            
            visualizations.append(viz)
        
        logger.info(f"Generated {len(visualizations)} visualizations")
        return visualizations
    
    # ===== ANALYTICS DATA EXPORT =====
    
    async def export_analytics_data(
        self,
        db: AsyncSession,
        user_id: UUID,
        export_type: str,  # 'csv', 'json', 'excel'
        data_types: List[str],  # 'expenses', 'categories', 'trends', 'anomalies'
        start_date: date,
        end_date: date,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Export analytics data in various formats.
        
        Args:
            db: Database session
            user_id: User ID
            export_type: Export format
            data_types: Types of data to export
            start_date: Data start date
            end_date: Data end date
            filters: Additional filters
            
        Returns:
            Export data and metadata
        """
        logger.info(f"Exporting analytics data for user {user_id}")
        
        export_data = {
            "metadata": {
                "user_id": str(user_id),
                "export_type": export_type,
                "data_types": data_types,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "generated_at": datetime.utcnow().isoformat(),
                "filters": filters or {}
            },
            "data": {}
        }
        
        # Export expenses
        if "expenses" in data_types:
            expenses = await self._get_expenses_with_relationships(
                db, user_id, start_date, end_date
            )
            export_data["data"]["expenses"] = await self._format_expenses_for_export(
                expenses, export_type
            )
        
        # Export category analysis
        if "categories" in data_types:
            from app.services.analytics_service import analytics_service
            category_analysis = await analytics_service.get_category_spending_trends(
                db, user_id, start_date, end_date, limit=50
            )
            export_data["data"]["categories"] = await self._format_categories_for_export(
                category_analysis, export_type
            )
        
        # Export trends
        if "trends" in data_types:
            trends = await self.analyze_trends_and_forecast(db, user_id, 6)
            export_data["data"]["trends"] = await self._format_trends_for_export(
                trends, export_type
            )
        
        # Export anomalies
        if "anomalies" in data_types:
            anomalies = await self.detect_advanced_anomalies(
                db, user_id, start_date, end_date
            )
            export_data["data"]["anomalies"] = await self._format_anomalies_for_export(
                anomalies, export_type
            )
        
        logger.info(f"Exported {len(export_data['data'])} data types")
        return export_data   
 
    # ===== PRIVATE HELPER METHODS =====
    
    async def _get_expenses_with_relationships(
        self,
        db: AsyncSession,
        user_id: UUID,
        start_date: date,
        end_date: date
    ) -> List[ExpenseTable]:
        """Get expenses with all relationships loaded."""
        
        query = db.query(ExpenseTable).filter(
            ExpenseTable.user_id == user_id,
            ExpenseTable.date >= start_date,
            ExpenseTable.date <= end_date
        ).options(
            selectinload(ExpenseTable.category),
            selectinload(ExpenseTable.merchant),
            selectinload(ExpenseTable.payment_method)
        )
        
        return await query.all()
    
    async def _detect_statistical_anomalies(
        self,
        expenses: List[ExpenseTable],
        historical_expenses: List[ExpenseTable],
        sensitivity: str
    ) -> List[AdvancedAnomaly]:
        """Detect statistical anomalies using Z-score and IQR methods."""
        
        if not historical_expenses:
            return []
        
        anomalies = []
        
        # Calculate historical statistics
        historical_amounts = [float(expense.amount) for expense in historical_expenses]
        mean_amount = statistics.mean(historical_amounts)
        std_amount = statistics.stdev(historical_amounts) if len(historical_amounts) > 1 else 0
        
        # Set thresholds based on sensitivity
        z_thresholds = {"low": 3.0, "medium": 2.5, "high": 2.0}
        z_threshold = z_thresholds.get(sensitivity, 2.5)
        
        for expense in expenses:
            amount = float(expense.amount)
            
            # Z-score anomaly detection
            if std_amount > 0:
                z_score = abs(amount - mean_amount) / std_amount
                if z_score > z_threshold:
                    confidence = min(z_score / 4.0, 1.0)  # Normalize to 0-1
                    severity = self._calculate_severity(z_score, [2.0, 2.5, 3.0, 4.0])
                    
                    anomalies.append(AdvancedAnomaly(
                        id=str(uuid4()),
                        expense_id=expense.id,
                        date=expense.date,
                        amount=expense.amount,
                        category=expense.category.name if expense.category else "Uncategorized",
                        merchant=expense.merchant.name if expense.merchant else "Unknown",
                        anomaly_type="statistical",
                        severity=severity,
                        confidence_score=confidence,
                        description=f"Amount ${amount:.2f} is {z_score:.1f} standard deviations from normal (avg: ${mean_amount:.2f})",
                        contributing_factors=[
                            f"Z-score: {z_score:.2f}",
                            f"Historical average: ${mean_amount:.2f}",
                            f"Standard deviation: ${std_amount:.2f}"
                        ],
                        suggested_actions=[
                            "Verify this transaction is legitimate",
                            "Check if this represents a one-time purchase",
                            "Consider if this indicates a spending pattern change"
                        ],
                        historical_context={
                            "mean_amount": mean_amount,
                            "std_amount": std_amount,
                            "z_score": z_score
                        }
                    ))
        
        return anomalies
    
    async def _detect_behavioral_anomalies(
        self,
        expenses: List[ExpenseTable],
        historical_expenses: List[ExpenseTable],
        sensitivity: str
    ) -> List[AdvancedAnomaly]:
        """Detect behavioral pattern anomalies."""
        
        anomalies = []
        
        # Analyze spending frequency patterns
        current_merchant_freq = defaultdict(int)
        historical_merchant_freq = defaultdict(int)
        
        for expense in expenses:
            merchant = expense.merchant.name if expense.merchant else "Unknown"
            current_merchant_freq[merchant] += 1
        
        for expense in historical_expenses:
            merchant = expense.merchant.name if expense.merchant else "Unknown"
            historical_merchant_freq[merchant] += 1
        
        # Detect unusual frequency changes
        for merchant, current_count in current_merchant_freq.items():
            historical_count = historical_merchant_freq.get(merchant, 0)
            
            if historical_count > 0:
                frequency_ratio = current_count / historical_count
                
                # Significant increase in frequency
                if frequency_ratio > 3.0:
                    # Find representative expense
                    merchant_expenses = [e for e in expenses if (e.merchant.name if e.merchant else "Unknown") == merchant]
                    representative_expense = merchant_expenses[0]
                    
                    confidence = min(frequency_ratio / 5.0, 1.0)
                    severity = self._calculate_severity(frequency_ratio, [2.0, 3.0, 4.0, 5.0])
                    
                    anomalies.append(AdvancedAnomaly(
                        id=str(uuid4()),
                        expense_id=representative_expense.id,
                        date=representative_expense.date,
                        amount=representative_expense.amount,
                        category=representative_expense.category.name if representative_expense.category else "Uncategorized",
                        merchant=merchant,
                        anomaly_type="behavioral",
                        severity=severity,
                        confidence_score=confidence,
                        description=f"Unusual increase in spending frequency at {merchant}: {current_count} transactions (normal: {historical_count})",
                        contributing_factors=[
                            f"Current frequency: {current_count} transactions",
                            f"Historical average: {historical_count} transactions",
                            f"Frequency ratio: {frequency_ratio:.1f}x"
                        ],
                        suggested_actions=[
                            f"Review recent transactions at {merchant}",
                            "Check if this represents a new spending habit",
                            "Consider setting up spending alerts for this merchant"
                        ],
                        historical_context={
                            "current_frequency": current_count,
                            "historical_frequency": historical_count,
                            "frequency_ratio": frequency_ratio
                        }
                    ))
        
        return anomalies
    
    def _calculate_severity(self, value: float, thresholds: List[float]) -> str:
        """Calculate severity based on value and thresholds."""
        if value >= thresholds[3]:
            return "critical"
        elif value >= thresholds[2]:
            return "high"
        elif value >= thresholds[1]:
            return "medium"
        else:
            return "low"    

    async def _analyze_category_trend(
        self,
        category_name: str,
        expenses: List[ExpenseTable],
        forecast_periods: int
    ) -> TrendForecast:
        """Analyze trend for a specific category."""
        
        # Group expenses by month
        monthly_spending = defaultdict(Decimal)
        for expense in expenses:
            month_key = expense.date.replace(day=1)
            monthly_spending[month_key] += expense.amount
        
        # Sort by date
        sorted_months = sorted(monthly_spending.keys())
        amounts = [float(monthly_spending[month]) for month in sorted_months]
        
        if len(amounts) < 6:  # Need at least 6 months
            return TrendForecast(
                category=category_name,
                current_trend="insufficient_data",
                trend_strength=0.0,
                seasonal_pattern={},
                forecast_periods=[],
                confidence_interval=(0.0, 0.0),
                key_insights=["Insufficient data for trend analysis"]
            )
        
        # Calculate trend using linear regression
        x_values = list(range(len(amounts)))
        n = len(amounts)
        sum_x = sum(x_values)
        sum_y = sum(amounts)
        sum_xy = sum(x * y for x, y in zip(x_values, amounts))
        sum_x2 = sum(x * x for x in x_values)
        
        # Linear regression slope
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n
        
        # Determine trend direction and strength
        avg_amount = statistics.mean(amounts)
        trend_strength = abs(slope) / avg_amount if avg_amount > 0 else 0
        
        if slope > avg_amount * 0.05:  # 5% increase per month
            current_trend = "increasing"
        elif slope < -avg_amount * 0.05:  # 5% decrease per month
            current_trend = "decreasing"
        elif trend_strength < 0.1:
            current_trend = "stable"
        else:
            current_trend = "volatile"
        
        # Calculate seasonal pattern
        seasonal_pattern = {}
        monthly_averages = defaultdict(list)
        for month, amount in zip(sorted_months, amounts):
            monthly_averages[month.month].append(amount)
        
        overall_avg = statistics.mean(amounts)
        for month in range(1, 13):
            if month in monthly_averages:
                month_avg = statistics.mean(monthly_averages[month])
                seasonal_pattern[str(month)] = month_avg / overall_avg if overall_avg > 0 else 1.0
            else:
                seasonal_pattern[str(month)] = 1.0
        
        # Generate forecasts
        forecast_periods_data = []
        for i in range(forecast_periods):
            future_x = len(amounts) + i
            base_forecast = slope * future_x + intercept
            
            # Apply seasonal adjustment
            future_date = sorted_months[-1] + timedelta(days=30 * (i + 1))
            seasonal_multiplier = seasonal_pattern.get(str(future_date.month), 1.0)
            adjusted_forecast = base_forecast * seasonal_multiplier
            
            forecast_periods_data.append({
                "period": i + 1,
                "date": future_date.isoformat(),
                "forecast_amount": max(0, adjusted_forecast),
                "seasonal_multiplier": seasonal_multiplier
            })
        
        # Calculate confidence interval (simplified)
        residuals = [amounts[i] - (slope * i + intercept) for i in range(len(amounts))]
        mse = sum(r * r for r in residuals) / len(residuals)
        std_error = math.sqrt(mse)
        confidence_interval = (max(0, avg_amount - 2 * std_error), avg_amount + 2 * std_error)
        
        # Generate insights
        key_insights = []
        if current_trend == "increasing":
            key_insights.append(f"Spending in {category_name} is increasing by ${slope:.2f} per month on average")
        elif current_trend == "decreasing":
            key_insights.append(f"Spending in {category_name} is decreasing by ${abs(slope):.2f} per month on average")
        
        if trend_strength > 0.3:
            key_insights.append(f"Strong trend detected (strength: {trend_strength:.2f})")
        
        return TrendForecast(
            category=category_name,
            current_trend=current_trend,
            trend_strength=min(trend_strength, 1.0),
            seasonal_pattern=seasonal_pattern,
            forecast_periods=forecast_periods_data,
            confidence_interval=confidence_interval,
            key_insights=key_insights
        )
    
    def _get_default_layout(self) -> Dict[str, Any]:
        """Get default dashboard layout."""
        return {
            "grid": {
                "columns": 12,
                "rows": 8,
                "gap": 16
            },
            "widgets": [
                {"id": "summary", "x": 0, "y": 0, "w": 12, "h": 2},
                {"id": "spending_chart", "x": 0, "y": 2, "w": 8, "h": 3},
                {"id": "category_breakdown", "x": 8, "y": 2, "w": 4, "h": 3},
                {"id": "recent_transactions", "x": 0, "y": 5, "w": 6, "h": 3},
                {"id": "budget_status", "x": 6, "y": 5, "w": 6, "h": 3}
            ]
        }
    
    def _get_default_widgets(self) -> List[Dict[str, Any]]:
        """Get default dashboard widgets."""
        return [
            {
                "id": "summary",
                "type": "summary_cards",
                "title": "Spending Summary",
                "config": {
                    "metrics": ["total_spending", "transaction_count", "average_transaction", "budget_usage"]
                }
            },
            {
                "id": "spending_chart",
                "type": "line_chart",
                "title": "Spending Trend",
                "config": {
                    "data_source": "time_series",
                    "granularity": "daily",
                    "period_days": 30
                }
            },
            {
                "id": "category_breakdown",
                "type": "pie_chart",
                "title": "Category Breakdown",
                "config": {
                    "data_source": "category_analysis",
                    "limit": 8
                }
            }
        ] 
   
    # Visualization generation methods
    async def _generate_spending_heatmap(self, expenses: List[ExpenseTable]) -> VisualizationData:
        """Generate spending heatmap by day of week and hour."""
        
        # Group by day of week and create heatmap data
        heatmap_data = defaultdict(lambda: defaultdict(float))
        
        for expense in expenses:
            day_of_week = expense.date.strftime("%A")
            # For simplicity, we'll use a random hour since we don't have time data
            hour = hash(str(expense.id)) % 24
            heatmap_data[day_of_week][hour] += float(expense.amount)
        
        # Convert to visualization format
        data = []
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for day in days:
            for hour in range(24):
                data.append({
                    "day": day,
                    "hour": hour,
                    "amount": heatmap_data[day][hour]
                })
        
        return VisualizationData(
            type="heatmap",
            title="Spending Heatmap by Day and Hour",
            data=data,
            config={
                "x_axis": "hour",
                "y_axis": "day",
                "value": "amount",
                "color_scale": "blues"
            },
            insights=[
                "Heatmap shows spending patterns by day of week and time",
                "Darker areas indicate higher spending periods"
            ]
        )
    
    async def _generate_category_treemap(self, expenses: List[ExpenseTable]) -> VisualizationData:
        """Generate category treemap visualization."""
        
        category_totals = defaultdict(float)
        for expense in expenses:
            category = expense.category.name if expense.category else "Uncategorized"
            category_totals[category] += float(expense.amount)
        
        data = [
            {
                "category": category,
                "amount": amount,
                "percentage": (amount / sum(category_totals.values())) * 100
            }
            for category, amount in category_totals.items()
        ]
        
        data.sort(key=lambda x: x["amount"], reverse=True)
        
        return VisualizationData(
            type="treemap",
            title="Spending by Category (Treemap)",
            data=data,
            config={
                "value_field": "amount",
                "label_field": "category",
                "color_scheme": "category20"
            },
            insights=[
                f"Top category: {data[0]['category']} (${data[0]['amount']:.2f})" if data else "No data",
                f"Total categories: {len(data)}"
            ]
        )
    
    async def _generate_trend_line_chart(self, expenses: List[ExpenseTable]) -> VisualizationData:
        """Generate trend line chart."""
        
        # Group by date
        daily_totals = defaultdict(float)
        for expense in expenses:
            daily_totals[expense.date] += float(expense.amount)
        
        data = [
            {
                "date": date_key.isoformat(),
                "amount": amount
            }
            for date_key, amount in sorted(daily_totals.items())
        ]
        
        return VisualizationData(
            type="line",
            title="Daily Spending Trend",
            data=data,
            config={
                "x_axis": "date",
                "y_axis": "amount",
                "line_color": "#3b82f6"
            },
            insights=[
                f"Total data points: {len(data)}",
                f"Average daily spending: ${statistics.mean([d['amount'] for d in data]):.2f}" if data else "No data"
            ]
        )
    
    async def _generate_merchant_scatter_plot(self, expenses: List[ExpenseTable]) -> VisualizationData:
        """Generate merchant scatter plot (frequency vs average amount)."""
        
        merchant_stats = defaultdict(lambda: {"total": 0, "count": 0})
        
        for expense in expenses:
            merchant = expense.merchant.name if expense.merchant else "Unknown"
            merchant_stats[merchant]["total"] += float(expense.amount)
            merchant_stats[merchant]["count"] += 1
        
        data = [
            {
                "merchant": merchant,
                "frequency": stats["count"],
                "average_amount": stats["total"] / stats["count"],
                "total_amount": stats["total"]
            }
            for merchant, stats in merchant_stats.items()
        ]
        
        return VisualizationData(
            type="scatter",
            title="Merchant Analysis (Frequency vs Average Amount)",
            data=data,
            config={
                "x_axis": "frequency",
                "y_axis": "average_amount",
                "size_field": "total_amount",
                "label_field": "merchant"
            },
            insights=[
                f"Total merchants: {len(data)}",
                "Bubble size represents total spending at merchant"
            ]
        )
    
    async def _generate_seasonal_pattern_chart(self, expenses: List[ExpenseTable]) -> VisualizationData:
        """Generate seasonal spending pattern chart."""
        
        monthly_totals = defaultdict(float)
        for expense in expenses:
            month_name = expense.date.strftime("%B")
            monthly_totals[month_name] += float(expense.amount)
        
        # Ensure all months are represented
        all_months = ["January", "February", "March", "April", "May", "June",
                     "July", "August", "September", "October", "November", "December"]
        
        data = [
            {
                "month": month,
                "amount": monthly_totals.get(month, 0)
            }
            for month in all_months
        ]
        
        return VisualizationData(
            type="bar",
            title="Seasonal Spending Pattern",
            data=data,
            config={
                "x_axis": "month",
                "y_axis": "amount",
                "bar_color": "#10b981"
            },
            insights=[
                "Shows spending patterns across months",
                f"Peak month: {max(data, key=lambda x: x['amount'])['month']}" if any(d['amount'] > 0 for d in data) else "No data"
            ]
        )
    
    async def _generate_spending_distribution(self, expenses: List[ExpenseTable]) -> VisualizationData:
        """Generate spending amount distribution histogram."""
        
        amounts = [float(expense.amount) for expense in expenses]
        
        if not amounts:
            return VisualizationData(
                type="histogram",
                title="Spending Amount Distribution",
                data=[],
                config={},
                insights=["No data available"]
            )
        
        # Create histogram bins
        min_amount = min(amounts)
        max_amount = max(amounts)
        bin_count = min(20, len(amounts))  # Max 20 bins
        bin_width = (max_amount - min_amount) / bin_count if bin_count > 0 else 1
        
        bins = defaultdict(int)
        for amount in amounts:
            bin_index = int((amount - min_amount) / bin_width) if bin_width > 0 else 0
            bin_index = min(bin_index, bin_count - 1)  # Ensure within bounds
            bins[bin_index] += 1
        
        data = [
            {
                "bin_start": min_amount + i * bin_width,
                "bin_end": min_amount + (i + 1) * bin_width,
                "count": bins[i],
                "bin_label": f"${min_amount + i * bin_width:.0f}-${min_amount + (i + 1) * bin_width:.0f}"
            }
            for i in range(bin_count)
        ]
        
        return VisualizationData(
            type="histogram",
            title="Spending Amount Distribution",
            data=data,
            config={
                "x_axis": "bin_label",
                "y_axis": "count",
                "bar_color": "#f59e0b"
            },
            insights=[
                f"Total transactions: {len(amounts)}",
                f"Average amount: ${statistics.mean(amounts):.2f}",
                f"Median amount: ${statistics.median(amounts):.2f}"
            ]
        )
    
    # Export formatting methods
    async def _format_expenses_for_export(self, expenses: List[ExpenseTable], export_type: str) -> List[Dict[str, Any]]:
        """Format expenses for export."""
        return [
            {
                "id": str(expense.id),
                "date": expense.date.isoformat(),
                "amount": float(expense.amount),
                "description": expense.description,
                "category": expense.category.name if expense.category else "Uncategorized",
                "merchant": expense.merchant.name if expense.merchant else "Unknown",
                "payment_method": expense.payment_method.name if expense.payment_method else "Unknown"
            }
            for expense in expenses
        ]
    
    async def _format_categories_for_export(self, categories: List[Any], export_type: str) -> List[Dict[str, Any]]:
        """Format category analysis for export."""
        return [
            {
                "category_name": cat.category_name,
                "total_amount": float(cat.total_amount),
                "transaction_count": cat.transaction_count,
                "percentage_of_total": cat.percentage_of_total,
                "average_transaction": float(cat.average_transaction),
                "trend_direction": cat.trend_direction,
                "trend_percentage": cat.trend_percentage
            }
            for cat in categories
        ]
    
    async def _format_trends_for_export(self, trends: List[TrendForecast], export_type: str) -> List[Dict[str, Any]]:
        """Format trends for export."""
        return [asdict(trend) for trend in trends]
    
    async def _format_anomalies_for_export(self, anomalies: List[AdvancedAnomaly], export_type: str) -> List[Dict[str, Any]]:
        """Format anomalies for export."""
        return [asdict(anomaly) for anomaly in anomalies]


# Create service instance
advanced_analytics_service = AdvancedAnalyticsService()