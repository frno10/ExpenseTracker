"""Add recurring expenses tables

Revision ID: 003
Revises: 002
Create Date: 2025-01-28 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create recurrence frequency enum
    recurrence_frequency_enum = postgresql.ENUM(
        'daily', 'weekly', 'biweekly', 'monthly', 'quarterly', 'semiannually', 'annually',
        name='recurrencefrequency'
    )
    recurrence_frequency_enum.create(op.get_bind())
    
    # Create recurrence status enum
    recurrence_status_enum = postgresql.ENUM(
        'active', 'paused', 'completed', 'cancelled',
        name='recurrencestatus'
    )
    recurrence_status_enum.create(op.get_bind())
    
    # Create recurring_expenses table
    op.create_table('recurring_expenses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('merchant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('payment_method_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('frequency', recurrence_frequency_enum, nullable=False),
        sa.Column('interval', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('next_due_date', sa.Date(), nullable=False),
        sa.Column('max_occurrences', sa.Integer(), nullable=True),
        sa.Column('current_occurrences', sa.Integer(), nullable=False),
        sa.Column('status', recurrence_status_enum, nullable=False),
        sa.Column('is_auto_create', sa.Boolean(), nullable=False),
        sa.Column('day_of_month', sa.Integer(), nullable=True),
        sa.Column('day_of_week', sa.Integer(), nullable=True),
        sa.Column('month_of_year', sa.Integer(), nullable=True),
        sa.Column('notify_before_days', sa.Integer(), nullable=False),
        sa.Column('last_notification_sent', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_processed', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id'], ),
        sa.ForeignKeyConstraint(['payment_method_id'], ['payment_methods.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recurring_expenses_user_id'), 'recurring_expenses', ['user_id'], unique=False)
    op.create_index(op.f('ix_recurring_expenses_status'), 'recurring_expenses', ['status'], unique=False)
    op.create_index(op.f('ix_recurring_expenses_next_due_date'), 'recurring_expenses', ['next_due_date'], unique=False)
    op.create_index(op.f('ix_recurring_expenses_frequency'), 'recurring_expenses', ['frequency'], unique=False)
    
    # Create recurring_expense_history table
    op.create_table('recurring_expense_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recurring_expense_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('processed_date', sa.DateTime(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('expense_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('was_created', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('processing_method', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['expense_id'], ['expenses.id'], ),
        sa.ForeignKeyConstraint(['recurring_expense_id'], ['recurring_expenses.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recurring_expense_history_recurring_expense_id'), 'recurring_expense_history', ['recurring_expense_id'], unique=False)
    op.create_index(op.f('ix_recurring_expense_history_processed_date'), 'recurring_expense_history', ['processed_date'], unique=False)
    op.create_index(op.f('ix_recurring_expense_history_due_date'), 'recurring_expense_history', ['due_date'], unique=False)
    
    # Create recurring_expense_notifications table
    op.create_table('recurring_expense_notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('recurring_expense_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['recurring_expense_id'], ['recurring_expenses.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recurring_expense_notifications_user_id'), 'recurring_expense_notifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_recurring_expense_notifications_sent_at'), 'recurring_expense_notifications', ['sent_at'], unique=False)
    op.create_index(op.f('ix_recurring_expense_notifications_is_read'), 'recurring_expense_notifications', ['is_read'], unique=False)
    
    # Add recurring_expense_id column to expenses table
    op.add_column('expenses', sa.Column('recurring_expense_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_expenses_recurring_expense_id', 'expenses', 'recurring_expenses', ['recurring_expense_id'], ['id'])
    op.create_index(op.f('ix_expenses_recurring_expense_id'), 'expenses', ['recurring_expense_id'], unique=False)


def downgrade() -> None:
    # Remove recurring_expense_id from expenses table
    op.drop_index(op.f('ix_expenses_recurring_expense_id'), table_name='expenses')
    op.drop_constraint('fk_expenses_recurring_expense_id', 'expenses', type_='foreignkey')
    op.drop_column('expenses', 'recurring_expense_id')
    
    # Drop recurring_expense_notifications table
    op.drop_index(op.f('ix_recurring_expense_notifications_is_read'), table_name='recurring_expense_notifications')
    op.drop_index(op.f('ix_recurring_expense_notifications_sent_at'), table_name='recurring_expense_notifications')
    op.drop_index(op.f('ix_recurring_expense_notifications_user_id'), table_name='recurring_expense_notifications')
    op.drop_table('recurring_expense_notifications')
    
    # Drop recurring_expense_history table
    op.drop_index(op.f('ix_recurring_expense_history_due_date'), table_name='recurring_expense_history')
    op.drop_index(op.f('ix_recurring_expense_history_processed_date'), table_name='recurring_expense_history')
    op.drop_index(op.f('ix_recurring_expense_history_recurring_expense_id'), table_name='recurring_expense_history')
    op.drop_table('recurring_expense_history')
    
    # Drop recurring_expenses table
    op.drop_index(op.f('ix_recurring_expenses_frequency'), table_name='recurring_expenses')
    op.drop_index(op.f('ix_recurring_expenses_next_due_date'), table_name='recurring_expenses')
    op.drop_index(op.f('ix_recurring_expenses_status'), table_name='recurring_expenses')
    op.drop_index(op.f('ix_recurring_expenses_user_id'), table_name='recurring_expenses')
    op.drop_table('recurring_expenses')
    
    # Drop enums
    op.execute('DROP TYPE recurrencestatus')
    op.execute('DROP TYPE recurrencefrequency')