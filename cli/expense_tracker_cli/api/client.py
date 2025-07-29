"""
API client for communicating with the Expense Tracker backend.
"""
import json
from typing import Dict, List, Optional, Any, Union
from datetime import date, datetime
from decimal import Decimal
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import keyring

from ..config import Config
from ..utils.exceptions import APIError, AuthenticationError, NotFoundError
from ..utils.serialization import ExpenseTrackerJSONEncoder


class APIClient:
    """Client for interacting with the Expense Tracker API."""
    
    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.api.base_url
        self.timeout = config.api.timeout
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Setup authentication
        self._setup_auth()
    
    def _setup_auth(self):
        """Setup authentication headers."""
        if self.config.auth.method == "api_key":
            api_key = self.config.auth.api_key
            if not api_key:
                # Try to get from keyring
                api_key = keyring.get_password("expense-tracker-cli", "api_key")
            
            if api_key:
                self.session.headers.update({"Authorization": f"Bearer {api_key}"})
        
        elif self.config.auth.method == "basic":
            username = self.config.auth.username
            password = keyring.get_password("expense-tracker-cli", username) if username else None
            
            if username and password:
                self.session.auth = (username, password)
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        files: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request to the API."""
        url = f"{self.base_url}/api{endpoint}"
        
        try:
            # Serialize data with custom encoder
            json_data = None
            if data:
                json_data = json.dumps(data, cls=ExpenseTrackerJSONEncoder)
            
            response = self.session.request(
                method=method,
                url=url,
                data=json_data,
                params=params,
                files=files,
                headers={"Content-Type": "application/json"} if json_data else None,
                timeout=self.timeout,
                verify=self.config.api.verify_ssl
            )
            
            if response.status_code == 401:
                raise AuthenticationError("Authentication failed. Please check your credentials.")
            elif response.status_code == 404:
                raise NotFoundError("Resource not found.")
            elif response.status_code >= 400:
                try:
                    error_data = response.json()
                    error_message = error_data.get("detail", f"HTTP {response.status_code}")
                except:
                    error_message = f"HTTP {response.status_code}: {response.text}"
                raise APIError(error_message)
            
            return response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {e}")
    
    # Health and Status
    def get_health(self) -> Dict[str, Any]:
        """Get API health status."""
        return self._make_request("GET", "/health")
    
    # Expense Management
    def get_expenses(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        category: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get expenses with optional filtering."""
        params = {}
        if limit: params["limit"] = limit
        if offset: params["offset"] = offset
        if category: params["category"] = category
        if date_from: params["date_from"] = date_from.isoformat()
        if date_to: params["date_to"] = date_to.isoformat()
        if min_amount: params["min_amount"] = str(min_amount)
        if max_amount: params["max_amount"] = str(max_amount)
        if search: params["search"] = search
        
        return self._make_request("GET", "/expenses", params=params)
    
    def get_expense(self, expense_id: str) -> Dict[str, Any]:
        """Get a specific expense."""
        return self._make_request("GET", f"/expenses/{expense_id}")
    
    def create_expense(self, expense_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new expense."""
        return self._make_request("POST", "/expenses", data=expense_data)
    
    def update_expense(self, expense_id: str, expense_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an expense."""
        return self._make_request("PUT", f"/expenses/{expense_id}", data=expense_data)
    
    def delete_expense(self, expense_id: str) -> None:
        """Delete an expense."""
        self._make_request("DELETE", f"/expenses/{expense_id}")
    
    def search_expenses(self, query: str, **kwargs) -> Dict[str, Any]:
        """Search expenses."""
        params = {"q": query, **kwargs}
        return self._make_request("GET", "/expenses/search", params=params)
    
    # Category Management
    def get_categories(self) -> List[Dict[str, Any]]:
        """Get all categories."""
        return self._make_request("GET", "/categories")
    
    def create_category(self, category_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new category."""
        return self._make_request("POST", "/categories", data=category_data)
    
    def update_category(self, category_id: str, category_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a category."""
        return self._make_request("PUT", f"/categories/{category_id}", data=category_data)
    
    def delete_category(self, category_id: str) -> None:
        """Delete a category."""
        self._make_request("DELETE", f"/categories/{category_id}")
    
    # Budget Management
    def get_budgets(self) -> List[Dict[str, Any]]:
        """Get all budgets."""
        return self._make_request("GET", "/budgets")
    
    def get_budget(self, budget_id: str) -> Dict[str, Any]:
        """Get a specific budget."""
        return self._make_request("GET", f"/budgets/{budget_id}")
    
    def create_budget(self, budget_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new budget."""
        return self._make_request("POST", "/budgets", data=budget_data)
    
    def update_budget(self, budget_id: str, budget_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a budget."""
        return self._make_request("PUT", f"/budgets/{budget_id}", data=budget_data)
    
    def delete_budget(self, budget_id: str) -> None:
        """Delete a budget."""
        self._make_request("DELETE", f"/budgets/{budget_id}")
    
    def get_budget_alerts(self) -> List[Dict[str, Any]]:
        """Get budget alerts."""
        return self._make_request("GET", "/budgets/alerts")
    
    # Analytics
    def get_analytics_summary(
        self, 
        period: str = "monthly",
        months: Optional[int] = None,
        days: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get analytics summary."""
        params = {"period": period}
        if months: params["months"] = months
        if days: params["days"] = days
        return self._make_request("GET", "/analytics/summary", params=params)
    
    def get_analytics_trends(self, **kwargs) -> Dict[str, Any]:
        """Get spending trends."""
        return self._make_request("GET", "/analytics/trends", params=kwargs)
    
    def get_analytics_categories(self, **kwargs) -> Dict[str, Any]:
        """Get category breakdown."""
        return self._make_request("GET", "/analytics/categories", params=kwargs)
    
    def get_analytics_dashboard(self, period_days: int = 30) -> Dict[str, Any]:
        """Get dashboard analytics."""
        return self._make_request("GET", "/analytics/dashboard", params={"period_days": period_days})
    
    # Import/Export
    def import_statement(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """Import a bank statement."""
        with open(file_path, 'rb') as f:
            files = {"file": f}
            return self._make_request("POST", "/import/statement", files=files)
    
    def export_expenses(self, format: str = "csv", **kwargs) -> bytes:
        """Export expenses."""
        params = {"format": format, **kwargs}
        response = self.session.get(
            f"{self.base_url}/api/export/expenses",
            params=params,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.content
    
    def export_report(self, format: str = "pdf", **kwargs) -> bytes:
        """Export detailed report."""
        params = {"format": format, **kwargs}
        response = self.session.get(
            f"{self.base_url}/api/export/report",
            params=params,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.content
    
    # Recurring Expenses
    def get_recurring_expenses(self) -> List[Dict[str, Any]]:
        """Get all recurring expenses."""
        return self._make_request("GET", "/recurring-expenses")
    
    def create_recurring_expense(self, recurring_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new recurring expense."""
        return self._make_request("POST", "/recurring-expenses", data=recurring_data)
    
    def update_recurring_expense(self, recurring_id: str, recurring_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a recurring expense."""
        return self._make_request("PUT", f"/recurring-expenses/{recurring_id}", data=recurring_data)
    
    def delete_recurring_expense(self, recurring_id: str) -> None:
        """Delete a recurring expense."""
        self._make_request("DELETE", f"/recurring-expenses/{recurring_id}")
    
    def process_recurring_expenses(self) -> Dict[str, Any]:
        """Process due recurring expenses."""
        return self._make_request("POST", "/recurring-expenses/process-due")
    
    def get_recurring_notifications(self) -> List[Dict[str, Any]]:
        """Get recurring expense notifications."""
        return self._make_request("GET", "/recurring-expenses/notifications")
    
    # Payment Methods and Accounts
    def get_payment_methods(self) -> List[Dict[str, Any]]:
        """Get all payment methods."""
        return self._make_request("GET", "/payment-methods")
    
    def get_accounts(self) -> List[Dict[str, Any]]:
        """Get all accounts."""
        return self._make_request("GET", "/accounts")
    
    def create_payment_method(self, payment_method_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new payment method."""
        return self._make_request("POST", "/payment-methods", data=payment_method_data)
    
    def create_account(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new account."""
        return self._make_request("POST", "/accounts", data=account_data)