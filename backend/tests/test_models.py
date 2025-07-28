"""
Tests for Pydantic models and validation.
"""
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models import (
    AttachmentCreate,
    AttachmentType,
    BudgetCreate,
    BudgetPeriod,
    CategoryCreate,
    CategoryBudgetCreate,
    ExpenseCreate,
    PaymentMethodCreate,
    PaymentType,
)


class TestCategoryModels:
    """Test category model validation."""
    
    def test_category_create_valid(self):
        """Test creating a valid category."""
        category_data = {
            "name": "Food",
            "color": "#FF5733",
            "icon": "utensils",
            "is_custom": True
        }
        category = CategoryCreate(**category_data)
        
        assert category.name == "Food"
        assert category.color == "#FF5733"
        assert category.icon == "utensils"
        assert category.is_custom is True
    
    def test_category_create_minimal(self):
        """Test creating a category with minimal data."""
        category = CategoryCreate(name="Transportation")
        
        assert category.name == "Transportation"
        assert category.color == "#6B7280"  # Default color
        assert category.icon is None
        assert category.is_custom is True  # Default
    
    def test_category_invalid_color(self):
        """Test category creation with invalid color format."""
        with pytest.raises(ValidationError) as exc_info:
            CategoryCreate(name="Food", color="invalid-color")
        
        assert "String should match pattern" in str(exc_info.value)
    
    def test_category_empty_name(self):
        """Test category creation with empty name."""
        with pytest.raises(ValidationError) as exc_info:
            CategoryCreate(name="")
        
        assert "String should have at least 1 character" in str(exc_info.value)
    
    def test_category_name_too_long(self):
        """Test category creation with name too long."""
        long_name = "a" * 101  # Exceeds 100 character limit
        
        with pytest.raises(ValidationError) as exc_info:
            CategoryCreate(name=long_name)
        
        assert "String should have at most 100 characters" in str(exc_info.value)


class TestPaymentMethodModels:
    """Test payment method model validation."""
    
    def test_payment_method_create_valid(self):
        """Test creating a valid payment method."""
        payment_data = {
            "name": "Chase Credit Card",
            "type": PaymentType.CREDIT_CARD,
            "account_number": "1234",
            "institution": "Chase Bank",
            "is_active": True
        }
        payment_method = PaymentMethodCreate(**payment_data)
        
        assert payment_method.name == "Chase Credit Card"
        assert payment_method.type == PaymentType.CREDIT_CARD
        assert payment_method.account_number == "1234"
        assert payment_method.institution == "Chase Bank"
        assert payment_method.is_active is True
    
    def test_payment_method_create_minimal(self):
        """Test creating a payment method with minimal data."""
        payment_method = PaymentMethodCreate(
            name="Cash",
            type=PaymentType.CASH
        )
        
        assert payment_method.name == "Cash"
        assert payment_method.type == PaymentType.CASH
        assert payment_method.account_number is None
        assert payment_method.institution is None
        assert payment_method.is_active is True  # Default
    
    def test_payment_method_invalid_type(self):
        """Test payment method creation with invalid type."""
        with pytest.raises(ValidationError) as exc_info:
            PaymentMethodCreate(name="Test", type="invalid_type")
        
        assert "Input should be" in str(exc_info.value)


class TestExpenseModels:
    """Test expense model validation."""
    
    def test_expense_create_valid(self):
        """Test creating a valid expense."""
        category_id = uuid4()
        payment_method_id = uuid4()
        
        expense_data = {
            "amount": Decimal("25.50"),
            "description": "Lunch at restaurant",
            "expense_date": date(2024, 1, 15),
            "notes": "Business lunch with client",
            "category_id": category_id,
            "payment_method_id": payment_method_id,
            "is_recurring": False
        }
        expense = ExpenseCreate(**expense_data)
        
        assert expense.amount == Decimal("25.50")
        assert expense.description == "Lunch at restaurant"
        assert expense.expense_date == date(2024, 1, 15)
        assert expense.notes == "Business lunch with client"
        assert expense.category_id == category_id
        assert expense.payment_method_id == payment_method_id
        assert expense.is_recurring is False
    
    def test_expense_create_minimal(self):
        """Test creating an expense with minimal data."""
        category_id = uuid4()
        payment_method_id = uuid4()
        
        expense = ExpenseCreate(
            amount=Decimal("10.00"),
            category_id=category_id,
            payment_method_id=payment_method_id
        )
        
        assert expense.amount == Decimal("10.00")
        assert expense.description is None
        assert expense.expense_date == date.today()  # Default
        assert expense.notes is None
        assert expense.is_recurring is False  # Default
    
    def test_expense_amount_validation(self):
        """Test expense amount validation."""
        category_id = uuid4()
        payment_method_id = uuid4()
        
        # Test negative amount
        with pytest.raises(ValidationError) as exc_info:
            ExpenseCreate(
                amount=Decimal("-10.00"),
                category_id=category_id,
                payment_method_id=payment_method_id
            )
        assert "Amount must be positive" in str(exc_info.value)
        
        # Test zero amount
        with pytest.raises(ValidationError) as exc_info:
            ExpenseCreate(
                amount=Decimal("0.00"),
                category_id=category_id,
                payment_method_id=payment_method_id
            )
        assert "Amount must be positive" in str(exc_info.value)
    
    def test_expense_amount_decimal_precision(self):
        """Test expense amount decimal precision handling."""
        category_id = uuid4()
        payment_method_id = uuid4()
        
        # Test amount with more than 2 decimal places
        expense = ExpenseCreate(
            amount=Decimal("25.999"),
            category_id=category_id,
            payment_method_id=payment_method_id
        )
        
        # Should be rounded to 2 decimal places
        assert expense.amount == Decimal("26.00")
    
    def test_expense_string_amount_conversion(self):
        """Test expense amount conversion from string."""
        category_id = uuid4()
        payment_method_id = uuid4()
        
        expense = ExpenseCreate(
            amount="25.50",
            category_id=category_id,
            payment_method_id=payment_method_id
        )
        
        assert expense.amount == Decimal("25.50")
        assert isinstance(expense.amount, Decimal)


class TestBudgetModels:
    """Test budget model validation."""
    
    def test_budget_create_valid(self):
        """Test creating a valid budget."""
        budget_data = {
            "name": "Monthly Budget",
            "period": BudgetPeriod.MONTHLY,
            "total_limit": Decimal("1000.00"),
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 1, 31),
            "is_active": True
        }
        budget = BudgetCreate(**budget_data)
        
        assert budget.name == "Monthly Budget"
        assert budget.period == BudgetPeriod.MONTHLY
        assert budget.total_limit == Decimal("1000.00")
        assert budget.start_date == date(2024, 1, 1)
        assert budget.end_date == date(2024, 1, 31)
        assert budget.is_active is True
    
    def test_budget_create_minimal(self):
        """Test creating a budget with minimal data."""
        budget = BudgetCreate(name="Test Budget")
        
        assert budget.name == "Test Budget"
        assert budget.period == BudgetPeriod.MONTHLY  # Default
        assert budget.total_limit is None
        assert budget.start_date == date.today()  # Default
        assert budget.end_date is None
        assert budget.is_active is True  # Default
    
    def test_budget_date_validation(self):
        """Test budget date validation."""
        # Test end date before start date
        with pytest.raises(ValidationError) as exc_info:
            BudgetCreate(
                name="Test Budget",
                start_date=date(2024, 1, 31),
                end_date=date(2024, 1, 1)
            )
        assert "End date must be after start date" in str(exc_info.value)
    
    def test_category_budget_create_valid(self):
        """Test creating a valid category budget."""
        budget_id = uuid4()
        category_id = uuid4()
        
        category_budget = CategoryBudgetCreate(
            limit_amount=Decimal("200.00"),
            budget_id=budget_id,
            category_id=category_id
        )
        
        assert category_budget.limit_amount == Decimal("200.00")
        assert category_budget.budget_id == budget_id
        assert category_budget.category_id == category_id


class TestAttachmentModels:
    """Test attachment model validation."""
    
    def test_attachment_create_valid(self):
        """Test creating a valid attachment."""
        expense_id = uuid4()
        
        attachment_data = {
            "filename": "receipt_123.jpg",
            "original_filename": "IMG_001.jpg",
            "file_path": "/uploads/receipts/receipt_123.jpg",
            "file_size": 1024000,  # 1MB
            "mime_type": "image/jpeg",
            "attachment_type": AttachmentType.RECEIPT,
            "expense_id": expense_id
        }
        attachment = AttachmentCreate(**attachment_data)
        
        assert attachment.filename == "receipt_123.jpg"
        assert attachment.original_filename == "IMG_001.jpg"
        assert attachment.file_path == "/uploads/receipts/receipt_123.jpg"
        assert attachment.file_size == 1024000
        assert attachment.mime_type == "image/jpeg"
        assert attachment.attachment_type == AttachmentType.RECEIPT
        assert attachment.expense_id == expense_id
    
    def test_attachment_file_size_validation(self):
        """Test attachment file size validation."""
        expense_id = uuid4()
        
        # Test file size too large (over 10MB)
        with pytest.raises(ValidationError) as exc_info:
            AttachmentCreate(
                filename="large_file.pdf",
                original_filename="large_file.pdf",
                file_path="/uploads/large_file.pdf",
                file_size=11 * 1024 * 1024,  # 11MB
                mime_type="application/pdf",
                expense_id=expense_id
            )
        assert "File size cannot exceed" in str(exc_info.value)
    
    def test_attachment_create_minimal(self):
        """Test creating an attachment with minimal data."""
        expense_id = uuid4()
        
        attachment = AttachmentCreate(
            filename="receipt.jpg",
            original_filename="receipt.jpg",
            file_path="/uploads/receipt.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            expense_id=expense_id
        )
        
        assert attachment.attachment_type == AttachmentType.RECEIPT  # Default