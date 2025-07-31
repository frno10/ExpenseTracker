from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session

from ..models.payment_method import (
    PaymentMethodTable, AccountTable, AccountBalanceHistory, AccountTransfer,
    PaymentMethodType, AccountType
)
from ..repositories.payment_method import payment_method_repository
from ..repositories.account_repository import AccountRepository
from ..core.exceptions import ValidationError, NotFoundError, BusinessLogicError


class PaymentMethodService:
    """Service for payment method management and business logic."""
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = PaymentMethodRepository(db)
    
    # ===== PAYMENT METHOD OPERATIONS =====
    
    async def create_payment_method(
        self, 
        user_id: UUID, 
        payment_method_data: Dict[str, Any]
    ) -> PaymentMethodTable:
        """Create a new payment method with validation."""
        # Validate payment method data
        self._validate_payment_method_data(payment_method_data)
        
        # Add user_id to payment method data
        payment_method_data['user_id'] = user_id
        
        # If this is the first payment method, make it default
        existing_methods = self.repository.get_user_payment_methods(user_id)
        if not existing_methods:
            payment_method_data['is_default'] = True
        
        # Create payment method
        payment_method = self.repository.create_payment_method(payment_method_data)
        
        return payment_method
    
    async def get_payment_method(
        self, 
        payment_method_id: UUID, 
        user_id: UUID
    ) -> PaymentMethodTable:
        """Get a payment method by ID."""
        payment_method = self.repository.get_payment_method_by_id(payment_method_id, user_id)
        if not payment_method:
            raise NotFoundError(f"Payment method {payment_method_id} not found")
        
        return payment_method
    
    async def get_user_payment_methods(
        self, 
        user_id: UUID, 
        active_only: bool = False,
        payment_type: Optional[PaymentMethodType] = None
    ) -> List[PaymentMethodTable]:
        """Get all payment methods for a user."""
        return self.repository.get_user_payment_methods(user_id, active_only, payment_type)
    
    async def update_payment_method(
        self, 
        payment_method_id: UUID, 
        user_id: UUID, 
        update_data: Dict[str, Any]
    ) -> PaymentMethodTable:
        """Update a payment method."""
        # Validate update data
        self._validate_payment_method_update_data(update_data)
        
        # Update payment method
        payment_method = self.repository.update_payment_method(
            payment_method_id, user_id, update_data
        )
        if not payment_method:
            raise NotFoundError(f"Payment method {payment_method_id} not found")
        
        return payment_method
    
    async def delete_payment_method(
        self, 
        payment_method_id: UUID, 
        user_id: UUID
    ) -> bool:
        """Delete a payment method."""
        # Check if payment method is in use
        payment_method = await self.get_payment_method(payment_method_id, user_id)
        
        # Check if there are expenses using this payment method
        from ..models.expense import ExpenseTable
        expense_count = self.db.query(ExpenseTable).filter(
            ExpenseTable.payment_method_id == payment_method_id
        ).count()
        
        if expense_count > 0:
            raise BusinessLogicError(
                f"Cannot delete payment method. It is used by {expense_count} expenses."
            )
        
        success = self.repository.delete_payment_method(payment_method_id, user_id)
        if not success:
            raise NotFoundError(f"Payment method {payment_method_id} not found")
        
        # If this was the default, set another as default
        if payment_method.is_default:
            remaining_methods = self.repository.get_user_payment_methods(user_id, active_only=True)
            if remaining_methods:
                self.repository.set_default_payment_method(remaining_methods[0].id, user_id)
        
        return success
    
    async def set_default_payment_method(
        self, 
        payment_method_id: UUID, 
        user_id: UUID
    ) -> bool:
        """Set a payment method as default."""
        success = self.repository.set_default_payment_method(payment_method_id, user_id)
        if not success:
            raise NotFoundError(f"Payment method {payment_method_id} not found")
        
        return success
    
    async def get_default_payment_method(self, user_id: UUID) -> Optional[PaymentMethodTable]:
        """Get the default payment method for a user."""
        return self.repository.get_default_payment_method(user_id)
    
    # ===== VALIDATION METHODS =====
    
    def _validate_payment_method_data(self, payment_method_data: Dict[str, Any]) -> None:
        """Validate payment method creation data."""
        required_fields = ['name', 'type']
        for field in required_fields:
            if field not in payment_method_data:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate payment method type
        if payment_method_data['type'] not in PaymentMethodType:
            raise ValidationError(f"Invalid payment method type: {payment_method_data['type']}")
        
        # Validate name length
        if len(payment_method_data['name']) > 100:
            raise ValidationError("Payment method name cannot exceed 100 characters")
        
        # Validate last four digits if provided
        if 'last_four_digits' in payment_method_data:
            last_four = payment_method_data['last_four_digits']
            if last_four and (not last_four.isdigit() or len(last_four) != 4):
                raise ValidationError("Last four digits must be exactly 4 digits")
    
    def _validate_payment_method_update_data(self, update_data: Dict[str, Any]) -> None:
        """Validate payment method update data."""
        # Validate payment method type if provided
        if 'type' in update_data and update_data['type'] not in PaymentMethodType:
            raise ValidationError(f"Invalid payment method type: {update_data['type']}")
        
        # Validate name length if provided
        if 'name' in update_data and len(update_data['name']) > 100:
            raise ValidationError("Payment method name cannot exceed 100 characters")
        
        # Validate last four digits if provided
        if 'last_four_digits' in update_data:
            last_four = update_data['last_four_digits']
            if last_four and (not last_four.isdigit() or len(last_four) != 4):
                raise ValidationError("Last four digits must be exactly 4 digits")


class AccountService:
    """Service for account management and business logic."""
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = AccountRepository(db)
    
    # ===== ACCOUNT OPERATIONS =====
    
    async def create_account(
        self, 
        user_id: UUID, 
        account_data: Dict[str, Any]
    ) -> AccountTable:
        """Create a new account with validation."""
        # Validate account data
        self._validate_account_data(account_data)
        
        # Add user_id to account data
        account_data['user_id'] = user_id
        
        # If this is the first account, make it default
        existing_accounts = self.repository.get_user_accounts(user_id)
        if not existing_accounts:
            account_data['is_default'] = True
        
        # Set default values
        if 'current_balance' not in account_data:
            account_data['current_balance'] = Decimal('0.00')
        
        if 'track_balance' not in account_data:
            account_data['track_balance'] = True
        
        # Create account
        account = self.repository.create_account(account_data)
        
        return account
    
    async def get_account(
        self, 
        account_id: UUID, 
        user_id: UUID
    ) -> AccountTable:
        """Get an account by ID."""
        account = self.repository.get_account_by_id(account_id, user_id)
        if not account:
            raise NotFoundError(f"Account {account_id} not found")
        
        return account
    
    async def get_user_accounts(
        self, 
        user_id: UUID, 
        active_only: bool = False,
        account_type: Optional[AccountType] = None
    ) -> List[AccountTable]:
        """Get all accounts for a user."""
        return self.repository.get_user_accounts(user_id, active_only, account_type)
    
    async def update_account(
        self, 
        account_id: UUID, 
        user_id: UUID, 
        update_data: Dict[str, Any]
    ) -> AccountTable:
        """Update an account."""
        # Validate update data
        self._validate_account_update_data(update_data)
        
        # Update account
        account = self.repository.update_account(account_id, user_id, update_data)
        if not account:
            raise NotFoundError(f"Account {account_id} not found")
        
        return account
    
    async def delete_account(
        self, 
        account_id: UUID, 
        user_id: UUID
    ) -> bool:
        """Delete an account."""
        # Check if account is in use
        account = await self.get_account(account_id, user_id)
        
        # Check if there are expenses using this account
        from ..models.expense import ExpenseTable
        expense_count = self.db.query(ExpenseTable).filter(
            ExpenseTable.account_id == account_id
        ).count()
        
        if expense_count > 0:
            raise BusinessLogicError(
                f"Cannot delete account. It is used by {expense_count} expenses."
            )
        
        # Check if there are payment methods linked to this account
        payment_method_count = self.db.query(PaymentMethodTable).filter(
            PaymentMethodTable.account_id == account_id
        ).count()
        
        if payment_method_count > 0:
            raise BusinessLogicError(
                f"Cannot delete account. It has {payment_method_count} linked payment methods."
            )
        
        success = self.repository.delete_account(account_id, user_id)
        if not success:
            raise NotFoundError(f"Account {account_id} not found")
        
        # If this was the default, set another as default
        if account.is_default:
            remaining_accounts = self.repository.get_user_accounts(user_id, active_only=True)
            if remaining_accounts:
                self.repository.set_default_account(remaining_accounts[0].id, user_id)
        
        return success
    
    async def set_default_account(
        self, 
        account_id: UUID, 
        user_id: UUID
    ) -> bool:
        """Set an account as default."""
        success = self.repository.set_default_account(account_id, user_id)
        if not success:
            raise NotFoundError(f"Account {account_id} not found")
        
        return success
    
    async def get_default_account(self, user_id: UUID) -> Optional[AccountTable]:
        """Get the default account for a user."""
        return self.repository.get_default_account(user_id)
    
    # ===== BALANCE MANAGEMENT =====
    
    async def update_account_balance(
        self, 
        account_id: UUID, 
        user_id: UUID, 
        new_balance: Decimal, 
        notes: Optional[str] = None
    ) -> bool:
        """Update account balance manually."""
        # Verify account ownership
        account = await self.get_account(account_id, user_id)
        
        if not account.track_balance:
            raise BusinessLogicError("Balance tracking is disabled for this account")
        
        success = self.repository.update_account_balance(
            account_id, new_balance, "manual_adjustment", None, notes
        )
        
        return success
    
    async def process_expense_balance_update(
        self, 
        account_id: UUID, 
        expense_amount: Decimal, 
        expense_id: UUID
    ) -> bool:
        """Update account balance when an expense is created."""
        account = self.repository.db.query(AccountTable).filter(
            AccountTable.id == account_id
        ).first()
        
        if not account or not account.auto_update_balance:
            return False
        
        # For most accounts, expenses reduce the balance
        # For credit accounts, expenses increase the balance (more debt)
        if account.is_credit_account:
            balance_change = expense_amount  # Increase debt
        else:
            balance_change = -expense_amount  # Decrease available funds
        
        success = self.repository.adjust_account_balance(
            account_id,
            balance_change,
            "expense",
            expense_id,
            f"Expense: ${expense_amount}"
        )
        
        return success
    
    async def get_account_balance_history(
        self, 
        account_id: UUID, 
        user_id: UUID, 
        limit: Optional[int] = None
    ) -> List[AccountBalanceHistory]:
        """Get balance history for an account."""
        # Verify account ownership
        await self.get_account(account_id, user_id)
        
        return self.repository.get_account_balance_history(account_id, user_id, limit)
    
    # ===== ACCOUNT TRANSFERS =====
    
    async def create_transfer(
        self,
        user_id: UUID,
        from_account_id: UUID,
        to_account_id: UUID,
        amount: Decimal,
        description: Optional[str] = None
    ) -> AccountTransfer:
        """Create a transfer between accounts."""
        # Validate transfer
        if from_account_id == to_account_id:
            raise ValidationError("Cannot transfer to the same account")
        
        if amount <= 0:
            raise ValidationError("Transfer amount must be positive")
        
        # Verify account ownership
        from_account = await self.get_account(from_account_id, user_id)
        to_account = await self.get_account(to_account_id, user_id)
        
        # Check if from_account has sufficient balance (for non-credit accounts)
        if not from_account.is_credit_account and from_account.track_balance:
            if from_account.current_balance < amount:
                raise BusinessLogicError(
                    f"Insufficient balance. Available: ${from_account.current_balance}, Required: ${amount}"
                )
        
        # Create transfer
        transfer = self.repository.create_transfer(
            user_id, from_account_id, to_account_id, amount, description
        )
        
        if not transfer:
            raise BusinessLogicError("Failed to create transfer")
        
        return transfer
    
    async def get_user_transfers(
        self, 
        user_id: UUID, 
        limit: Optional[int] = None
    ) -> List[AccountTransfer]:
        """Get transfers for a user."""
        return self.repository.get_user_transfers(user_id, limit)
    
    # ===== ANALYTICS AND REPORTING =====
    
    async def get_account_summary(self, user_id: UUID) -> Dict[str, Any]:
        """Get account summary for a user."""
        return self.repository.get_account_summary(user_id)
    
    async def get_account_spending_analysis(
        self, 
        account_id: UUID, 
        user_id: UUID, 
        days: int = 30
    ) -> Dict[str, Any]:
        """Get spending analysis for a specific account."""
        # Verify account ownership
        await self.get_account(account_id, user_id)
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        return self.repository.get_account_spending_analysis(
            account_id, user_id, start_date, end_date
        )
    
    async def get_cash_balance_warnings(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get accounts with low cash balance warnings."""
        cash_accounts = self.repository.get_user_accounts(
            user_id, active_only=True, account_type=AccountType.CASH
        )
        
        warnings = []
        for account in cash_accounts:
            if account.is_low_balance:
                warnings.append({
                    'account_id': str(account.id),
                    'account_name': account.name,
                    'current_balance': account.current_balance,
                    'warning_threshold': account.low_balance_warning,
                    'severity': 'critical' if account.current_balance <= 0 else 'warning'
                })
        
        return warnings
    
    # ===== VALIDATION METHODS =====
    
    def _validate_account_data(self, account_data: Dict[str, Any]) -> None:
        """Validate account creation data."""
        required_fields = ['name', 'type']
        for field in required_fields:
            if field not in account_data:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate account type
        if account_data['type'] not in AccountType:
            raise ValidationError(f"Invalid account type: {account_data['type']}")
        
        # Validate name length
        if len(account_data['name']) > 100:
            raise ValidationError("Account name cannot exceed 100 characters")
        
        # Validate balance fields
        if 'current_balance' in account_data:
            try:
                Decimal(str(account_data['current_balance']))
            except:
                raise ValidationError("Invalid current balance format")
        
        if 'credit_limit' in account_data and account_data['credit_limit'] is not None:
            try:
                limit = Decimal(str(account_data['credit_limit']))
                if limit < 0:
                    raise ValidationError("Credit limit cannot be negative")
            except:
                raise ValidationError("Invalid credit limit format")
        
        # Validate account number last four
        if 'account_number_last_four' in account_data:
            last_four = account_data['account_number_last_four']
            if last_four and (not last_four.isdigit() or len(last_four) != 4):
                raise ValidationError("Account number last four must be exactly 4 digits")
    
    def _validate_account_update_data(self, update_data: Dict[str, Any]) -> None:
        """Validate account update data."""
        # Validate account type if provided
        if 'type' in update_data and update_data['type'] not in AccountType:
            raise ValidationError(f"Invalid account type: {update_data['type']}")
        
        # Validate name length if provided
        if 'name' in update_data and len(update_data['name']) > 100:
            raise ValidationError("Account name cannot exceed 100 characters")
        
        # Validate balance fields
        if 'current_balance' in update_data:
            try:
                Decimal(str(update_data['current_balance']))
            except:
                raise ValidationError("Invalid current balance format")
        
        if 'credit_limit' in update_data and update_data['credit_limit'] is not None:
            try:
                limit = Decimal(str(update_data['credit_limit']))
                if limit < 0:
                    raise ValidationError("Credit limit cannot be negative")
            except:
                raise ValidationError("Invalid credit limit format")
        
        # Validate account number last four
        if 'account_number_last_four' in update_data:
            last_four = update_data['account_number_last_four']
            if last_four and (not last_four.isdigit() or len(last_four) != 4):
                raise ValidationError("Account number last four must be exactly 4 digits")