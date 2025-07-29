"""
Expense management commands for the CLI.
"""
import click
import asyncio
from datetime import datetime, date
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
import json

from cli.utils.api import ExpenseAPI
from cli.utils.formatters import format_currency, format_date, format_expense_table
from cli.utils.validators import validate_date, validate_amount

console = Console()


@click.group(name="expenses")
def expenses_group():
    """Manage expenses - add, list, edit, and delete expenses."""
    pass


@expenses_group.command()
@click.option("--amount", "-a", type=float, required=True, help="Expense amount")
@click.option("--description", "-d", type=str, required=True, help="Expense description")
@click.option("--category", "-c", type=str, help="Expense category")
@click.option("--date", type=str, help="Expense date (YYYY-MM-DD, defaults to today)")
@click.option("--account", type=str, help="Account name")
@click.option("--payment-method", type=str, help="Payment method")
@click.option("--tags", type=str, help="Comma-separated tags")
@click.option("--notes", type=str, help="Additional notes")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.pass_context
def add(ctx, amount: float, description: str, category: Optional[str], 
        date: Optional[str], account: Optional[str], payment_method: Optional[str],
        tags: Optional[str], notes: Optional[str], interactive: bool):
    """Add a new expense."""
    
    if interactive:
        # Interactive mode - prompt for all fields
        amount = float(Prompt.ask("Amount", default=str(amount) if amount else None))
        description = Prompt.ask("Description", default=description or "")
        category = Prompt.ask("Category", default=category or "")
        date = Prompt.ask("Date (YYYY-MM-DD)", default=date or str(datetime.now().date()))
        account = Prompt.ask("Account", default=account or "")
        payment_method = Prompt.ask("Payment method", default=payment_method or "")
        tags = Prompt.ask("Tags (comma-separated)", default=tags or "")
        notes = Prompt.ask("Notes", default=notes or "")
    
    # Validate inputs
    if not validate_amount(amount):
        console.print("[red]Error: Amount must be positive[/red]")
        return
    
    if date and not validate_date(date):
        console.print("[red]Error: Invalid date format. Use YYYY-MM-DD[/red]")
        return
    
    # Prepare expense data
    expense_data = {
        "amount": amount,
        "description": description,
        "date": date or str(datetime.now().date())
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
    
    # Create expense
    async def create_expense():
        api = ExpenseAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Creating expense...", total=None)
            
            try:
                expense = await api.create_expense(expense_data)
                progress.update(task, description="✓ Expense created successfully")
                
                console.print(f"\n[green]✓ Expense added successfully![/green]")
                console.print(f"ID: {expense.get('id', 'N/A')}")
                console.print(f"Amount: {format_currency(amount)}")
                console.print(f"Description: {description}")
                if category:
                    console.print(f"Category: {category}")
                console.print(f"Date: {format_date(expense_data['date'])}")
                
            except Exception as e:
                progress.update(task, description="✗ Failed to create expense")
                console.print(f"[red]Error creating expense: {e}[/red]")
    
    asyncio.run(create_expense())


@expenses_group.command()
@click.option("--limit", "-l", type=int, default=20, help="Number of expenses to show")
@click.option("--category", "-c", type=str, help="Filter by category")
@click.option("--account", "-a", type=str, help="Filter by account")
@click.option("--date-from", type=str, help="Start date (YYYY-MM-DD)")
@click.option("--date-to", type=str, help="End date (YYYY-MM-DD)")
@click.option("--min-amount", type=float, help="Minimum amount")
@click.option("--max-amount", type=float, help="Maximum amount")
@click.option("--search", "-s", type=str, help="Search in description and notes")
@click.option("--format", type=click.Choice(["table", "json", "csv"]), 
              default="table", help="Output format")
@click.option("--sort", type=click.Choice(["date", "amount", "description", "category"]),
              default="date", help="Sort by field")
@click.option("--order", type=click.Choice(["asc", "desc"]), default="desc", help="Sort order")
@click.pass_context
def list(ctx, limit: int, category: Optional[str], account: Optional[str],
         date_from: Optional[str], date_to: Optional[str], min_amount: Optional[float],
         max_amount: Optional[float], search: Optional[str], format: str, sort: str, order: str):
    """List expenses with filtering and sorting options."""
    
    # Validate date inputs
    if date_from and not validate_date(date_from):
        console.print("[red]Error: Invalid date-from format. Use YYYY-MM-DD[/red]")
        return
    
    if date_to and not validate_date(date_to):
        console.print("[red]Error: Invalid date-to format. Use YYYY-MM-DD[/red]")
        return
    
    # Prepare filters
    filters = {"limit": limit, "sort": f"{sort}_{order}"}
    if category:
        filters["category"] = category
    if account:
        filters["account"] = account
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    if min_amount is not None:
        filters["min_amount"] = min_amount
    if max_amount is not None:
        filters["max_amount"] = max_amount
    if search:
        filters["search"] = search
    
    async def fetch_expenses():
        api = ExpenseAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Fetching expenses...", total=None)
            
            try:
                expenses = await api.get_expenses(filters)
                progress.update(task, description="✓ Expenses loaded")
                
                if not expenses:
                    console.print("[yellow]No expenses found matching the criteria.[/yellow]")
                    return
                
                if format == "json":
                    console.print(json.dumps(expenses, indent=2, default=str))
                elif format == "csv":
                    # TODO: Implement CSV output
                    console.print("CSV format not yet implemented")
                else:
                    # Table format
                    table = format_expense_table(expenses)
                    console.print(f"\n[bold]Found {len(expenses)} expenses[/bold]")
                    console.print(table)
                
            except Exception as e:
                progress.update(task, description="✗ Failed to fetch expenses")
                console.print(f"[red]Error fetching expenses: {e}[/red]")
    
    asyncio.run(fetch_expenses())


@expenses_group.command()
@click.argument("expense_id", type=str)
@click.option("--amount", "-a", type=float, help="New expense amount")
@click.option("--description", "-d", type=str, help="New expense description")
@click.option("--category", "-c", type=str, help="New expense category")
@click.option("--date", type=str, help="New expense date (YYYY-MM-DD)")
@click.option("--account", type=str, help="New account name")
@click.option("--payment-method", type=str, help="New payment method")
@click.option("--tags", type=str, help="New comma-separated tags")
@click.option("--notes", type=str, help="New additional notes")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.pass_context
def edit(ctx, expense_id: str, amount: Optional[float], description: Optional[str],
         category: Optional[str], date: Optional[str], account: Optional[str],
         payment_method: Optional[str], tags: Optional[str], notes: Optional[str],
         interactive: bool):
    """Edit an existing expense."""
    
    async def update_expense():
        api = ExpenseAPI(ctx.obj['config'])
        
        try:
            # First, get the current expense
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Loading expense...", total=None)
                current_expense = await api.get_expense(expense_id)
                progress.update(task, description="✓ Expense loaded")
            
            if interactive:
                # Interactive mode - show current values and prompt for new ones
                console.print(f"\n[bold]Editing expense: {current_expense.get('description', 'N/A')}[/bold]")
                console.print("Press Enter to keep current value, or type new value:")
                
                amount = amount or float(Prompt.ask(
                    f"Amount (current: {format_currency(current_expense.get('amount', 0))})",
                    default=str(current_expense.get('amount', 0))
                ))
                description = description or Prompt.ask(
                    f"Description (current: {current_expense.get('description', '')})",
                    default=current_expense.get('description', '')
                )
                category = category or Prompt.ask(
                    f"Category (current: {current_expense.get('category', '')})",
                    default=current_expense.get('category', '')
                )
                date = date or Prompt.ask(
                    f"Date (current: {current_expense.get('date', '')})",
                    default=current_expense.get('date', '')
                )
            
            # Prepare update data
            update_data = {}
            if amount is not None:
                if not validate_amount(amount):
                    console.print("[red]Error: Amount must be positive[/red]")
                    return
                update_data["amount"] = amount
            
            if description is not None:
                update_data["description"] = description
            
            if category is not None:
                update_data["category"] = category
            
            if date is not None:
                if not validate_date(date):
                    console.print("[red]Error: Invalid date format. Use YYYY-MM-DD[/red]")
                    return
                update_data["date"] = date
            
            if account is not None:
                update_data["account"] = account
            
            if payment_method is not None:
                update_data["payment_method"] = payment_method
            
            if tags is not None:
                update_data["tags"] = [tag.strip() for tag in tags.split(",")]
            
            if notes is not None:
                update_data["notes"] = notes
            
            if not update_data:
                console.print("[yellow]No changes specified.[/yellow]")
                return
            
            # Update expense
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Updating expense...", total=None)
                updated_expense = await api.update_expense(expense_id, update_data)
                progress.update(task, description="✓ Expense updated successfully")
            
            console.print(f"\n[green]✓ Expense updated successfully![/green]")
            console.print(f"ID: {expense_id}")
            for key, value in update_data.items():
                if key == "amount":
                    console.print(f"{key.title()}: {format_currency(value)}")
                elif key == "date":
                    console.print(f"{key.title()}: {format_date(value)}")
                else:
                    console.print(f"{key.title()}: {value}")
            
        except Exception as e:
            console.print(f"[red]Error updating expense: {e}[/red]")
    
    asyncio.run(update_expense())


@expenses_group.command()
@click.argument("expense_id", type=str)
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete(ctx, expense_id: str, force: bool):
    """Delete an expense."""
    
    async def remove_expense():
        api = ExpenseAPI(ctx.obj['config'])
        
        try:
            # Get expense details for confirmation
            if not force:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("Loading expense...", total=None)
                    expense = await api.get_expense(expense_id)
                    progress.update(task, description="✓ Expense loaded")
                
                console.print(f"\n[bold]Expense to delete:[/bold]")
                console.print(f"Amount: {format_currency(expense.get('amount', 0))}")
                console.print(f"Description: {expense.get('description', 'N/A')}")
                console.print(f"Category: {expense.get('category', 'N/A')}")
                console.print(f"Date: {format_date(expense.get('date', ''))}")
                
                if not Confirm.ask("\nAre you sure you want to delete this expense?"):
                    console.print("[yellow]Deletion cancelled.[/yellow]")
                    return
            
            # Delete expense
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Deleting expense...", total=None)
                await api.delete_expense(expense_id)
                progress.update(task, description="✓ Expense deleted successfully")
            
            console.print(f"\n[green]✓ Expense deleted successfully![/green]")
            
        except Exception as e:
            console.print(f"[red]Error deleting expense: {e}[/red]")
    
    asyncio.run(remove_expense())


@expenses_group.command()
@click.argument("expense_id", type=str)
@click.pass_context
def show(ctx, expense_id: str):
    """Show detailed information about a specific expense."""
    
    async def get_expense_details():
        api = ExpenseAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Loading expense details...", total=None)
            
            try:
                expense = await api.get_expense(expense_id)
                progress.update(task, description="✓ Expense details loaded")
                
                console.print(f"\n[bold blue]Expense Details[/bold blue]")
                console.print("=" * 40)
                console.print(f"[bold]ID:[/bold] {expense.get('id', 'N/A')}")
                console.print(f"[bold]Amount:[/bold] {format_currency(expense.get('amount', 0))}")
                console.print(f"[bold]Description:[/bold] {expense.get('description', 'N/A')}")
                console.print(f"[bold]Category:[/bold] {expense.get('category', 'N/A')}")
                console.print(f"[bold]Date:[/bold] {format_date(expense.get('date', ''))}")
                
                if expense.get('account'):
                    console.print(f"[bold]Account:[/bold] {expense['account']}")
                
                if expense.get('payment_method'):
                    console.print(f"[bold]Payment Method:[/bold] {expense['payment_method']}")
                
                if expense.get('tags'):
                    console.print(f"[bold]Tags:[/bold] {', '.join(expense['tags'])}")
                
                if expense.get('notes'):
                    console.print(f"[bold]Notes:[/bold] {expense['notes']}")
                
                if expense.get('created_at'):
                    console.print(f"[bold]Created:[/bold] {format_date(expense['created_at'])}")
                
                if expense.get('updated_at'):
                    console.print(f"[bold]Updated:[/bold] {format_date(expense['updated_at'])}")
                
                console.print()
                
            except Exception as e:
                progress.update(task, description="✗ Failed to load expense details")
                console.print(f"[red]Error loading expense details: {e}[/red]")
    
    asyncio.run(get_expense_details())


@expenses_group.command()
@click.option("--category", "-c", type=str, help="Filter by category")
@click.option("--account", "-a", type=str, help="Filter by account")
@click.option("--date-from", type=str, help="Start date (YYYY-MM-DD)")
@click.option("--date-to", type=str, help="End date (YYYY-MM-DD)")
@click.pass_context
def summary(ctx, category: Optional[str], account: Optional[str],
            date_from: Optional[str], date_to: Optional[str]):
    """Show expense summary statistics."""
    
    # Prepare filters
    filters = {}
    if category:
        filters["category"] = category
    if account:
        filters["account"] = account
    if date_from:
        filters["date_from"] = date_from
    if date_to:
        filters["date_to"] = date_to
    
    async def get_summary():
        api = ExpenseAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Calculating summary...", total=None)
            
            try:
                summary_data = await api.get_expense_summary(filters)
                progress.update(task, description="✓ Summary calculated")
                
                console.print(f"\n[bold blue]Expense Summary[/bold blue]")
                console.print("=" * 40)
                console.print(f"[bold]Total Expenses:[/bold] {summary_data.get('count', 0)}")
                console.print(f"[bold]Total Amount:[/bold] {format_currency(summary_data.get('total_amount', 0))}")
                console.print(f"[bold]Average Amount:[/bold] {format_currency(summary_data.get('average_amount', 0))}")
                console.print(f"[bold]Largest Expense:[/bold] {format_currency(summary_data.get('max_amount', 0))}")
                console.print(f"[bold]Smallest Expense:[/bold] {format_currency(summary_data.get('min_amount', 0))}")
                
                if summary_data.get('categories'):
                    console.print(f"\n[bold]Top Categories:[/bold]")
                    for cat in summary_data['categories'][:5]:
                        console.print(f"  • {cat['name']}: {format_currency(cat['amount'])} ({cat['count']} expenses)")
                
                console.print()
                
            except Exception as e:
                progress.update(task, description="✗ Failed to calculate summary")
                console.print(f"[red]Error calculating summary: {e}[/red]")
    
    asyncio.run(get_summary())