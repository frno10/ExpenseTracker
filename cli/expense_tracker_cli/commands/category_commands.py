"""
Category management commands.
"""
from typing import Optional
import sys

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm

from ..api.client import APIClient
from ..utils.exceptions import ExpenseTrackerCLIError
from ..utils.serialization import format_output
from ..config import Config


@click.group()
def category():
    """Manage expense categories."""
    pass


@category.command()
@click.option("--name", "-n", required=True, help="Category name")
@click.option("--color", "-c", help="Category color (hex code)")
@click.option("--parent", "-p", help="Parent category name")
@click.pass_context
def add(
    ctx,
    name: str,
    color: Optional[str],
    parent: Optional[str],
):
    """Add a new category."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        # Prepare category data
        category_data = {"name": name}
        if color:
            if not color.startswith('#'):
                color = f"#{color}"
            category_data["color"] = color
        if parent:
            # Find parent category ID
            categories = client.get_categories()
            parent_category = next((c for c in categories if c["name"] == parent), None)
            if not parent_category:
                raise ExpenseTrackerCLIError(f"Parent category '{parent}' not found")
            category_data["parent_id"] = parent_category["id"]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Creating category...", total=None)
            category = client.create_category(category_data)
        
        console.print(f"[green]✓[/green] Category created successfully!")
        console.print(f"[blue]ID:[/blue] {category['id']}")
        console.print(f"[blue]Name:[/blue] {category['name']}")
        if category.get('color'):
            console.print(f"[blue]Color:[/blue] {category['color']}")
        if category.get('parent_name'):
            console.print(f"[blue]Parent:[/blue] {category['parent_name']}")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to create category: {e}")


@category.command()
@click.pass_context
def list(ctx):
    """List all categories."""
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
            task = progress.add_task("Loading categories...", total=None)
            categories = client.get_categories()
        
        if not categories:
            console.print("[yellow]No categories found.[/yellow]")
            return
        
        if output_format == "table":
            table = Table(title=f"Categories ({len(categories)} items)")
            table.add_column("Name", style="white")
            table.add_column("Color", style="magenta")
            table.add_column("Parent", style="cyan")
            table.add_column("Expenses", style="green", justify="right")
            table.add_column("Created", style="blue")
            
            for category in categories:
                color_display = category.get('color', '')
                if color_display:
                    color_display = f"[{color_display}]●[/{color_display}] {color_display}"
                
                table.add_row(
                    category.get('name', ''),
                    color_display,
                    category.get('parent_name', ''),
                    str(category.get('expense_count', 0)),
                    category.get('created_at', '')[:10] if category.get('created_at') else '',
                )
            
            console.print(table)
        else:
            output = format_output(categories, output_format)
            console.print(output)
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to list categories: {e}")


@category.command()
@click.argument("category_name")
@click.option("--name", "-n", help="New category name")
@click.option("--color", "-c", help="New category color (hex code)")
@click.option("--parent", "-p", help="New parent category name")
@click.pass_context
def update(
    ctx,
    category_name: str,
    name: Optional[str],
    color: Optional[str],
    parent: Optional[str],
):
    """Update an existing category."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        # Find category by name
        categories = client.get_categories()
        category = next((c for c in categories if c["name"] == category_name), None)
        if not category:
            raise ExpenseTrackerCLIError(f"Category '{category_name}' not found")
        
        # Prepare update data
        update_data = {}
        if name:
            update_data["name"] = name
        if color:
            if not color.startswith('#'):
                color = f"#{color}"
            update_data["color"] = color
        if parent:
            # Find parent category ID
            parent_category = next((c for c in categories if c["name"] == parent), None)
            if not parent_category:
                raise ExpenseTrackerCLIError(f"Parent category '{parent}' not found")
            update_data["parent_id"] = parent_category["id"]
        
        if not update_data:
            console.print("[yellow]No updates specified.[/yellow]")
            return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Updating category...", total=None)
            updated_category = client.update_category(category["id"], update_data)
        
        console.print(f"[green]✓[/green] Category updated successfully!")
        console.print(f"[blue]ID:[/blue] {updated_category['id']}")
        console.print(f"[blue]Name:[/blue] {updated_category['name']}")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to update category: {e}")


@category.command()
@click.argument("category_name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete(ctx, category_name: str, yes: bool):
    """Delete a category."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        # Find category by name
        categories = client.get_categories()
        category = next((c for c in categories if c["name"] == category_name), None)
        if not category:
            raise ExpenseTrackerCLIError(f"Category '{category_name}' not found")
        
        # Check if category has expenses
        expense_count = category.get('expense_count', 0)
        if expense_count > 0:
            console.print(f"[yellow]Warning: This category has {expense_count} expenses.[/yellow]")
        
        if not yes:
            if not Confirm.ask(f"Are you sure you want to delete category '{category_name}'?"):
                console.print("[yellow]Deletion cancelled.[/yellow]")
                return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Deleting category...", total=None)
            client.delete_category(category["id"])
        
        console.print(f"[green]✓[/green] Category '{category_name}' deleted successfully!")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to delete category: {e}")


@category.command()
@click.argument("category_name")
@click.option("--period", type=click.Choice(["week", "month", "quarter", "year"]), default="month", help="Analysis period")
@click.pass_context
def stats(ctx, category_name: str, period: str):
    """Show statistics for a specific category."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        # Find category by name
        categories = client.get_categories()
        category = next((c for c in categories if c["name"] == category_name), None)
        if not category:
            raise ExpenseTrackerCLIError(f"Category '{category_name}' not found")
        
        # Calculate date range
        from datetime import date, timedelta
        today = date.today()
        
        if period == "week":
            date_from = today - timedelta(days=today.weekday())
            date_to = today
        elif period == "month":
            date_from = today.replace(day=1)
            date_to = today
        elif period == "quarter":
            quarter = (today.month - 1) // 3
            date_from = date(today.year, quarter * 3 + 1, 1)
            date_to = today
        else:  # year
            date_from = today.replace(month=1, day=1)
            date_to = today
        
        # Get category expenses
        filters = {
            "category": category_name,
            "date_from": date_from.strftime("%Y-%m-%d"),
            "date_to": date_to.strftime("%Y-%m-%d"),
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Loading category statistics...", total=None)
            response = client.get_expenses(filters)
            stats = client.get_expense_statistics(filters)
        
        expenses = response.get("items", [])
        
        console.print(f"[bold]Category Statistics - {category_name}[/bold]")
        console.print(f"[blue]Period:[/blue] {period.title()} ({date_from} to {date_to})")
        console.print(f"[blue]Total Expenses:[/blue] {stats.get('expense_count', 0)}")
        console.print(f"[blue]Total Amount:[/blue] {config.display.currency}{stats.get('total_amount', 0):.2f}")
        console.print(f"[blue]Average Amount:[/blue] {config.display.currency}{stats.get('average_amount', 0):.2f}")
        console.print(f"[blue]Min Amount:[/blue] {config.display.currency}{stats.get('min_amount', 0):.2f}")
        console.print(f"[blue]Max Amount:[/blue] {config.display.currency}{stats.get('max_amount', 0):.2f}")
        
        # Show recent expenses
        if expenses:
            console.print(f"\n[bold]Recent Expenses (last {min(5, len(expenses))}):[/bold]")
            table = Table()
            table.add_column("Date", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Amount", style="green", justify="right")
            
            for expense in expenses[:5]:
                table.add_row(
                    expense.get("date", ""),
                    expense.get("description", "")[:40] + ("..." if len(expense.get("description", "")) > 40 else ""),
                    f"{config.display.currency}{expense.get('amount', 0):.2f}",
                )
            
            console.print(table)
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to get category statistics: {e}")