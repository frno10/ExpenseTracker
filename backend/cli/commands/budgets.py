"""
Budget management commands for the CLI.
"""
import click
import asyncio
from datetime import datetime, date
from typing import Optional, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
import json

from cli.utils.api import BudgetAPI
from cli.utils.formatters import format_currency, format_date, format_budget_table, format_percentage
from cli.utils.validators import validate_date, validate_amount, validate_budget_period

console = Console()


@click.group(name="budgets")
def budgets_group():
    """Manage budgets - create, monitor, and track spending limits."""
    pass


@budgets_group.command()
@click.option("--name", "-n", type=str, required=True, help="Budget name")
@click.option("--limit", "-l", type=float, required=True, help="Budget limit amount")
@click.option("--period", "-p", type=click.Choice(['daily', 'weekly', 'monthly', 'quarterly', 'yearly']),
              default='monthly', help="Budget period")
@click.option("--start-date", type=str, help="Budget start date (YYYY-MM-DD)")
@click.option("--end-date", type=str, help="Budget end date (YYYY-MM-DD)")
@click.option("--categories", type=str, help="Comma-separated list of categories to include")
@click.option("--description", type=str, help="Budget description")
@click.option("--alert-threshold", type=float, default=80.0, help="Alert threshold percentage (default: 80%)")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.pass_context
def create(ctx, name: str, limit: float, period: str, start_date: Optional[str],
           end_date: Optional[str], categories: Optional[str], description: Optional[str],
           alert_threshold: float, interactive: bool):
    """Create a new budget."""
    
    if interactive:
        # Interactive mode - prompt for all fields
        name = Prompt.ask("Budget name", default=name)
        limit = float(Prompt.ask("Budget limit", default=str(limit)))
        period = Prompt.ask("Period", choices=['daily', 'weekly', 'monthly', 'quarterly', 'yearly'], default=period)
        start_date = Prompt.ask("Start date (YYYY-MM-DD)", default=start_date or "")
        end_date = Prompt.ask("End date (YYYY-MM-DD)", default=end_date or "")
        categories = Prompt.ask("Categories (comma-separated)", default=categories or "")
        description = Prompt.ask("Description", default=description or "")
        alert_threshold = float(Prompt.ask("Alert threshold (%)", default=str(alert_threshold)))
    
    # Validate inputs
    if not validate_amount(limit):
        console.print("[red]Error: Budget limit must be positive[/red]")
        return
    
    if start_date and not validate_date(start_date):
        console.print("[red]Error: Invalid start date format. Use YYYY-MM-DD[/red]")
        return
    
    if end_date and not validate_date(end_date):
        console.print("[red]Error: Invalid end date format. Use YYYY-MM-DD[/red]")
        return
    
    if not validate_budget_period(period):
        console.print("[red]Error: Invalid budget period[/red]")
        return
    
    if alert_threshold < 0 or alert_threshold > 100:
        console.print("[red]Error: Alert threshold must be between 0 and 100[/red]")
        return
    
    # Prepare budget data
    budget_data = {
        "name": name,
        "total_limit": limit,
        "period": period,
        "alert_threshold": alert_threshold / 100  # Convert to decimal
    }
    
    if start_date:
        budget_data["start_date"] = start_date
    if end_date:
        budget_data["end_date"] = end_date
    if description:
        budget_data["description"] = description
    if categories:
        budget_data["categories"] = [cat.strip() for cat in categories.split(",")]
    
    # Create budget
    async def create_budget():
        api = BudgetAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Creating budget...", total=None)
            
            try:
                budget = await api.create_budget(budget_data)
                progress.update(task, description="✓ Budget created successfully")
                
                console.print(f"\n[green]✓ Budget created successfully![/green]")
                console.print(f"ID: {budget.get('id', 'N/A')}")
                console.print(f"Name: {name}")
                console.print(f"Limit: {format_currency(limit)}")
                console.print(f"Period: {period}")
                console.print(f"Alert threshold: {alert_threshold}%")
                
            except Exception as e:
                progress.update(task, description="✗ Failed to create budget")
                console.print(f"[red]Error creating budget: {e}[/red]")
    
    asyncio.run(create_budget())


@budgets_group.command()
@click.option("--status", type=click.Choice(['active', 'exceeded', 'completed']), help="Filter by status")
@click.option("--period", type=click.Choice(['daily', 'weekly', 'monthly', 'quarterly', 'yearly']), help="Filter by period")
@click.option("--format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def list(ctx, status: Optional[str], period: Optional[str], format: str):
    """List all budgets with their current status."""
    
    # Prepare filters
    filters = {}
    if status:
        filters["status"] = status
    if period:
        filters["period"] = period
    
    async def fetch_budgets():
        api = BudgetAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Fetching budgets...", total=None)
            
            try:
                budgets = await api.get_budgets(filters)
                progress.update(task, description="✓ Budgets loaded")
                
                if not budgets:
                    console.print("[yellow]No budgets found.[/yellow]")
                    return
                
                if format == "json":
                    console.print(json.dumps(budgets, indent=2, default=str))
                else:
                    # Table format
                    table = format_budget_table(budgets)
                    console.print(f"\n[bold]Found {len(budgets)} budgets[/bold]")
                    console.print(table)
                
            except Exception as e:
                progress.update(task, description="✗ Failed to fetch budgets")
                console.print(f"[red]Error fetching budgets: {e}[/red]")
    
    asyncio.run(fetch_budgets())


@budgets_group.command()
@click.argument("budget_id", type=str)
@click.pass_context
def status(ctx, budget_id: str):
    """Show detailed status of a specific budget."""
    
    async def get_budget_status():
        api = BudgetAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Loading budget status...", total=None)
            
            try:
                budget_status = await api.get_budget_status(budget_id)
                progress.update(task, description="✓ Budget status loaded")
                
                console.print(f"\n[bold blue]Budget Status: {budget_status.get('name', 'N/A')}[/bold blue]")
                console.print("=" * 50)
                
                # Basic info
                console.print(f"[bold]ID:[/bold] {budget_status.get('id', 'N/A')}")
                console.print(f"[bold]Period:[/bold] {budget_status.get('period', 'N/A')}")
                console.print(f"[bold]Limit:[/bold] {format_currency(budget_status.get('total_limit', 0))}")
                
                # Usage info
                spent = budget_status.get('spent_amount', 0)
                limit = budget_status.get('total_limit', 0)
                remaining = limit - spent
                usage_pct = (spent / limit * 100) if limit > 0 else 0
                
                console.print(f"[bold]Spent:[/bold] {format_currency(spent)}")
                console.print(f"[bold]Remaining:[/bold] {format_currency(remaining)}")
                console.print(f"[bold]Usage:[/bold] {format_percentage(usage_pct)}")
                
                # Status indicator
                if usage_pct > 100:
                    console.print(f"[bold]Status:[/bold] [red]EXCEEDED[/red]")
                elif usage_pct > 80:
                    console.print(f"[bold]Status:[/bold] [yellow]WARNING[/yellow]")
                else:
                    console.print(f"[bold]Status:[/bold] [green]ON TRACK[/green]")
                
                # Date range
                if budget_status.get('start_date'):
                    console.print(f"[bold]Start Date:[/bold] {format_date(budget_status['start_date'])}")
                if budget_status.get('end_date'):
                    console.print(f"[bold]End Date:[/bold] {format_date(budget_status['end_date'])}")
                
                # Categories
                if budget_status.get('categories'):
                    console.print(f"[bold]Categories:[/bold]")
                    for category in budget_status['categories']:
                        cat_spent = category.get('spent_amount', 0)
                        cat_limit = category.get('limit_amount', 0)
                        cat_pct = (cat_spent / cat_limit * 100) if cat_limit > 0 else 0
                        console.print(f"  • {category.get('category_name', 'N/A')}: {format_currency(cat_spent)} / {format_currency(cat_limit)} ({format_percentage(cat_pct)})")
                
                # Recent transactions
                if budget_status.get('recent_transactions'):
                    console.print(f"\n[bold]Recent Transactions:[/bold]")
                    for transaction in budget_status['recent_transactions'][:5]:
                        console.print(f"  • {format_date(transaction.get('date', ''))}: {transaction.get('description', 'N/A')} - {format_currency(transaction.get('amount', 0))}")
                
                console.print()
                
            except Exception as e:
                progress.update(task, description="✗ Failed to load budget status")
                console.print(f"[red]Error loading budget status: {e}[/red]")
    
    asyncio.run(get_budget_status())


@budgets_group.command()
@click.argument("budget_id", type=str)
@click.option("--name", "-n", type=str, help="New budget name")
@click.option("--limit", "-l", type=float, help="New budget limit")
@click.option("--alert-threshold", type=float, help="New alert threshold percentage")
@click.option("--description", type=str, help="New description")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.pass_context
def edit(ctx, budget_id: str, name: Optional[str], limit: Optional[float],
         alert_threshold: Optional[float], description: Optional[str], interactive: bool):
    """Edit an existing budget."""
    
    async def update_budget():
        api = BudgetAPI(ctx.obj['config'])
        
        try:
            # First, get the current budget
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Loading budget...", total=None)
                current_budget = await api.get_budget(budget_id)
                progress.update(task, description="✓ Budget loaded")
            
            if interactive:
                # Interactive mode - show current values and prompt for new ones
                console.print(f"\n[bold]Editing budget: {current_budget.get('name', 'N/A')}[/bold]")
                console.print("Press Enter to keep current value, or type new value:")
                
                name = name or Prompt.ask(
                    f"Name (current: {current_budget.get('name', '')})",
                    default=current_budget.get('name', '')
                )
                limit = limit or float(Prompt.ask(
                    f"Limit (current: {format_currency(current_budget.get('total_limit', 0))})",
                    default=str(current_budget.get('total_limit', 0))
                ))
                alert_threshold = alert_threshold or float(Prompt.ask(
                    f"Alert threshold % (current: {current_budget.get('alert_threshold', 0.8) * 100})",
                    default=str(current_budget.get('alert_threshold', 0.8) * 100)
                ))
                description = description or Prompt.ask(
                    f"Description (current: {current_budget.get('description', '')})",
                    default=current_budget.get('description', '')
                )
            
            # Prepare update data
            update_data = {}
            if name is not None:
                update_data["name"] = name
            
            if limit is not None:
                if not validate_amount(limit):
                    console.print("[red]Error: Budget limit must be positive[/red]")
                    return
                update_data["total_limit"] = limit
            
            if alert_threshold is not None:
                if alert_threshold < 0 or alert_threshold > 100:
                    console.print("[red]Error: Alert threshold must be between 0 and 100[/red]")
                    return
                update_data["alert_threshold"] = alert_threshold / 100
            
            if description is not None:
                update_data["description"] = description
            
            if not update_data:
                console.print("[yellow]No changes specified.[/yellow]")
                return
            
            # Update budget
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Updating budget...", total=None)
                updated_budget = await api.update_budget(budget_id, update_data)
                progress.update(task, description="✓ Budget updated successfully")
            
            console.print(f"\n[green]✓ Budget updated successfully![/green]")
            console.print(f"ID: {budget_id}")
            for key, value in update_data.items():
                if key == "total_limit":
                    console.print(f"Limit: {format_currency(value)}")
                elif key == "alert_threshold":
                    console.print(f"Alert threshold: {value * 100}%")
                else:
                    console.print(f"{key.title()}: {value}")
            
        except Exception as e:
            console.print(f"[red]Error updating budget: {e}[/red]")
    
    asyncio.run(update_budget())


@budgets_group.command()
@click.argument("budget_id", type=str)
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete(ctx, budget_id: str, force: bool):
    """Delete a budget."""
    
    async def remove_budget():
        api = BudgetAPI(ctx.obj['config'])
        
        try:
            # Get budget details for confirmation
            if not force:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("Loading budget...", total=None)
                    budget = await api.get_budget(budget_id)
                    progress.update(task, description="✓ Budget loaded")
                
                console.print(f"\n[bold]Budget to delete:[/bold]")
                console.print(f"Name: {budget.get('name', 'N/A')}")
                console.print(f"Limit: {format_currency(budget.get('total_limit', 0))}")
                console.print(f"Period: {budget.get('period', 'N/A')}")
                
                if not Confirm.ask("\nAre you sure you want to delete this budget?"):
                    console.print("[yellow]Deletion cancelled.[/yellow]")
                    return
            
            # Delete budget
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Deleting budget...", total=None)
                await api.delete_budget(budget_id)
                progress.update(task, description="✓ Budget deleted successfully")
            
            console.print(f"\n[green]✓ Budget deleted successfully![/green]")
            
        except Exception as e:
            console.print(f"[red]Error deleting budget: {e}[/red]")
    
    asyncio.run(remove_budget())


@budgets_group.command()
@click.pass_context
def alerts(ctx):
    """Show all budget alerts and warnings."""
    
    async def get_budget_alerts():
        api = BudgetAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Loading budget alerts...", total=None)
            
            try:
                budgets = await api.get_budgets()
                progress.update(task, description="✓ Budget alerts loaded")
                
                alerts = []
                warnings = []
                exceeded = []
                
                for budget in budgets:
                    spent = budget.get('spent_amount', 0)
                    limit = budget.get('total_limit', 0)
                    usage_pct = (spent / limit * 100) if limit > 0 else 0
                    alert_threshold = budget.get('alert_threshold', 0.8) * 100
                    
                    budget_info = {
                        'name': budget.get('name', 'N/A'),
                        'usage_pct': usage_pct,
                        'spent': spent,
                        'limit': limit,
                        'remaining': limit - spent
                    }
                    
                    if usage_pct > 100:
                        exceeded.append(budget_info)
                    elif usage_pct > alert_threshold:
                        warnings.append(budget_info)
                
                console.print(f"\n[bold blue]Budget Alerts Summary[/bold blue]")
                console.print("=" * 40)
                
                if exceeded:
                    console.print(f"\n[bold red]🚨 EXCEEDED BUDGETS ({len(exceeded)})[/bold red]")
                    for budget in exceeded:
                        console.print(f"  • {budget['name']}: {format_percentage(budget['usage_pct'])} ({format_currency(budget['spent'])} / {format_currency(budget['limit'])})")
                        console.print(f"    Over by: {format_currency(abs(budget['remaining']))}")
                
                if warnings:
                    console.print(f"\n[bold yellow]⚠️  WARNING BUDGETS ({len(warnings)})[/bold yellow]")
                    for budget in warnings:
                        console.print(f"  • {budget['name']}: {format_percentage(budget['usage_pct'])} ({format_currency(budget['spent'])} / {format_currency(budget['limit'])})")
                        console.print(f"    Remaining: {format_currency(budget['remaining'])}")
                
                if not exceeded and not warnings:
                    console.print(f"\n[green]✓ All budgets are on track![/green]")
                
                console.print()
                
            except Exception as e:
                progress.update(task, description="✗ Failed to load budget alerts")
                console.print(f"[red]Error loading budget alerts: {e}[/red]")
    
    asyncio.run(get_budget_alerts())


@budgets_group.command()
@click.pass_context
def summary(ctx):
    """Show budget summary statistics."""
    
    async def get_budget_summary():
        api = BudgetAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Calculating budget summary...", total=None)
            
            try:
                budgets = await api.get_budgets()
                progress.update(task, description="✓ Budget summary calculated")
                
                if not budgets:
                    console.print("[yellow]No budgets found.[/yellow]")
                    return
                
                total_budgets = len(budgets)
                total_limit = sum(b.get('total_limit', 0) for b in budgets)
                total_spent = sum(b.get('spent_amount', 0) for b in budgets)
                total_remaining = total_limit - total_spent
                overall_usage = (total_spent / total_limit * 100) if total_limit > 0 else 0
                
                # Count by status
                on_track = 0
                warning = 0
                exceeded = 0
                
                for budget in budgets:
                    spent = budget.get('spent_amount', 0)
                    limit = budget.get('total_limit', 0)
                    usage_pct = (spent / limit * 100) if limit > 0 else 0
                    alert_threshold = budget.get('alert_threshold', 0.8) * 100
                    
                    if usage_pct > 100:
                        exceeded += 1
                    elif usage_pct > alert_threshold:
                        warning += 1
                    else:
                        on_track += 1
                
                console.print(f"\n[bold blue]Budget Summary[/bold blue]")
                console.print("=" * 40)
                console.print(f"[bold]Total Budgets:[/bold] {total_budgets}")
                console.print(f"[bold]Total Budget Limit:[/bold] {format_currency(total_limit)}")
                console.print(f"[bold]Total Spent:[/bold] {format_currency(total_spent)}")
                console.print(f"[bold]Total Remaining:[/bold] {format_currency(total_remaining)}")
                console.print(f"[bold]Overall Usage:[/bold] {format_percentage(overall_usage)}")
                
                console.print(f"\n[bold]Budget Status:[/bold]")
                console.print(f"  [green]On Track:[/green] {on_track}")
                console.print(f"  [yellow]Warning:[/yellow] {warning}")
                console.print(f"  [red]Exceeded:[/red] {exceeded}")
                
                console.print()
                
            except Exception as e:
                progress.update(task, description="✗ Failed to calculate budget summary")
                console.print(f"[red]Error calculating budget summary: {e}[/red]")
    
    asyncio.run(get_budget_summary())