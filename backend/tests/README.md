# Comprehensive Testing Suite

This directory contains a comprehensive testing suite for the Expense Tracker application, implementing multiple testing strategies to ensure code quality, reliability, and performance.

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and fixtures
├── unit/                    # Unit tests
│   ├── test_expense_service.py
│   ├── test_budget_service.py
│   ├── test_user_service.py
│   └── test_repositories.py
├── integration/             # Integration tests
│   ├── test_expense_api.py
│   ├── test_budget_api.py
│   └── test_auth_api.py
├── e2e/                     # End-to-end tests
│   ├── test_expense_management_flow.py
│   ├── test_budget_management_flow.py
│   └── test_user_workflows.py
├── performance/             # Performance tests
│   ├── test_expense_performance.py
│   ├── test_budget_performance.py
│   └── test_database_performance.py
├── load/                    # Load testing
│   └── locustfile.py
└── README.md               # This file
```

## Test Categories

### 1. Unit Tests (`tests/unit/`)

Unit tests focus on testing individual components in isolation:

- **Service Layer Tests**: Test business logic and service methods
- **Repository Tests**: Test data access layer functionality
- **Model Tests**: Test data models and validation
- **Utility Tests**: Test helper functions and utilities

**Markers**: `@pytest.mark.unit`

**Coverage**: Aims for 90%+ code coverage on service and repository layers

### 2. Integration Tests (`tests/integration/`)

Integration tests verify that different components work together correctly:

- **API Endpoint Tests**: Test HTTP endpoints with real database
- **Database Integration**: Test repository-database interactions
- **Service Integration**: Test service-to-service communication
- **External Service Integration**: Test third-party service integrations

**Markers**: `@pytest.mark.integration`, `@pytest.mark.api`

### 3. End-to-End Tests (`tests/e2e/`)

E2E tests simulate complete user workflows:

- **User Journey Tests**: Complete workflows from user perspective
- **Cross-Feature Tests**: Tests spanning multiple features
- **Error Recovery Tests**: Test error handling and recovery scenarios
- **Data Consistency Tests**: Verify data integrity across operations

**Markers**: `@pytest.mark.e2e`

### 4. Performance Tests (`tests/performance/`)

Performance tests ensure the application meets performance requirements:

- **Load Tests**: Test performance under expected load
- **Stress Tests**: Test behavior under extreme conditions
- **Scalability Tests**: Test performance with large datasets
- **Memory Tests**: Monitor memory usage and detect leaks

**Markers**: `@pytest.mark.performance`, `@pytest.mark.slow`

### 5. Load Tests (`tests/load/`)

Load tests using Locust to simulate realistic user behavior:

- **Concurrent User Simulation**: Multiple users performing various actions
- **Realistic Usage Patterns**: Based on actual user behavior
- **Performance Monitoring**: Response times, throughput, error rates
- **Scalability Assessment**: Determine system limits

## Test Configuration

### Pytest Configuration (`pytest.ini`)

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --verbose
    --tb=short
    --cov=app
    --cov-report=html:htmlcov
    --cov-report=xml:coverage.xml
    --cov-report=term-missing
    --cov-fail-under=80
```

### Test Markers

- `unit`: Unit tests
- `integration`: Integration tests
- `e2e`: End-to-end tests
- `performance`: Performance tests
- `slow`: Slow-running tests
- `database`: Tests requiring database
- `external`: Tests requiring external services
- `auth`: Authentication/authorization tests
- `api`: API endpoint tests

## Running Tests

### Using the Test Runner

```bash
# Run all tests
python run_tests.py --all

# Run specific test categories
python run_tests.py --unit
python run_tests.py --integration
python run_tests.py --e2e
python run_tests.py --performance

# Run with coverage
python run_tests.py --coverage

# Run quality checks
python run_tests.py --quality

# Fast mode (skip slow tests)
python run_tests.py --fast

# Parallel execution
python run_tests.py --parallel
```

### Using Pytest Directly

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m "e2e and not slow"

# Run specific test files
pytest tests/unit/test_expense_service.py
pytest tests/integration/test_expense_api.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run in parallel
pytest -n auto

# Verbose output
pytest -v
```

### Load Testing

```bash
# Install Locust
pip install locust

# Run load tests
locust -f tests/load/locustfile.py --host http://localhost:8000

# Headless load test
locust -f tests/load/locustfile.py --headless -u 50 -r 10 -t 60s --host http://localhost:8000
```

## Test Data and Fixtures

### Database Fixtures

- `db_session`: Test database session with automatic rollback
- `test_user`: Standard test user
- `test_admin_user`: Admin user for testing admin features
- `test_category`: Test expense category
- `test_expense`: Single test expense
- `test_budget`: Test budget
- `multiple_expenses`: Collection of test expenses

### Mock Fixtures

- `mock_redis`: Mocked Redis client
- `mock_email_service`: Mocked email service
- `mock_file_storage`: Mocked file storage service

### Data Factories

- `TestDataFactory`: Factory for creating test data
- `performance_test_data`: Large dataset for performance testing

## Performance Benchmarks

### Response Time Targets

- **API Endpoints**: < 200ms for 95th percentile
- **Database Queries**: < 100ms for complex queries
- **Search Operations**: < 500ms for full-text search
- **Export Operations**: < 5s for 1000 records

### Throughput Targets

- **Expense Creation**: > 100 requests/second
- **Expense Retrieval**: > 500 requests/second
- **Search Operations**: > 50 requests/second
- **Bulk Operations**: > 10 operations/second

### Resource Usage Limits

- **Memory Usage**: < 512MB under normal load
- **CPU Usage**: < 70% under normal load
- **Database Connections**: < 20 concurrent connections

## Quality Gates

### Code Coverage

- **Minimum Coverage**: 80%
- **Target Coverage**: 90%
- **Critical Paths**: 95%+ coverage required

### Performance Criteria

- All performance tests must pass
- No memory leaks detected
- Response times within targets
- Error rate < 0.1% under normal load

### Code Quality

- All linting checks pass (flake8, black, isort)
- Type checking passes (mypy)
- Security analysis passes (bandit)
- No critical security vulnerabilities

## Continuous Integration

The testing pipeline runs automatically on:

- **Pull Requests**: Full test suite
- **Main Branch**: Full test suite + performance tests
- **Nightly**: Extended performance and load tests

### CI/CD Pipeline Stages

1. **Linting and Code Quality**
2. **Unit Tests**
3. **Integration Tests**
4. **End-to-End Tests**
5. **Performance Tests**
6. **Security Scanning**
7. **Load Testing** (main branch only)

## Test Environment Setup

### Local Development

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Set up test database
export DATABASE_URL="sqlite+aiosqlite:///./test.db"
export TESTING=true

# Run tests
python run_tests.py --all
```

### Docker Environment

```bash
# Build test environment
docker-compose -f docker-compose.test.yml up -d

# Run tests in container
docker-compose -f docker-compose.test.yml exec app python run_tests.py --all
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Ensure test database is running
   - Check DATABASE_URL environment variable
   - Verify database permissions

2. **Slow Test Performance**
   - Use `--fast` flag to skip slow tests
   - Run tests in parallel with `-n auto`
   - Check database query performance

3. **Memory Issues**
   - Monitor memory usage during tests
   - Check for memory leaks in fixtures
   - Reduce test data size if needed

4. **Flaky Tests**
   - Check for race conditions
   - Verify test isolation
   - Review async test handling

### Debug Mode

```bash
# Run tests with debug output
pytest -v -s --tb=long

# Run specific failing test
pytest tests/unit/test_expense_service.py::TestExpenseService::test_create_expense_success -v -s

# Drop into debugger on failure
pytest --pdb
```

## Contributing

When adding new tests:

1. Follow the existing test structure and naming conventions
2. Use appropriate test markers
3. Include both positive and negative test cases
4. Add performance tests for new features
5. Update this documentation for new test categories
6. Ensure tests are isolated and repeatable

### Test Naming Conventions

- Test files: `test_<module_name>.py`
- Test classes: `Test<ClassName>`
- Test methods: `test_<functionality>_<scenario>`

### Example Test Structure

```python
class TestExpenseService:
    """Test cases for ExpenseService."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_expense_success(self, db_session, test_user):
        """Test successful expense creation."""
        # Arrange
        expense_data = ExpenseCreate(...)
        
        # Act
        result = await expense_service.create_expense(...)
        
        # Assert
        assert result.amount == expense_data.amount
        assert result.user_id == test_user.id
```

## Reporting

### Coverage Reports

- **HTML Report**: `htmlcov/index.html`
- **XML Report**: `coverage.xml`
- **Terminal Report**: Displayed after test run

### Performance Reports

- **Response Time Charts**: Generated after performance tests
- **Memory Usage Graphs**: Available in performance artifacts
- **Load Test Results**: Locust generates detailed reports

### Quality Reports

- **Linting Results**: Displayed in CI/CD pipeline
- **Security Scan Results**: Available in GitHub Security tab
- **Test Results**: JUnit XML format for CI/CD integration