"""
Command Line Interface for the Expense Tracker.
"""
import click
from typing import Optional


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Expense Tracker CLI - Manage your expenses from the command line."""
    pass


@cli.command()
@click.option("--amount", "-a", type=float, required=True, help="Expense amount")
@click.option("--description", "-d", type=str, required=True, help="Expense description")
@click.option("--category", "-c", type=str, help="Expense category")
@click.option("--date", type=str, help="Expense date (YYYY-MM-DD)")
def add(amount: float, description: str, category: Optional[str], date: Optional[str]):
    """Add a new expense."""
    click.echo(f"Adding expense: ${amount:.2f} - {description}")
    if category:
        click.echo(f"Category: {category}")
    if date:
        click.echo(f"Date: {date}")
    # TODO: Implement actual expense creation


@cli.command()
@click.option("--period", type=click.Choice(["daily", "weekly", "monthly", "yearly"]), 
              default="monthly", help="Report period")
@click.option("--category", type=str, help="Filter by category")
@click.option("--format", type=click.Choice(["table", "json", "csv"]), 
              default="table", help="Output format")
def report(period: str, category: Optional[str], format: str):
    """Generate expense reports."""
    click.echo(f"Generating {period} report in {format} format")
    if category:
        click.echo(f"Filtered by category: {category}")
    # TODO: Implement actual report generation


if __name__ == "__main__":
    cli()