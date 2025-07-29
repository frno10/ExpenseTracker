"""Basic tests for the CLI application."""
import pytest
from click.testing import CliRunner
from expense_tracker_cli.main import cli


def test_cli_help():
    """Test that CLI help command works."""
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'Expense Tracker CLI' in result.output


def test_version_command():
    """Test version command."""
    runner = CliRunner()
    result = runner.invoke(cli, ['version'])
    assert result.exit_code == 0
    assert 'Expense Tracker CLI' in result.output


def test_expense_help():
    """Test expense command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ['expense', '--help'])
    assert result.exit_code == 0
    assert 'Manage expenses' in result.output


def test_config_help():
    """Test config command help."""
    runner = CliRunner()
    result = runner.invoke(cli, ['config', '--help'])
    assert result.exit_code == 0