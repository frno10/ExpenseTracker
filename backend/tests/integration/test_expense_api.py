"""Integration tests for expense API endpoints."""
import pytest
from decimal import Decimal
from datetime import date
from uuid import uuid4

from fastapi import status
from tests.conftest import TestDataFactory


class TestExpenseAPI:
    """Integration tests for expense API endpoints."""
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_create_expense_success(self, client, auth_headers, test_category):
        """Test successful expense creation via API."""
        expense_data = {
            "amount": 25.50,
            "description": "Coffee and pastry",
            "category_id": str(test_category.id),
            "date": date.today().isoformat(),
            "payment_method": "Credit Card",
            "notes": "Morning coffee"
        }
        
        response = client.post(
            "/api/v1/expenses/",
            json=expense_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        assert data["amount"] == "25.50"
        assert data["description"] == "Coffee and pastry"
        assert data["category_id"] == str(test_category.id)
        assert data["payment_method"] == "Credit Card"
        assert data["notes"] == "Morning coffee"
        assert "id" in data
        assert "created_at" in data
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_create_expense_invalid_data(self, client, auth_headers):
        """Test expense creation with invalid data."""
        expense_data = {
            "amount": -10.00,  # Invalid negative amount
            "description": "",  # Empty description
            "date": "invalid-date"  # Invalid date format
        }
        
        response = client.post(
            "/api/v1/expenses/",
            json=expense_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        data = response.json()
        assert "detail" in data
        errors = data["detail"]
        
        # Check for validation errors
        error_fields = [error["loc"][-1] for error in errors]
        assert "amount" in error_fields
        assert "description" in error_fields
        assert "date" in error_fields
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_create_expense_unauthorized(self, client, test_category):
        """Test expense creation without authentication."""
        expense_data = {
            "amount": 25.50,
            "description": "Coffee",
            "category_id": str(test_category.id),
            "date": date.today().isoformat()
        }
        
        response = client.post("/api/v1/expenses/", json=expense_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_get_expense_by_id_success(self, client, auth_headers, test_expense):
        """Test successful expense retrieval by ID."""
        response = client.get(
            f"/api/v1/expenses/{test_expense.id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["id"] == str(test_expense.id)
        assert data["amount"] == str(test_expense.amount)
        assert data["description"] == test_expense.description
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_get_expense_by_id_not_found(self, client, auth_headers):
        """Test expense retrieval with non-existent ID."""
        non_existent_id = uuid4()
        
        response = client.get(
            f"/api/v1/expenses/{non_existent_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_update_expense_success(self, client, auth_headers, test_expense):
        """Test successful expense update."""
        update_data = {
            "amount": 30.00,
            "description": "Updated coffee",
            "notes": "Updated notes"
        }
        
        response = client.put(
            f"/api/v1/expenses/{test_expense.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["amount"] == "30.00"
        assert data["description"] == "Updated coffee"
        assert data["notes"] == "Updated notes"
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_update_expense_partial(self, client, auth_headers, test_expense):
        """Test partial expense update."""
        update_data = {
            "description": "Partially updated"
        }
        
        response = client.put(
            f"/api/v1/expenses/{test_expense.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["description"] == "Partially updated"
        assert data["amount"] == str(test_expense.amount)  # Unchanged
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_delete_expense_success(self, client, auth_headers, test_expense):
        """Test successful expense deletion."""
        response = client.delete(
            f"/api/v1/expenses/{test_expense.id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify expense is deleted
        get_response = client.get(
            f"/api/v1/expenses/{test_expense.id}",
            headers=auth_headers
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_get_user_expenses_success(self, client, auth_headers, multiple_expenses):
        """Test successful retrieval of user expenses."""
        response = client.get("/api/v1/expenses/", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        
        assert len(data["items"]) == len(multiple_expenses)
        assert data["total"] == len(multiple_expenses)
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_get_user_expenses_with_filters(self, client, auth_headers, multiple_expenses):
        """Test user expenses retrieval with filters."""
        params = {
            "min_amount": 15.00,
            "max_amount": 25.00,
            "date_from": date.today().isoformat(),
            "date_to": date.today().isoformat()
        }
        
        response = client.get(
            "/api/v1/expenses/",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "items" in data
        
        # Verify all returned expenses match filters
        for expense in data["items"]:
            amount = float(expense["amount"])
            assert 15.00 <= amount <= 25.00
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_get_user_expenses_pagination(self, client, auth_headers, multiple_expenses):
        """Test user expenses retrieval with pagination."""
        params = {
            "page": 1,
            "size": 2
        }
        
        response = client.get(
            "/api/v1/expenses/",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["size"] == 2
        assert data["total"] == len(multiple_expenses)
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_search_expenses_success(self, client, auth_headers, test_expense):
        """Test successful expense search."""
        params = {
            "q": "Test"  # Search for "Test" in description
        }
        
        response = client.get(
            "/api/v1/expenses/search",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "items" in data
        
        # Verify search results contain the search term
        for expense in data["items"]:
            assert "Test" in expense["description"]
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_get_expense_statistics_success(self, client, auth_headers, multiple_expenses):
        """Test successful expense statistics retrieval."""
        params = {
            "date_from": date.today().isoformat(),
            "date_to": date.today().isoformat()
        }
        
        response = client.get(
            "/api/v1/expenses/statistics",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "total_amount" in data
        assert "expense_count" in data
        assert "average_amount" in data
        assert "min_amount" in data
        assert "max_amount" in data
        assert "category_breakdown" in data
        
        assert data["expense_count"] == len(multiple_expenses)
        assert float(data["total_amount"]) > 0
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_bulk_create_expenses_success(self, client, auth_headers, test_category):
        """Test successful bulk expense creation."""
        expenses_data = [
            {
                "amount": 25.50,
                "description": "Expense 1",
                "category_id": str(test_category.id),
                "date": date.today().isoformat()
            },
            {
                "amount": 45.00,
                "description": "Expense 2",
                "category_id": str(test_category.id),
                "date": date.today().isoformat()
            }
        ]
        
        response = client.post(
            "/api/v1/expenses/bulk",
            json={"expenses": expenses_data},
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        assert "created_expenses" in data
        assert len(data["created_expenses"]) == 2
        
        for i, expense in enumerate(data["created_expenses"]):
            assert expense["amount"] == str(expenses_data[i]["amount"])
            assert expense["description"] == expenses_data[i]["description"]
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_export_expenses_success(self, client, auth_headers, multiple_expenses):
        """Test successful expense export."""
        params = {
            "format": "csv",
            "date_from": date.today().isoformat(),
            "date_to": date.today().isoformat()
        }
        
        response = client.get(
            "/api/v1/expenses/export",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        
        # Verify CSV content
        csv_content = response.content.decode("utf-8")
        lines = csv_content.strip().split("\n")
        
        # Should have header + data rows
        assert len(lines) >= 2
        assert "amount" in lines[0].lower()  # Header row
        assert "description" in lines[0].lower()
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_get_expense_trends_success(self, client, auth_headers, multiple_expenses):
        """Test successful expense trends retrieval."""
        params = {
            "period": "daily",
            "date_from": date.today().isoformat(),
            "date_to": date.today().isoformat()
        }
        
        response = client.get(
            "/api/v1/expenses/trends",
            params=params,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "trends" in data
        assert "period" in data
        assert "summary" in data
        
        assert data["period"] == "daily"
        assert isinstance(data["trends"], list)
    
    @pytest.mark.integration
    @pytest.mark.api
    def test_expense_access_control(self, client, auth_headers, test_user, test_admin_user):
        """Test expense access control between different users."""
        # Create expense as regular user
        expense_data = TestDataFactory.create_expense_data()
        
        create_response = client.post(
            "/api/v1/expenses/",
            json=expense_data,
            headers=auth_headers
        )
        
        assert create_response.status_code == status.HTTP_201_CREATED
        expense_id = create_response.json()["id"]
        
        # Try to access with different user (should fail)
        admin_headers = {"Authorization": f"Bearer {test_admin_user.id}"}
        
        get_response = client.get(
            f"/api/v1/expenses/{expense_id}",
            headers=admin_headers
        )
        
        # Should return 404 (not found) rather than 403 to avoid information leakage
        assert get_response.status_code == status.HTTP_404_NOT_FOUND