"""
Tests for repository layer functionality.
"""
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BudgetTable,
    CategoryBudgetTable,
    CategoryTable,
    ExpenseTable,
    PaymentMethodTable,
    PaymentType,
)
from app.repositories import (
    budget_repository,
    category_budget_repository,
    category_repository,
    expense_repository,
    payment_method_repository,
)


class TestCategoryRepository:
    """Test category repository operations."""
    
    async def test_create_category(self, db_session: AsyncSession):
        """Test creating a category."""
        from app.models import CategoryCreate
        
        category_data = CategoryCreate(
            name="Test Category",
            color="#FF5733",
            is_custom=True
        )
        
        category = await category_repository.create(db_session, obj_in=category_data)
        
        assert category.name == "Test Category"
        assert category.color == "#FF5733"
        assert category.is_custom is True
        assert category.id is not None
        assert category.created_at is not None
    
    async def test_get_category_by_id(self, db_session: AsyncSession, sample_category: CategoryTable):
        """Test getting a category by ID."""
        category = await category_repository.get(db_session, sample_category.id)
        
        assert category is not None
        assert category.id == sample_category.id
        assert category.name == sample_category.name
    
    async def test_get_category_by_name(self, db_session: AsyncSession, sample_category: CategoryTable):
        """Test getting a category by name."""
        category = await category_repository.get_by_name(db_session, sample_category.name)
        
        assert category is not None
        assert category.name == sample_category.name
        assert category.id == sample_category.id
    
    async def test_get_root_categories(self, db_session: AsyncSession):
        """Test getting root categories (no parent)."""
        # Create root category
        root_category = CategoryTable(
            name="Root Category",
            color="#FF0000",
            is_custom=False
        )
        db_session.add(root_category)
        await db_session.commit()
        await db_session.refresh(root_category)
        
        # Create child category
        child_category = CategoryTable(
            name="Child Category",
            color="#00FF00",
            parent_category_id=root_category.id,
            is_custom=False
        )
        db_session.add(child_category)
        await db_session.commit()
        
        # Get root categories
        root_categories = await category_repository.get_root_categories(db_session)
        
        assert len(root_categories) >= 1
        root_names = [cat.name for cat in root_categories]
        assert "Root Category" in root_names
        assert "Child Category" not in root_names
    
    async def test_get_subcategories(self, db_session: AsyncSession):
        """Test getting subcategories of a parent."""
        # Create parent category
        parent_category = CategoryTable(
            name="Parent Category",
            color="#FF0000",
            is_custom=False
        )
        db_session.add(parent_category)
        await db_session.commit()
        await db_session.refresh(parent_category)
        
        # Create child categories
        child1 = CategoryTable(
            name="Child 1",
            color="#00FF00",
            parent_category_id=parent_category.id,
            is_custom=False
        )
        child2 = CategoryTable(
            name="Child 2",
            color="#0000FF",
            parent_category_id=parent_category.id,
            is_custom=False
        )
        db_session.add_all([child1, child2])
        await db_session.commit()
        
        # Get subcategories
        subcategories = await category_repository.get_subcategories(db_session, parent_category.id)
        
        assert len(subcategories) == 2
        child_names = [cat.name for cat in subcategories]
        assert "Child 1" in child_names
        assert "Child 2" in child_names
    
    async def test_get_custom_categories(self, db_session: AsyncSession):
        """Test getting custom categories."""
        # Create custom category
        custom_category = CategoryTable(
            name="Custom Category",
            color="#FF0000",
            is_custom=True
        )
        # Create system category
        system_category = CategoryTable(
            name="System Category",
            color="#00FF00",
            is_custom=False
        )
        db_session.add_all([custom_category, system_category])
        await db_session.commit()
        
        # Get custom categories
        custom_categories = await category_repository.get_custom_categories(db_session)
        
        custom_names = [cat.name for cat in custom_categories]
        assert "Custom Category" in custom_names
        assert "System Category" not in custom_names


class TestPaymentMethodRepository:
    """Test payment method repository operations."""
    
    async def test_create_payment_method(self, db_session: AsyncSession):
        """Test creating a payment method."""
        from app.models import PaymentMethodCreate
        
        payment_data = PaymentMethodCreate(
            name="Test Credit Card",
            type=PaymentType.CREDIT_CARD,
            account_number="1234",
            institution="Test Bank"
        )
        
        payment_method = await payment_method_repository.create(db_session, obj_in=payment_data)
        
        assert payment_method.name == "Test Credit Card"
        assert payment_method.type == PaymentType.CREDIT_CARD
        assert payment_method.account_number == "1234"
        assert payment_method.institution == "Test Bank"
        assert payment_method.is_active is True
    
    async def test_get_by_type(self, db_session: AsyncSession):
        """Test getting payment methods by type."""
        # Create payment methods of different types
        credit_card = PaymentMethodTable(
            name="Credit Card",
            type=PaymentType.CREDIT_CARD,
            is_active=True
        )
        cash = PaymentMethodTable(
            name="Cash",
            type=PaymentType.CASH,
            is_active=True
        )
        db_session.add_all([credit_card, cash])
        await db_session.commit()
        
        # Get credit card payment methods
        credit_cards = await payment_method_repository.get_by_type(db_session, PaymentType.CREDIT_CARD)
        
        assert len(credit_cards) >= 1
        assert all(pm.type == PaymentType.CREDIT_CARD for pm in credit_cards)
    
    async def test_get_active_payment_methods(self, db_session: AsyncSession):
        """Test getting active payment methods."""
        # Create active and inactive payment methods
        active_pm = PaymentMethodTable(
            name="Active Card",
            type=PaymentType.CREDIT_CARD,
            is_active=True
        )
        inactive_pm = PaymentMethodTable(
            name="Inactive Card",
            type=PaymentType.CREDIT_CARD,
            is_active=False
        )
        db_session.add_all([active_pm, inactive_pm])
        await db_session.commit()
        
        # Get active payment methods
        active_methods = await payment_method_repository.get_active(db_session)
        
        active_names = [pm.name for pm in active_methods]
        assert "Active Card" in active_names
        assert "Inactive Card" not in active_names


class TestExpenseRepository:
    """Test expense repository operations."""
    
    async def test_create_expense(
        self, 
        db_session: AsyncSession, 
        sample_category: CategoryTable,
        sample_payment_method: PaymentMethodTable
    ):
        """Test creating an expense."""
        from app.models import ExpenseCreate
        
        expense_data = ExpenseCreate(
            amount=Decimal("25.50"),
            description="Test expense",
            expense_date=date(2024, 1, 15),
            category_id=sample_category.id,
            payment_method_id=sample_payment_method.id
        )
        
        expense = await expense_repository.create(db_session, obj_in=expense_data)
        
        assert expense.amount == Decimal("25.50")
        assert expense.description == "Test expense"
        assert expense.expense_date == date(2024, 1, 15)
        assert expense.category_id == sample_category.id
        assert expense.payment_method_id == sample_payment_method.id
    
    async def test_get_by_date_range(
        self, 
        db_session: AsyncSession,
        sample_category: CategoryTable,
        sample_payment_method: PaymentMethodTable
    ):
        """Test getting expenses by date range."""
        # Create expenses with different dates
        expense1 = ExpenseTable(
            amount=Decimal("10.00"),
            description="Expense 1",
            expense_date=date(2024, 1, 10),
            category_id=sample_category.id,
            payment_method_id=sample_payment_method.id
        )
        expense2 = ExpenseTable(
            amount=Decimal("20.00"),
            description="Expense 2",
            expense_date=date(2024, 1, 20),
            category_id=sample_category.id,
            payment_method_id=sample_payment_method.id
        )
        expense3 = ExpenseTable(
            amount=Decimal("30.00"),
            description="Expense 3",
            expense_date=date(2024, 2, 5),
            category_id=sample_category.id,
            payment_method_id=sample_payment_method.id
        )
        db_session.add_all([expense1, expense2, expense3])
        await db_session.commit()
        
        # Get expenses in January 2024
        expenses = await expense_repository.get_by_date_range(
            db_session,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        assert len(expenses) == 2
        descriptions = [exp.description for exp in expenses]
        assert "Expense 1" in descriptions
        assert "Expense 2" in descriptions
        assert "Expense 3" not in descriptions
    
    async def test_get_total_amount(
        self, 
        db_session: AsyncSession,
        sample_category: CategoryTable,
        sample_payment_method: PaymentMethodTable
    ):
        """Test getting total expense amount for a date range."""
        # Create expenses
        expense1 = ExpenseTable(
            amount=Decimal("10.50"),
            expense_date=date(2024, 1, 10),
            category_id=sample_category.id,
            payment_method_id=sample_payment_method.id
        )
        expense2 = ExpenseTable(
            amount=Decimal("25.75"),
            expense_date=date(2024, 1, 20),
            category_id=sample_category.id,
            payment_method_id=sample_payment_method.id
        )
        db_session.add_all([expense1, expense2])
        await db_session.commit()
        
        # Get total amount
        total = await expense_repository.get_total_amount(
            db_session,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        assert total == Decimal("36.25")
    
    async def test_search_expenses(
        self, 
        db_session: AsyncSession,
        sample_category: CategoryTable,
        sample_payment_method: PaymentMethodTable
    ):
        """Test searching expenses by description and notes."""
        # Create expenses with different descriptions
        expense1 = ExpenseTable(
            amount=Decimal("10.00"),
            description="Coffee at Starbucks",
            notes="Morning coffee",
            expense_date=date(2024, 1, 10),
            category_id=sample_category.id,
            payment_method_id=sample_payment_method.id
        )
        expense2 = ExpenseTable(
            amount=Decimal("20.00"),
            description="Lunch at restaurant",
            notes="Business lunch",
            expense_date=date(2024, 1, 20),
            category_id=sample_category.id,
            payment_method_id=sample_payment_method.id
        )
        expense3 = ExpenseTable(
            amount=Decimal("30.00"),
            description="Gas station",
            notes="Fuel for car",
            expense_date=date(2024, 1, 25),
            category_id=sample_category.id,
            payment_method_id=sample_payment_method.id
        )
        db_session.add_all([expense1, expense2, expense3])
        await db_session.commit()
        
        # Search for "coffee"
        coffee_expenses = await expense_repository.search_expenses(db_session, "coffee")
        assert len(coffee_expenses) == 1
        assert coffee_expenses[0].description == "Coffee at Starbucks"
        
        # Search for "business" (in notes)
        business_expenses = await expense_repository.search_expenses(db_session, "business")
        assert len(business_expenses) == 1
        assert business_expenses[0].notes == "Business lunch"


class TestBudgetRepository:
    """Test budget repository operations."""
    
    async def test_create_budget(self, db_session: AsyncSession):
        """Test creating a budget."""
        from app.models import BudgetCreate
        
        budget_data = BudgetCreate(
            name="Test Budget",
            total_limit=Decimal("1000.00"),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        budget = await budget_repository.create(db_session, obj_in=budget_data)
        
        assert budget.name == "Test Budget"
        assert budget.total_limit == Decimal("1000.00")
        assert budget.start_date == date(2024, 1, 1)
        assert budget.end_date == date(2024, 1, 31)
        assert budget.is_active is True
    
    async def test_get_active_budgets(self, db_session: AsyncSession):
        """Test getting active budgets."""
        # Create active budget
        active_budget = BudgetTable(
            name="Active Budget",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            is_active=True
        )
        # Create inactive budget
        inactive_budget = BudgetTable(
            name="Inactive Budget",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            is_active=False
        )
        db_session.add_all([active_budget, inactive_budget])
        await db_session.commit()
        
        # Get active budgets for current date
        active_budgets = await budget_repository.get_active_budgets(
            db_session, 
            current_date=date(2024, 6, 15)
        )
        
        budget_names = [b.name for b in active_budgets]
        assert "Active Budget" in budget_names
        assert "Inactive Budget" not in budget_names
    
    async def test_category_budget_operations(
        self, 
        db_session: AsyncSession,
        sample_category: CategoryTable
    ):
        """Test category budget operations."""
        from app.models import BudgetCreate, CategoryBudgetCreate
        
        # Create budget
        budget_data = BudgetCreate(
            name="Test Budget",
            start_date=date(2024, 1, 1)
        )
        budget = await budget_repository.create(db_session, obj_in=budget_data)
        
        # Create category budget
        category_budget_data = CategoryBudgetCreate(
            limit_amount=Decimal("200.00"),
            budget_id=budget.id,
            category_id=sample_category.id
        )
        category_budget = await category_budget_repository.create(
            db_session, 
            obj_in=category_budget_data
        )
        
        assert category_budget.limit_amount == Decimal("200.00")
        assert category_budget.spent_amount == Decimal("0.00")
        assert category_budget.budget_id == budget.id
        assert category_budget.category_id == sample_category.id
        
        # Test getting category budget by budget and category
        found_category_budget = await category_budget_repository.get_by_budget_and_category(
            db_session,
            budget.id,
            sample_category.id
        )
        
        assert found_category_budget is not None
        assert found_category_budget.id == category_budget.id
        
        # Test updating spent amount
        updated_category_budget = await category_budget_repository.update_spent_amount(
            db_session,
            budget.id,
            sample_category.id,
            Decimal("50.00")
        )
        
        assert updated_category_budget is not None
        assert updated_category_budget.spent_amount == Decimal("50.00")