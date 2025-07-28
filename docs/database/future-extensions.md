# Database Future Extensions Analysis

This document analyzes potential future extensions to the database schema and recommends whether to implement them now or later.

## 🔮 Likely Future Extensions

### 1. Multi-User Support (HIGH PRIORITY)
**Current State**: Single-user system
**Future Need**: Multiple users with data isolation

```sql
-- Would need to add:
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add user_id to all main tables:
ALTER TABLE expenses ADD COLUMN user_id UUID REFERENCES users(id);
ALTER TABLE categories ADD COLUMN user_id UUID REFERENCES users(id);
ALTER TABLE budgets ADD COLUMN user_id UUID REFERENCES users(id);
```

**Recommendation**: 🟡 **Add Now** - This is a fundamental architectural change that's easier to implement early.

### 2. Recurring Expenses (MEDIUM PRIORITY)
**Current State**: Boolean flag only
**Future Need**: Complex recurring patterns

```sql
CREATE TABLE recurring_patterns (
    id UUID PRIMARY KEY,
    expense_id UUID REFERENCES expenses(id),
    frequency_type VARCHAR(20) NOT NULL, -- daily, weekly, monthly, yearly
    frequency_value INTEGER NOT NULL,    -- every N days/weeks/months
    end_date DATE,
    next_occurrence DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Recommendation**: 🟢 **Add Later** - Current boolean flag is sufficient for MVP.

### 3. Tags System (LOW PRIORITY)
**Current State**: Single category per expense
**Future Need**: Multiple tags per expense

```sql
CREATE TABLE tags (
    id UUID PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    color VARCHAR(7) DEFAULT '#6B7280',
    user_id UUID REFERENCES users(id)
);

CREATE TABLE expense_tags (
    expense_id UUID REFERENCES expenses(id),
    tag_id UUID REFERENCES tags(id),
    PRIMARY KEY (expense_id, tag_id)
);
```

**Recommendation**: 🟢 **Add Later** - Categories are sufficient initially.

### 4. Statement Import Tracking (MEDIUM PRIORITY)
**Current State**: No import tracking
**Future Need**: Track parsed statements and prevent duplicates

```sql
CREATE TABLE statement_imports (
    id UUID PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) UNIQUE NOT NULL, -- SHA-256 hash
    bank_name VARCHAR(100),
    account_number VARCHAR(50),
    statement_period_start DATE,
    statement_period_end DATE,
    total_transactions INTEGER,
    imported_transactions INTEGER,
    status VARCHAR(20) DEFAULT 'pending', -- pending, processed, failed
    metadata JSONB,
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE statement_transactions (
    id UUID PRIMARY KEY,
    statement_import_id UUID REFERENCES statement_imports(id),
    expense_id UUID REFERENCES expenses(id), -- NULL if not imported
    raw_data JSONB NOT NULL,
    confidence_score DECIMAL(3,2), -- 0.00 to 1.00
    is_duplicate BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Recommendation**: 🟡 **Add Soon** - Critical for statement parsing feature.

### 5. Audit Trail (HIGH PRIORITY)
**Current State**: Basic created_at/updated_at
**Future Need**: Full audit trail for financial data

```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_id UUID NOT NULL,
    action VARCHAR(10) NOT NULL, -- INSERT, UPDATE, DELETE
    old_values JSONB,
    new_values JSONB,
    user_id UUID REFERENCES users(id),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Trigger function for automatic audit logging
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    -- Implementation for audit logging
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;
```

**Recommendation**: 🟡 **Add Now** - Financial data needs audit trails from the start.

### 6. Advanced Analytics Tables (LOW PRIORITY)
**Current State**: Real-time calculations
**Future Need**: Pre-computed analytics for performance

```sql
CREATE TABLE monthly_summaries (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    category_id UUID REFERENCES categories(id),
    total_amount DECIMAL(10,2) NOT NULL,
    transaction_count INTEGER NOT NULL,
    avg_amount DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, year, month, category_id)
);
```

**Recommendation**: 🟢 **Add Later** - Premature optimization.

## 🚨 Critical Extensions to Add Now

### 1. User Support
```sql
-- Add to current migration
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100),
    timezone VARCHAR(50) DEFAULT 'UTC',
    currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Add user_id to existing tables
ALTER TABLE categories ADD COLUMN user_id UUID REFERENCES users(id);
ALTER TABLE payment_methods ADD COLUMN user_id UUID REFERENCES users(id);
ALTER TABLE expenses ADD COLUMN user_id UUID REFERENCES users(id);
ALTER TABLE budgets ADD COLUMN user_id UUID REFERENCES users(id);

-- Create indexes
CREATE INDEX idx_expenses_user_date ON expenses(user_id, expense_date);
CREATE INDEX idx_categories_user ON categories(user_id);
CREATE INDEX idx_budgets_user ON budgets(user_id);
```

### 2. Audit Trail
```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name VARCHAR(50) NOT NULL,
    record_id UUID NOT NULL,
    action VARCHAR(10) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_log_table_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_log_user_date ON audit_log(user_id, created_at);
```

## 🔧 Recommended Schema Updates

### Updated Base Model
```python
# app/models/base.py
class BaseTable(Base):
    __abstract__ = True
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

### User Model
```python
# app/models/user.py
class UserTable(BaseTable):
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=True)
    timezone = Column(String(50), default="UTC")
    currency = Column(String(3), default="USD")
    
    # Remove user_id from BaseTable for User model
    user_id = None
```

## 📊 Migration Strategy

### Phase 1: Critical Extensions (Now)
1. Add users table
2. Add user_id to all existing tables
3. Add audit_log table
4. Update all models and repositories
5. Add authentication middleware

### Phase 2: Statement Processing (Next Sprint)
1. Add statement_imports table
2. Add statement_transactions table
3. Implement duplicate detection
4. Add file hash tracking

### Phase 3: Advanced Features (Later)
1. Recurring patterns table
2. Tags system
3. Pre-computed analytics
4. Advanced reporting tables

## 🎯 Decision Matrix

| Extension | Complexity | Impact | Timing | Priority |
|-----------|------------|--------|---------|----------|
| Multi-user | High | High | Now | 🔴 Critical |
| Audit Trail | Medium | High | Now | 🔴 Critical |
| Statement Import | Medium | Medium | Soon | 🟡 Important |
| Recurring Patterns | Low | Medium | Later | 🟢 Nice-to-have |
| Tags System | Low | Low | Later | 🟢 Nice-to-have |
| Analytics Tables | Medium | Low | Later | 🟢 Nice-to-have |

## 🚀 Extensibility Features Already Built-In

### 1. JSONB Columns for Flexibility
```sql
-- Can add flexible metadata without schema changes
ALTER TABLE expenses ADD COLUMN metadata JSONB;
ALTER TABLE statement_imports ADD COLUMN parsing_metadata JSONB;
```

### 2. Enum Extensibility
```sql
-- Easy to add new payment types
ALTER TYPE paymenttype ADD VALUE 'cryptocurrency';
ALTER TYPE paymenttype ADD VALUE 'gift_card';
```

### 3. Hierarchical Categories
```sql
-- Already supports unlimited category nesting
-- No schema changes needed for complex category trees
```

### 4. UUID Keys
```sql
-- Already using UUIDs for easy distribution/sharding
-- No auto-increment issues when scaling
```

## 💡 Recommendations

### Implement Now (Before Task 3):
1. **Multi-user support** - Fundamental architectural change
2. **Audit trail** - Financial data compliance requirement
3. **User context in all operations** - Security requirement

### Implement Soon (Task 6-8):
1. **Statement import tracking** - Needed for parsing features
2. **File hash duplicate detection** - Prevent duplicate imports

### Implement Later:
1. **Tags system** - Categories are sufficient initially
2. **Recurring patterns** - Boolean flag works for MVP
3. **Analytics tables** - Real-time queries are fine initially

The database is well-designed for extension, but multi-user support and audit trails should be added now as they're architectural foundations that are much harder to retrofit later.