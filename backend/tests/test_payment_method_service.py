import pytest
from decimal import Decimal
from datetime import datetime, date, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch

from app.services.payment_method_service import PaymentMethodService, AccountService
from app.models.payment_method import (
    PaymentMethodTable, AccountTable, AccountBalanceHistory, AccountTransfer,
    PaymentMethodType, AccountType
)
from app.core.exceptions import ValidationError, NotFoundError, BusinessLogicError


class TestPaymentMethodService:
    """Test cases for PaymentMethodService."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def mock_repository(self):
        """Mock payment method repository."""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_db, mock_repository):
        """PaymentMethodService instance with mocked dependencies."""
        service = PaymentMethodService(mock_db)
        service.repository = mock_repository
        return service
    
    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID."""
        return uuid4()
    
    @pytest.fixture
    def sample_payment_method_data(self):
        """Sample payment method data."""
        return {
            'name': 'Chase Sapphire',
            'type': PaymentMethodType.CREDIT_CARD,
            'description': 'Primary credit card',
            'last_four_digits': '1234',
            'institution_name': 'Chase Bank'
        }
    
    @pytest.fixture
    def sample_payment_method(self, sample_user_id):
        """Sample payment method instance."""
        return PaymentMethodTable(
            id=uuid4(),
            user_id=sample_user_id,
            name='Chase Sapphire',
            type=PaymentMethodType.CREDIT_CARD,
            description='Primary credit card',
            last_four_digits='1234',
            institution_name='Chase Bank',
            is_active=True,
            is_default=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    # ===== CREATE PAYMENT METHOD TESTS =====
    
    @pytest.mark.asyncio
    async def test_create_payment_method_success(
        self, service, sample_user_id, sample_payment_method_data, sample_payment_method
    ):
        """Test successful payment method creation."""
        # Setup
        service.repository.get_user_payment_methods.return_value = []
        service.repository.create_payment_method.return_value = sample_payment_method
        
        # Execute
        result = await service.create_payment_method(sample_user_id, sample_payment_method_data)
        
        # Verify
        assert result == sample_payment_method
        service.repository.create_payment_method.assert_called_once()
        
        # Check that user_id was added and is_default was set for first payment method
        call_args = service.repository.create_payment_method.call_args[0][0]
        assert call_args['user_id'] == sample_user_id
        assert call_args['is_default'] == True
    
    @pytest.mark.asyncio
    async def test_create_payment_method_not_first_default(
        self, service, sample_user_id, sample_payment_method_data, sample_payment_method
    ):
        """Test payment method creation when not the first (shouldn't be default)."""
        # Setup - existing payment methods
        existing_method = Mock()
        service.repository.get_user_payment_methods.return_value = [existing_method]
        service.repository.create_payment_method.return_value = sample_payment_method
        
        # Execute
        await service.create_payment_method(sample_user_id, sample_payment_method_data)
        
        # Verify
        call_args = service.repository.create_payment_method.call_args[0][0]
        assert 'is_default' not in call_args or call_args.get('is_default') != True
    
    @pytest.mark.asyncio
    async def test_create_payment_method_validation_error(
        self, service, sample_user_id
    ):
        """Test payment method creation with invalid data."""
        # Setup - invalid data (missing required fields)
        invalid_data = {'description': 'Missing required fields'}
        
        # Execute & Verify
        with pytest.raises(ValidationError, match="Missing required field: name"):
            await service.create_payment_method(sample_user_id, invalid_data)
    
    @pytest.mark.asyncio
    async def test_create_payment_method_invalid_type(
        self, service, sample_user_id
    ):
        """Test payment method creation with invalid type."""
        # Setup
        invalid_data = {
            'name': 'Test Method',
            'type': 'invalid_type'
        }
        
        # Execute & Verify
        with pytest.raises(ValidationError, match="Invalid payment method type"):
            await service.create_payment_method(sample_user_id, invalid_data)
    
    @pytest.mark.asyncio
    async def test_create_payment_method_invalid_last_four(
        self, service, sample_user_id
    ):
        """Test payment method creation with invalid last four digits."""
        # Setup
        invalid_data = {
            'name': 'Test Method',
            'type': PaymentMethodType.CREDIT_CARD,
            'last_four_digits': '123'  # Should be 4 digits
        }
        
        # Execute & Verify
        with pytest.raises(ValidationError, match="Last four digits must be exactly 4 digits"):
            await service.create_payment_method(sample_user_id, invalid_data)
    
    # ===== GET PAYMENT METHOD TESTS =====
    
    @pytest.mark.asyncio
    async def test_get_payment_method_success(
        self, service, sample_user_id, sample_payment_method
    ):
        """Test successful payment method retrieval."""
        # Setup
        payment_method_id = sample_payment_method.id
        service.repository.get_payment_method_by_id.return_value = sample_payment_method
        
        # Execute
        result = await service.get_payment_method(payment_method_id, sample_user_id)
        
        # Verify
        assert result == sample_payment_method
        service.repository.get_payment_method_by_id.assert_called_once_with(
            payment_method_id, sample_user_id
        )
    
    @pytest.mark.asyncio
    async def test_get_payment_method_not_found(
        self, service, sample_user_id
    ):
        """Test payment method retrieval when not found."""
        # Setup
        payment_method_id = uuid4()
        service.repository.get_payment_method_by_id.return_value = None
        
        # Execute & Verify
        with pytest.raises(NotFoundError, match=f"Payment method {payment_method_id} not found"):
            await service.get_payment_method(payment_method_id, sample_user_id)
    
    # ===== UPDATE PAYMENT METHOD TESTS =====
    
    @pytest.mark.asyncio
    async def test_update_payment_method_success(
        self, service, sample_user_id, sample_payment_method
    ):
        """Test successful payment method update."""
        # Setup
        payment_method_id = sample_payment_method.id
        update_data = {'name': 'Updated Name', 'description': 'Updated description'}
        service.repository.update_payment_method.return_value = sample_payment_method
        
        # Execute
        result = await service.update_payment_method(payment_method_id, sample_user_id, update_data)
        
        # Verify
        assert result == sample_payment_method
        service.repository.update_payment_method.assert_called_once_with(
            payment_method_id, sample_user_id, update_data
        )
    
    @pytest.mark.asyncio
    async def test_update_payment_method_not_found(
        self, service, sample_user_id
    ):
        """Test payment method update when not found."""
        # Setup
        payment_method_id = uuid4()
        update_data = {'name': 'Updated Name'}
        service.repository.update_payment_method.return_value = None
        
        # Execute & Verify
        with pytest.raises(NotFoundError, match=f"Payment method {payment_method_id} not found"):
            await service.update_payment_method(payment_method_id, sample_user_id, update_data)
    
    # ===== DELETE PAYMENT METHOD TESTS =====
    
    @pytest.mark.asyncio
    async def test_delete_payment_method_success(
        self, service, sample_user_id, sample_payment_method
    ):
        """Test successful payment method deletion."""
        # Setup
        payment_method_id = sample_payment_method.id
        service.repository.get_payment_method_by_id.return_value = sample_payment_method
        service.db.query.return_value.filter.return_value.count.return_value = 0
        service.repository.delete_payment_method.return_value = True
        service.repository.get_user_payment_methods.return_value = []
        
        # Execute
        result = await service.delete_payment_method(payment_method_id, sample_user_id)
        
        # Verify
        assert result == True
        service.repository.delete_payment_method.assert_called_once_with(
            payment_method_id, sample_user_id
        )
    
    @pytest.mark.asyncio
    async def test_delete_payment_method_in_use(
        self, service, sample_user_id, sample_payment_method
    ):
        """Test payment method deletion when in use by expenses."""
        # Setup
        payment_method_id = sample_payment_method.id
        service.repository.get_payment_method_by_id.return_value = sample_payment_method
        service.db.query.return_value.filter.return_value.count.return_value = 5  # 5 expenses using it
        
        # Execute & Verify
        with pytest.raises(BusinessLogicError, match="Cannot delete payment method. It is used by 5 expenses."):
            await service.delete_payment_method(payment_method_id, sample_user_id)
    
    @pytest.mark.asyncio
    async def test_delete_default_payment_method_sets_new_default(
        self, service, sample_user_id, sample_payment_method
    ):
        """Test deleting default payment method sets another as default."""
        # Setup
        sample_payment_method.is_default = True
        payment_method_id = sample_payment_method.id
        service.repository.get_payment_method_by_id.return_value = sample_payment_method
        service.db.query.return_value.filter.return_value.count.return_value = 0
        service.repository.delete_payment_method.return_value = True
        
        # Mock remaining payment methods
        remaining_method = Mock()
        remaining_method.id = uuid4()
        service.repository.get_user_payment_methods.return_value = [remaining_method]
        
        # Execute
        await service.delete_payment_method(payment_method_id, sample_user_id)
        
        # Verify new default was set
        service.repository.set_default_payment_method.assert_called_once_with(
            remaining_method.id, sample_user_id
        )
    
    # ===== SET DEFAULT PAYMENT METHOD TESTS =====
    
    @pytest.mark.asyncio
    async def test_set_default_payment_method_success(
        self, service, sample_user_id
    ):
        """Test successful default payment method setting."""
        # Setup
        payment_method_id = uuid4()
        service.repository.set_default_payment_method.return_value = True
        
        # Execute
        result = await service.set_default_payment_method(payment_method_id, sample_user_id)
        
        # Verify
        assert result == True
        service.repository.set_default_payment_method.assert_called_once_with(
            payment_method_id, sample_user_id
        )
    
    @pytest.mark.asyncio
    async def test_set_default_payment_method_not_found(
        self, service, sample_user_id
    ):
        """Test setting default payment method when not found."""
        # Setup
        payment_method_id = uuid4()
        service.repository.set_default_payment_method.return_value = False
        
        # Execute & Verify
        with pytest.raises(NotFoundError, match=f"Payment method {payment_method_id} not found"):
            await service.set_default_payment_method(payment_method_id, sample_user_id)


class TestAccountService:
    """Test cases for AccountService."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def mock_repository(self):
        """Mock account repository."""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_db, mock_repository):
        """AccountService instance with mocked dependencies."""
        service = AccountService(mock_db)
        service.repository = mock_repository
        return service
    
    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID."""
        return uuid4()
    
    @pytest.fixture
    def sample_account_data(self):
        """Sample account data."""
        return {
            'name': 'Chase Checking',
            'type': AccountType.CHECKING,
            'description': 'Primary checking account',
            'institution_name': 'Chase Bank',
            'current_balance': Decimal('1000.00')
        }
    
    @pytest.fixture
    def sample_account(self, sample_user_id):
        """Sample account instance."""
        return AccountTable(
            id=uuid4(),
            user_id=sample_user_id,
            name='Chase Checking',
            type=AccountType.CHECKING,
            description='Primary checking account',
            institution_name='Chase Bank',
            current_balance=Decimal('1000.00'),
            track_balance=True,
            auto_update_balance=False,
            is_active=True,
            is_default=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    # ===== CREATE ACCOUNT TESTS =====
    
    @pytest.mark.asyncio
    async def test_create_account_success(
        self, service, sample_user_id, sample_account_data, sample_account
    ):
        """Test successful account creation."""
        # Setup
        service.repository.get_user_accounts.return_value = []
        service.repository.create_account.return_value = sample_account
        
        # Execute
        result = await service.create_account(sample_user_id, sample_account_data)
        
        # Verify
        assert result == sample_account
        service.repository.create_account.assert_called_once()
        
        # Check that user_id was added and defaults were set
        call_args = service.repository.create_account.call_args[0][0]
        assert call_args['user_id'] == sample_user_id
        assert call_args['is_default'] == True  # First account should be default
        assert call_args['track_balance'] == True  # Default value
    
    @pytest.mark.asyncio
    async def test_create_account_validation_error(
        self, service, sample_user_id
    ):
        """Test account creation with invalid data."""
        # Setup - invalid data (missing required fields)
        invalid_data = {'description': 'Missing required fields'}
        
        # Execute & Verify
        with pytest.raises(ValidationError, match="Missing required field: name"):
            await service.create_account(sample_user_id, invalid_data)
    
    @pytest.mark.asyncio
    async def test_create_account_invalid_type(
        self, service, sample_user_id
    ):
        """Test account creation with invalid type."""
        # Setup
        invalid_data = {
            'name': 'Test Account',
            'type': 'invalid_type'
        }
        
        # Execute & Verify
        with pytest.raises(ValidationError, match="Invalid account type"):
            await service.create_account(sample_user_id, invalid_data)
    
    # ===== BALANCE MANAGEMENT TESTS =====
    
    @pytest.mark.asyncio
    async def test_update_account_balance_success(
        self, service, sample_user_id, sample_account
    ):
        """Test successful account balance update."""
        # Setup
        account_id = sample_account.id
        new_balance = Decimal('1500.00')
        notes = "Manual adjustment"
        
        service.repository.get_account_by_id.return_value = sample_account
        service.repository.update_account_balance.return_value = True
        
        # Execute
        result = await service.update_account_balance(account_id, sample_user_id, new_balance, notes)
        
        # Verify
        assert result == True
        service.repository.update_account_balance.assert_called_once_with(
            account_id, new_balance, "manual_adjustment", None, notes
        )
    
    @pytest.mark.asyncio
    async def test_update_account_balance_tracking_disabled(
        self, service, sample_user_id, sample_account
    ):
        """Test account balance update when tracking is disabled."""
        # Setup
        sample_account.track_balance = False
        account_id = sample_account.id
        new_balance = Decimal('1500.00')
        
        service.repository.get_account_by_id.return_value = sample_account
        
        # Execute & Verify
        with pytest.raises(BusinessLogicError, match="Balance tracking is disabled for this account"):
            await service.update_account_balance(account_id, sample_user_id, new_balance)
    
    # ===== TRANSFER TESTS =====
    
    @pytest.mark.asyncio
    async def test_create_transfer_success(
        self, service, sample_user_id
    ):
        """Test successful transfer creation."""
        # Setup
        from_account_id = uuid4()
        to_account_id = uuid4()
        amount = Decimal('100.00')
        description = "Test transfer"
        
        from_account = Mock()
        from_account.is_credit_account = False
        from_account.track_balance = True
        from_account.current_balance = Decimal('500.00')
        
        to_account = Mock()
        to_account.name = "Savings Account"
        
        transfer = Mock()
        transfer.id = uuid4()
        
        service.repository.get_account_by_id.side_effect = [from_account, to_account]
        service.repository.create_transfer.return_value = transfer
        
        # Execute
        result = await service.create_transfer(
            sample_user_id, from_account_id, to_account_id, amount, description
        )
        
        # Verify
        assert result == transfer
        service.repository.create_transfer.assert_called_once_with(
            sample_user_id, from_account_id, to_account_id, amount, description
        )
    
    @pytest.mark.asyncio
    async def test_create_transfer_same_account(
        self, service, sample_user_id
    ):
        """Test transfer creation with same source and destination account."""
        # Setup
        account_id = uuid4()
        amount = Decimal('100.00')
        
        # Execute & Verify
        with pytest.raises(ValidationError, match="Cannot transfer to the same account"):
            await service.create_transfer(sample_user_id, account_id, account_id, amount)
    
    @pytest.mark.asyncio
    async def test_create_transfer_insufficient_balance(
        self, service, sample_user_id
    ):
        """Test transfer creation with insufficient balance."""
        # Setup
        from_account_id = uuid4()
        to_account_id = uuid4()
        amount = Decimal('1000.00')  # More than available
        
        from_account = Mock()
        from_account.is_credit_account = False
        from_account.track_balance = True
        from_account.current_balance = Decimal('500.00')  # Less than transfer amount
        
        to_account = Mock()
        
        service.repository.get_account_by_id.side_effect = [from_account, to_account]
        
        # Execute & Verify
        with pytest.raises(BusinessLogicError, match="Insufficient balance"):
            await service.create_transfer(sample_user_id, from_account_id, to_account_id, amount)
    
    # ===== ANALYTICS TESTS =====
    
    @pytest.mark.asyncio
    async def test_get_account_summary(
        self, service, sample_user_id
    ):
        """Test account summary retrieval."""
        # Setup
        summary_data = {
            'total_accounts': 3,
            'total_assets': Decimal('5000.00'),
            'total_liabilities': Decimal('1000.00'),
            'net_worth': Decimal('4000.00'),
            'cash_balance': Decimal('500.00'),
            'low_balance_accounts': 1,
            'low_balance_account_details': []
        }
        service.repository.get_account_summary.return_value = summary_data
        
        # Execute
        result = await service.get_account_summary(sample_user_id)
        
        # Verify
        assert result == summary_data
        service.repository.get_account_summary.assert_called_once_with(sample_user_id)
    
    @pytest.mark.asyncio
    async def test_get_cash_balance_warnings(
        self, service, sample_user_id
    ):
        """Test cash balance warnings retrieval."""
        # Setup
        cash_account = Mock()
        cash_account.id = uuid4()
        cash_account.name = "Cash Wallet"
        cash_account.current_balance = Decimal('10.00')
        cash_account.low_balance_warning = Decimal('50.00')
        cash_account.is_low_balance = True
        
        service.repository.get_user_accounts.return_value = [cash_account]
        
        # Execute
        result = await service.get_cash_balance_warnings(sample_user_id)
        
        # Verify
        assert len(result) == 1
        warning = result[0]
        assert warning['account_id'] == str(cash_account.id)
        assert warning['account_name'] == cash_account.name
        assert warning['current_balance'] == cash_account.current_balance
        assert warning['severity'] == 'warning'  # Balance > 0 but below threshold