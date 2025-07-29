"""
Account repository for managing financial accounts and balances.
"""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.orm import selectinload

from app.models.account import (
    AccountTable, AccountBalanceTable, PaymentMethodTable,
    AccountType, AccountStatus, CurrencyCode
)

logger = logging.getLogger(__name__)


class AccountRepository:
    """Repository for account data access operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ===== ACCOUNT CRUD OPERATIONS =====
    
    async def create_account(self, account_data: Dict[str, Any]) -> AccountTable:
        """Create a new account."""
        account = AccountTable(**account_data)
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        return account
    
    async def get_account_by_id(self, account_id: UUID, user_id: UUID) -> Optional[AccountTable]:
        """Get account by ID for a specific user."""
        result = await self.db.execute(
            self.db.query(AccountTable).filter(
                AccountTable.id == account_id,
                AccountTable.user_id == user_id
            ).options(
                selectinload(AccountTable.payment_methods),
                selectinload(AccountTable.balance_history)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_user_accounts(
        self, 
        user_id: UUID, 
        account_type: Optional[AccountType] = None,
        status: Optional[AccountStatus] = None,
        active_only: bool = False
    ) -> List[AccountTable]:
        """Get all accounts for a user with optional filters."""
        query = self.db.query(AccountTable).filter(AccountTable.user_id == user_id)
        
        if account_type:
            query = query.filter(AccountTable.account_type == account_type)
        
        if status:
            query = query.filter(AccountTable.status == status)
        
        if active_only:
            query = query.filter(AccountTable.status == AccountStatus.ACTIVE)
        
        result = await self.db.execute(
            query.options(
                selectinload(AccountTable.payment_methods),
                selectinload(AccountTable.balance_history)
            ).order_by(asc(AccountTable.sort_order), asc(AccountTable.name))
        )
        return result.scalars().all()
    
    async def update_account(
        self, 
        account_id: UUID, 
        user_id: UUID, 
        update_data: Dict[str, Any]
    ) -> Optional[AccountTable]:
        """Update an account."""
        account = await self.get_account_by_id(account_id, user_id)
        if not account:
            return None
        
        for key, value in update_data.items():
            if hasattr(account, key):
                setattr(account, key, value)
        
        account.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(account)
        return account
    
    async def delete_account(self, account_id: UUID, user_id: UUID) -> bool:
        """Delete an account."""
        account = await self.get_account_by_id(account_id, user_id)
        if not account:
            return False
        
        await self.db.delete(account)
        await self.db.commit()
        return True
    
    # ===== BALANCE MANAGEMENT =====
    
    async def create_balance_record(
        self, 
        balance_data: Dict[str, Any]
    ) -> AccountBalanceTable:
        """Create a new balance record."""
        balance = AccountBalanceTable(**balance_data)
        self.db.add(balance)
        await self.db.commit()
        await self.db.refresh(balance)
        return balance
    
    async def get_account_balance_history(
        self, 
        account_id: UUID, 
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None
    ) -> List[AccountBalanceTable]:
        """Get balance history for an account."""
        query = self.db.query(AccountBalanceTable).filter(
            AccountBalanceTable.account_id == account_id,
            AccountBalanceTable.user_id == user_id
        )
        
        if start_date:
            query = query.filter(AccountBalanceTable.balance_date >= start_date)
        
        if end_date:
            query = query.filter(AccountBalanceTable.balance_date <= end_date)
        
        query = query.order_by(desc(AccountBalanceTable.balance_date))
        
        if limit:
            query = query.limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_latest_balance(
        self, 
        account_id: UUID, 
        user_id: UUID
    ) -> Optional[AccountBalanceTable]:
        """Get the most recent balance record for an account."""
        result = await self.db.execute(
            self.db.query(AccountBalanceTable).filter(
                AccountBalanceTable.account_id == account_id,
                AccountBalanceTable.user_id == user_id
            ).order_by(desc(AccountBalanceTable.balance_date)).limit(1)
        )
        return result.scalar_one_or_none()
    
    async def update_account_balance(
        self, 
        account_id: UUID, 
        user_id: UUID, 
        new_balance: Decimal,
        available_balance: Optional[Decimal] = None,
        change_reason: Optional[str] = None,
        source: str = "manual"
    ) -> AccountBalanceTable:
        """Update account balance and create history record."""
        
        # Get current balance
        current_balance_record = await self.get_latest_balance(account_id, user_id)
        current_balance = current_balance_record.balance_amount if current_balance_record else Decimal('0.00')
        
        # Calculate change
        change_amount = new_balance - current_balance
        
        # Create balance history record
        balance_data = {
            "account_id": account_id,
            "user_id": user_id,
            "balance_date": date.today(),
            "balance_amount": new_balance,
            "available_amount": available_balance,
            "change_amount": change_amount,
            "change_reason": change_reason,
            "source": source
        }
        
        balance_record = await self.create_balance_record(balance_data)
        
        # Update account current balance
        await self.update_account(account_id, user_id, {
            "current_balance": new_balance,
            "available_balance": available_balance
        })
        
        return balance_record
    
    # ===== PAYMENT METHOD OPERATIONS =====
    
    async def create_payment_method(
        self, 
        payment_method_data: Dict[str, Any]
    ) -> PaymentMethodTable:
        """Create a new payment method."""
        payment_method = PaymentMethodTable(**payment_method_data)
        self.db.add(payment_method)
        await self.db.commit()
        await self.db.refresh(payment_method)
        return payment_method
    
    async def get_payment_method_by_id(
        self, 
        payment_method_id: UUID, 
        user_id: UUID
    ) -> Optional[PaymentMethodTable]:
        """Get payment method by ID for a specific user."""
        result = await self.db.execute(
            self.db.query(PaymentMethodTable).filter(
                PaymentMethodTable.id == payment_method_id,
                PaymentMethodTable.user_id == user_id
            ).options(selectinload(PaymentMethodTable.account))
        )
        return result.scalar_one_or_none()
    
    async def get_user_payment_methods(
        self, 
        user_id: UUID,
        account_id: Optional[UUID] = None,
        payment_type: Optional[str] = None,
        active_only: bool = False
    ) -> List[PaymentMethodTable]:
        """Get all payment methods for a user with optional filters."""
        query = self.db.query(PaymentMethodTable).filter(PaymentMethodTable.user_id == user_id)
        
        if account_id:
            query = query.filter(PaymentMethodTable.account_id == account_id)
        
        if payment_type:
            query = query.filter(PaymentMethodTable.type == payment_type)
        
        if active_only:
            query = query.filter(PaymentMethodTable.is_active == True)
        
        result = await self.db.execute(
            query.options(selectinload(PaymentMethodTable.account))
            .order_by(desc(PaymentMethodTable.is_default), asc(PaymentMethodTable.name))
        )
        return result.scalars().all()
    
    async def update_payment_method(
        self, 
        payment_method_id: UUID, 
        user_id: UUID, 
        update_data: Dict[str, Any]
    ) -> Optional[PaymentMethodTable]:
        """Update a payment method."""
        payment_method = await self.get_payment_method_by_id(payment_method_id, user_id)
        if not payment_method:
            return None
        
        for key, value in update_data.items():
            if hasattr(payment_method, key):
                setattr(payment_method, key, value)
        
        payment_method.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(payment_method)
        return payment_method
    
    async def delete_payment_method(
        self, 
        payment_method_id: UUID, 
        user_id: UUID
    ) -> bool:
        """Delete a payment method."""
        payment_method = await self.get_payment_method_by_id(payment_method_id, user_id)
        if not payment_method:
            return False
        
        await self.db.delete(payment_method)
        await self.db.commit()
        return True
    
    async def set_default_payment_method(
        self, 
        payment_method_id: UUID, 
        user_id: UUID
    ) -> bool:
        """Set a payment method as default (and unset others)."""
        
        # First, unset all other default payment methods for the user
        await self.db.execute(
            self.db.query(PaymentMethodTable).filter(
                PaymentMethodTable.user_id == user_id,
                PaymentMethodTable.is_default == True
            ).update({"is_default": False})
        )
        
        # Set the specified payment method as default
        payment_method = await self.get_payment_method_by_id(payment_method_id, user_id)
        if not payment_method:
            return False
        
        payment_method.is_default = True
        await self.db.commit()
        return True
    
    # ===== ANALYTICS AND REPORTING =====
    
    async def get_account_summary(
        self, 
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get account summary with spending totals."""
        
        accounts = await self.get_user_accounts(user_id, active_only=True)
        
        summary = {
            "total_accounts": len(accounts),
            "accounts_by_type": {},
            "total_balance": Decimal('0.00'),
            "total_available_credit": Decimal('0.00'),
            "accounts": []
        }
        
        # Group accounts by type
        for account in accounts:
            account_type = account.account_type.value
            if account_type not in summary["accounts_by_type"]:
                summary["accounts_by_type"][account_type] = {
                    "count": 0,
                    "total_balance": Decimal('0.00')
                }
            
            summary["accounts_by_type"][account_type]["count"] += 1
            
            if account.current_balance:
                summary["accounts_by_type"][account_type]["total_balance"] += account.current_balance
                summary["total_balance"] += account.current_balance
            
            if account.available_credit:
                summary["total_available_credit"] += account.available_credit
            
            # Get spending for this account (if date range provided)
            account_spending = Decimal('0.00')
            if start_date and end_date:
                # This would require joining with expenses table
                # For now, we'll leave it as 0 and implement in service layer
                pass
            
            summary["accounts"].append({
                "id": account.id,
                "name": account.name,
                "type": account.account_type.value,
                "current_balance": account.current_balance,
                "available_credit": account.available_credit,
                "spending_in_period": account_spending
            })
        
        return summary
    
    async def get_payment_method_spending(
        self, 
        user_id: UUID,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get spending totals by payment method."""
        
        # This would require joining with expenses table
        # For now, return empty list and implement in service layer
        return []
    
    async def get_balance_trends(
        self, 
        account_id: UUID, 
        user_id: UUID,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get balance trends for an account."""
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        balance_history = await self.get_account_balance_history(
            account_id, user_id, start_date, end_date
        )
        
        trends = []
        for balance in balance_history:
            trends.append({
                "date": balance.balance_date,
                "balance": balance.balance_amount,
                "available": balance.available_amount,
                "change": balance.change_amount,
                "reason": balance.change_reason
            })
        
        return trends
    
    # ===== CASH BALANCE TRACKING =====
    
    async def get_cash_accounts(self, user_id: UUID) -> List[AccountTable]:
        """Get all cash accounts for a user."""
        return await self.get_user_accounts(
            user_id, 
            account_type=AccountType.CASH, 
            active_only=True
        )
    
    async def update_cash_balance_from_expense(
        self, 
        user_id: UUID, 
        expense_amount: Decimal,
        payment_method_id: UUID,
        operation: str = "subtract"  # "subtract" or "add"
    ) -> Optional[AccountBalanceTable]:
        """Update cash balance when a cash expense is recorded."""
        
        # Get payment method and associated account
        payment_method = await self.get_payment_method_by_id(payment_method_id, user_id)
        if not payment_method or not payment_method.account_id:
            return None
        
        account = await self.get_account_by_id(payment_method.account_id, user_id)
        if not account or account.account_type != AccountType.CASH:
            return None
        
        if not account.track_balance or not account.auto_update_balance:
            return None
        
        # Calculate new balance
        current_balance = account.current_balance or Decimal('0.00')
        
        if operation == "subtract":
            new_balance = current_balance - expense_amount
            change_reason = f"Expense: -{expense_amount}"
        else:  # add
            new_balance = current_balance + expense_amount
            change_reason = f"Refund: +{expense_amount}"
        
        # Update balance
        return await self.update_account_balance(
            account.id,
            user_id,
            new_balance,
            change_reason=change_reason,
            source="transaction"
        )
    
    # ===== UTILITY METHODS =====
    
    async def get_account_types_summary(self, user_id: UUID) -> Dict[str, int]:
        """Get count of accounts by type."""
        
        result = await self.db.execute(
            self.db.query(
                AccountTable.account_type,
                func.count(AccountTable.id).label('count')
            ).filter(
                AccountTable.user_id == user_id,
                AccountTable.status == AccountStatus.ACTIVE
            ).group_by(AccountTable.account_type)
        )
        
        summary = {}
        for row in result:
            summary[row.account_type.value] = row.count
        
        return summary
    
    async def get_expired_payment_methods(self, user_id: UUID) -> List[PaymentMethodTable]:
        """Get payment methods that are expired."""
        
        current_date = date.today()
        current_month = current_date.strftime("%m")
        current_year = current_date.strftime("%Y")
        
        result = await self.db.execute(
            self.db.query(PaymentMethodTable).filter(
                PaymentMethodTable.user_id == user_id,
                PaymentMethodTable.is_active == True,
                PaymentMethodTable.expiry_year.isnot(None),
                PaymentMethodTable.expiry_month.isnot(None),
                or_(
                    PaymentMethodTable.expiry_year < current_year,
                    and_(
                        PaymentMethodTable.expiry_year == current_year,
                        PaymentMethodTable.expiry_month < current_month
                    )
                )
            ).options(selectinload(PaymentMethodTable.account))
        )
        
        return result.scalars().all()


# Create repository instance function
def get_account_repository(db: AsyncSession) -> AccountRepository:
    """Get account repository instance."""
    return AccountRepository(db)