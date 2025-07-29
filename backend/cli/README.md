# Expense Tracker CLI

A comprehensive command-line interface for managing expenses, budgets, and financial analytics.

## Features

- **Expense Management**: Add, edit, delete, and search expenses
- **Budget Tracking**: Create and monitor budgets with alerts
- **Statement Import**: Import bank statements in multiple formats (PDF, CSV, Excel, OFX, QIF)
- **Analytics**: Advanced spending analysis with anomaly detection
- **Reports**: Generate detailed financial reports
- **Rich Output**: Beautiful tables and progress bars using Rich library
- **Configuration**: Flexible configuration with TOML/JSON support

## Installation

### From Source

```bash
cd backend/cli
pip install -e .
```

### Using pip (when published)

```bash
pip install expense-tracker-cli
```

## Quick Start

1. **Initial Setup**
   ```bash
   expense-cli config setup
   ```

2. **Authenticate**
   ```bash
   expense-cli config auth
   ```

3. **Add your first expense**
   ```bash
   expense-cli expenses add -a 25.50 -d "Coffee" -c "Food"
   ```

4. **View expenses**
   ```bash
   expense-cli expenses list
   ```

5. **Generate a report**
   ```bash
   expense-cli reports monthly
   ```

## Commands Overview

### Configuration
- `config setup` - Interactive configuration setup
- `config show` - Show current configuration
- `config auth` - Authenticate with API
- `config status` - Show authentication status

### Expenses
- `expenses add` - Add a new expense
- `expenses list` - List expenses with filtering
- `expenses edit` - Edit an existing expense
- `expenses delete` - Delete an expense
- `expenses show` - Show detailed expense information
- `expenses summary` - Show expense statistics

### Budgets
- `budgets create` - Create a new budget
- `budgets list` - List all budgets
- `budgets status` - Show detailed budget status
- `budgets edit` - Edit an existing budget
- `budgets delete` - Delete a budget
- `budgets alerts` - Show budget alerts
- `budgets summary` - Show budget statistics

### Import
- `import file` - Import from bank statement file
- `import status` - Check import status
- `import preview` - Preview transactions before importing
- `import confirm` - Confirm and finalize import
- `import formats` - Show supported file formats

### Reports
- `reports monthly` - Generate monthly report
- `reports yearly` - Generate yearly report
- `reports custom` - Generate custom date range report
- `reports tax` - Generate tax-focused report
- `reports categories` - Generate category breakdown

### Analytics
- `analytics dashboard` - Show analytics dashboard
- `analytics trends` - Analyze spending trends
- `analytics categories` - Analyze spending by category
- `analytics anomalies` - Detect unusual spending patterns
- `analytics insights` - Get AI-generated insights
- `analytics forecast` - Generate spending forecasts

## Usage Examples

### Adding Expenses

```bash
# Basic expense
expense-cli expenses add -a 15.99 -d "Lunch" -c "Food"

# Expense with all details
expense-cli expenses add -a 89.99 -d "Gas" -c "Transportation" \
  --account "Checking" --payment-method "Credit Card" \
  --tags "work,travel" --notes "Business trip"

# Interactive mode
expense-cli expenses add -i
```

### Filtering and Searching

```bash
# List expenses from last 30 days
expense-cli expenses list --limit 30

# Filter by category
expense-cli expenses list --category "Food"

# Search in descriptions
expense-cli expenses list --search "coffee"

# Date range filtering
expense-cli expenses list --date-from 2023-01-01 --date-to 2023-12-31

# Amount range filtering
expense-cli expenses list --min-amount 50 --max-amount 200
```

### Budget Management

```bash
# Create a monthly budget
expense-cli budgets create -n "Monthly Budget" -l 2000 -p monthly

# Create budget with categories
expense-cli budgets create -n "Food Budget" -l 500 -p monthly \
  --categories "Food,Dining,Groceries"

# Check budget status
expense-cli budgets status budget-id-123

# Show all budget alerts
expense-cli budgets alerts
```

### Importing Statements

```bash
# Import PDF statement
expense-cli import file statement.pdf

# Import with preview
expense-cli import file statement.csv --preview

# Import specific file type
expense-cli import file data.xlsx --type excel

# Check import status
expense-cli import status import-id-123
```

### Generating Reports

```bash
# Monthly report for current month
expense-cli reports monthly

# Monthly report for specific month
expense-cli reports monthly --month 2023-12

# Yearly report
expense-cli reports yearly --year 2023

# Custom date range
expense-cli reports custom --start-date 2023-01-01 --end-date 2023-06-30

# Save report to file
expense-cli reports monthly --save monthly-report.txt

# Export as CSV
expense-cli reports monthly --format csv --save report.csv
```

### Analytics

```bash
# Show dashboard
expense-cli analytics dashboard

# Analyze trends for last 90 days
expense-cli analytics trends --period 90

# Category analysis
expense-cli analytics categories

# Detect anomalies
expense-cli analytics anomalies --sensitivity high

# Get insights
expense-cli analytics insights
```

## Configuration

The CLI uses a configuration file stored at `~/.expense-tracker/config.toml` by default.

### Configuration Options

```toml
api_url = "http://localhost:8000"
auth_token = "your-auth-token"
default_currency = "USD"
date_format = "%Y-%m-%d"
output_format = "table"
page_size = 20
auto_confirm = false
verbose = false
```

### Environment Variables

You can also use environment variables:

- `EXPENSE_TRACKER_API_URL` - API URL
- `EXPENSE_TRACKER_AUTH_TOKEN` - Authentication token
- `EXPENSE_TRACKER_CONFIG` - Path to configuration file

## Output Formats

Most commands support multiple output formats:

- `table` (default) - Rich formatted tables
- `json` - JSON output for scripting
- `csv` - CSV format for spreadsheets

```bash
# JSON output
expense-cli expenses list --format json

# CSV output
expense-cli expenses list --format csv
```

## Interactive Mode

Many commands support interactive mode with the `-i` flag:

```bash
# Interactive expense creation
expense-cli expenses add -i

# Interactive budget creation
expense-cli budgets create -i

# Interactive configuration
expense-cli config setup
```

## Error Handling

The CLI provides helpful error messages and suggestions:

```bash
# Invalid date format
expense-cli expenses add -a 10 -d "Test" --date "invalid-date"
# Error: Invalid date format. Use YYYY-MM-DD

# Missing authentication
expense-cli expenses list
# Error: Authentication required. Run 'expense-cli config auth'
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   ```bash
   expense-cli config status
   expense-cli config auth
   ```

2. **Configuration Issues**
   ```bash
   expense-cli config doctor
   expense-cli config validate
   ```

3. **API Connection Issues**
   ```bash
   expense-cli status
   ```

### Debug Mode

Enable verbose output for debugging:

```bash
expense-cli --verbose expenses list
```

## Development

### Running Tests

```bash
cd backend
python -m pytest tests/test_cli.py -v
```

### Adding New Commands

1. Create a new command file in `cli/commands/`
2. Add the command group to `cli/main.py`
3. Add tests in `tests/test_cli.py`

### Code Style

The CLI follows these conventions:
- Use Click for command definitions
- Use Rich for output formatting
- Use async/await for API calls
- Provide helpful error messages
- Support multiple output formats
- Include comprehensive help text

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- Check the troubleshooting section
- Run `expense-cli config doctor` for diagnostics
- Use `--help` on any command for detailed usage
- Enable verbose mode with `--verbose` for debugging