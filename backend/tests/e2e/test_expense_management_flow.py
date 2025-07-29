"""End-to-end tests for expense management flow."""
import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta
from uuid import uuid4

from fastapi import status
from tests.conftest import TestDataFactory


class TestExpenseManagementFlow:
    """End-to-end tests for complete expense management workflows."""
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_complete_expense_lifecycle(self, client, auth_headers, test_category):
        """Test complete expense lifecycle: create, read, update, delete."""
        
        # Step 1: Create expense
        expense_data = {
            "amount": 25.50,
            "description": "Coffee and pastry",
            "category_id": str(test_category.id),
            "date": date.today().isoformat(),
            "payment_method": "Credit Card",
            "notes": "Morning coffee at local cafe"
        }
        
        create_response = client.post(
            "/api/v1/expenses/",
            json=expense_data,
            headers=auth_headers
        )
        
        assert create_response.status_code == status.HTTP_201_CREATED
        created_expense = create_response.json()
        expense_id = created_expense["id"]
        
        # Verify creation
        assert created_expense["amount"] == "25.50"
        assert created_expense["description"] == "Coffee and pastry"
        assert "created_at" in created_expense
        
        # Step 2: Read expense
        get_response = client.get(
            f"/api/v1/expenses/{expense_id}",
            headers=auth_headers
        )
        
        assert get_response.status_code == status.HTTP_200_OK
        retrieved_expense = get_response.json()
        
        assert retrieved_expense["id"] == expense_id
        assert retrieved_expense["amount"] == "25.50"
        assert retrieved_expense["description"] == "Coffee and pastry"
        
        # Step 3: Update expense
        update_data = {
            "amount": 30.00,
            "description": "Coffee, pastry, and tip",
            "notes": "Added tip for good service"
        }
        
        update_response = client.put(
            f"/api/v1/expenses/{expense_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert update_response.status_code == status.HTTP_200_OK
        updated_expense = update_response.json()
        
        assert updated_expense["amount"] == "30.00"
        assert updated_expense["description"] == "Coffee, pastry, and tip"
        assert updated_expense["notes"] == "Added tip for good service"
        
        # Step 4: Verify update persisted
        get_updated_response = client.get(
            f"/api/v1/expenses/{expense_id}",
            headers=auth_headers
        )
        
        assert get_updated_response.status_code == status.HTTP_200_OK
        persisted_expense = get_updated_response.json()
        assert persisted_expense["amount"] == "30.00"
        
        # Step 5: Delete expense
        delete_response = client.delete(
            f"/api/v1/expenses/{expense_id}",
            headers=auth_headers
        )
        
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT
        
        # Step 6: Verify deletion
        get_deleted_response = client.get(
            f"/api/v1/expenses/{expense_id}",
            headers=auth_headers
        )
        
        assert get_deleted_response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_expense_filtering_and_search_flow(self, client, auth_headers, test_category):
        """Test expense filtering and search functionality."""
        
        # Step 1: Create multiple expenses with different attributes
        expenses_data = [
            {
                "amount": 15.50,
                "description": "Coffee at Starbucks",
                "category_id": str(test_category.id),
                "date": date.today().isoformat(),
                "payment_method": "Credit Card"
            },
            {
                "amount": 45.00,
                "description": "Lunch at restaurant",
                "category_id": str(test_category.id),
                "date": (date.today() - timedelta(days=1)).isoformat(),
                "payment_method": "Cash"
            },
            {
                "amount": 8.75,
                "description": "Coffee at local cafe",
                "category_id": str(test_category.id),
                "date": (date.today() - timedelta(days=2)).isoformat(),
                "payment_method": "Debit Card"
            }
        ]
        
        created_expenses = []
        for expense_data in expenses_data:
            response = client.post(
                "/api/v1/expenses/",
                json=expense_data,
                headers=auth_headers
            )
            assert response.status_code == status.HTTP_201_CREATED
            created_expenses.append(response.json())
        
        # Step 2: Test amount filtering
        amount_filter_response = client.get(
            "/api/v1/expenses/",
            params={"min_amount": 10.00, "max_amount": 20.00},
            headers=auth_headers
        )
        
        assert amount_filter_response.status_code == status.HTTP_200_OK
        filtered_expenses = amount_filter_response.json()["items"]
        
        # Should only return the first expense (15.50)
        assert len(filtered_expenses) == 1
        assert float(filtered_expenses[0]["amount"]) == 15.50
        
        # Step 3: Test date filtering
        today_filter_response = client.get(
            "/api/v1/expenses/",
            params={
                "date_from": date.today().isoformat(),
                "date_to": date.today().isoformat()
            },
            headers=auth_headers
        )
        
        assert today_filter_response.status_code == status.HTTP_200_OK
        today_expenses = today_filter_response.json()["items"]
        
        # Should only return today's expense
        assert len(today_expenses) == 1
        assert today_expenses[0]["description"] == "Coffee at Starbucks"
        
        # Step 4: Test search functionality
        search_response = client.get(
            "/api/v1/expenses/search",
            params={"q": "coffee"},
            headers=auth_headers
        )
        
        assert search_response.status_code == status.HTTP_200_OK
        search_results = search_response.json()["items"]
        
        # Should return both coffee expenses
        assert len(search_results) == 2
        for expense in search_results:
            assert "coffee" in expense["description"].lower()
        
        # Step 5: Test payment method filtering
        cash_filter_response = client.get(
            "/api/v1/expenses/",
            params={"payment_method": "Cash"},
            headers=auth_headers
        )
        
        assert cash_filter_response.status_code == status.HTTP_200_OK
        cash_expenses = cash_filter_response.json()["items"]
        
        # Should only return the cash expense
        assert len(cash_expenses) == 1
        assert cash_expenses[0]["payment_method"] == "Cash"
        assert cash_expenses[0]["description"] == "Lunch at restaurant"
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_expense_statistics_and_analytics_flow(self, client, auth_headers, test_category):
        """Test expense statistics and analytics functionality."""
        
        # Step 1: Create expenses for analytics
        base_date = date.today()
        expenses_data = [
            {
                "amount": 25.00,
                "description": "Breakfast",
                "category_id": str(test_category.id),
                "date": base_date.isoformat()
            },
            {
                "amount": 45.00,
                "description": "Lunch",
                "category_id": str(test_category.id),
                "date": base_date.isoformat()
            },
            {
                "amount": 35.00,
                "description": "Dinner",
                "category_id": str(test_category.id),
                "date": (base_date - timedelta(days=1)).isoformat()
            }
        ]
        
        for expense_data in expenses_data:
            response = client.post(
                "/api/v1/expenses/",
                json=expense_data,
                headers=auth_headers
            )
            assert response.status_code == status.HTTP_201_CREATED
        
        # Step 2: Get overall statistics
        stats_response = client.get(
            "/api/v1/expenses/statistics",
            params={
                "date_from": (base_date - timedelta(days=7)).isoformat(),
                "date_to": base_date.isoformat()
            },
            headers=auth_headers
        )
        
        assert stats_response.status_code == status.HTTP_200_OK
        stats = stats_response.json()
        
        assert stats["expense_count"] == 3
        assert float(stats["total_amount"]) == 105.00
        assert float(stats["average_amount"]) == 35.00
        assert float(stats["min_amount"]) == 25.00
        assert float(stats["max_amount"]) == 45.00
        
        # Step 3: Get trends data
        trends_response = client.get(
            "/api/v1/expenses/trends",
            params={
                "period": "daily",
                "date_from": (base_date - timedelta(days=7)).isoformat(),
                "date_to": base_date.isoformat()
            },
            headers=auth_headers
        )
        
        assert trends_response.status_code == status.HTTP_200_OK
        trends = trends_response.json()
        
        assert trends["period"] == "daily"
        assert "trends" in trends
        assert "summary" in trends
        
        # Verify trend data structure
        trend_data = trends["trends"]
        assert isinstance(trend_data, list)
        
        # Should have data for the days with expenses
        dates_with_data = [item["date"] for item in trend_data if item["amount"] > 0]
        assert len(dates_with_data) >= 2
        
        # Step 4: Get category breakdown
        category_response = client.get(
            "/api/v1/expenses/statistics",
            params={
                "date_from": (base_date - timedelta(days=7)).isoformat(),
                "date_to": base_date.isoformat(),
                "group_by": "category"
            },
            headers=auth_headers
        )
        
        assert category_response.status_code == status.HTTP_200_OK
        category_stats = category_response.json()
        
        assert "category_breakdown" in category_stats
        category_breakdown = category_stats["category_breakdown"]
        
        # Should have breakdown for our test category
        assert len(category_breakdown) >= 1
        for category_data in category_breakdown:
            assert "category_name" in category_data
            assert "total_amount" in category_data
            assert "expense_count" in category_data
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_bulk_operations_flow(self, client, auth_headers, test_category):
        """Test bulk operations for expenses."""
        
        # Step 1: Bulk create expenses
        bulk_expenses_data = [
            {
                "amount": 12.50,
                "description": "Coffee 1",
                "category_id": str(test_category.id),
                "date": date.today().isoformat()
            },
            {
                "amount": 15.75,
                "description": "Coffee 2",
                "category_id": str(test_category.id),
                "date": date.today().isoformat()
            },
            {
                "amount": 18.25,
                "description": "Coffee 3",
                "category_id": str(test_category.id),
                "date": date.today().isoformat()
            }
        ]
        
        bulk_create_response = client.post(
            "/api/v1/expenses/bulk",
            json={"expenses": bulk_expenses_data},
            headers=auth_headers
        )
        
        assert bulk_create_response.status_code == status.HTTP_201_CREATED
        bulk_result = bulk_create_response.json()
        
        assert "created_expenses" in bulk_result
        created_expenses = bulk_result["created_expenses"]
        assert len(created_expenses) == 3
        
        # Verify all expenses were created correctly
        for i, expense in enumerate(created_expenses):
            assert expense["amount"] == str(bulk_expenses_data[i]["amount"])
            assert expense["description"] == bulk_expenses_data[i]["description"]
            assert "id" in expense
        
        # Step 2: Verify bulk created expenses appear in list
        list_response = client.get(
            "/api/v1/expenses/",
            headers=auth_headers
        )
        
        assert list_response.status_code == status.HTTP_200_OK
        all_expenses = list_response.json()["items"]
        
        # Should include our bulk created expenses
        assert len(all_expenses) >= 3
        
        created_ids = {expense["id"] for expense in created_expenses}
        listed_ids = {expense["id"] for expense in all_expenses}
        
        # All created expense IDs should be in the list
        assert created_ids.issubset(listed_ids)
        
        # Step 3: Test bulk export
        export_response = client.get(
            "/api/v1/expenses/export",
            params={
                "format": "csv",
                "date_from": date.today().isoformat(),
                "date_to": date.today().isoformat()
            },
            headers=auth_headers
        )
        
        assert export_response.status_code == status.HTTP_200_OK
        assert "text/csv" in export_response.headers["content-type"]
        
        # Verify CSV contains our expenses
        csv_content = export_response.content.decode("utf-8")
        lines = csv_content.strip().split("\n")
        
        # Should have header + at least our 3 expenses
        assert len(lines) >= 4
        
        # Check that our expense descriptions appear in the CSV
        csv_text = csv_content.lower()
        assert "coffee 1" in csv_text
        assert "coffee 2" in csv_text
        assert "coffee 3" in csv_text
    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery_flow(self, client, auth_headers, test_category):
        """Test error handling and recovery scenarios."""
        
        # Step 1: Test validation error handling
        invalid_expense_data = {
            "amount": -10.00,  # Invalid negative amount
            "description": "",  # Empty description
            "category_id": "invalid-uuid",  # Invalid UUID
            "date": "invalid-date"  # Invalid date
        }
        
        error_response = client.post(
            "/api/v1/expenses/",
            json=invalid_expense_data,
            headers=auth_headers
        )
        
        assert error_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        error_data = error_response.json()
        
        assert "detail" in error_data
        errors = error_data["detail"]
        assert len(errors) >= 3  # Multiple validation errors
        
        # Step 2: Fix errors and retry
        valid_expense_data = {
            "amount": 25.50,
            "description": "Valid expense",
            "category_id": str(test_category.id),
            "date": date.today().isoformat()
        }
        
        success_response = client.post(
            "/api/v1/expenses/",
            json=valid_expense_data,
            headers=auth_headers
        )
        
        assert success_response.status_code == status.HTTP_201_CREATED
        created_expense = success_response.json()
        expense_id = created_expense["id"]
        
        # Step 3: Test not found error handling
        non_existent_id = str(uuid4())
        
        not_found_response = client.get(
            f"/api/v1/expenses/{non_existent_id}",
            headers=auth_headers
        )
        
        assert not_found_response.status_code == status.HTTP_404_NOT_FOUND
        
        # Step 4: Test unauthorized access
        unauthorized_response = client.get(f"/api/v1/expenses/{expense_id}")
        
        assert unauthorized_response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Step 5: Verify valid operations still work after errors
        valid_get_response = client.get(
            f"/api/v1/expenses/{expense_id}",
            headers=auth_headers
        )
        
        assert valid_get_response.status_code == status.HTTP_200_OK
        retrieved_expense = valid_get_response.json()
        assert retrieved_expense["id"] == expense_id