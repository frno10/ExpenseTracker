"""
Main CLI entry point for the Expense Tracker application.
"""
import sys
from typing import Optional

import click
from rich.console import Console
from rich.traceback import install

from .config import Config, ConfigManager
from .commands import (
    config_commands,
    expense_commands,
    category_commands,
    budget_commands,
    analytics_commands,
    import_export_commands,
    recurring_commands,
)
from .utils.exceptions import ExpenseTrackerCLIError
from .utils.logging import setup_logging

# Install rich traceback handler for better error display
install(show_locals=True)

console = Console()


@click.group()
@click.option(
    "--config-file",
    type=click.Path(),
    help="Path to configuration file",
    envvar="EXPENSE_TRACKER_CONFIG",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug mode",
    envvar="EXPENSE_TRACKER_DEBUG",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "csv", "yaml"]),
    default="table",
    help="Output format",
)
@click.option(
    "--no-color",
    is_flag=True,
    help="Disable colored output",
)
@click.pass_context
def cli(
    ctx: click.Context,
    config_file: Optional[str],
    debug: bool,
    output_format: str,
    no_color: bool,
):
    """
    Expense Tracker CLI - Manage your expenses from the command line.
    
    This CLI provides full access to expense management, analytics, and reporting
    features. Use 'expense-tracker COMMAND --help' for detailed help on any command.
    
    Examples:
        expense-tracker expense add --amount 12.50 --description "Coffee"
        expense-tracker analytics summary --period monthly
        expense-tracker export expenses --format csv
    """
    # Setup logging
    setup_logging(debug=debug)
    
    # Initialize configuration
    config_manager = ConfigManager(config_file)
    config = config_manager.load_config()
    
    # Disable colors if requested
    if no_color:
        console.no_color = True
    
    # Store context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["config_manager"] = config_manager
    ctx.obj["console"] = console
    ctx.obj["debug"] = debug
    ctx.obj["output_format"] = output_format


@cli.result_callback()
def handle_result(result, **kwargs):
    """Handle command results and errors."""
    if isinstance(result, Exception):
        if isinstance(result, ExpenseTrackerCLIError):
            console.print(f"[red]Error: {result}[/red]")
            sys.exit(1)
        else:
            console.print(f"[red]Unexpected error: {result}[/red]")
            if kwargs.get("debug"):
                console.print_exception()
            sys.exit(1)


# Register command groups
cli.add_command(config_commands.config)
cli.add_command(expense_commands.expense)
cli.add_command(category_commands.category)
cli.add_command(budget_commands.budget)
cli.add_command(analytics_commands.analytics)
cli.add_command(import_export_commands.import_cmd, name="import")
cli.add_command(import_export_commands.export)
cli.add_command(recurring_commands.recurring)


@cli.command()
@click.pass_context
def version(ctx):
    """Show version information."""
    from . import __version__
    
    console = ctx.obj["console"]
    console.print(f"Expense Tracker CLI v{__version__}")


@cli.command()
@click.pass_context
def status(ctx):
    """Show system status and configuration."""
    config = ctx.obj["config"]
    console = ctx.obj["console"]
    
    from .api.client import APIClient
    
    try:
        client = APIClient(config)
        health = client.get_health()
        
        console.print("[green]✓[/green] API connection successful")
        console.print(f"[blue]API Version:[/blue] {health.get('version', 'Unknown')}")
        console.print(f"[blue]API Status:[/blue] {health.get('status', 'Unknown')}")
        
        # Show configuration
        console.print("\n[bold]Configuration:[/bold]")
        console.print(f"[blue]API URL:[/blue] {config.api.base_url}")
        console.print(f"[blue]Timeout:[/blue] {config.api.timeout}s")
        console.print(f"[blue]Currency:[/blue] {config.display.currency}")
        
    except Exception as e:
        console.print(f"[red]✗[/red] API connection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()