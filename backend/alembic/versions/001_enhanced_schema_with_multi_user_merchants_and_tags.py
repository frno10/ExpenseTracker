"""Enhanced schema with multi-user, merchants, and tags

Revision ID: 001
Revises: 
Create Date: 2025-01-26 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='UTC'),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create categories table
    op.create_table('categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('color', sa.String(length=7), nullable=False, server_default='#6B7280'),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('parent_category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_custom', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['parent_category_id'], ['categories.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_categories_name'), 'categories', ['name'])
    op.create_index(op.f('ix_categories_user_id'), 'categories', ['user_id'])

    # Create merchants table
    op.create_table('merchants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('normalized_name', sa.String(length=255), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('merchant_identifier', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('default_category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['default_category_id'], ['categories.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_merchants_name'), 'merchants', ['name'])
    op.create_index(op.f('ix_merchants_normalized_name'), 'merchants', ['normalized_name'])
    op.create_index(op.f('ix_merchants_user_id'), 'merchants', ['user_id'])

    # Create tags table
    op.create_table('tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('color', sa.String(length=7), nullable=False, server_default='#6B7280'),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tags_name'), 'tags', ['name'])
    op.create_index(op.f('ix_tags_user_id'), 'tags', ['user_id'])

    # Create payment_methods table
    op.create_table('payment_methods',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.Enum('CASH', 'CREDIT_CARD', 'DEBIT_CARD', 'BANK_TRANSFER', 'CHECK', 'DIGITAL_WALLET', 'OTHER', name='paymenttype'), nullable=False),
        sa.Column('account_number', sa.String(length=50), nullable=True),
        sa.Column('institution', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_methods_name'), 'payment_methods', ['name'])
    op.create_index(op.f('ix_payment_methods_type'), 'payment_methods', ['type'])
    op.create_index(op.f('ix_payment_methods_user_id'), 'payment_methods', ['user_id'])

    # Create statement_imports table
    op.create_table('statement_imports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('bank_name', sa.String(length=100), nullable=True),
        sa.Column('account_number', sa.String(length=50), nullable=True),
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_end', sa.Date(), nullable=True),
        sa.Column('opening_balance', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('closing_balance', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('transaction_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('imported_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED', name='importstatus'), nullable=False, server_default='PENDING'),
        sa.Column('parsing_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_statement_imports_file_hash'), 'statement_imports', ['file_hash'], unique=True)
    op.create_index(op.f('ix_statement_imports_user_id'), 'statement_imports', ['user_id'])

    # Create budgets table
    op.create_table('budgets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('period', sa.Enum('MONTHLY', 'QUARTERLY', 'YEARLY', 'CUSTOM', name='budgetperiod'), nullable=False, server_default='MONTHLY'),
        sa.Column('total_limit', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_budgets_name'), 'budgets', ['name'])
    op.create_index(op.f('ix_budgets_start_date'), 'budgets', ['start_date'])
    op.create_index(op.f('ix_budgets_end_date'), 'budgets', ['end_date'])
    op.create_index(op.f('ix_budgets_user_id'), 'budgets', ['user_id'])

    # Create expenses table
    op.create_table('expenses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('expense_date', sa.Date(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_recurring', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('merchant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_method_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('statement_import_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ),
        sa.ForeignKeyConstraint(['payment_method_id'], ['payment_methods.id'], ),
        sa.ForeignKeyConstraint(['statement_import_id'], ['statement_imports.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_expenses_amount'), 'expenses', ['amount'])
    op.create_index(op.f('ix_expenses_category_id'), 'expenses', ['category_id'])
    op.create_index(op.f('ix_expenses_expense_date'), 'expenses', ['expense_date'])
    op.create_index(op.f('ix_expenses_merchant_id'), 'expenses', ['merchant_id'])
    op.create_index(op.f('ix_expenses_payment_method_id'), 'expenses', ['payment_method_id'])
    op.create_index(op.f('ix_expenses_statement_import_id'), 'expenses', ['statement_import_id'])
    op.create_index(op.f('ix_expenses_user_id'), 'expenses', ['user_id'])
    # Composite index for analytics
    op.create_index('ix_expenses_composite', 'expenses', ['expense_date', 'category_id', 'amount'])

    # Create attachments table
    op.create_table('attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('attachment_type', sa.Enum('RECEIPT', 'INVOICE', 'DOCUMENT', 'IMAGE', 'OTHER', name='attachmenttype'), nullable=False, server_default='RECEIPT'),
        sa.Column('expense_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['expense_id'], ['expenses.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attachments_expense_id'), 'attachments', ['expense_id'])
    op.create_index(op.f('ix_attachments_user_id'), 'attachments', ['user_id'])

    # Create category_budgets table
    op.create_table('category_budgets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('limit_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('spent_amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('budget_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['budget_id'], ['budgets.id'], ),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_category_budgets_budget_id'), 'category_budgets', ['budget_id'])
    op.create_index(op.f('ix_category_budgets_category_id'), 'category_budgets', ['category_id'])
    # Unique constraint for budget-category combination
    op.create_index('ix_category_budgets_composite', 'category_budgets', ['budget_id', 'category_id'], unique=True)

    # Create merchant_tags junction table
    op.create_table('merchant_tags',
        sa.Column('merchant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ),
        sa.PrimaryKeyConstraint('merchant_id', 'tag_id')
    )

    # Create expense_tags junction table
    op.create_table('expense_tags',
        sa.Column('expense_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['expense_id'], ['expenses.id'], ),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ),
        sa.PrimaryKeyConstraint('expense_id', 'tag_id')
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('expense_tags')
    op.drop_table('merchant_tags')
    op.drop_table('category_budgets')
    op.drop_table('attachments')
    op.drop_table('expenses')
    op.drop_table('budgets')
    op.drop_table('statement_imports')
    op.drop_table('payment_methods')
    op.drop_table('tags')
    op.drop_table('merchants')
    op.drop_table('categories')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS attachmenttype')
    op.execute('DROP TYPE IF EXISTS budgetperiod')
    op.execute('DROP TYPE IF EXISTS importstatus')
    op.execute('DROP TYPE IF EXISTS paymenttype')