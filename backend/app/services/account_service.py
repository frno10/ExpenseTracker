"""
Account service for managing financial accounts, payment methods, and balance tracking.
"""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import (
    AccountTable, AccountBalanceTable, PaymentMethodTable,
    AccountType, AccountStatus, CurrencyCode
)
from app.repositories.account_repository import get_account_repository
from app.core.exceptions import ValidationError, NotFoundError, BusinessLogicError

logger = logging.getLogger(__name__)


class AccountService:
    """Service for account and payment method management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = get_account_repository(db)
    
    # ===== ACCOUNT MANAGEMENT =====
    
    async def create_account(
        self,
        user_id: UUID,
        account_data: Dict[str, Any]
    ) -> AccountTable:
        """
        Create a new financial account.
        
        Args:
            user_id: User ID
            account_data: Account creation data
            
        Returns:
            Created account instance
        """
        logger.info(f"Creating account for user {user_id}: {account_data.get('name')}")
        
        # Validate account data
        self._validate_account_data(account_data)
        
        # Add user_id to account data
        account_data['user_id'] = user_id
        
        # Set default values
        if 'status' not in account_data:
            account_data['status'] = AccountStatus.ACTIVE
        
        if 'currency' not in account_data:
            account_data['currency'] = CurrencyCode.USD
        
        # Create account
        account = await self.repository.create_account(account_data)
        
        # Create initial balance record if balance is provided
        if account_data.get('current_balance') is not None:
            await self.repository.create_balance_record({
                'account_id': account.id,
                'user_id': user_id,
                'balance_date': date.today(),
                'balance_amount': account_data['current_balance'],
                'available_amount': account_data.get('available_balance'),
                'change_reason': 'Initial balance',
                'source': 'manual'
            })
        
        logger.info(f"Created account {account.id}")
        return account
    
    async def get_account(
        self,
        account_id: UUID,
        user_id: UUID
    ) -> AccountTable:
        """Get an account by ID."""
        account = await self.repository.get_account_by_id(account_id, user_id)
        if not account:
            raise NotFoundError(f"Account {account_id} not found")
        
        return account
    
    async def get_user_accounts(
        self,
        user_id: UUID,
        account_type: Optional[AccountType] = None,
        status: Optional[AccountStatus] = None,
        active_only: bool = False
    ) -> List[AccountTable]:
        """Get all accounts for a user."""
        return await self.repository.get_user_accounts(
            user_id, account_type, status, active_only
        )
    
    async def update_account(
        self,
        account_id: UUID,
        user_id: UUID,
        update_data: Dict[str, Any]
    ) -> AccountTable:
        """Update an account."""
        logger.info(f"Updating account {account_id} for user {user_id}")
        
        # Validate update data
        self._validate_account_update_data(update_data)
        
        # Update account
        account = await self.repository.update_account(account_id, user_id, update_data)
        if not account:
            raise NotFoundError(f"Account {account_id} not found")
        
        # If balance was updated, create balance history record
        if 'current_balance' in update_data:
            await self.repository.create_balance_record({
                'account_id': account_id,
                'user_id': user_id,
                'balance_date': date.today(),
                'balance_amount': update_data['current_balance'],
                'available_amount': update_data.get('available_balance'),
                'change_reason': 'Manual update',
                'source': 'manual'
            })
        
        logger.info(f"Updated account {account_id}")
        return account
    
    async def delete_account(
        self,
        account_id: UUID,
        user_id: UUID
    ) -> bool:
        """Delete an account."""
        logger.info(f"Deleting account {account_id} for user {user_id}")
        
        # Check if account has associated payment methods
        payment_methods = await self.repository.get_user_payment_methods(
            user_id, account_id=account_id
        )
        
        if payment_methods:
            raise BusinessLogicError(
                f"Cannot delete account with {len(payment_methods)} associated payment methods"
            )
        
        success = await self.repository.delete_account(account_id, user_id)
        if not success:
            raise NotFoundError(f"Account {account_id} not found")
        
        logger.info(f"Deleted account {account_id}")
        return success
    
    # ===== BALANCE MANAGEMENT =====
    
    async def update_account_balance(
        self,
        account_id: UUID,
        user_id: UUID,
        new_balance: Decimal,
        available_balance: Optional[Decimal] = None,
        change_reason: Optional[str] = None
    ) -> AccountBalanceTable:
        """Update account balance and create history record."""
        logger.info(f"Updating balance for account {account_id}: {new_balance}")
        
        # Verify account exists and belongs to user
        account = await self.get_account(account_id, user_id)
        
        # Update balance
        balance_record = await self.repository.update_account_balance(
            account_id, user_id, new_balance, available_balance, change_reason
        )
        
        logger.info(f"Updated balance for account {account_id}")
        return balance_record
    
    async def get_account_balance_history(
        self,
        account_id: UUID,
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None
    ) -> List[AccountBalanceTable]:
        """Get balance history for an account."""
        # Verify account exists and belongs to user
        await self.get_account(account_id, user_id)
        
        return await self.repository.get_account_balance_history(
            account_id, user_id, start_date, end_date, limit
        )
    
    async def get_balance_trends(
        self,
        account_id: UUID,
        user_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get balance trends and analysis."""
        # Verify account exists and belongs to user
        account = await self.get_account(account_id, user_id)
        
        # Get balance trends
        trends = await self.repository.get_balance_trends(account_id, user_id, days)
        
        if not trends:
            return {
                "account_id": account_id,
                "account_name": account.name,
                "period_days": days,
                "trends": [],
                "analysis": {
                    "trend_direction": "no_data",
                    "average_balance": Decimal('0.00'),
                    "balance_change": Decimal('0.00'),
                    "volatility": "unknown"
                }
            }
        
        # Calculate analysis
        balances = [trend["balance"] for trend in trends if trend["balance"]]
        
        if len(balances) >= 2:
            first_balance = balances[-1]  # Oldest (trends are desc order)
            last_balance = balances[0]    # Newest
            balance_change = last_balance - first_balance
            
            if balance_change > 0:
                trend_direction = "increasing"
            elif balance_change < 0:
                trend_direction = "decreasing"
            else:
                trend_direction = "stable"
            
            average_balance = sum(balances) / len(balances)
            
            # Calculate volatility (simplified standard deviation)
            variance = sum((b - average_balance) ** 2 for b in balances) / len(balances)
            std_dev = variance ** 0.5
            volatility = "high" if std_dev > average_balance * 0.1 else "low"
        else:
            trend_direction = "insufficient_data"
            average_balance = balances[0] if balances else Decimal('0.00')
            balance_change = Decimal('0.00')
            volatility = "unknown"
        
        return {
            "account_id": account_id,
            "account_name": account.name,
            "period_days": days,
            "trends": trends,
            "analysis": {
                "trend_direction": trend_direction,
                "average_balance": average_balance,
                "balance_change": balance_change,
                "volatility": volatility
            }
        }
    
    # ===== PAYMENT METHOD MANAGEMENT =====
    
    async def create_payment_method(
        self,
        user_id: UUID,
        payment_method_data: Dict[str, Any]
    ) -> PaymentMethodTable:
        """Create a new payment method."""
        logger.info(f"Creating payment method for user {user_id}: {payment_method_data.get('name')}")
        
        # Validate payment method data
        self._validate_payment_method_data(payment_method_data)
        
        # Add user_id to payment method data
        payment_method_data['user_id'] = user_id
        
        # If this is set as default, unset other defaults first
        if payment_method_data.get('is_default'):
            await self._unset_default_payment_methods(user_id)
        
        # Create payment method
        payment_method = await self.repository.create_payment_method(payment_method_data)
        
        logger.info(f"Created payment method {payment_method.id}")
        return payment_method
    
    async def get_payment_method(
        self,
        payment_method_id: UUID,
        user_id: UUID
    ) -> PaymentMethodTable:
        """Get a payment method by ID."""
        payment_method = await self.repository.get_payment_method_by_id(payment_method_id, user_id)
        if not payment_method:
            raise NotFoundError(f"Payment method {payment_method_id} not found")
        
        return payment_method
    
    async def get_user_payment_methods(
        self,
        user_id: UUID,
        account_id: Optional[UUID] = None,
        payment_type: Optional[str] = None,
        active_only: bool = False
    ) -> List[PaymentMethodTable]:
        """Get all payment methods for a user."""
        return await self.repository.get_user_payment_methods(
            user_id, account_id, payment_type, active_only
        )
    
    async def update_payment_method(
        self,
        payment_method_id: UUID,
        user_id: UUID,
        update_data: Dict[str, Any]
    ) -> PaymentMethodTable:
        """Update a payment method."""
        logger.info(f"Updating payment method {payment_method_id} for user {user_id}")
        
        # Validate update data
        self._validate_payment_method_update_data(update_data)
        
        # If this is being set as default, unset other defaults first
        if update_data.get('is_default'):
            await self._unset_default_payment_methods(user_id)
        
        # Update payment method
        payment_method = await self.repository.update_payment_method(
            payment_method_id, user_id, update_data
        )
        if not payment_method:
            raise NotFoundError(f"Payment method {payment_method_id} not found")
        
        logger.info(f"Updated payment method {payment_method_id}")
        return payment_method
    
    async def delete_payment_method(
        self,
        payment_method_id: UUID,
        user_id: UUID
    ) -> bool:
        """Delete a payment method."""
        logger.info(f"Deleting payment method {payment_method_id} for user {user_id}")
        
        # TODO: Check if payment method is used in expenses
        # This would require checking the expenses table
        
        success = await self.repository.delete_payment_method(payment_method_id, user_id)
        if not success:
            raise NotFoundError(f"Payment method {payment_method_id} not found")
        
        logger.info(f"Deleted payment method {payment_method_id}")
        return success
    
    async def set_default_payment_method(
        self,
        payment_method_id: UUID,
        user_id: UUID
    ) -> bool:
        """Set a payment method as default."""
        logger.info(f"Setting payment method {payment_method_id} as default for user {user_id}")
        
        success = await self.repository.set_default_payment_method(payment_method_id, user_id)
        if not success:
            raise NotFoundError(f"Payment method {payment_method_id} not found")
        
        logger.info(f"Set payment method {payment_method_id} as default")
        return success
    
    # ===== ANALYTICS AND REPORTING =====
    
    async def get_account_summary(
        self,
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get comprehensive account summary."""
        logger.info(f"Generating account summary for user {user_id}")
        
        summary = await self.repository.get_account_summary(user_id, start_date, end_date)
        
        # Add additional insights
        expired_payment_methods = await self.repository.get_expired_payment_methods(user_id)
        summary["expired_payment_methods"] = len(expired_payment_methods)
        
        # Add account type distribution
        account_types = await self.repository.get_account_types_summary(user_id)
        summary["account_type_distribution"] = account_types
        
        logger.info(f"Generated account summary for user {user_id}")
        return summary
    
    async def get_payment_method_analysis(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get payment method usage analysis."""
        logger.info(f"Analyzing payment method usage for user {user_id}")
        
        # Get payment methods
        payment_methods = await self.get_user_payment_methods(user_id, active_only=True)
        
        # TODO: Get spending by payment method from expenses
        # This would require joining with expenses table
        # For now, return basic structure
        
        analysis = {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": (end_date - start_date).days
            },
            "payment_methods": [],
            "summary": {
                "total_payment_methods": len(payment_methods),
                "active_payment_methods": len([pm for pm in payment_methods if pm.is_active]),
                "expired_payment_methods": len([pm for pm in payment_methods if pm.is_expired])
            }
        }
        
        for pm in payment_methods:
            analysis["payment_methods"].append({
                "id": pm.id,
                "name": pm.name,
                "type": pm.type,
                "is_default": pm.is_default,
                "is_expired": pm.is_expired,
                "account_name": pm.account.name if pm.account else None,
                "spending_amount": Decimal('0.00'),  # TODO: Calculate from expenses
                "transaction_count": 0  # TODO: Calculate from expenses
            })
        
        logger.info(f"Generated payment method analysis for user {user_id}")
        return analysis
    
    # ===== CASH BALANCE TRACKING =====
    
    async def get_cash_accounts(self, user_id: UUID) -> List[AccountTable]:
        """Get all cash accounts for a user."""
        return await self.repository.get_cash_accounts(user_id)
    
    async def update_cash_balance_from_expense(
        self,
        user_id: UUID,
        expense_amount: Decimal,
        payment_method_id: UUID,
        operation: str = "subtract"
    ) -> Optional[AccountBalanceTable]:
        """Update cash balance when a cash expense is recorded."""
        logger.info(f"Updating cash balance for user {user_id}: {operation} {expense_amount}")
        
        balance_record = await self.repository.update_cash_balance_from_expense(
            user_id, expense_amount, payment_method_id, operation
        )
        
        if balance_record:
            logger.info(f"Updated cash balance: new balance {balance_record.balance_amount}")
        
        return balance_record
    
    # ===== UTILITY METHODS =====
    
    async def get_expired_payment_methods(self, user_id: UUID) -> List[PaymentMethodTable]:
        """Get expired payment methods for a user."""
        return await self.repository.get_expired_payment_methods(user_id)
    
    async def get_default_payment_method(self, user_id: UUID) -> Optional[PaymentMethodTable]:
        """Get the default payment method for a user."""
        payment_methods = await self.get_user_payment_methods(user_id, active_only=True)
        
        for pm in payment_methods:
            if pm.is_default:
                return pm
        
        return None
    
    # ===== PRIVATE HELPER METHODS =====
    
    def _validate_account_data(self, account_data: Dict[str, Any]) -> None:
        """Validate account creation data."""
        required_fields = ['name', 'account_type']
        for field in required_fields:
            if field not in account_data:
                raise ValidationError(f"Missing required field: {field}")
        
        if not account_data['name'].strip():
            raise ValidationError("Account name cannot be empty")
        
        # Validate account type
        try:
            AccountType(account_data['account_type'])
        except ValueError:
            raise ValidationError(f"Invalid account type: {account_data['account_type']}")
        
        # Validate currency if provided
        if 'currency' in account_data:
            try:
                CurrencyCode(account_data['currency'])
            except ValueError:
                raise ValidationError(f"Invalid currency: {account_data['currency']}")
        
        # Validate balances
        for field in ['current_balance', 'available_balance', 'credit_limit']:
            if field in account_data and account_data[field] is not None:
                if not isinstance(account_data[field], (int, float, Decimal)):
                    raise ValidationError(f"{field} must be a number")
                if account_data[field] < 0 and field != 'current_balance':
                    raise ValidationError(f"{field} cannot be negative")
    
    def _validate_account_update_data(self, update_data: Dict[str, Any]) -> None:
        """Validate account update data."""
        if 'name' in update_data and not update_data['name'].strip():
            raise ValidationError("Account name cannot be empty")
        
        # Validate currency if provided
        if 'currency' in update_data:
            try:
                CurrencyCode(update_data['currency'])
            except ValueError:
                raise ValidationError(f"Invalid currency: {update_data['currency']}")
        
        # Validate balances
        for field in ['current_balance', 'available_balance', 'credit_limit']:
            if field in update_data and update_data[field] is not None:
                if not isinstance(update_data[field], (int, float, Decimal)):
                    raise ValidationError(f"{field} must be a number")
                if update_data[field] < 0 and field != 'current_balance':
                    raise ValidationError(f"{field} cannot be negative")
    
    def _validate_payment_method_data(self, payment_method_data: Dict[str, Any]) -> None:
        """Validate payment method creation data."""
        required_fields = ['name', 'type']
        for field in required_fields:
            if field not in payment_method_data:
                raise ValidationError(f"Missing required field: {field}")
        
        if not payment_method_data['name'].strip():
            raise ValidationError("Payment method name cannot be empty")
        
        # Validate expiry date if provided
        if 'expiry_month' in payment_method_data or 'expiry_year' in payment_method_data:
            month = payment_method_data.get('expiry_month')
            year = payment_method_data.get('expiry_year')
            
            if month and (not month.isdigit() or not (1 <= int(month) <= 12)):
                raise ValidationError("Invalid expiry month")
            
            if year and (not year.isdigit() or len(year) != 4):
                raise ValidationError("Invalid expiry year")
    
    def _validate_payment_method_update_data(self, update_data: Dict[str, Any]) -> None:
        """Validate payment method update data."""
        if 'name' in update_data and not update_data['name'].strip():
            raise ValidationError("Payment method name cannot be empty")
        
        # Validate expiry date if provided
        if 'expiry_month' in update_data:
            month = update_data['expiry_month']
            if month and (not month.isdigit() or not (1 <= int(month) <= 12)):
                raise ValidationError("Invalid expiry month")
        
        if 'expiry_year' in update_data:
            year = update_data['expiry_year']
            if year and (not year.isdigit() or len(year) != 4):
                raise ValidationError("Invalid expiry year")
    
    async def _unset_default_payment_methods(self, user_id: UUID) -> None:
        """Unset all default payment methods for a user."""
        payment_methods = await self.get_user_payment_methods(user_id)
        
        for pm in payment_methods:
            if pm.is_default:
                await self.repository.update_payment_method(
                    pm.id, user_id, {"is_default": False}
                )


# Create service instance function
def get_account_service(db: AsyncSession) -> AccountService:
    """Get account service instance."""
    return AccountService(db)