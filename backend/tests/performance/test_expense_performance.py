"""Performance tests for expense operations."""
import pytest
import asyncio
import time
from decimal import Decimal
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi import status
from tests.conftest import performance_test, slow_test


class TestExpensePerformance:
    """Performance tests for expense operations."""
    
    @pytest.mark.performance
    @slow_test
    def test_bulk_expense_creation_performance(self, client, auth_headers, test_category, performance_monitor):
        """Test performance of bulk expense creation."""
        
        # Generate large dataset
        num_expenses = 1000
        bulk_expenses_data = []
        
        for i in range(num_expenses):
            bulk_expenses_data.append({
                "amount": round(10 + (i % 100) * 0.5, 2),
                "description": f"Performance Test Expense {i + 1}",
                "category_id": str(test_category.id),
                "date": date.today().isoformat(),
                "payment_method": "Credit Card"
            })
        
        # Start performance monitoring
        performance_monitor.start()
        
        # Execute bulk creation
        response = client.post(
            "/api/v1/expenses/bulk",
            json={"expenses": bulk_expenses_data},
            headers=auth_headers
        )
        
        # Stop monitoring
        performance_monitor.stop()
        
        # Verify success
        assert response.status_code == status.HTTP_201_CREATED
        result = response.json()
        assert len(result["created_expenses"]) == num_expenses
        
        # Performance assertions
        assert performance_monitor.duration < 30.0  # Should complete within 30 seconds
        assert performance_monitor.peak_memory < 500  # Should use less than 500MB
        
        print(f"Bulk creation performance:")
        print(f"  Duration: {performance_monitor.duration:.2f}s")
        print(f"  Peak Memory: {performance_monitor.peak_memory:.2f}MB")
        print(f"  Avg CPU: {performance_monitor.avg_cpu:.2f}%")
        print(f"  Throughput: {num_expenses / performance_monitor.duration:.2f} expenses/sec")
    
    @pytest.mark.performance
    @slow_test
    def test_expense_list_pagination_performance(self, client, auth_headers, performance_test_data, performance_monitor):
        """Test performance of expense list with pagination."""
        
        # First create the test data
        bulk_response = client.post(
            "/api/v1/expenses/bulk",
            json={"expenses": performance_test_data[:500]},  # Create 500 expenses
            headers=auth_headers
        )
        assert bulk_response.status_code == status.HTTP_201_CREATED
        
        # Test pagination performance
        page_size = 50
        total_pages = 10
        
        performance_monitor.start()
        
        for page in range(1, total_pages + 1):
            response = client.get(
                "/api/v1/expenses/",
                params={"page": page, "size": page_size},
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["items"]) <= page_size
        
        performance_monitor.stop()
        
        # Performance assertions
        assert performance_monitor.duration < 10.0  # Should complete within 10 seconds
        avg_response_time = performance_monitor.duration / total_pages
        assert avg_response_time < 1.0  # Each page should load within 1 second
        
        print(f"Pagination performance:")
        print(f"  Total Duration: {performance_monitor.duration:.2f}s")
        print(f"  Avg Response Time: {avg_response_time:.3f}s per page")
        print(f"  Peak Memory: {performance_monitor.peak_memory:.2f}MB")
    
    @pytest.mark.performance
    @slow_test
    def test_expense_search_performance(self, client, auth_headers, performance_test_data, performance_monitor):
        """Test performance of expense search functionality."""
        
        # Create test data with searchable content
        search_expenses = []
        for i in range(200):
            search_expenses.append({
                "amount": round(10 + i * 0.5, 2),
                "description": f"Coffee shop visit number {i} at location {i % 10}",
                "category_id": str(uuid4()),
                "date": date.today().isoformat()
            })
        
        # Create the expenses
        bulk_response = client.post(
            "/api/v1/expenses/bulk",
            json={"expenses": search_expenses},
            headers=auth_headers
        )
        assert bulk_response.status_code == status.HTTP_201_CREATED
        
        # Test various search queries
        search_queries = [
            "coffee",
            "shop",
            "location 5",
            "visit number 1",
            "coffee shop location"
        ]
        
        performance_monitor.start()
        
        for query in search_queries:
            response = client.get(
                "/api/v1/expenses/search",
                params={"q": query},
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "items" in data
        
        performance_monitor.stop()
        
        # Performance assertions
        assert performance_monitor.duration < 5.0  # All searches within 5 seconds
        avg_search_time = performance_monitor.duration / len(search_queries)
        assert avg_search_time < 1.0  # Each search within 1 second
        
        print(f"Search performance:")
        print(f"  Total Duration: {performance_monitor.duration:.2f}s")
        print(f"  Avg Search Time: {avg_search_time:.3f}s per query")
        print(f"  Peak Memory: {performance_monitor.peak_memory:.2f}MB")
    
    @pytest.mark.performance
    @slow_test
    def test_expense_statistics_performance(self, client, auth_headers, performance_test_data, performance_monitor):
        """Test performance of expense statistics calculation."""
        
        # Create large dataset for statistics
        bulk_response = client.post(
            "/api/v1/expenses/bulk",
            json={"expenses": performance_test_data},
            headers=auth_headers
        )
        assert bulk_response.status_code == status.HTTP_201_CREATED
        
        # Test statistics calculation performance
        date_ranges = [
            (date.today() - timedelta(days=7), date.today()),
            (date.today() - timedelta(days=30), date.today()),
            (date.today() - timedelta(days=90), date.today()),
            (date.today() - timedelta(days=365), date.today())
        ]
        
        performance_monitor.start()
        
        for start_date, end_date in date_ranges:
            response = client.get(
                "/api/v1/expenses/statistics",
                params={
                    "date_from": start_date.isoformat(),
                    "date_to": end_date.isoformat()
                },
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "total_amount" in data
            assert "expense_count" in data
            assert "average_amount" in data
        
        performance_monitor.stop()
        
        # Performance assertions
        assert performance_monitor.duration < 8.0  # All calculations within 8 seconds
        avg_calc_time = performance_monitor.duration / len(date_ranges)
        assert avg_calc_time < 2.0  # Each calculation within 2 seconds
        
        print(f"Statistics performance:")
        print(f"  Total Duration: {performance_monitor.duration:.2f}s")
        print(f"  Avg Calculation Time: {avg_calc_time:.3f}s per range")
        print(f"  Peak Memory: {performance_monitor.peak_memory:.2f}MB")
    
    @pytest.mark.performance
    @slow_test
    def test_concurrent_expense_operations(self, client, auth_headers, test_category, performance_monitor):
        """Test performance under concurrent load."""
        
        def create_expense(expense_id):
            """Create a single expense."""
            expense_data = {
                "amount": 25.50,
                "description": f"Concurrent Expense {expense_id}",
                "category_id": str(test_category.id),
                "date": date.today().isoformat()
            }
            
            response = client.post(
                "/api/v1/expenses/",
                json=expense_data,
                headers=auth_headers
            )
            
            return response.status_code == status.HTTP_201_CREATED
        
        # Test concurrent creation
        num_concurrent = 50
        
        performance_monitor.start()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(create_expense, i)
                for i in range(num_concurrent)
            ]
            
            results = [future.result() for future in futures]
        
        performance_monitor.stop()
        
        # Verify all operations succeeded
        success_count = sum(results)
        assert success_count == num_concurrent
        
        # Performance assertions
        assert performance_monitor.duration < 15.0  # Should complete within 15 seconds
        throughput = num_concurrent / performance_monitor.duration
        assert throughput > 3.0  # Should handle at least 3 operations per second
        
        print(f"Concurrent operations performance:")
        print(f"  Duration: {performance_monitor.duration:.2f}s")
        print(f"  Throughput: {throughput:.2f} operations/sec")
        print(f"  Peak Memory: {performance_monitor.peak_memory:.2f}MB")
        print(f"  Success Rate: {success_count}/{num_concurrent} ({success_count/num_concurrent*100:.1f}%)")
    
    @pytest.mark.performance
    @slow_test
    def test_expense_export_performance(self, client, auth_headers, performance_test_data, performance_monitor):
        """Test performance of expense export functionality."""
        
        # Create large dataset for export
        bulk_response = client.post(
            "/api/v1/expenses/bulk",
            json={"expenses": performance_test_data},
            headers=auth_headers
        )
        assert bulk_response.status_code == status.HTTP_201_CREATED
        
        # Test export performance for different formats
        export_formats = ["csv", "json", "xlsx"]
        
        performance_monitor.start()
        
        for format_type in export_formats:
            response = client.get(
                "/api/v1/expenses/export",
                params={
                    "format": format_type,
                    "date_from": (date.today() - timedelta(days=30)).isoformat(),
                    "date_to": date.today().isoformat()
                },
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            assert len(response.content) > 0  # Should have content
        
        performance_monitor.stop()
        
        # Performance assertions
        assert performance_monitor.duration < 10.0  # All exports within 10 seconds
        avg_export_time = performance_monitor.duration / len(export_formats)
        assert avg_export_time < 4.0  # Each export within 4 seconds
        
        print(f"Export performance:")
        print(f"  Total Duration: {performance_monitor.duration:.2f}s")
        print(f"  Avg Export Time: {avg_export_time:.3f}s per format")
        print(f"  Peak Memory: {performance_monitor.peak_memory:.2f}MB")
    
    @pytest.mark.performance
    @slow_test
    def test_database_query_performance(self, db_session, test_user, performance_monitor):
        """Test database query performance directly."""
        
        # This test would require direct database access
        # and would test repository layer performance
        
        from app.repositories.expense import expense_repository
        from app.models.expense import ExpenseCreate
        
        # Create test data directly in database
        expenses_data = []
        for i in range(500):
            expense_data = ExpenseCreate(
                amount=Decimal(f"{10 + i * 0.5:.2f}"),
                description=f"DB Performance Test {i}",
                date=date.today(),
                category_id=uuid4()
            )
            expenses_data.append(expense_data)
        
        performance_monitor.start()
        
        # Test bulk creation performance
        created_expenses = await expense_repository.bulk_create(
            db_session, expenses_data, test_user.id
        )
        await db_session.commit()
        
        # Test query performance
        filters = {
            "date_from": date.today() - timedelta(days=30),
            "date_to": date.today(),
            "min_amount": 10.0,
            "max_amount": 100.0
        }
        
        filtered_expenses = await expense_repository.get_by_user_with_filters(
            db_session, test_user.id, **filters
        )
        
        performance_monitor.stop()
        
        # Verify results
        assert len(created_expenses) == 500
        assert len(filtered_expenses) > 0
        
        # Performance assertions
        assert performance_monitor.duration < 5.0  # Database operations within 5 seconds
        
        print(f"Database performance:")
        print(f"  Duration: {performance_monitor.duration:.2f}s")
        print(f"  Created: {len(created_expenses)} expenses")
        print(f"  Filtered: {len(filtered_expenses)} expenses")
        print(f"  Peak Memory: {performance_monitor.peak_memory:.2f}MB")