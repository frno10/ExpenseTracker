# Expense Tracker CLI

A powerful command-line interface for the Expense Tracker application, providing full access to expense management, analytics, and reporting features from the terminal.

## Installation

```bash
pip install expense-tracker-cli
```

Or install from source:

```bash
git clone https://github.com/expense-tracker/cli.git
cd cli
pip install -e .
```

## Quick Start

1. **Configure the CLI**:
   ```bash
   expense-tracker config setup
   ```

2. **Add your first expense**:
   ```bash
   expense-tracker expense add --amount 12.50 --description "Coffee" --category "Food & Dining"
   ```

3. **View your expenses**:
   ```bash
   expense-tracker expense list
   ```

4. **Generate a report**:
   ```bash
   expense-tracker report monthly
   ```

## Commands

### Configuration
- `config setup` - Initial configuration setup
- `config show` - Display current configuration
- `config set <key> <value>` - Set configuration value

### Expense Management
- `expense add` - Add a new expense
- `expense list` - List expenses with filtering
- `expense show <id>` - Show expense details
- `expense edit <id>` - Edit an expense
- `expense delete <id>` - Delete an expense
- `expense search <query>` - Search expenses

### Categories
- `category list` - List all categories
- `category add <name>` - Add a new category
- `category edit <id>` - Edit a category

### Budgets
- `budget list` - List all budgets
- `budget add` - Create a new budget
- `budget status` - Show budget status
- `budget alerts` - Show budget alerts

### Analytics
- `analytics summary` - Show spending summary
- `analytics trends` - Show spending trends
- `analytics categories` - Category breakdown
- `analytics monthly` - Monthly analysis

### Import/Export
- `import statement <file>` - Import bank statement
- `export expenses` - Export expenses to CSV/PDF
- `export report` - Export detailed report

### Recurring Expenses
- `recurring list` - List recurring expenses
- `recurring add` - Add recurring expense
- `recurring process` - Process due recurring expenses

## Configuration

The CLI uses a configuration file located at `~/.expense-tracker/config.toml`:

```toml
[api]
base_url = "http://localhost:8000"
timeout = 30

[auth]
# Authentication will be stored securely using keyring

[display]
currency = "USD"
date_format = "%Y-%m-%d"
table_style = "grid"

[export]
default_format = "csv"
output_directory = "~/Downloads"
```

## Examples

### Adding Expenses
```bash
# Basic expense
expense-tracker expense add -a 25.99 -d "Lunch at restaurant" -c "Food & Dining"

# With payment method and account
expense-tracker expense add -a 150.00 -d "Gas bill" -c "Utilities" -p "Chase Credit" -A "Checking"

# With date
expense-tracker expense add -a 89.99 -d "Book purchase" -c "Education" --date 2024-01-15
```

### Filtering and Searching
```bash
# List expenses from last 30 days
expense-tracker expense list --days 30

# Filter by category
expense-tracker expense list --category "Food & Dining"

# Search by description
expense-tracker expense search "coffee"

# Filter by amount range
expense-tracker expense list --min-amount 10 --max-amount 100
```

### Analytics and Reports
```bash
# Monthly summary
expense-tracker analytics summary --period monthly

# Category breakdown for last 3 months
expense-tracker analytics categories --months 3

# Export monthly report
expense-tracker export report --period monthly --format pdf
```

### Recurring Expenses
```bash
# Add monthly subscription
expense-tracker recurring add -n "Netflix" -a 15.99 -c "Entertainment" -f monthly

# List all recurring expenses
expense-tracker recurring list

# Process due recurring expenses
expense-tracker recurring process
```

## Authentication

The CLI supports multiple authentication methods:

1. **API Key**: Set via `expense-tracker config set auth.api_key <key>`
2. **Username/Password**: Interactive login with secure credential storage
3. **OAuth**: Browser-based authentication flow

Credentials are stored securely using the system keyring.

## Output Formats

The CLI supports multiple output formats:

- **Table**: Human-readable tables (default)
- **JSON**: Machine-readable JSON output
- **CSV**: Comma-separated values
- **YAML**: YAML format

Use the `--format` flag to specify the output format:

```bash
expense-tracker expense list --format json
```

## Scripting and Automation

The CLI is designed for scripting and automation:

```bash
#!/bin/bash
# Daily expense report script

# Add today's expenses
expense-tracker expense add -a 4.50 -d "Morning coffee" -c "Food & Dining"
expense-tracker expense add -a 12.00 -d "Lunch" -c "Food & Dining"

# Generate daily summary
expense-tracker analytics summary --period daily --format json > daily_report.json

# Check budget status
expense-tracker budget status --format table
```

## Troubleshooting

### Common Issues

1. **Connection Error**: Check API URL in configuration
2. **Authentication Failed**: Verify credentials with `config show`
3. **Command Not Found**: Ensure CLI is properly installed

### Debug Mode

Enable debug mode for detailed logging:

```bash
expense-tracker --debug expense list
```

### Getting Help

```bash
# General help
expense-tracker --help

# Command-specific help
expense-tracker expense --help
expense-tracker expense add --help
```

## Contributing

See the main project repository for contribution guidelines.

## License

MIT License - see LICENSE file for details.