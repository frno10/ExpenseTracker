"""
Analytics API endpoints for expense data analysis and reporting.
"""
import logging
from datetime import date, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.security import rate_limit
from app.models.user import User
from app.services.analytics_service import analytics_service, TimeSeriesPoint, CategoryAnalysis, SpendingTrend, SpendingAnomaly

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# ===== REQUEST/RESPONSE MODELS =====

class TimeSeriesResponse(BaseModel):
    """Response model for time series data."""
    date: date
    amount: float
    count: int
    category: Optional[str] = None
    merchant: Optional[str] = None
    payment_method: Optional[str] = None
    
    class Config:
        from_attributes = True


class CategoryAnalysisResponse(BaseModel):
    """Response model for category analysis."""
    category_id: Optional[UUID]
    category_name: str
    total_amount: float
    transaction_count: int
    percentage_of_total: float
    average_transaction: float
    trend_direction: str
    trend_percentage: float
    
    class Config:
        from_attributes = True


class SpendingTrendResponse(BaseModel):
    """Response model for spending trends."""
    period: str
    current_amount: float
    previous_amount: float
    change_amount: float
    change_percentage: float
    trend_direction: str
    
    class Config:
        from_attributes = True


class SpendingAnomalyResponse(BaseModel):
    """Response model for spending anomalies."""
    date: date
    amount: float
    category: str
    merchant: str
    anomaly_type: str
    severity: str
    description: str
    
    class Config:
        from_attributes = True


class DashboardSummaryResponse(BaseModel):
    """Response model for dashboard summary."""
    period: Dict[str, Any]
    summary: Dict[str, Any]
    trend: Dict[str, Any]
    category_breakdown: List[Dict[str, Any]]
    merchant_breakdown: List[Dict[str, Any]]
    anomalies: List[SpendingAnomalyResponse]
    insights: List[str]


# ===== TIME SERIES ENDPOINTS =====

@router.get("/time-series", response_model=List[TimeSeriesResponse])
@rate_limit("analytics_read", per_minute=30)
async def get_spending_time_series(
    start_date: date = Query(..., description="Analysis start date"),
    end_date: date = Query(..., description="Analysis end date"),
    granularity: str = Query("daily", regex="^(daily|weekly|monthly)$", description="Time granularity"),
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    merchant_id: Optional[UUID] = Query(None, description="Filter by merchant"),
    payment_method_id: Optional[UUID] = Query(None, description="Filter by payment method"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get time series data for spending analysis.
    
    Returns spending data grouped by time periods (daily, weekly, or monthly)
    with optional filtering by category, merchant, or payment method.
    """
    logger.info(f"Getting time series data for user {current_user.id}")
    
    try:
        # Validate date range
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date"
            )
        
        # Limit analysis period to prevent performance issues
        max_days = 365
        if (end_date - start_date).days > max_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Analysis period cannot exceed {max_days} days"
            )
        
        time_series = await analytics_service.get_spending_time_series(
            db=db,
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
            category_id=category_id,
            merchant_id=merchant_id,
            payment_method_id=payment_method_id
        )
        
        # Convert to response format
        response_data = []
        for point in time_series:
            response_data.append(TimeSeriesResponse(
                date=point.date,
                amount=float(point.amount),
                count=point.count,
                category=point.category,
                merchant=point.merchant,
                payment_method=point.payment_method
            ))
        
        logger.info(f"Returned {len(response_data)} time series points")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting time series data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve time series data"
        )


@router.get("/category-trends", response_model=List[CategoryAnalysisResponse])
@rate_limit("analytics_read", per_minute=30)
async def get_category_spending_trends(
    start_date: date = Query(..., description="Analysis start date"),
    end_date: date = Query(..., description="Analysis end date"),
    limit: int = Query(20, ge=1, le=50, description="Maximum number of categories"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get spending trends by category.
    
    Returns category-wise spending analysis with trend information
    compared to the previous period.
    """
    logger.info(f"Getting category trends for user {current_user.id}")
    
    try:
        # Validate date range
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date"
            )
        
        category_analyses = await analytics_service.get_category_spending_trends(
            db=db,
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        # Convert to response format
        response_data = []
        for analysis in category_analyses:
            response_data.append(CategoryAnalysisResponse(
                category_id=analysis.category_id,
                category_name=analysis.category_name,
                total_amount=float(analysis.total_amount),
                transaction_count=analysis.transaction_count,
                percentage_of_total=analysis.percentage_of_total,
                average_transaction=float(analysis.average_transaction),
                trend_direction=analysis.trend_direction,
                trend_percentage=analysis.trend_percentage
            ))
        
        logger.info(f"Returned {len(response_data)} category analyses")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category trends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve category trends"
        )


# ===== COMPARATIVE ANALYSIS ENDPOINTS =====

@router.get("/period-comparison", response_model=SpendingTrendResponse)
@rate_limit("analytics_read", per_minute=30)
async def get_period_comparison(
    current_start: date = Query(..., description="Current period start date"),
    current_end: date = Query(..., description="Current period end date"),
    comparison_type: str = Query("previous_period", regex="^(previous_period|year_over_year)$", description="Comparison type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Compare spending between periods.
    
    Returns spending comparison between current period and either
    the previous period or the same period last year.
    """
    logger.info(f"Getting period comparison for user {current_user.id}")
    
    try:
        # Validate date range
        if current_start > current_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date"
            )
        
        trend = await analytics_service.get_period_comparison(
            db=db,
            user_id=current_user.id,
            current_start=current_start,
            current_end=current_end,
            comparison_type=comparison_type
        )
        
        response_data = SpendingTrendResponse(
            period=trend.period,
            current_amount=float(trend.current_amount),
            previous_amount=float(trend.previous_amount),
            change_amount=float(trend.change_amount),
            change_percentage=trend.change_percentage,
            trend_direction=trend.trend_direction
        )
        
        logger.info(f"Returned period comparison: {trend.trend_direction}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting period comparison: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve period comparison"
        )


@router.get("/monthly-comparison")
@rate_limit("analytics_read", per_minute=20)
async def get_monthly_comparison(
    months: int = Query(12, ge=1, le=24, description="Number of months to analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get month-over-month spending comparison.
    
    Returns monthly spending data for the specified number of months
    with category breakdowns and trend analysis.
    """
    logger.info(f"Getting monthly comparison for user {current_user.id}")
    
    try:
        monthly_data = await analytics_service.get_monthly_comparison(
            db=db,
            user_id=current_user.id,
            months=months
        )
        
        # Convert Decimal values to float for JSON serialization
        for month_data in monthly_data:
            month_data["total_amount"] = float(month_data["total_amount"])
            for category in month_data["category_breakdown"]:
                category["amount"] = float(category["amount"])
        
        logger.info(f"Returned {len(monthly_data)} months of data")
        return monthly_data
        
    except Exception as e:
        logger.error(f"Error getting monthly comparison: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve monthly comparison"
        )


# ===== ANOMALY DETECTION ENDPOINTS =====

@router.get("/anomalies", response_model=List[SpendingAnomalyResponse])
@rate_limit("analytics_read", per_minute=20)
async def detect_spending_anomalies(
    start_date: date = Query(..., description="Analysis start date"),
    end_date: date = Query(..., description="Analysis end date"),
    sensitivity: str = Query("medium", regex="^(low|medium|high)$", description="Detection sensitivity"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Detect unusual spending patterns.
    
    Returns detected spending anomalies based on historical patterns
    with configurable sensitivity levels.
    """
    logger.info(f"Detecting anomalies for user {current_user.id}")
    
    try:
        # Validate date range
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date"
            )
        
        anomalies = await analytics_service.detect_spending_anomalies(
            db=db,
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            sensitivity=sensitivity
        )
        
        # Convert to response format
        response_data = []
        for anomaly in anomalies:
            response_data.append(SpendingAnomalyResponse(
                date=anomaly.date,
                amount=float(anomaly.amount),
                category=anomaly.category,
                merchant=anomaly.merchant,
                anomaly_type=anomaly.anomaly_type,
                severity=anomaly.severity,
                description=anomaly.description
            ))
        
        logger.info(f"Detected {len(response_data)} anomalies")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to detect spending anomalies"
        )


# ===== DASHBOARD ENDPOINTS =====

@router.get("/dashboard", response_model=DashboardSummaryResponse)
@rate_limit("analytics_read", per_minute=60)
async def get_dashboard_summary(
    period_days: int = Query(30, ge=1, le=365, description="Analysis period in days"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive dashboard summary.
    
    Returns a complete dashboard summary including spending totals,
    trends, category breakdowns, top merchants, and insights.
    """
    logger.info(f"Getting dashboard summary for user {current_user.id}")
    
    try:
        dashboard_data = await analytics_service.get_dashboard_summary(
            db=db,
            user_id=current_user.id,
            period_days=period_days
        )
        
        # Convert Decimal values to float for JSON serialization
        dashboard_data["summary"]["total_spending"] = float(dashboard_data["summary"]["total_spending"])
        dashboard_data["summary"]["average_transaction"] = float(dashboard_data["summary"]["average_transaction"])
        dashboard_data["summary"]["daily_average"] = float(dashboard_data["summary"]["daily_average"])
        
        dashboard_data["trend"]["change_amount"] = float(dashboard_data["trend"]["change_amount"])
        
        for category in dashboard_data["category_breakdown"]:
            category["amount"] = float(category["amount"])
        
        for merchant in dashboard_data["merchant_breakdown"]:
            merchant["amount"] = float(merchant["amount"])
        
        # Convert anomalies to response format
        anomaly_responses = []
        for anomaly in dashboard_data["anomalies"]:
            anomaly_responses.append(SpendingAnomalyResponse(
                date=anomaly.date,
                amount=float(anomaly.amount),
                category=anomaly.category,
                merchant=anomaly.merchant,
                anomaly_type=anomaly.anomaly_type,
                severity=anomaly.severity,
                description=anomaly.description
            ))
        
        response_data = DashboardSummaryResponse(
            period=dashboard_data["period"],
            summary=dashboard_data["summary"],
            trend=dashboard_data["trend"],
            category_breakdown=dashboard_data["category_breakdown"],
            merchant_breakdown=dashboard_data["merchant_breakdown"],
            anomalies=anomaly_responses,
            insights=dashboard_data["insights"]
        )
        
        logger.info("Returned dashboard summary")
        return response_data
        
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard summary"
        )


# ===== INSIGHTS ENDPOINTS =====

@router.get("/insights")
@rate_limit("analytics_read", per_minute=30)
async def get_spending_insights(
    period_days: int = Query(30, ge=7, le=365, description="Analysis period in days"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get personalized spending insights.
    
    Returns AI-generated insights about spending patterns,
    trends, and recommendations for better financial management.
    """
    logger.info(f"Getting spending insights for user {current_user.id}")
    
    try:
        # Get dashboard data which includes insights
        dashboard_data = await analytics_service.get_dashboard_summary(
            db=db,
            user_id=current_user.id,
            period_days=period_days
        )
        
        # Get additional trend analysis
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)
        
        trend = await analytics_service.get_period_comparison(
            db=db,
            user_id=current_user.id,
            current_start=start_date,
            current_end=end_date,
            comparison_type="previous_period"
        )
        
        # Get category trends
        category_trends = await analytics_service.get_category_spending_trends(
            db=db,
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            limit=10
        )
        
        insights = {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": period_days
            },
            "general_insights": dashboard_data["insights"],
            "spending_trend": {
                "direction": trend.trend_direction,
                "change_percentage": trend.change_percentage,
                "recommendation": _get_trend_recommendation(trend)
            },
            "top_categories": [
                {
                    "category": cat.category_name,
                    "amount": float(cat.total_amount),
                    "trend": cat.trend_direction,
                    "recommendation": _get_category_recommendation(cat)
                }
                for cat in category_trends[:5]
            ],
            "anomalies_summary": {
                "count": len(dashboard_data["anomalies"]),
                "high_severity": len([a for a in dashboard_data["anomalies"] if a.severity == "high"]),
                "recommendation": _get_anomaly_recommendation(dashboard_data["anomalies"])
            }
        }
        
        logger.info("Returned spending insights")
        return insights
        
    except Exception as e:
        logger.error(f"Error getting spending insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve spending insights"
        )


# ===== HELPER FUNCTIONS =====

def _get_trend_recommendation(trend: SpendingTrend) -> str:
    """Generate recommendation based on spending trend."""
    if trend.trend_direction == "up" and trend.change_percentage > 20:
        return "Consider reviewing your recent expenses and identifying areas where you can reduce spending."
    elif trend.trend_direction == "down" and abs(trend.change_percentage) > 10:
        return "Great job reducing your spending! Keep up the good work."
    else:
        return "Your spending is relatively stable. Consider setting up budgets to maintain control."


def _get_category_recommendation(category: CategoryAnalysis) -> str:
    """Generate recommendation based on category analysis."""
    if category.trend_direction == "up" and category.trend_percentage > 30:
        return f"Spending in {category.category_name} has increased significantly. Consider setting a budget for this category."
    elif category.percentage_of_total > 40:
        return f"{category.category_name} represents a large portion of your spending. Look for optimization opportunities."
    else:
        return f"Spending in {category.category_name} appears normal."


def _get_anomaly_recommendation(anomalies: List[SpendingAnomaly]) -> str:
    """Generate recommendation based on detected anomalies."""
    if not anomalies:
        return "No unusual spending patterns detected. Your spending appears consistent."
    
    high_severity = len([a for a in anomalies if a.severity == "high"])
    if high_severity > 0:
        return f"Review {high_severity} high-value unusual transactions to ensure they are legitimate."
    else:
        return "Some minor spending anomalies detected. Review them when convenient."