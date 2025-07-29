"""
Analytics service for expense data analysis and reporting.
"""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, and_, or_, extract, desc, asc
from sqlalchemy.orm import selectinload

from app.models.expense import ExpenseTable
from app.models.category import CategoryTable
from app.models.merchant import MerchantTable
from app.models.payment_method import PaymentMethodTable
from app.repositories.expense import expense_repository
from app.services.analytics_cache_service import analytics_cache_service

logger = logging.getLogger(__name__)


@dataclass
class TimeSeriesPoint:
    """Single point in time series data."""
    date: date
    amount: Decimal
    count: int
    category: Optional[str] = None
    merchant: Optional[str] = None
    payment_method: Optional[str] = None


@dataclass
class CategoryAnalysis:
    """Category spending analysis."""
    category_id: UUID
    category_name: str
    total_amount: Decimal
    transaction_count: int
    percentage_of_total: float
    average_transaction: Decimal
    trend_direction: str  # 'up', 'down', 'stable'
    trend_percentage: float


@dataclass
class SpendingTrend:
    """Spending trend analysis."""
    period: str
    current_amount: Decimal
    previous_amount: Decimal
    change_amount: Decimal
    change_percentage: float
    trend_direction: str


@dataclass
class SpendingAnomaly:
    """Detected spending anomaly."""
    date: date
    amount: Decimal
    category: str
    merchant: str
    anomaly_type: str  # 'high_amount', 'unusual_category', 'frequency_spike'
    severity: str  # 'low', 'medium', 'high'
    description: str


class AnalyticsService:
    """Service for expense analytics and reporting."""
    
    def __init__(self):
        self.expense_repo = expense_repository
    
    # ===== TIME SERIES ANALYSIS =====
    
    async def get_spending_time_series(
        self,
        db: AsyncSession,
        user_id: UUID,
        start_date: date,
        end_date: date,
        granularity: str = "daily",  # daily, weekly, monthly
        category_id: Optional[UUID] = None,
        merchant_id: Optional[UUID] = None,
        payment_method_id: Optional[UUID] = None
    ) -> List[TimeSeriesPoint]:
        """
        Get time series data for spending analysis.
        
        Args:
            db: Database session
            user_id: User ID
            start_date: Analysis start date
            end_date: Analysis end date
            granularity: Time granularity (daily, weekly, monthly)
            category_id: Optional category filter
            merchant_id: Optional merchant filter
            payment_method_id: Optional payment method filter
            
        Returns:
            List of time series points
        """
        logger.info(f"Generating {granularity} time series for user {user_id}")
        
        # Build base query
        query = db.query(ExpenseTable).filter(
            ExpenseTable.user_id == user_id,
            ExpenseTable.date >= start_date,
            ExpenseTable.date <= end_date
        )
        
        # Apply filters
        if category_id:
            query = query.filter(ExpenseTable.category_id == category_id)
        if merchant_id:
            query = query.filter(ExpenseTable.merchant_id == merchant_id)
        if payment_method_id:
            query = query.filter(ExpenseTable.payment_method_id == payment_method_id)
        
        # Load relationships for analysis
        query = query.options(
            selectinload(ExpenseTable.category),
            selectinload(ExpenseTable.merchant),
            selectinload(ExpenseTable.payment_method)
        )
        
        expenses = await query.all()
        
        # Group by time period
        time_series = self._group_expenses_by_time(expenses, granularity, start_date, end_date)
        
        logger.info(f"Generated {len(time_series)} time series points")
        return time_series
    
    async def get_category_spending_trends(
        self,
        db: AsyncSession,
        user_id: UUID,
        start_date: date,
        end_date: date,
        limit: int = 20
    ) -> List[CategoryAnalysis]:
        """
        Get spending trends by category.
        
        Args:
            db: Database session
            user_id: User ID
            start_date: Analysis start date
            end_date: Analysis end date
            limit: Maximum number of categories to return
            
        Returns:
            List of category analyses
        """
        logger.info(f"Analyzing category spending trends for user {user_id}")
        
        # Get current period expenses
        current_expenses = await self._get_expenses_with_categories(
            db, user_id, start_date, end_date
        )
        
        # Get previous period for comparison
        period_length = (end_date - start_date).days
        prev_start = start_date - timedelta(days=period_length)
        prev_end = start_date - timedelta(days=1)
        
        previous_expenses = await self._get_expenses_with_categories(
            db, user_id, prev_start, prev_end
        )
        
        # Analyze categories
        category_analyses = self._analyze_categories(
            current_expenses, previous_expenses, limit
        )
        
        logger.info(f"Analyzed {len(category_analyses)} categories")
        return category_analyses
    
    # ===== COMPARATIVE ANALYSIS =====
    
    async def get_period_comparison(
        self,
        db: AsyncSession,
        user_id: UUID,
        current_start: date,
        current_end: date,
        comparison_type: str = "previous_period"  # previous_period, year_over_year
    ) -> SpendingTrend:
        """
        Compare spending between periods.
        
        Args:
            db: Database session
            user_id: User ID
            current_start: Current period start
            current_end: Current period end
            comparison_type: Type of comparison
            
        Returns:
            Spending trend analysis
        """
        logger.info(f"Comparing periods for user {user_id}: {comparison_type}")
        
        # Get current period spending
        current_total = await self._get_period_total(
            db, user_id, current_start, current_end
        )
        
        # Calculate comparison period
        if comparison_type == "year_over_year":
            prev_start = current_start.replace(year=current_start.year - 1)
            prev_end = current_end.replace(year=current_end.year - 1)
        else:  # previous_period
            period_length = (current_end - current_start).days
            prev_start = current_start - timedelta(days=period_length + 1)
            prev_end = current_start - timedelta(days=1)
        
        # Get previous period spending
        previous_total = await self._get_period_total(
            db, user_id, prev_start, prev_end
        )
        
        # Calculate trend
        change_amount = current_total - previous_total
        change_percentage = (
            (change_amount / previous_total * 100) 
            if previous_total > 0 else 0
        )
        
        trend_direction = (
            "up" if change_amount > 0 else
            "down" if change_amount < 0 else
            "stable"
        )
        
        return SpendingTrend(
            period=comparison_type,
            current_amount=current_total,
            previous_amount=previous_total,
            change_amount=change_amount,
            change_percentage=change_percentage,
            trend_direction=trend_direction
        )
    
    async def get_monthly_comparison(
        self,
        db: AsyncSession,
        user_id: UUID,
        months: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Get month-over-month spending comparison.
        
        Args:
            db: Database session
            user_id: User ID
            months: Number of months to analyze
            
        Returns:
            List of monthly spending data
        """
        logger.info(f"Analyzing {months} months of spending for user {user_id}")
        
        monthly_data = []
        current_date = date.today().replace(day=1)  # First day of current month
        
        for i in range(months):
            # Calculate month boundaries
            month_start = current_date.replace(day=1)
            if current_date.month == 12:
                month_end = date(current_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(current_date.year, current_date.month + 1, 1) - timedelta(days=1)
            
            # Get month spending
            month_total = await self._get_period_total(
                db, user_id, month_start, month_end
            )
            
            # Get category breakdown
            month_expenses = await self._get_expenses_with_categories(
                db, user_id, month_start, month_end
            )
            
            category_breakdown = self._get_category_breakdown(month_expenses)
            
            monthly_data.append({
                "year": current_date.year,
                "month": current_date.month,
                "month_name": current_date.strftime("%B"),
                "start_date": month_start,
                "end_date": month_end,
                "total_amount": month_total,
                "category_breakdown": category_breakdown,
                "transaction_count": len(month_expenses)
            })
            
            # Move to previous month
            if current_date.month == 1:
                current_date = current_date.replace(year=current_date.year - 1, month=12)
            else:
                current_date = current_date.replace(month=current_date.month - 1)
        
        logger.info(f"Generated {len(monthly_data)} months of data")
        return monthly_data
    
    # ===== ANOMALY DETECTION =====
    
    async def detect_spending_anomalies(
        self,
        db: AsyncSession,
        user_id: UUID,
        start_date: date,
        end_date: date,
        sensitivity: str = "medium"  # low, medium, high
    ) -> List[SpendingAnomaly]:
        """
        Detect unusual spending patterns.
        
        Args:
            db: Database session
            user_id: User ID
            start_date: Analysis start date
            end_date: Analysis end date
            sensitivity: Detection sensitivity
            
        Returns:
            List of detected anomalies
        """
        logger.info(f"Detecting spending anomalies for user {user_id}")
        
        # Get expenses for analysis
        expenses = await self._get_expenses_with_categories(
            db, user_id, start_date, end_date
        )
        
        # Get historical data for baseline
        historical_start = start_date - timedelta(days=90)  # 3 months history
        historical_expenses = await self._get_expenses_with_categories(
            db, user_id, historical_start, start_date - timedelta(days=1)
        )
        
        anomalies = []
        
        # Detect high amount anomalies
        anomalies.extend(self._detect_amount_anomalies(
            expenses, historical_expenses, sensitivity
        ))
        
        # Detect unusual category spending
        anomalies.extend(self._detect_category_anomalies(
            expenses, historical_expenses, sensitivity
        ))
        
        # Detect frequency anomalies
        anomalies.extend(self._detect_frequency_anomalies(
            expenses, historical_expenses, sensitivity
        ))
        
        logger.info(f"Detected {len(anomalies)} spending anomalies")
        return anomalies
    
    # ===== DASHBOARD ANALYTICS =====
    
    async def get_dashboard_summary(
        self,
        db: AsyncSession,
        user_id: UUID,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive dashboard summary.
        
        Args:
            db: Database session
            user_id: User ID
            period_days: Analysis period in days
            
        Returns:
            Dashboard summary data
        """
        logger.info(f"Generating dashboard summary for user {user_id}")
        
        # Check cache first
        cache_key_params = {"period_days": period_days}
        cached_result = analytics_cache_service.get_cached_result(
            "dashboard", user_id, **cache_key_params
        )
        if cached_result:
            return cached_result
        
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)
        
        # Get basic metrics
        current_expenses = await self._get_expenses_with_categories(
            db, user_id, start_date, end_date
        )
        
        total_spending = sum(expense.amount for expense in current_expenses)
        transaction_count = len(current_expenses)
        average_transaction = total_spending / transaction_count if transaction_count > 0 else Decimal('0.00')
        
        # Get category breakdown
        category_breakdown = self._get_category_breakdown(current_expenses)
        
        # Get top merchants
        merchant_breakdown = self._get_merchant_breakdown(current_expenses)
        
        # Get spending trend
        trend = await self.get_period_comparison(
            db, user_id, start_date, end_date, "previous_period"
        )
        
        # Get recent anomalies
        anomalies = await self.detect_spending_anomalies(
            db, user_id, start_date, end_date, "medium"
        )
        
        result = {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": period_days
            },
            "summary": {
                "total_spending": total_spending,
                "transaction_count": transaction_count,
                "average_transaction": average_transaction,
                "daily_average": total_spending / period_days if period_days > 0 else Decimal('0.00')
            },
            "trend": {
                "direction": trend.trend_direction,
                "change_amount": trend.change_amount,
                "change_percentage": trend.change_percentage
            },
            "category_breakdown": category_breakdown[:10],  # Top 10 categories
            "merchant_breakdown": merchant_breakdown[:10],  # Top 10 merchants
            "anomalies": anomalies[:5],  # Top 5 anomalies
            "insights": self._generate_insights(current_expenses, trend, anomalies)
        }
        
        # Cache the result
        analytics_cache_service.cache_result(
            "dashboard", user_id, result, **cache_key_params
        )
        
        return result
    
    # ===== PRIVATE HELPER METHODS =====
    
    def _group_expenses_by_time(
        self,
        expenses: List[ExpenseTable],
        granularity: str,
        start_date: date,
        end_date: date
    ) -> List[TimeSeriesPoint]:
        """Group expenses by time period."""
        
        # Create time buckets
        time_buckets = defaultdict(lambda: {"amount": Decimal('0.00'), "count": 0})
        
        for expense in expenses:
            # Determine time bucket key
            if granularity == "daily":
                key = expense.date
            elif granularity == "weekly":
                # Start of week (Monday)
                days_since_monday = expense.date.weekday()
                key = expense.date - timedelta(days=days_since_monday)
            elif granularity == "monthly":
                key = expense.date.replace(day=1)
            else:
                key = expense.date
            
            time_buckets[key]["amount"] += expense.amount
            time_buckets[key]["count"] += 1
        
        # Convert to time series points
        time_series = []
        current_date = start_date
        
        while current_date <= end_date:
            # Determine bucket key for current date
            if granularity == "daily":
                key = current_date
                next_date = current_date + timedelta(days=1)
            elif granularity == "weekly":
                days_since_monday = current_date.weekday()
                key = current_date - timedelta(days=days_since_monday)
                next_date = current_date + timedelta(days=7)
            elif granularity == "monthly":
                key = current_date.replace(day=1)
                if current_date.month == 12:
                    next_date = date(current_date.year + 1, 1, 1)
                else:
                    next_date = date(current_date.year, current_date.month + 1, 1)
            else:
                key = current_date
                next_date = current_date + timedelta(days=1)
            
            bucket_data = time_buckets.get(key, {"amount": Decimal('0.00'), "count": 0})
            
            time_series.append(TimeSeriesPoint(
                date=key,
                amount=bucket_data["amount"],
                count=bucket_data["count"]
            ))
            
            current_date = next_date
        
        return time_series
    
    async def _get_expenses_with_categories(
        self,
        db: AsyncSession,
        user_id: UUID,
        start_date: date,
        end_date: date
    ) -> List[ExpenseTable]:
        """Get expenses with category relationships loaded."""
        
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
    
    async def _get_period_total(
        self,
        db: AsyncSession,
        user_id: UUID,
        start_date: date,
        end_date: date
    ) -> Decimal:
        """Get total spending for a period."""
        
        result = await db.query(func.sum(ExpenseTable.amount)).filter(
            ExpenseTable.user_id == user_id,
            ExpenseTable.date >= start_date,
            ExpenseTable.date <= end_date
        ).scalar()
        
        return result or Decimal('0.00')
    
    def _analyze_categories(
        self,
        current_expenses: List[ExpenseTable],
        previous_expenses: List[ExpenseTable],
        limit: int
    ) -> List[CategoryAnalysis]:
        """Analyze category spending patterns."""
        
        # Group current expenses by category
        current_categories = defaultdict(lambda: {"amount": Decimal('0.00'), "count": 0})
        for expense in current_expenses:
            category_name = expense.category.name if expense.category else "Uncategorized"
            category_id = expense.category.id if expense.category else None
            
            current_categories[category_name]["amount"] += expense.amount
            current_categories[category_name]["count"] += 1
            current_categories[category_name]["id"] = category_id
        
        # Group previous expenses by category
        previous_categories = defaultdict(lambda: {"amount": Decimal('0.00'), "count": 0})
        for expense in previous_expenses:
            category_name = expense.category.name if expense.category else "Uncategorized"
            previous_categories[category_name]["amount"] += expense.amount
            previous_categories[category_name]["count"] += 1
        
        # Calculate total for percentages
        total_current = sum(data["amount"] for data in current_categories.values())
        
        # Create category analyses
        analyses = []
        for category_name, current_data in current_categories.items():
            previous_data = previous_categories.get(category_name, {"amount": Decimal('0.00'), "count": 0})
            
            # Calculate trend
            if previous_data["amount"] > 0:
                change_percentage = float((current_data["amount"] - previous_data["amount"]) / previous_data["amount"] * 100)
                if change_percentage > 10:
                    trend_direction = "up"
                elif change_percentage < -10:
                    trend_direction = "down"
                else:
                    trend_direction = "stable"
            else:
                change_percentage = 100.0 if current_data["amount"] > 0 else 0.0
                trend_direction = "up" if current_data["amount"] > 0 else "stable"
            
            analyses.append(CategoryAnalysis(
                category_id=current_data["id"],
                category_name=category_name,
                total_amount=current_data["amount"],
                transaction_count=current_data["count"],
                percentage_of_total=float(current_data["amount"] / total_current * 100) if total_current > 0 else 0.0,
                average_transaction=current_data["amount"] / current_data["count"] if current_data["count"] > 0 else Decimal('0.00'),
                trend_direction=trend_direction,
                trend_percentage=change_percentage
            ))
        
        # Sort by amount and limit
        analyses.sort(key=lambda x: x.total_amount, reverse=True)
        return analyses[:limit]
    
    def _get_category_breakdown(self, expenses: List[ExpenseTable]) -> List[Dict[str, Any]]:
        """Get category breakdown from expenses."""
        
        categories = defaultdict(lambda: {"amount": Decimal('0.00'), "count": 0})
        
        for expense in expenses:
            category_name = expense.category.name if expense.category else "Uncategorized"
            categories[category_name]["amount"] += expense.amount
            categories[category_name]["count"] += 1
        
        # Convert to list and sort
        breakdown = []
        total_amount = sum(data["amount"] for data in categories.values())
        
        for category_name, data in categories.items():
            breakdown.append({
                "category": category_name,
                "amount": data["amount"],
                "count": data["count"],
                "percentage": float(data["amount"] / total_amount * 100) if total_amount > 0 else 0.0
            })
        
        breakdown.sort(key=lambda x: x["amount"], reverse=True)
        return breakdown
    
    def _get_merchant_breakdown(self, expenses: List[ExpenseTable]) -> List[Dict[str, Any]]:
        """Get merchant breakdown from expenses."""
        
        merchants = defaultdict(lambda: {"amount": Decimal('0.00'), "count": 0})
        
        for expense in expenses:
            merchant_name = expense.merchant.name if expense.merchant else "Unknown"
            merchants[merchant_name]["amount"] += expense.amount
            merchants[merchant_name]["count"] += 1
        
        # Convert to list and sort
        breakdown = []
        for merchant_name, data in merchants.items():
            breakdown.append({
                "merchant": merchant_name,
                "amount": data["amount"],
                "count": data["count"]
            })
        
        breakdown.sort(key=lambda x: x["amount"], reverse=True)
        return breakdown
    
    def _detect_amount_anomalies(
        self,
        expenses: List[ExpenseTable],
        historical_expenses: List[ExpenseTable],
        sensitivity: str
    ) -> List[SpendingAnomaly]:
        """Detect unusually high amounts."""
        
        if not historical_expenses:
            return []
        
        # Calculate historical statistics
        historical_amounts = [float(expense.amount) for expense in historical_expenses]
        avg_amount = sum(historical_amounts) / len(historical_amounts)
        
        # Calculate standard deviation
        variance = sum((x - avg_amount) ** 2 for x in historical_amounts) / len(historical_amounts)
        std_dev = variance ** 0.5
        
        # Set threshold based on sensitivity
        thresholds = {
            "low": 3.0,
            "medium": 2.5,
            "high": 2.0
        }
        threshold = thresholds.get(sensitivity, 2.5)
        
        anomalies = []
        for expense in expenses:
            amount = float(expense.amount)
            if amount > avg_amount + (threshold * std_dev):
                severity = "high" if amount > avg_amount + (3 * std_dev) else "medium"
                
                anomalies.append(SpendingAnomaly(
                    date=expense.date,
                    amount=expense.amount,
                    category=expense.category.name if expense.category else "Uncategorized",
                    merchant=expense.merchant.name if expense.merchant else "Unknown",
                    anomaly_type="high_amount",
                    severity=severity,
                    description=f"Unusually high amount: ${amount:.2f} (avg: ${avg_amount:.2f})"
                ))
        
        return anomalies
    
    def _detect_category_anomalies(
        self,
        expenses: List[ExpenseTable],
        historical_expenses: List[ExpenseTable],
        sensitivity: str
    ) -> List[SpendingAnomaly]:
        """Detect unusual category spending."""
        
        # This is a simplified implementation
        # In a real system, you'd analyze category patterns more thoroughly
        anomalies = []
        
        # Group by category
        current_categories = defaultdict(Decimal)
        historical_categories = defaultdict(Decimal)
        
        for expense in expenses:
            category = expense.category.name if expense.category else "Uncategorized"
            current_categories[category] += expense.amount
        
        for expense in historical_expenses:
            category = expense.category.name if expense.category else "Uncategorized"
            historical_categories[category] += expense.amount
        
        # Find categories with unusual spending
        for category, current_amount in current_categories.items():
            historical_amount = historical_categories.get(category, Decimal('0.00'))
            
            if historical_amount > 0:
                change_ratio = float(current_amount / historical_amount)
                if change_ratio > 3.0:  # 300% increase
                    # Find the largest expense in this category
                    category_expenses = [e for e in expenses if (e.category.name if e.category else "Uncategorized") == category]
                    largest_expense = max(category_expenses, key=lambda x: x.amount)
                    
                    anomalies.append(SpendingAnomaly(
                        date=largest_expense.date,
                        amount=largest_expense.amount,
                        category=category,
                        merchant=largest_expense.merchant.name if largest_expense.merchant else "Unknown",
                        anomaly_type="unusual_category",
                        severity="medium",
                        description=f"Unusual spending in {category}: {change_ratio:.1f}x normal amount"
                    ))
        
        return anomalies
    
    def _detect_frequency_anomalies(
        self,
        expenses: List[ExpenseTable],
        historical_expenses: List[ExpenseTable],
        sensitivity: str
    ) -> List[SpendingAnomaly]:
        """Detect unusual spending frequency."""
        
        # This is a simplified implementation
        # In a real system, you'd analyze frequency patterns more thoroughly
        anomalies = []
        
        # Group by merchant
        current_merchants = defaultdict(int)
        historical_merchants = defaultdict(int)
        
        for expense in expenses:
            merchant = expense.merchant.name if expense.merchant else "Unknown"
            current_merchants[merchant] += 1
        
        for expense in historical_expenses:
            merchant = expense.merchant.name if expense.merchant else "Unknown"
            historical_merchants[merchant] += 1
        
        # Find merchants with unusual frequency
        for merchant, current_count in current_merchants.items():
            historical_count = historical_merchants.get(merchant, 0)
            
            if historical_count > 0:
                frequency_ratio = current_count / historical_count
                if frequency_ratio > 2.0:  # 200% increase in frequency
                    # Find a representative expense
                    merchant_expenses = [e for e in expenses if (e.merchant.name if e.merchant else "Unknown") == merchant]
                    representative_expense = merchant_expenses[0]  # Just take the first one
                    
                    anomalies.append(SpendingAnomaly(
                        date=representative_expense.date,
                        amount=representative_expense.amount,
                        category=representative_expense.category.name if representative_expense.category else "Uncategorized",
                        merchant=merchant,
                        anomaly_type="frequency_spike",
                        severity="low",
                        description=f"Unusual frequency at {merchant}: {current_count} transactions (normal: {historical_count})"
                    ))
        
        return anomalies
    
    def _generate_insights(
        self,
        expenses: List[ExpenseTable],
        trend: SpendingTrend,
        anomalies: List[SpendingAnomaly]
    ) -> List[str]:
        """Generate spending insights."""
        
        insights = []
        
        # Trend insights
        if trend.trend_direction == "up" and trend.change_percentage > 20:
            insights.append(f"Your spending increased by {trend.change_percentage:.1f}% compared to the previous period")
        elif trend.trend_direction == "down" and abs(trend.change_percentage) > 20:
            insights.append(f"Great job! Your spending decreased by {abs(trend.change_percentage):.1f}% compared to the previous period")
        
        # Category insights
        category_breakdown = self._get_category_breakdown(expenses)
        if category_breakdown:
            top_category = category_breakdown[0]
            insights.append(f"Your top spending category is {top_category['category']} at {top_category['percentage']:.1f}% of total spending")
        
        # Anomaly insights
        if anomalies:
            high_severity_anomalies = [a for a in anomalies if a.severity == "high"]
            if high_severity_anomalies:
                insights.append(f"Detected {len(high_severity_anomalies)} high-value unusual transactions that may need review")
        
        # Transaction insights
        if expenses:
            avg_transaction = sum(expense.amount for expense in expenses) / len(expenses)
            insights.append(f"Your average transaction amount is ${avg_transaction:.2f}")
        
        return insights


# Create service instance
analytics_service = AnalyticsService()