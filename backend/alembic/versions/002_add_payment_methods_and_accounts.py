"""Add payment methods and accounts tables

Revision ID: 002
Revises: 001
Create Date: 2025-01-28 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create payment method type enum
    payment_method_type_enum = postgresql.ENUM(
        'credit_card', 'debit_card', 'cash', 'bank_transfer', 'digital_wallet', 'check', 'other',
        name='paymentmethodtype'
    )
    payment_method_type_enum.create(op.get_bind())
    
    # Create account type enum
    account_type_enum = postgresql.ENUM(
        'checking', 'savings', 'credit_card', 'cash', 'investment', 'other',
        name='accounttype'
    )
    account_type_enum.create(op.get_bind())
    
    # Create accounts table
    op.create_table('accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', account_type_enum, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('institution_name', sa.String(length=100), nullable=True),
        sa.Column('account_number_last_four', sa.String(length=4), nullable=True),
        sa.Column('current_balance', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('available_balance', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('credit_limit', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('track_balance', sa.Boolean(), nullable=True),
        sa.Column('auto_update_balance', sa.Boolean(), nullable=True),
        sa.Column('last_balance_update', sa.DateTime(), nullable=True),
        sa.Column('low_balance_warning', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_accounts_user_id'), 'accounts', ['user_id'], unique=False)
    op.create_index(op.f('ix_accounts_type'), 'accounts', ['type'], unique=False)
    op.create_index(op.f('ix_accounts_is_active'), 'accounts', ['is_active'], unique=False)
    op.create_index(op.f('ix_accounts_is_default'), 'accounts', ['is_default'], unique=False)
    
    # Create payment_methods table
    op.create_table('payment_methods',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', payment_method_type_enum, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('last_four_digits', sa.String(length=4), nullable=True),
        sa.Column('institution_name', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_methods_user_id'), 'payment_methods', ['user_id'], unique=False)
    op.create_index(op.f('ix_payment_methods_type'), 'payment_methods', ['type'], unique=False)
    op.create_index(op.f('ix_payment_methods_is_active'), 'payment_methods', ['is_active'], unique=False)
    op.create_index(op.f('ix_payment_methods_is_default'), 'payment_methods', ['is_default'], unique=False)
    
    # Create account_balance_history table
    op.create_table('account_balance_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('balance', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('previous_balance', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('change_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('change_reason', sa.String(length=100), nullable=True),
        sa.Column('related_expense_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.ForeignKeyConstraint(['related_expense_id'], ['expenses.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_account_balance_history_account_id'), 'account_balance_history', ['account_id'], unique=False)
    op.create_index(op.f('ix_account_balance_history_recorded_at'), 'account_balance_history', ['recorded_at'], unique=False)
    
    # Create account_transfers table
    op.create_table('account_transfers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('from_account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('to_account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('transfer_date', sa.DateTime(), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['from_account_id'], ['accounts.id'], ),
        sa.ForeignKeyConstraint(['to_account_id'], ['accounts.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_account_transfers_user_id'), 'account_transfers', ['user_id'], unique=False)
    op.create_index(op.f('ix_account_transfers_transfer_date'), 'account_transfers', ['transfer_date'], unique=False)
    
    # Add account_id column to expenses table
    op.add_column('expenses', sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_expenses_account_id', 'expenses', 'accounts', ['account_id'], ['id'])
    op.create_index(op.f('ix_expenses_account_id'), 'expenses', ['account_id'], unique=False)


def downgrade() -> None:
    # Remove account_id from expenses table
    op.drop_index(op.f('ix_expenses_account_id'), table_name='expenses')
    op.drop_constraint('fk_expenses_account_id', 'expenses', type_='foreignkey')
    op.drop_column('expenses', 'account_id')
    
    # Drop account_transfers table
    op.drop_index(op.f('ix_account_transfers_transfer_date'), table_name='account_transfers')
    op.drop_index(op.f('ix_account_transfers_user_id'), table_name='account_transfers')
    op.drop_table('account_transfers')
    
    # Drop account_balance_history table
    op.drop_index(op.f('ix_account_balance_history_recorded_at'), table_name='account_balance_history')
    op.drop_index(op.f('ix_account_balance_history_account_id'), table_name='account_balance_history')
    op.drop_table('account_balance_history')
    
    # Drop payment_methods table
    op.drop_index(op.f('ix_payment_methods_is_default'), table_name='payment_methods')
    op.drop_index(op.f('ix_payment_methods_is_active'), table_name='payment_methods')
    op.drop_index(op.f('ix_payment_methods_type'), table_name='payment_methods')
    op.drop_index(op.f('ix_payment_methods_user_id'), table_name='payment_methods')
    op.drop_table('payment_methods')
    
    # Drop accounts table
    op.drop_index(op.f('ix_accounts_is_default'), table_name='accounts')
    op.drop_index(op.f('ix_accounts_is_active'), table_name='accounts')
    op.drop_index(op.f('ix_accounts_type'), table_name='accounts')
    op.drop_index(op.f('ix_accounts_user_id'), table_name='accounts')
    op.drop_table('accounts')
    
    # Drop enums
    op.execute('DROP TYPE accounttype')
    op.execute('DROP TYPE paymentmethodtype')