"""
Command Line Interface for the Expense Tracker.
"""
import click
import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.append(str(Path(__file__).parent.parent))

from cli.commands.expenses import expenses_group
from cli.commands.budgets import budgets_group
from cli.commands.import_cmd import import_group
from cli.commands.reports import reports_group
from cli.commands.analytics import analytics_group
from cli.commands.config import config_group
from cli.utils.config import load_config, ensure_config_exists
from cli.utils.auth import ensure_authenticated
from rich.console import Console

console = Console()


@click.group()
@click.version_option(version="1.0.0")
@click.option("--config", "-c", type=click.Path(), help="Path to configuration file")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, config, verbose):
    """Expense Tracker CLI - Manage your expenses from the command line.
    
    A comprehensive command-line interface for managing expenses, budgets,
    imports, and generating reports with rich formatting and visualizations.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Store configuration in context
    ctx.obj['verbose'] = verbose
    ctx.obj['config_path'] = config
    
    # Load configuration
    try:
        ensure_config_exists(config)
        ctx.obj['config'] = load_config(config)
    except Exception as e:
        if verbose:
            console.print(f"[red]Error loading configuration: {e}[/red]")
        ctx.obj['config'] = {}


# Add command groups
cli.add_command(expenses_group)
cli.add_command(budgets_group)
cli.add_command(import_group)
cli.add_command(reports_group)
cli.add_command(analytics_group)
cli.add_command(config_group)


@cli.command()
@click.pass_context
def status(ctx):
    """Show system status and configuration."""
    config = ctx.obj.get('config', {})
    
    console.print("\n[bold blue]Expense Tracker CLI Status[/bold blue]")
    console.print("=" * 40)
    
    # Configuration status
    console.print(f"[green]✓[/green] Configuration loaded")
    console.print(f"  API URL: {config.get('api_url', 'Not configured')}")
    console.print(f"  Config file: {ctx.obj.get('config_path', 'Default')}")
    
    # Authentication status
    try:
        auth_status = asyncio.run(ensure_authenticated(config))
        if auth_status:
            console.print(f"[green]✓[/green] Authentication valid")
        else:
            console.print(f"[red]✗[/red] Authentication required")
    except Exception as e:
        console.print(f"[red]✗[/red] Authentication error: {e}")
    
    # API connectivity
    console.print(f"[yellow]?[/yellow] API connectivity: Testing...")
    # TODO: Add API connectivity test
    
    console.print()


@cli.command()
def quickstart():
    """Quick setup guide for first-time users."""
    console.print("\n[bold blue]Expense Tracker CLI - Quick Start Guide[/bold blue]")
    console.print("=" * 50)
    
    console.print("\n[bold]1. Configuration[/bold]")
    console.print("   Run: [cyan]expense-cli config setup[/cyan]")
    console.print("   This will create your configuration file with API settings.")
    
    console.print("\n[bold]2. Authentication[/bold]")
    console.print("   Run: [cyan]expense-cli config auth[/cyan]")
    console.print("   This will authenticate you with the expense tracker API.")
    
    console.print("\n[bold]3. Add your first expense[/bold]")
    console.print("   Run: [cyan]expense-cli expenses add -a 25.50 -d 'Coffee' -c 'Food'[/cyan]")
    
    console.print("\n[bold]4. View your expenses[/bold]")
    console.print("   Run: [cyan]expense-cli expenses list[/cyan]")
    
    console.print("\n[bold]5. Generate a report[/bold]")
    console.print("   Run: [cyan]expense-cli reports monthly[/cyan]")
    
    console.print("\n[bold]6. Import bank statements[/bold]")
    console.print("   Run: [cyan]expense-cli import file statement.pdf[/cyan]")
    
    console.print("\n[green]For more help on any command, use --help[/green]")
    console.print("Example: [cyan]expense-cli expenses --help[/cyan]\n")


if __name__ == "__main__":
    cli()