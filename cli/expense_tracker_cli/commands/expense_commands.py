"""
Expense management commands.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
import sys

import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..api.client import APIClient
from ..utils.exceptions import ExpenseTrackerCLIError
from ..utils.serialization import format_output, parse_date
from ..config import Config


@click.group()
def expense():
    """Manage expenses."""
    pass


@expense.command()
@click.option("--amount", "-a", type=float, required=True, help="Expense amount")
@click.option("--description", "-d", required=True, help="Expense description")
@click.option("--category", "-c", help="Expense category")
@click.option("--date", type=click.DateTime(formats=["%Y-%m-%d"]), help="Expense date (YYYY-MM-DD)")
@click.option("--account", help="Account name")
@click.option("--payment-method", help="Payment method")
@click.option("--tags", help="Comma-separated tags")
@click.option("--notes", help="Additional notes")
@click.pass_context
def add(
    ctx,
    amount: float,
    description: str,
    category: Optional[str],
    date: Optional[datetime],
    account: Optional[str],
    payment_method: Optional[str],
    tags: Optional[str],
    notes: Optional[str],
):
    """Add a new expense."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        # Prepare expense data
        expense_data = {
            "amount": amount,
            "description": description,
            "date": (date or datetime.now()).strftime("%Y-%m-%d"),
        }
        
        if category:
            expense_data["category"] = category
        if account:
            expense_data["account"] = account
        if payment_method:
            expense_data["payment_method"] = payment_method
        if tags:
            expense_data["tags"] = [tag.strip() for tag in tags.split(",")]
        if notes:
            expense_data["notes"] = notes
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Creating expense...", total=None)
            expense = client.create_expense(expense_data)
        
        console.print(f"[green]✓[/green] Expense created successfully!")
        console.print(f"[blue]ID:[/blue] {expense['id']}")
        console.print(f"[blue]Amount:[/blue] {config.display.currency}{amount:.2f}")
        console.print(f"[blue]Description:[/blue] {description}")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to create expense: {e}")


@expense.command()
@click.option("--limit", "-l", type=int, default=20, help="Number of expenses to show")
@click.option("--category", "-c", help="Filter by category")
@click.option("--account", "-a", help="Filter by account")
@click.option("--date-from", type=click.DateTime(formats=["%Y-%m-%d"]), help="Start date filter")
@click.option("--date-to", type=click.DateTime(formats=["%Y-%m-%d"]), help="End date filter")
@click.option("--min-amount", type=float, help="Minimum amount filter")
@click.option("--max-amount", type=float, help="Maximum amount filter")
@click.option("--search", "-s", help="Search in descriptions")
@click.pass_context
def list(
    ctx,
    limit: int,
    category: Optional[str],
    account: Optional[str],
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    min_amount: Optional[float],
    max_amount: Optional[float],
    search: Optional[str],
):
    """List expenses with optional filters."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    output_format: str = ctx.obj["output_format"]
    
    try:
        client = APIClient(config)
        
        # Prepare filters
        filters = {"size": limit}
        if category:
            filters["category"] = category
        if account:
            filters["account"] = account
        if date_from:
            filters["date_from"] = date_from.strftime("%Y-%m-%d")
        if date_to:
            filters["date_to"] = date_to.strftime("%Y-%m-%d")
        if min_amount is not None:
            filters["min_amount"] = min_amount
        if max_amount is not None:
            filters["max_amount"] = max_amount
        if search:
            filters["search"] = search
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Loading expenses...", total=None)
            response = client.get_expenses(filters)
        
        expenses = response.get("items", [])
        
        if not expenses:
            console.print("[yellow]No expenses found.[/yellow]")
            return
        
        if output_format == "table":
            table = Table(title=f"Expenses ({len(expenses)} items)")
            table.add_column("Date", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Category", style="magenta")
            table.add_column("Amount", style="green", justify="right")
            table.add_column("Account", style="blue")
            
            for expense in expenses:
                table.add_row(
                    expense.get("date", ""),
                    expense.get("description", ""),
                    expense.get("category", ""),
                    f"{config.display.currency}{expense.get('amount', 0):.2f}",
                    expense.get("account", ""),
                )
            
            console.print(table)
        else:
            output = format_output(expenses, output_format)
            console.print(output)
        
        # Show summary
        total_amount = sum(float(expense.get("amount", 0)) for expense in expenses)
        console.print(f"\n[bold]Total: {config.display.currency}{total_amount:.2f}[/bold]")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to list expenses: {e}")


@expense.command()
@click.argument("expense_id")
@click.pass_context
def show(ctx, expense_id: str):
    """Show detailed information about a specific expense."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Loading expense...", total=None)
            expense = client.get_expense(expense_id)
        
        # Display expense details
        console.print(f"[bold]Expense Details[/bold]")
        console.print(f"[blue]ID:[/blue] {expense['id']}")
        console.print(f"[blue]Amount:[/blue] {config.display.currency}{expense['amount']:.2f}")
        console.print(f"[blue]Description:[/blue] {expense['description']}")
        console.print(f"[blue]Category:[/blue] {expense.get('category', 'N/A')}")
        console.print(f"[blue]Date:[/blue] {expense['date']}")
        console.print(f"[blue]Account:[/blue] {expense.get('account', 'N/A')}")
        console.print(f"[blue]Payment Method:[/blue] {expense.get('payment_method', 'N/A')}")
        
        if expense.get("tags"):
            console.print(f"[blue]Tags:[/blue] {', '.join(expense['tags'])}")
        
        if expense.get("notes"):
            console.print(f"[blue]Notes:[/blue] {expense['notes']}")
        
        console.print(f"[blue]Created:[/blue] {expense.get('created_at', 'N/A')}")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to show expense: {e}")


@expense.command()
@click.argument("expense_id")
@click.option("--amount", "-a", type=float, help="New expense amount")
@click.option("--description", "-d", help="New expense description")
@click.option("--category", "-c", help="New expense category")
@click.option("--date", type=click.DateTime(formats=["%Y-%m-%d"]), help="New expense date")
@click.option("--account", help="New account name")
@click.option("--payment-method", help="New payment method")
@click.option("--tags", help="New comma-separated tags")
@click.option("--notes", help="New additional notes")
@click.pass_context
def update(
    ctx,
    expense_id: str,
    amount: Optional[float],
    description: Optional[str],
    category: Optional[str],
    date: Optional[datetime],
    account: Optional[str],
    payment_method: Optional[str],
    tags: Optional[str],
    notes: Optional[str],
):
    """Update an existing expense."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        # Prepare update data
        update_data = {}
        if amount is not None:
            update_data["amount"] = amount
        if description:
            update_data["description"] = description
        if category:
            update_data["category"] = category
        if date:
            update_data["date"] = date.strftime("%Y-%m-%d")
        if account:
            update_data["account"] = account
        if payment_method:
            update_data["payment_method"] = payment_method
        if tags:
            update_data["tags"] = [tag.strip() for tag in tags.split(",")]
        if notes:
            update_data["notes"] = notes
        
        if not update_data:
            console.print("[yellow]No updates specified.[/yellow]")
            return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Updating expense...", total=None)
            expense = client.update_expense(expense_id, update_data)
        
        console.print(f"[green]✓[/green] Expense updated successfully!")
        console.print(f"[blue]ID:[/blue] {expense['id']}")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to update expense: {e}")


@expense.command()
@click.argument("expense_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete(ctx, expense_id: str, yes: bool):
    """Delete an expense."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        if not yes:
            if not Confirm.ask("Are you sure you want to delete this expense?"):
                console.print("[yellow]Deletion cancelled.[/yellow]")
                return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Deleting expense...", total=None)
            client.delete_expense(expense_id)
        
        console.print(f"[green]✓[/green] Expense deleted successfully!")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to delete expense: {e}")


@expense.command()
@click.option("--search", "-s", help="Search query")
@click.option("--limit", "-l", type=int, default=10, help="Number of results to show")
@click.pass_context
def search(ctx, search: str, limit: int):
    """Search expenses by description, notes, or tags."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    if not search:
        search = Prompt.ask("Enter search query")
    
    try:
        client = APIClient(config)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Searching expenses...", total=None)
            response = client.search_expenses(search)
        
        expenses = response.get("items", [])[:limit]
        
        if not expenses:
            console.print(f"[yellow]No expenses found for '{search}'.[/yellow]")
            return
        
        table = Table(title=f"Search Results for '{search}' ({len(expenses)} items)")
        table.add_column("Date", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Category", style="magenta")
        table.add_column("Amount", style="green", justify="right")
        
        for expense in expenses:
            table.add_row(
                expense.get("date", ""),
                expense.get("description", ""),
                expense.get("category", ""),
                f"{config.display.currency}{expense.get('amount', 0):.2f}",
            )
        
        console.print(table)
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to search expenses: {e}")


@expense.command()
@click.option("--period", type=click.Choice(["today", "week", "month", "year"]), default="month", help="Summary period")
@click.pass_context
def summary(ctx, period: str):
    """Show expense summary for a period."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        # Calculate date range based on period
        today = date.today()
        if period == "today":
            date_from = date_to = today
        elif period == "week":
            date_from = today.replace(day=today.day - today.weekday())
            date_to = today
        elif period == "month":
            date_from = today.replace(day=1)
            date_to = today
        elif period == "year":
            date_from = today.replace(month=1, day=1)
            date_to = today
        
        filters = {
            "date_from": date_from.strftime("%Y-%m-%d"),
            "date_to": date_to.strftime("%Y-%m-%d"),
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Loading summary...", total=None)
            stats = client.get_expense_statistics(filters)
        
        console.print(f"[bold]Expense Summary - {period.title()}[/bold]")
        console.print(f"[blue]Period:[/blue] {date_from} to {date_to}")
        console.print(f"[blue]Total Expenses:[/blue] {stats.get('expense_count', 0)}")
        console.print(f"[blue]Total Amount:[/blue] {config.display.currency}{stats.get('total_amount', 0):.2f}")
        console.print(f"[blue]Average Amount:[/blue] {config.display.currency}{stats.get('average_amount', 0):.2f}")
        console.print(f"[blue]Min Amount:[/blue] {config.display.currency}{stats.get('min_amount', 0):.2f}")
        console.print(f"[blue]Max Amount:[/blue] {config.display.currency}{stats.get('max_amount', 0):.2f}")
        
        # Show category breakdown if available
        if stats.get("category_breakdown"):
            console.print("\n[bold]Category Breakdown:[/bold]")
            table = Table()
            table.add_column("Category", style="magenta")
            table.add_column("Count", style="cyan", justify="right")
            table.add_column("Amount", style="green", justify="right")
            table.add_column("Percentage", style="yellow", justify="right")
            
            total_amount = stats.get('total_amount', 0)
            for category_data in stats["category_breakdown"]:
                percentage = (category_data["total_amount"] / total_amount * 100) if total_amount > 0 else 0
                table.add_row(
                    category_data["category_name"],
                    str(category_data["expense_count"]),
                    f"{config.display.currency}{category_data['total_amount']:.2f}",
                    f"{percentage:.1f}%",
                )
            
            console.print(table)
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to get expense summary: {e}")