from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, validator

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.user import User
from ..models.payment_method import PaymentMethodType, AccountType
from ..services.payment_method_service import PaymentMethodService, AccountService
from ..core.exceptions import ValidationError, NotFoundError, BusinessLogicError

router = APIRouter(prefix="/payment-methods", tags=["payment-methods"])


# ===== PYDANTIC MODELS =====

class PaymentMethodCreate(BaseModel):
    name: str = Field(..., max_length=100, description="Payment method name")
    type: PaymentMethodType = Field(..., description="Payment method type")
    description: Optional[str] = Field(None, description="Payment method description")
    account_id: Optional[UUID] = Field(None, description="Associated account ID")
    last_four_digits: Optional[str] = Field(None, description="Last 4 digits for cards")
    institution_name: Optional[str] = Field(None, max_length=100, description="Bank/Institution name")
    color: Optional[str] = Field(None, regex=r"^#[0-9A-Fa-f]{6}$", description="Hex color code")
    icon: Optional[str] = Field(None, max_length=50, description="Icon identifier")
    
    @validator('last_four_digits')
    def validate_last_four_digits(cls, v):
        if v and (not v.isdigit() or len(v) != 4):
            raise ValueError('Last four digits must be exactly 4 digits')
        return v


class PaymentMethodUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="Payment method name")
    description: Optional[str] = Field(None, description="Payment method description")
    account_id: Optional[UUID] = Field(None, description="Associated account ID")
    last_four_digits: Optional[str] = Field(None, description="Last 4 digits for cards")
    institution_name: Optional[str] = Field(None, max_length=100, description="Bank/Institution name")
    is_active: Optional[bool] = Field(None, description="Whether payment method is active")
    color: Optional[str] = Field(None, regex=r"^#[0-9A-Fa-f]{6}$", description="Hex color code")
    icon: Optional[str] = Field(None, max_length=50, description="Icon identifier")
    
    @validator('last_four_digits')
    def validate_last_four_digits(cls, v):
        if v and (not v.isdigit() or len(v) != 4):
            raise ValueError('Last four digits must be exactly 4 digits')
        return v


class PaymentMethodResponse(BaseModel):
    id: UUID
    name: str
    type: PaymentMethodType
    description: Optional[str]
    account_id: Optional[UUID]
    last_four_digits: Optional[str]
    institution_name: Optional[str]
    is_active: bool
    is_default: bool
    color: Optional[str]
    icon: Optional[str]
    display_name: str
    is_cash: bool
    is_card: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AccountCreate(BaseModel):
    name: str = Field(..., max_length=100, description="Account name")
    type: AccountType = Field(..., description="Account type")
    description: Optional[str] = Field(None, description="Account description")
    institution_name: Optional[str] = Field(None, max_length=100, description="Bank/Institution name")
    account_number_last_four: Optional[str] = Field(None, description="Last 4 digits of account number")
    current_balance: Optional[Decimal] = Field(Decimal('0.00'), description="Current account balance")
    available_balance: Optional[Decimal] = Field(None, description="Available balance (for credit accounts)")
    credit_limit: Optional[Decimal] = Field(None, description="Credit limit (for credit accounts)")
    track_balance: Optional[bool] = Field(True, description="Whether to track balance")
    auto_update_balance: Optional[bool] = Field(False, description="Auto-update balance from expenses")
    low_balance_warning: Optional[Decimal] = Field(None, description="Low balance warning threshold")
    color: Optional[str] = Field(None, regex=r"^#[0-9A-Fa-f]{6}$", description="Hex color code")
    icon: Optional[str] = Field(None, max_length=50, description="Icon identifier")
    
    @validator('account_number_last_four')
    def validate_account_number_last_four(cls, v):
        if v and (not v.isdigit() or len(v) != 4):
            raise ValueError('Account number last four must be exactly 4 digits')
        return v
    
    @validator('credit_limit')
    def validate_credit_limit(cls, v):
        if v is not None and v < 0:
            raise ValueError('Credit limit cannot be negative')
        return v


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="Account name")
    description: Optional[str] = Field(None, description="Account description")
    institution_name: Optional[str] = Field(None, max_length=100, description="Bank/Institution name")
    account_number_last_four: Optional[str] = Field(None, description="Last 4 digits of account number")
    current_balance: Optional[Decimal] = Field(None, description="Current account balance")
    available_balance: Optional[Decimal] = Field(None, description="Available balance (for credit accounts)")
    credit_limit: Optional[Decimal] = Field(None, description="Credit limit (for credit accounts)")
    track_balance: Optional[bool] = Field(None, description="Whether to track balance")
    auto_update_balance: Optional[bool] = Field(None, description="Auto-update balance from expenses")
    low_balance_warning: Optional[Decimal] = Field(None, description="Low balance warning threshold")
    is_active: Optional[bool] = Field(None, description="Whether account is active")
    color: Optional[str] = Field(None, regex=r"^#[0-9A-Fa-f]{6}$", description="Hex color code")
    icon: Optional[str] = Field(None, max_length=50, description="Icon identifier")
    
    @validator('account_number_last_four')
    def validate_account_number_last_four(cls, v):
        if v and (not v.isdigit() or len(v) != 4):
            raise ValueError('Account number last four must be exactly 4 digits')
        return v
    
    @validator('credit_limit')
    def validate_credit_limit(cls, v):
        if v is not None and v < 0:
            raise ValueError('Credit limit cannot be negative')
        return v


class AccountResponse(BaseModel):
    id: UUID
    name: str
    type: AccountType
    description: Optional[str]
    institution_name: Optional[str]
    account_number_last_four: Optional[str]
    current_balance: Decimal
    available_balance: Optional[Decimal]
    credit_limit: Optional[Decimal]
    track_balance: bool
    auto_update_balance: bool
    low_balance_warning: Optional[Decimal]
    is_active: bool
    is_default: bool
    color: Optional[str]
    icon: Optional[str]
    display_name: str
    is_cash_account: bool
    is_credit_account: bool
    available_credit: Optional[Decimal]
    is_low_balance: bool
    utilization_percentage: Optional[float]
    last_balance_update: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TransferCreate(BaseModel):
    from_account_id: UUID = Field(..., description="Source account ID")
    to_account_id: UUID = Field(..., description="Destination account ID")
    amount: Decimal = Field(..., gt=0, description="Transfer amount")
    description: Optional[str] = Field(None, max_length=255, description="Transfer description")


class TransferResponse(BaseModel):
    id: UUID
    from_account_id: UUID
    to_account_id: UUID
    amount: Decimal
    description: Optional[str]
    transfer_date: datetime
    is_completed: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class BalanceUpdateRequest(BaseModel):
    new_balance: Decimal = Field(..., description="New account balance")
    notes: Optional[str] = Field(None, description="Notes about the balance update")


class BalanceHistoryResponse(BaseModel):
    id: UUID
    balance: Decimal
    previous_balance: Optional[Decimal]
    change_amount: Optional[Decimal]
    change_reason: str
    notes: Optional[str]
    recorded_at: datetime
    
    class Config:
        from_attributes = True


# ===== PAYMENT METHOD ENDPOINTS =====

@router.post("/", response_model=PaymentMethodResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_method(
    payment_method_data: PaymentMethodCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new payment method."""
    try:
        service = PaymentMethodService(db)
        payment_method = await service.create_payment_method(
            current_user.id, 
            payment_method_data.dict(exclude_unset=True)
        )
        return PaymentMethodResponse.from_orm(payment_method)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=List[PaymentMethodResponse])
async def get_payment_methods(
    active_only: bool = Query(False, description="Return only active payment methods"),
    payment_type: Optional[PaymentMethodType] = Query(None, description="Filter by payment method type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all payment methods for the current user."""
    try:
        service = PaymentMethodService(db)
        payment_methods = await service.get_user_payment_methods(
            current_user.id, active_only, payment_type
        )
        return [PaymentMethodResponse.from_orm(pm) for pm in payment_methods]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{payment_method_id}", response_model=PaymentMethodResponse)
async def get_payment_method(
    payment_method_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific payment method."""
    try:
        service = PaymentMethodService(db)
        payment_method = await service.get_payment_method(payment_method_id, current_user.id)
        return PaymentMethodResponse.from_orm(payment_method)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/{payment_method_id}", response_model=PaymentMethodResponse)
async def update_payment_method(
    payment_method_id: UUID,
    update_data: PaymentMethodUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a payment method."""
    try:
        service = PaymentMethodService(db)
        payment_method = await service.update_payment_method(
            payment_method_id, current_user.id, update_data.dict(exclude_unset=True)
        )
        return PaymentMethodResponse.from_orm(payment_method)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{payment_method_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_method(
    payment_method_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a payment method."""
    try:
        service = PaymentMethodService(db)
        await service.delete_payment_method(payment_method_id, current_user.id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{payment_method_id}/set-default", status_code=status.HTTP_200_OK)
async def set_default_payment_method(
    payment_method_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Set a payment method as default."""
    try:
        service = PaymentMethodService(db)
        await service.set_default_payment_method(payment_method_id, current_user.id)
        return {"message": "Payment method set as default"}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/default/current", response_model=Optional[PaymentMethodResponse])
async def get_default_payment_method(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the default payment method for the current user."""
    try:
        service = PaymentMethodService(db)
        payment_method = await service.get_default_payment_method(current_user.id)
        if payment_method:
            return PaymentMethodResponse.from_orm(payment_method)
        return None
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))