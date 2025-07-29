"""
Advanced analytics API endpoints for anomaly detection, forecasting, and custom dashboards.
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
from app.services.advanced_analytics_service import (
    advanced_analytics_service, 
    AdvancedAnomaly, 
    TrendForecast, 
    CustomDashboard, 
    VisualizationData
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/advanced-analytics", tags=["advanced-analytics"])


# ===== REQUEST/RESPONSE MODELS =====

class AdvancedAnomalyResponse(BaseModel):
    """Response model for advanced anomalies."""
    id: str
    expense_id: UUID
    date: date
    amount: float
    category: str
    merchant: str
    anomaly_type: str
    severity: str
    confidence_score: float
    description: str
    contributing_factors: List[str]
    suggested_actions: List[str]
    historical_context: Dict[str, Any]
    
    class Config:
        from_attributes = True


class TrendForecastResponse(BaseModel):
    """Response model for trend forecasts."""
    category: str
    current_trend: str
    trend_strength: float
    seasonal_pattern: Dict[str, float]
    forecast_periods: List[Dict[str, Any]]
    confidence_interval: List[float]  # Tuple converted to list for JSON
    key_insights: List[str]
    
    class Config:
        from_attributes = True


class CustomDashboardResponse(BaseModel):
    """Response model for custom dashboards."""
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    layout: Dict[str, Any]
    widgets: List[Dict[str, Any]]
    filters: Dict[str, Any]
    is_public: bool
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class CustomDashboardCreate(BaseModel):
    """Request model for creating custom dashboards."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    layout: Optional[Dict[str, Any]] = None
    widgets: Optional[List[Dict[str, Any]]] = None
    filters: Optional[Dict[str, Any]] = None
    is_public: bool = False


class CustomDashboardUpdate(BaseModel):
    """Request model for updating custom dashboards."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    layout: Optional[Dict[str, Any]] = None
    widgets: Optional[List[Dict[str, Any]]] = None
    filters: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None


class VisualizationResponse(BaseModel):
    """Response model for visualizations."""
    type: str
    title: str
    data: List[Dict[str, Any]]
    config: Dict[str, Any]
    insights: List[str]
    
    class Config:
        from_attributes = True


class ExportRequest(BaseModel):
    """Request model for data export."""
    export_type: str = Field(..., regex="^(csv|json|excel)$")
    data_types: List[str] = Field(..., min_items=1)
    start_date: date
    end_date: date
    filters: Optional[Dict[str, Any]] = None


# ===== ADVANCED ANOMALY DETECTION ENDPOINTS =====

@router.get("/anomalies", response_model=List[AdvancedAnomalyResponse])
@rate_limit("advanced_analytics_read", per_minute=20)
async def detect_advanced_anomalies(
    start_date: date = Query(..., description="Analysis start date"),
    end_date: date = Query(..., description="Analysis end date"),
    sensitivity: str = Query("medium", regex="^(low|medium|high)$", description="Detection sensitivity"),
    anomaly_types: Optional[List[str]] = Query(None, description="Types of anomalies to detect"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Detect advanced spending anomalies using multiple algorithms.
    
    Returns sophisticated anomaly detection results with confidence scores,
    contributing factors, and suggested actions.
    """
    logger.info(f"Detecting advanced anomalies for user {current_user.id}")
    
    try:
        # Validate date range
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date"
            )
        
        # Limit analysis period
        max_days = 180
        if (end_date - start_date).days > max_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Analysis period cannot exceed {max_days} days"
            )
        
        anomalies = await advanced_analytics_service.detect_advanced_anomalies(
            db=db,
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            sensitivity=sensitivity,
            anomaly_types=anomaly_types
        )
        
        # Convert to response format
        response_data = []
        for anomaly in anomalies:
            response_data.append(AdvancedAnomalyResponse(
                id=anomaly.id,
                expense_id=anomaly.expense_id,
                date=anomaly.date,
                amount=float(anomaly.amount),
                category=anomaly.category,
                merchant=anomaly.merchant,
                anomaly_type=anomaly.anomaly_type,
                severity=anomaly.severity,
                confidence_score=anomaly.confidence_score,
                description=anomaly.description,
                contributing_factors=anomaly.contributing_factors,
                suggested_actions=anomaly.suggested_actions,
                historical_context=anomaly.historical_context
            ))
        
        logger.info(f"Detected {len(response_data)} advanced anomalies")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting advanced anomalies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to detect advanced anomalies"
        )


# ===== TREND ANALYSIS AND FORECASTING ENDPOINTS =====

@router.get("/trends-forecast", response_model=List[TrendForecastResponse])
@rate_limit("advanced_analytics_read", per_minute=15)
async def analyze_trends_and_forecast(
    forecast_periods: int = Query(6, ge=1, le=24, description="Number of periods to forecast"),
    categories: Optional[List[str]] = Query(None, description="Specific categories to analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze spending trends and generate forecasts.
    
    Returns trend analysis with seasonal patterns and future predictions
    for spending categories.
    """
    logger.info(f"Analyzing trends and forecasting for user {current_user.id}")
    
    try:
        forecasts = await advanced_analytics_service.analyze_trends_and_forecast(
            db=db,
            user_id=current_user.id,
            forecast_periods=forecast_periods,
            categories=categories
        )
        
        # Convert to response format
        response_data = []
        for forecast in forecasts:
            response_data.append(TrendForecastResponse(
                category=forecast.category,
                current_trend=forecast.current_trend,
                trend_strength=forecast.trend_strength,
                seasonal_pattern=forecast.seasonal_pattern,
                forecast_periods=forecast.forecast_periods,
                confidence_interval=list(forecast.confidence_interval),
                key_insights=forecast.key_insights
            ))
        
        logger.info(f"Generated {len(response_data)} trend forecasts")
        return response_data
        
    except Exception as e:
        logger.error(f"Error analyzing trends and forecasting: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze trends and generate forecasts"
        )


# ===== CUSTOM DASHBOARD ENDPOINTS =====

@router.post("/dashboards", response_model=CustomDashboardResponse, status_code=status.HTTP_201_CREATED)
@rate_limit("advanced_analytics_write", per_minute=10)
async def create_custom_dashboard(
    dashboard_data: CustomDashboardCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a custom analytics dashboard.
    
    Allows users to create personalized dashboard configurations
    with custom layouts, widgets, and filters.
    """
    logger.info(f"Creating custom dashboard for user {current_user.id}")
    
    try:
        dashboard = await advanced_analytics_service.create_custom_dashboard(
            user_id=current_user.id,
            name=dashboard_data.name,
            description=dashboard_data.description,
            layout=dashboard_data.layout,
            widgets=dashboard_data.widgets,
            filters=dashboard_data.filters,
            is_public=dashboard_data.is_public
        )
        
        response_data = CustomDashboardResponse(
            id=dashboard.id,
            user_id=dashboard.user_id,
            name=dashboard.name,
            description=dashboard.description,
            layout=dashboard.layout,
            widgets=dashboard.widgets,
            filters=dashboard.filters,
            is_public=dashboard.is_public,
            created_at=dashboard.created_at.isoformat(),
            updated_at=dashboard.updated_at.isoformat()
        )
        
        logger.info(f"Created custom dashboard {dashboard.id}")
        return response_data
        
    except Exception as e:
        logger.error(f"Error creating custom dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create custom dashboard"
        )


@router.get("/dashboards", response_model=List[CustomDashboardResponse])
@rate_limit("advanced_analytics_read", per_minute=30)
async def get_user_dashboards(
    include_public: bool = Query(False, description="Include public dashboards"),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's custom dashboards.
    
    Returns all dashboards created by the user, optionally including
    public dashboards from other users.
    """
    logger.info(f"Getting dashboards for user {current_user.id}")
    
    try:
        dashboards = await advanced_analytics_service.get_user_dashboards(
            user_id=current_user.id,
            include_public=include_public
        )
        
        response_data = []
        for dashboard in dashboards:
            response_data.append(CustomDashboardResponse(
                id=dashboard.id,
                user_id=dashboard.user_id,
                name=dashboard.name,
                description=dashboard.description,
                layout=dashboard.layout,
                widgets=dashboard.widgets,
                filters=dashboard.filters,
                is_public=dashboard.is_public,
                created_at=dashboard.created_at.isoformat(),
                updated_at=dashboard.updated_at.isoformat()
            ))
        
        logger.info(f"Retrieved {len(response_data)} dashboards")
        return response_data
        
    except Exception as e:
        logger.error(f"Error getting user dashboards: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboards"
        )


@router.put("/dashboards/{dashboard_id}", response_model=CustomDashboardResponse)
@rate_limit("advanced_analytics_write", per_minute=20)
async def update_custom_dashboard(
    dashboard_id: UUID,
    dashboard_data: CustomDashboardUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update a custom dashboard.
    
    Allows users to modify their dashboard configurations,
    including layout, widgets, and settings.
    """
    logger.info(f"Updating dashboard {dashboard_id} for user {current_user.id}")
    
    try:
        dashboard = await advanced_analytics_service.update_custom_dashboard(
            dashboard_id=dashboard_id,
            user_id=current_user.id,
            updates=dashboard_data.dict(exclude_unset=True)
        )
        
        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found"
            )
        
        response_data = CustomDashboardResponse(
            id=dashboard.id,
            user_id=dashboard.user_id,
            name=dashboard.name,
            description=dashboard.description,
            layout=dashboard.layout,
            widgets=dashboard.widgets,
            filters=dashboard.filters,
            is_public=dashboard.is_public,
            created_at=dashboard.created_at.isoformat(),
            updated_at=dashboard.updated_at.isoformat()
        )
        
        logger.info(f"Updated dashboard {dashboard_id}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update dashboard"
        )


@router.delete("/dashboards/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit("advanced_analytics_write", per_minute=10)
async def delete_custom_dashboard(
    dashboard_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a custom dashboard.
    
    Permanently removes a dashboard configuration.
    Only the dashboard owner can delete it.
    """
    logger.info(f"Deleting dashboard {dashboard_id} for user {current_user.id}")
    
    try:
        success = await advanced_analytics_service.delete_custom_dashboard(
            dashboard_id=dashboard_id,
            user_id=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found"
            )
        
        logger.info(f"Deleted dashboard {dashboard_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete dashboard"
        )


# ===== VISUALIZATION ENDPOINTS =====

@router.get("/visualizations", response_model=List[VisualizationResponse])
@rate_limit("advanced_analytics_read", per_minute=20)
async def generate_visualizations(
    visualization_types: List[str] = Query(..., description="Types of visualizations to generate"),
    start_date: date = Query(..., description="Data start date"),
    end_date: date = Query(..., description="Data end date"),
    filters: Optional[Dict[str, Any]] = Query(None, description="Additional filters"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate multiple types of visualizations.
    
    Creates various chart types including heatmaps, treemaps, scatter plots,
    and other advanced visualization formats.
    """
    logger.info(f"Generating visualizations for user {current_user.id}")
    
    try:
        # Validate date range
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date"
            )
        
        # Validate visualization types
        valid_types = [
            "spending_heatmap", "category_treemap", "trend_line_chart",
            "merchant_scatter_plot", "seasonal_pattern_chart", "spending_distribution"
        ]
        
        invalid_types = [vt for vt in visualization_types if vt not in valid_types]
        if invalid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid visualization types: {invalid_types}"
            )
        
        visualizations = await advanced_analytics_service.generate_visualizations(
            db=db,
            user_id=current_user.id,
            visualization_types=visualization_types,
            start_date=start_date,
            end_date=end_date,
            filters=filters
        )
        
        response_data = []
        for viz in visualizations:
            response_data.append(VisualizationResponse(
                type=viz.type,
                title=viz.title,
                data=viz.data,
                config=viz.config,
                insights=viz.insights
            ))
        
        logger.info(f"Generated {len(response_data)} visualizations")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating visualizations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate visualizations"
        )


# ===== DATA EXPORT ENDPOINTS =====

@router.post("/export")
@rate_limit("advanced_analytics_export", per_minute=5)
async def export_analytics_data(
    export_request: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export analytics data in various formats.
    
    Allows users to export comprehensive analytics data including
    expenses, trends, anomalies, and category analysis.
    """
    logger.info(f"Exporting analytics data for user {current_user.id}")
    
    try:
        # Validate date range
        if export_request.start_date > export_request.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date"
            )
        
        # Validate data types
        valid_data_types = ["expenses", "categories", "trends", "anomalies"]
        invalid_types = [dt for dt in export_request.data_types if dt not in valid_data_types]
        if invalid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid data types: {invalid_types}"
            )
        
        export_data = await advanced_analytics_service.export_analytics_data(
            db=db,
            user_id=current_user.id,
            export_type=export_request.export_type,
            data_types=export_request.data_types,
            start_date=export_request.start_date,
            end_date=export_request.end_date,
            filters=export_request.filters
        )
        
        logger.info(f"Exported analytics data for user {current_user.id}")
        return export_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting analytics data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export analytics data"
        )