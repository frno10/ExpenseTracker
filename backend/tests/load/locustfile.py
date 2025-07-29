"""Load testing configuration using Locust."""
import json
import random
from datetime import date, timedelta
from uuid import uuid4

from locust import HttpUser, task, between


class ExpenseTrackerUser(HttpUser):
    """Simulated user for load testing expense tracker API."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Set up user session."""
        self.auth_headers = {}
        self.user_id = None
        self.categories = []
        self.expenses = []
        
        # Authenticate user
        self.login()
        
        # Create some initial data
        self.create_test_categories()
    
    def login(self):
        """Authenticate user and get access token."""
        # In a real scenario, you would implement actual authentication
        # For load testing, we'll simulate with a mock token
        self.user_id = str(uuid4())
        self.auth_headers = {
            "Authorization": f"Bearer mock_token_{self.user_id}",
            "Content-Type": "application/json"
        }
    
    def create_test_categories(self):
        """Create test categories for the user."""
        category_names = ["Food", "Transportation", "Entertainment", "Shopping", "Utilities"]
        
        for name in category_names:
            category_data = {
                "name": name,
                "color": f"#{random.randint(0, 0xFFFFFF):06x}"
            }
            
            response = self.client.post(
                "/api/v1/categories/",
                json=category_data,
                headers=self.auth_headers,
                name="Create Category"
            )
            
            if response.status_code == 201:
                self.categories.append(response.json())
    
    @task(5)
    def create_expense(self):
        """Create a new expense (most common operation)."""
        if not self.categories:
            return
        
        category = random.choice(self.categories)
        expense_data = {
            "amount": round(random.uniform(5.0, 200.0), 2),
            "description": f"Load test expense {random.randint(1, 1000)}",
            "category_id": category["id"],
            "date": (date.today() - timedelta(days=random.randint(0, 30))).isoformat(),
            "payment_method": random.choice(["Credit Card", "Cash", "Debit Card"]),
            "notes": f"Generated for load testing - {random.randint(1, 100)}"
        }
        
        response = self.client.post(
            "/api/v1/expenses/",
            json=expense_data,
            headers=self.auth_headers,
            name="Create Expense"
        )
        
        if response.status_code == 201:
            self.expenses.append(response.json())
    
    @task(3)
    def list_expenses(self):
        """List user expenses with pagination."""
        params = {
            "page": random.randint(1, 5),
            "size": random.choice([10, 20, 50])
        }
        
        # Sometimes add filters
        if random.random() < 0.3:
            params.update({
                "min_amount": random.uniform(10.0, 50.0),
                "max_amount": random.uniform(100.0, 500.0)
            })
        
        if random.random() < 0.2:
            params.update({
                "date_from": (date.today() - timedelta(days=30)).isoformat(),
                "date_to": date.today().isoformat()
            })
        
        self.client.get(
            "/api/v1/expenses/",
            params=params,
            headers=self.auth_headers,
            name="List Expenses"
        )
    
    @task(2)
    def get_expense_by_id(self):
        """Get a specific expense by ID."""
        if not self.expenses:
            return
        
        expense = random.choice(self.expenses)
        self.client.get(
            f"/api/v1/expenses/{expense['id']}",
            headers=self.auth_headers,
            name="Get Expense by ID"
        )
    
    @task(2)
    def update_expense(self):
        """Update an existing expense."""
        if not self.expenses:
            return
        
        expense = random.choice(self.expenses)
        update_data = {
            "amount": round(random.uniform(5.0, 200.0), 2),
            "description": f"Updated load test expense {random.randint(1, 1000)}",
            "notes": f"Updated for load testing - {random.randint(1, 100)}"
        }
        
        response = self.client.put(
            f"/api/v1/expenses/{expense['id']}",
            json=update_data,
            headers=self.auth_headers,
            name="Update Expense"
        )
        
        if response.status_code == 200:
            # Update local copy
            expense.update(update_data)
    
    @task(1)
    def delete_expense(self):
        """Delete an expense."""
        if not self.expenses:
            return
        
        expense = random.choice(self.expenses)
        response = self.client.delete(
            f"/api/v1/expenses/{expense['id']}",
            headers=self.auth_headers,
            name="Delete Expense"
        )
        
        if response.status_code == 204:
            self.expenses.remove(expense)
    
    @task(2)
    def search_expenses(self):
        """Search expenses."""
        search_terms = ["coffee", "lunch", "gas", "grocery", "restaurant", "shopping"]
        query = random.choice(search_terms)
        
        self.client.get(
            "/api/v1/expenses/search",
            params={"q": query},
            headers=self.auth_headers,
            name="Search Expenses"
        )
    
    @task(1)
    def get_expense_statistics(self):
        """Get expense statistics."""
        params = {
            "date_from": (date.today() - timedelta(days=random.choice([7, 30, 90]))).isoformat(),
            "date_to": date.today().isoformat()
        }
        
        self.client.get(
            "/api/v1/expenses/statistics",
            params=params,
            headers=self.auth_headers,
            name="Get Statistics"
        )
    
    @task(1)
    def get_expense_trends(self):
        """Get expense trends."""
        params = {
            "period": random.choice(["daily", "weekly", "monthly"]),
            "date_from": (date.today() - timedelta(days=30)).isoformat(),
            "date_to": date.today().isoformat()
        }
        
        self.client.get(
            "/api/v1/expenses/trends",
            params=params,
            headers=self.auth_headers,
            name="Get Trends"
        )
    
    @task(1)
    def bulk_create_expenses(self):
        """Create multiple expenses at once."""
        if not self.categories:
            return
        
        num_expenses = random.randint(2, 10)
        expenses_data = []
        
        for _ in range(num_expenses):
            category = random.choice(self.categories)
            expenses_data.append({
                "amount": round(random.uniform(5.0, 100.0), 2),
                "description": f"Bulk expense {random.randint(1, 1000)}",
                "category_id": category["id"],
                "date": (date.today() - timedelta(days=random.randint(0, 7))).isoformat(),
                "payment_method": random.choice(["Credit Card", "Cash", "Debit Card"])
            })
        
        response = self.client.post(
            "/api/v1/expenses/bulk",
            json={"expenses": expenses_data},
            headers=self.auth_headers,
            name="Bulk Create Expenses"
        )
        
        if response.status_code == 201:
            result = response.json()
            self.expenses.extend(result.get("created_expenses", []))
    
    @task(1)
    def export_expenses(self):
        """Export expenses in different formats."""
        format_type = random.choice(["csv", "json", "xlsx"])
        params = {
            "format": format_type,
            "date_from": (date.today() - timedelta(days=30)).isoformat(),
            "date_to": date.today().isoformat()
        }
        
        self.client.get(
            "/api/v1/expenses/export",
            params=params,
            headers=self.auth_headers,
            name=f"Export {format_type.upper()}"
        )


class BudgetUser(HttpUser):
    """Simulated user focusing on budget operations."""
    
    wait_time = between(2, 5)
    
    def on_start(self):
        """Set up budget user session."""
        self.auth_headers = {}
        self.user_id = None
        self.budgets = []
        
        self.login()
        self.create_test_budgets()
    
    def login(self):
        """Authenticate user."""
        self.user_id = str(uuid4())
        self.auth_headers = {
            "Authorization": f"Bearer mock_token_{self.user_id}",
            "Content-Type": "application/json"
        }
    
    def create_test_budgets(self):
        """Create test budgets."""
        budget_names = ["Monthly Food", "Transportation", "Entertainment", "Shopping"]
        
        for name in budget_names:
            budget_data = {
                "name": name,
                "total_limit": round(random.uniform(200.0, 1000.0), 2),
                "period": "monthly",
                "start_date": date.today().replace(day=1).isoformat(),
                "end_date": date.today().replace(day=28).isoformat(),
                "alert_threshold": random.uniform(0.7, 0.9)
            }
            
            response = self.client.post(
                "/api/v1/budgets/",
                json=budget_data,
                headers=self.auth_headers,
                name="Create Budget"
            )
            
            if response.status_code == 201:
                self.budgets.append(response.json())
    
    @task(3)
    def list_budgets(self):
        """List user budgets."""
        self.client.get(
            "/api/v1/budgets/",
            headers=self.auth_headers,
            name="List Budgets"
        )
    
    @task(2)
    def get_budget_usage(self):
        """Get budget usage information."""
        if not self.budgets:
            return
        
        budget = random.choice(self.budgets)
        self.client.get(
            f"/api/v1/budgets/{budget['id']}/usage",
            headers=self.auth_headers,
            name="Get Budget Usage"
        )
    
    @task(1)
    def get_budget_alerts(self):
        """Get budget alerts."""
        self.client.get(
            "/api/v1/budgets/alerts",
            headers=self.auth_headers,
            name="Get Budget Alerts"
        )
    
    @task(1)
    def update_budget(self):
        """Update a budget."""
        if not self.budgets:
            return
        
        budget = random.choice(self.budgets)
        update_data = {
            "total_limit": round(random.uniform(300.0, 1200.0), 2),
            "alert_threshold": random.uniform(0.6, 0.95)
        }
        
        response = self.client.put(
            f"/api/v1/budgets/{budget['id']}",
            json=update_data,
            headers=self.auth_headers,
            name="Update Budget"
        )
        
        if response.status_code == 200:
            budget.update(update_data)


class AdminUser(HttpUser):
    """Simulated admin user for administrative operations."""
    
    wait_time = between(5, 10)
    
    def on_start(self):
        """Set up admin session."""
        self.auth_headers = {
            "Authorization": "Bearer admin_mock_token",
            "Content-Type": "application/json"
        }
    
    @task(2)
    def get_system_statistics(self):
        """Get system-wide statistics."""
        self.client.get(
            "/api/v1/admin/statistics",
            headers=self.auth_headers,
            name="Admin Statistics"
        )
    
    @task(1)
    def get_user_list(self):
        """Get list of users."""
        params = {
            "page": random.randint(1, 3),
            "size": 20
        }
        
        self.client.get(
            "/api/v1/admin/users",
            params=params,
            headers=self.auth_headers,
            name="Admin User List"
        )
    
    @task(1)
    def get_system_health(self):
        """Check system health."""
        self.client.get(
            "/api/v1/health",
            name="Health Check"
        )


# Load testing scenarios
class LightLoad(ExpenseTrackerUser):
    """Light load scenario - normal usage."""
    weight = 3


class MediumLoad(ExpenseTrackerUser):
    """Medium load scenario - busy periods."""
    weight = 2
    wait_time = between(0.5, 2)


class HeavyLoad(ExpenseTrackerUser):
    """Heavy load scenario - peak usage."""
    weight = 1
    wait_time = between(0.1, 1)