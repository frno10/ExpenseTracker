"""Add audit logs table

Revision ID: 004
Revises: 003
Create Date: 2025-01-29 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add audit logs table for security and compliance tracking."""
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, index=True),
        sa.Column('event_type', sa.String(50), nullable=False, index=True),
        sa.Column('severity', sa.String(20), nullable=False, default='low'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('session_id', sa.String(255), nullable=True, index=True),
        sa.Column('ip_address', sa.String(45), nullable=True, index=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('resource_type', sa.String(50), nullable=True, index=True),
        sa.Column('resource_id', sa.String(255), nullable=True, index=True),
        sa.Column('action', sa.String(50), nullable=True),
        sa.Column('details', postgresql.JSONB(), nullable=True),
        sa.Column('old_values', postgresql.JSONB(), nullable=True),
        sa.Column('new_values', postgresql.JSONB(), nullable=True),
        sa.Column('success', sa.Integer(), nullable=False, default=1),
        sa.Column('error_message', sa.Text(), nullable=True),
    )
    
    # Create indexes for better query performance
    op.create_index('idx_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('idx_audit_logs_event_type', 'audit_logs', ['event_type'])
    op.create_index('idx_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('idx_audit_logs_severity', 'audit_logs', ['severity'])
    op.create_index('idx_audit_logs_success', 'audit_logs', ['success'])
    
    # Create composite indexes for common queries
    op.create_index('idx_audit_logs_user_timestamp', 'audit_logs', ['user_id', 'timestamp'])
    op.create_index('idx_audit_logs_event_timestamp', 'audit_logs', ['event_type', 'timestamp'])
    
    # Add foreign key constraint to users table
    op.create_foreign_key(
        'fk_audit_logs_user_id',
        'audit_logs', 'users',
        ['user_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Remove audit logs table."""
    
    # Drop foreign key constraint
    op.drop_constraint('fk_audit_logs_user_id', 'audit_logs', type_='foreignkey')
    
    # Drop indexes
    op.drop_index('idx_audit_logs_event_timestamp', 'audit_logs')
    op.drop_index('idx_audit_logs_user_timestamp', 'audit_logs')
    op.drop_index('idx_audit_logs_success', 'audit_logs')
    op.drop_index('idx_audit_logs_severity', 'audit_logs')
    op.drop_index('idx_audit_logs_resource', 'audit_logs')
    op.drop_index('idx_audit_logs_user_id', 'audit_logs')
    op.drop_index('idx_audit_logs_event_type', 'audit_logs')
    op.drop_index('idx_audit_logs_timestamp', 'audit_logs')
    
    # Drop table
    op.drop_table('audit_logs')