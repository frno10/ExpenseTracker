"""
Tests for the CLI application.
"""
import pytest
from click.testing import CliRunner
import tempfile
import json
from pathlib import Path

from cli.main import cli
from cli.utils.config import DEFAULT_CONFIG


class TestCLIBasics:
    """Test basic CLI functionality."""
    
    def test_cli_help(self):
        """Test that CLI shows help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Expense Tracker CLI' in result.output
    
    def test_cli_version(self):
        """Test that CLI shows version."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert '1.0.0' in result.output
    
    def test_status_command(self):
        """Test status command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['status'])
        assert result.exit_code == 0
        assert 'Expense Tracker CLI Status' in result.output
    
    def test_quickstart_command(self):
        """Test quickstart command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['quickstart'])
        assert result.exit_code == 0
        assert 'Quick Start Guide' in result.output


class TestConfigCommands:
    """Test configuration commands."""
    
    def test_config_show_default(self):
        """Test showing default configuration."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / 'test_config.toml'
            result = runner.invoke(cli, ['config', 'show', '--config', str(config_file)])
            assert result.exit_code == 0
    
    def test_config_set_get(self):
        """Test setting and getting configuration values."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / 'test_config.toml'
            
            # Set a value
            result = runner.invoke(cli, ['config', 'set', 'api_url', 'http://test.com', '--config', str(config_file)])
            assert result.exit_code == 0
            
            # Get the value
            result = runner.invoke(cli, ['config', 'get', 'api_url', '--config', str(config_file)])
            assert result.exit_code == 0
            assert 'http://test.com' in result.output
    
    def test_config_defaults(self):
        """Test showing default configuration."""
        runner = CliRunner()
        result = runner.invoke(cli, ['config', 'defaults'])
        assert result.exit_code == 0
        assert 'Default Configuration Values' in result.output
    
    def test_config_path(self):
        """Test showing configuration path."""
        runner = CliRunner()
        result = runner.invoke(cli, ['config', 'path'])
        assert result.exit_code == 0
        assert 'Configuration file path' in result.output


class TestExpenseCommands:
    """Test expense management commands."""
    
    def test_expenses_help(self):
        """Test expenses command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['expenses', '--help'])
        assert result.exit_code == 0
        assert 'Manage expenses' in result.output
    
    def test_expenses_add_help(self):
        """Test expenses add command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['expenses', 'add', '--help'])
        assert result.exit_code == 0
        assert 'Add a new expense' in result.output
    
    def test_expenses_list_help(self):
        """Test expenses list command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['expenses', 'list', '--help'])
        assert result.exit_code == 0
        assert 'List expenses' in result.output


class TestBudgetCommands:
    """Test budget management commands."""
    
    def test_budgets_help(self):
        """Test budgets command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['budgets', '--help'])
        assert result.exit_code == 0
        assert 'Manage budgets' in result.output
    
    def test_budgets_create_help(self):
        """Test budgets create command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['budgets', 'create', '--help'])
        assert result.exit_code == 0
        assert 'Create a new budget' in result.output


class TestImportCommands:
    """Test import commands."""
    
    def test_import_help(self):
        """Test import command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['import', '--help'])
        assert result.exit_code == 0
        assert 'Import bank statements' in result.output
    
    def test_import_formats(self):
        """Test import formats command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['import', 'formats'])
        assert result.exit_code == 0
        assert 'Supported Import Formats' in result.output
        assert 'PDF' in result.output
        assert 'CSV' in result.output


class TestReportsCommands:
    """Test report generation commands."""
    
    def test_reports_help(self):
        """Test reports command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['reports', '--help'])
        assert result.exit_code == 0
        assert 'Generate various financial reports' in result.output
    
    def test_reports_monthly_help(self):
        """Test monthly report command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['reports', 'monthly', '--help'])
        assert result.exit_code == 0
        assert 'Generate a monthly expense report' in result.output


class TestAnalyticsCommands:
    """Test analytics commands."""
    
    def test_analytics_help(self):
        """Test analytics command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ['analytics', '--help'])
        assert result.exit_code == 0
        assert 'Advanced analytics' in result.output


class TestUtilities:
    """Test utility functions."""
    
    def test_config_loading(self):
        """Test configuration loading."""
        from cli.utils.config import load_config, save_config
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / 'test_config.toml'
            
            # Test loading non-existent config (should return defaults)
            config = load_config(str(config_file))
            assert config == DEFAULT_CONFIG
            
            # Test saving and loading config
            test_config = DEFAULT_CONFIG.copy()
            test_config['api_url'] = 'http://test.example.com'
            
            assert save_config(test_config, str(config_file))
            loaded_config = load_config(str(config_file))
            assert loaded_config['api_url'] == 'http://test.example.com'
    
    def test_validators(self):
        """Test input validators."""
        from cli.utils.validators import (
            validate_date, validate_amount, validate_email, 
            validate_category_name, validate_tags
        )
        
        # Date validation
        assert validate_date('2023-12-25')
        assert not validate_date('2023-13-25')
        assert not validate_date('invalid-date')
        
        # Amount validation
        assert validate_amount(10.50)
        assert not validate_amount(-5.00)
        assert not validate_amount(0)
        
        # Email validation
        assert validate_email('test@example.com')
        assert not validate_email('invalid-email')
        
        # Category name validation
        assert validate_category_name('Food & Dining')
        assert not validate_category_name('')
        assert not validate_category_name('A' * 100)  # Too long
        
        # Tags validation
        tags = validate_tags('work, personal, important')
        assert len(tags) == 3
        assert 'work' in tags
    
    def test_formatters(self):
        """Test output formatters."""
        from cli.utils.formatters import (
            format_currency, format_date, format_percentage, format_file_size
        )
        
        # Currency formatting
        assert '$' in format_currency(123.45)
        
        # Date formatting
        formatted_date = format_date('2023-12-25')
        assert '2023-12-25' in formatted_date
        
        # Percentage formatting
        assert format_percentage(75.5) == '75.5%'
        
        # File size formatting
        assert format_file_size(1024) == '1.0 KB'
        assert format_file_size(1048576) == '1.0 MB'


class TestErrorHandling:
    """Test error handling in CLI commands."""
    
    def test_invalid_command(self):
        """Test handling of invalid commands."""
        runner = CliRunner()
        result = runner.invoke(cli, ['invalid-command'])
        assert result.exit_code != 0
    
    def test_missing_required_args(self):
        """Test handling of missing required arguments."""
        runner = CliRunner()
        # Try to add expense without required amount
        result = runner.invoke(cli, ['expenses', 'add', '--description', 'test'])
        assert result.exit_code != 0


if __name__ == '__main__':
    pytest.main([__file__])