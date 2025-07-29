"""
Recurring expense management commands.
"""
from datetime import date, datetime
from typing import Optional
import sys

import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..api.client import APIClient
from ..utils.exceptions import ExpenseTrackerCLIError
from ..utils.serialization import format_output
from ..config import Config


@click.group()
def recurring():
    """Manage recurring expenses."""
    pass


@recurring.command()
@click.option("--name", "-n", required=True, help="Recurring expense name")
@click.option("--amount", "-a", type=float, required=True, help="Expense amount")
@click.option("--description", "-d", required=True, help="Expense description")
@click.option("--category", "-c", required=True, help="Expense category")
@click.option("--frequency", "-f", 
              type=click.Choice(["daily", "weekly", "monthly", "yearly"]), 
              required=True, help="Recurrence frequency")
@click.option("--start-date", type=click.DateTime(formats=["%Y-%m-%d"]), 
              help="Start date (default: today)")
@click.option("--end-date", type=click.DateTime(formats=["%Y-%m-%d"]), 
              help="End date (optional)")
@click.option("--account", help="Account name")
@click.option("--payment-method", help="Payment method")
@click.pass_context
def add(
    ctx,
    name: str,
    amount: float,
    description: str,
    category: str,
    frequency: str,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    account: Optional[str],
    payment_method: Optional[str],
):
    """Add a new recurring expense."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        # Prepare recurring expense data
        recurring_data = {
            "name": name,
            "amount": amount,
            "description": description,
            "category": category,
            "frequency": frequency,
            "start_date": (start_date or datetime.now()).strftime("%Y-%m-%d"),
        }
        
        if end_date:
            recurring_data["end_date"] = end_date.strftime("%Y-%m-%d")
        if account:
            recurring_data["account"] = account
        if payment_method:
            recurring_data["payment_method"] = payment_method
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Creating recurring expense...", total=None)
            recurring_expense = client.create_recurring_expense(recurring_data)
        
        console.print(f"[green]✓[/green] Recurring expense created successfully!")
        console.print(f"[blue]ID:[/blue] {recurring_expense['id']}")
        console.print(f"[blue]Name:[/blue] {name}")
        console.print(f"[blue]Amount:[/blue] {config.display.currency}{amount:.2f}")
        console.print(f"[blue]Frequency:[/blue] {frequency}")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to create recurring expense: {e}")


@recurring.command()
@click.pass_context
def list(ctx):
    """List all recurring expenses."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    output_format: str = ctx.obj["output_format"]
    
    try:
        client = APIClient(config)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Loading recurring expenses...", total=None)
            recurring_expenses = client.get_recurring_expenses()
        
        if not recurring_expenses:
            console.print("[yellow]No recurring expenses found.[/yellow]")
            return
        
        if output_format == "table":
            table = Table(title=f"Recurring Expenses ({len(recurring_expenses)} items)")
            table.add_column("Name", style="white")
            table.add_column("Description", style="cyan")
            table.add_column("Category", style="magenta")
            table.add_column("Amount", style="green", justify="right")
            table.add_column("Frequency", style="blue")
            table.add_column("Status", style="yellow")
            
            for expense in recurring_expenses:
                status = "Active" if expense.get("is_active", True) else "Inactive"
                table.add_row(
                    expense.get("name", ""),
                    expense.get("description", ""),
                    expense.get("category", ""),
                    f"{config.display.currency}{expense.get('amount', 0):.2f}",
                    expense.get("frequency", ""),
                    status,
                )
            
            console.print(table)
        else:
            output = format_output(recurring_expenses, output_format)
            console.print(output)
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to list recurring expenses: {e}")


@recurring.command()
@click.argument("recurring_id")
@click.pass_context
def show(ctx, recurring_id: str):
    """Show detailed information about a recurring expense."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Loading recurring expense...", total=None)
            expense = client.get_recurring_expense(recurring_id)
        
        # Display recurring expense details
        console.print(f"[bold]Recurring Expense Details[/bold]")
        console.print(f"[blue]ID:[/blue] {expense['id']}")
        console.print(f"[blue]Name:[/blue] {expense['name']}")
        console.print(f"[blue]Amount:[/blue] {config.display.currency}{expense['amount']:.2f}")
        console.print(f"[blue]Description:[/blue] {expense['description']}")
        console.print(f"[blue]Category:[/blue] {expense['category']}")
        console.print(f"[blue]Frequency:[/blue] {expense['frequency']}")
        console.print(f"[blue]Start Date:[/blue] {expense['start_date']}")
        
        if expense.get("end_date"):
            console.print(f"[blue]End Date:[/blue] {expense['end_date']}")
        
        console.print(f"[blue]Account:[/blue] {expense.get('account', 'N/A')}")
        console.print(f"[blue]Payment Method:[/blue] {expense.get('payment_method', 'N/A')}")
        console.print(f"[blue]Status:[/blue] {'Active' if expense.get('is_active', True) else 'Inactive'}")
        console.print(f"[blue]Created:[/blue] {expense.get('created_at', 'N/A')}")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to show recurring expense: {e}")


@recurring.command()
@click.argument("recurring_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete(ctx, recurring_id: str, yes: bool):
    """Delete a recurring expense."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        if not yes:
            if not Confirm.ask("Are you sure you want to delete this recurring expense?"):
                console.print("[yellow]Deletion cancelled.[/yellow]")
                return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Deleting recurring expense...", total=None)
            client.delete_recurring_expense(recurring_id)
        
        console.print(f"[green]✓[/green] Recurring expense deleted successfully!")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to delete recurring expense: {e}")


@recurring.command()
@click.argument("recurring_id")
@click.option("--activate/--deactivate", default=None, help="Activate or deactivate the recurring expense")
@click.pass_context
def toggle(ctx, recurring_id: str, activate: Optional[bool]):
    """Toggle the active status of a recurring expense."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        # Get current status if not specified
        if activate is None:
            expense = client.get_recurring_expense(recurring_id)
            activate = not expense.get("is_active", True)
        
        update_data = {"is_active": activate}
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Updating recurring expense...", total=None)
            client.update_recurring_expense(recurring_id, update_data)
        
        status = "activated" if activate else "deactivated"
        console.print(f"[green]✓[/green] Recurring expense {status} successfully!")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to toggle recurring expense: {e}")


@recurring.command()
@click.option("--days", "-d", type=int, default=30, help="Number of days to look ahead")
@click.pass_context
def upcoming(ctx, days: int):
    """Show upcoming recurring expenses."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Loading upcoming expenses...", total=None)
            upcoming_expenses = client.get_upcoming_expenses()
        
        if not upcoming_expenses:
            console.print("[yellow]No upcoming recurring expenses found.[/yellow]")
            return
        
        table = Table(title=f"Upcoming Recurring Expenses (Next {days} days)")
        table.add_column("Due Date", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Description", style="yellow")
        table.add_column("Amount", style="green", justify="right")
        table.add_column("Frequency", style="blue")
        
        for expense in upcoming_expenses:
            table.add_row(
                expense.get("due_date", ""),
                expense.get("name", ""),
                expense.get("description", ""),
                f"{config.display.currency}{expense.get('amount', 0):.2f}",
                expense.get("frequency", ""),
            )
        
        console.print(table)
        
        # Show total
        total_amount = sum(float(expense.get("amount", 0)) for expense in upcoming_expenses)
        console.print(f"\n[bold]Total Upcoming: {config.display.currency}{total_amount:.2f}[/bold]")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to get upcoming expenses: {e}")