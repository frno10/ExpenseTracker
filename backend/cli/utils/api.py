"""
API client utilities for CLI commands.
"""
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
import json


class APIClient:
    """Base API client for making HTTP requests."""
    
    def __init__(self, config: Dict[str, Any]):
        self.base_url = config.get('api_url', 'http://localhost:8000')
        self.auth_token = config.get('auth_token')
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        return headers
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an HTTP request to the API."""
        url = urljoin(self.base_url, endpoint)
        headers = self._get_headers()
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.request(
                method, url, headers=headers, **kwargs
            ) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    raise Exception(f"API request failed ({response.status}): {error_text}")
                
                return await response.json()
    
    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GET request."""
        return await self._request('GET', endpoint, params=params)
    
    async def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a POST request."""
        return await self._request('POST', endpoint, json=data)
    
    async def put(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a PUT request."""
        return await self._request('PUT', endpoint, json=data)
    
    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make a DELETE request."""
        return await self._request('DELETE', endpoint)


class ExpenseAPI(APIClient):
    """API client for expense operations."""
    
    async def create_expense(self, expense_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new expense."""
        return await self.post('/api/expenses', expense_data)
    
    async def get_expenses(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get expenses with optional filtering."""
        response = await self.get('/api/expenses', params=filters)
        return response.get('expenses', [])
    
    async def get_expense(self, expense_id: str) -> Dict[str, Any]:
        """Get a specific expense by ID."""
        return await self.get(f'/api/expenses/{expense_id}')
    
    async def update_expense(self, expense_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing expense."""
        return await self.put(f'/api/expenses/{expense_id}', update_data)
    
    async def delete_expense(self, expense_id: str) -> Dict[str, Any]:
        """Delete an expense."""
        return await self.delete(f'/api/expenses/{expense_id}')
    
    async def get_expense_summary(self, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Get expense summary statistics."""
        return await self.get('/api/expenses/summary', params=filters)


class BudgetAPI(APIClient):
    """API client for budget operations."""
    
    async def create_budget(self, budget_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new budget."""
        return await self.post('/api/budgets', budget_data)
    
    async def get_budgets(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get budgets with optional filtering."""
        response = await self.get('/api/budgets', params=filters)
        return response if isinstance(response, list) else response.get('budgets', [])
    
    async def get_budget(self, budget_id: str) -> Dict[str, Any]:
        """Get a specific budget by ID."""
        return await self.get(f'/api/budgets/{budget_id}')
    
    async def update_budget(self, budget_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing budget."""
        return await self.put(f'/api/budgets/{budget_id}', update_data)
    
    async def delete_budget(self, budget_id: str) -> Dict[str, Any]:
        """Delete a budget."""
        return await self.delete(f'/api/budgets/{budget_id}')
    
    async def get_budget_status(self, budget_id: str) -> Dict[str, Any]:
        """Get budget status and usage."""
        return await self.get(f'/api/budgets/{budget_id}/status')


class ImportAPI(APIClient):
    """API client for import operations."""
    
    async def upload_statement(self, file_path: str, file_type: Optional[str] = None) -> Dict[str, Any]:
        """Upload a statement file for processing."""
        # Note: This would need to be implemented with multipart/form-data
        # For now, return a placeholder
        return {"message": "File upload not yet implemented in CLI"}
    
    async def get_import_status(self, import_id: str) -> Dict[str, Any]:
        """Get the status of an import operation."""
        return await self.get(f'/api/imports/{import_id}/status')
    
    async def get_import_preview(self, import_id: str) -> Dict[str, Any]:
        """Get preview of parsed transactions."""
        return await self.get(f'/api/imports/{import_id}/preview')
    
    async def confirm_import(self, import_id: str, confirmed_transactions: List[str]) -> Dict[str, Any]:
        """Confirm and finalize import."""
        return await self.post(f'/api/imports/{import_id}/confirm', {
            'transaction_ids': confirmed_transactions
        })


class AnalyticsAPI(APIClient):
    """API client for analytics operations."""
    
    async def get_dashboard_stats(self, period_days: int = 30) -> Dict[str, Any]:
        """Get dashboard statistics."""
        return await self.get('/api/analytics/dashboard-stats', params={'period_days': period_days})
    
    async def get_category_breakdown(self, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Get spending breakdown by category."""
        return await self.get('/api/analytics/category-breakdown', params=filters)
    
    async def get_spending_trends(self, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Get spending trends over time."""
        return await self.get('/api/analytics/spending-trends', params=filters)
    
    async def get_anomalies(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get spending anomalies."""
        response = await self.get('/api/analytics/anomalies', params=filters)
        return response.get('anomalies', [])


class ReportsAPI(APIClient):
    """API client for report operations."""
    
    async def generate_report(self, report_type: str, filters: Optional[Dict] = None, 
                            format: str = 'json') -> Dict[str, Any]:
        """Generate a report."""
        params = {'format': format}
        if filters:
            params.update(filters)
        
        return await self.get(f'/api/reports/{report_type}', params=params)
    
    async def export_data(self, export_type: str, filters: Optional[Dict] = None,
                         format: str = 'csv') -> bytes:
        """Export data in specified format."""
        # This would need special handling for binary data
        params = {'format': format}
        if filters:
            params.update(filters)
        
        # Placeholder implementation
        return b"Export data would be here"