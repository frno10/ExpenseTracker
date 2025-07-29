"""
Analytics and reporting commands.
"""
from datetime import date, datetime, timedelta
from typing import Optional
import sys

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.columns import Columns

from ..api.client import APIClient
from ..utils.exceptions import ExpenseTrackerCLIError
from ..utils.serialization import format_output
from ..config import Config


@click.group()
def analytics():
    """Analytics and reporting commands."""
    pass


@analytics.command()
@click.option("--period", type=click.Choice(["daily", "weekly", "monthly"]), default="monthly", help="Trend period")
@click.option("--date-from", type=click.DateTime(formats=["%Y-%m-%d"]), help="Start date")
@click.option("--date-to", type=click.DateTime(formats=["%Y-%m-%d"]), help="End date")
@click.pass_context
def trends(
    ctx,
    period: str,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
):
    """Show spending trends over time."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        # Set default date range if not provided
        if not date_from or not date_to:
            today = date.today()
            if period == "daily":
                date_from = datetime.combine(today - timedelta(days=30), datetime.min.time())
                date_to = datetime.combine(today, datetime.max.time())
            elif period == "weekly":
                date_from = datetime.combine(today - timedelta(weeks=12), datetime.min.time())
                date_to = datetime.combine(today, datetime.max.time())
            else:  # monthly
                date_from = datetime.combine(today - timedelta(days=365), datetime.min.time())
                date_to = datetime.combine(today, datetime.max.time())
        
        params = {
            "period": period,
            "date_from": date_from.strftime("%Y-%m-%d"),
            "date_to": date_to.strftime("%Y-%m-%d"),
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Loading trends...", total=None)
            trends_data = client.get_expense_trends(params)
        
        trends = trends_data.get("trends", [])
        summary = trends_data.get("summary", {})
        
        if not trends:
            console.print("[yellow]No trend data available for the specified period.[/yellow]")
            return
        
        # Display trends table
        table = Table(title=f"Spending Trends - {period.title()}")
        table.add_column("Period", style="cyan")
        table.add_column("Amount", style="green", justify="right")
        table.add_column("Transactions", style="blue", justify="right")
        table.add_column("Avg per Transaction", style="magenta", justify="right")
        
        for trend in trends:
            avg_amount = trend["amount"] / trend["count"] if trend["count"] > 0 else 0
            table.add_row(
                trend["period"],
                f"{config.display.currency}{trend['amount']:.2f}",
                str(trend["count"]),
                f"{config.display.currency}{avg_amount:.2f}",
            )
        
        console.print(table)
        
        # Display summary
        if summary:
            console.print(f"\n[bold]Summary:[/bold]")
            console.print(f"[blue]Total Amount:[/blue] {config.display.currency}{summary.get('total_amount', 0):.2f}")
            console.print(f"[blue]Average per Period:[/blue] {config.display.currency}{summary.get('average_per_period', 0):.2f}")
            console.print(f"[blue]Highest Period:[/blue] {config.display.currency}{summary.get('highest_amount', 0):.2f}")
            console.print(f"[blue]Lowest Period:[/blue] {config.display.currency}{summary.get('lowest_amount', 0):.2f}")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to get trends: {e}")


@analytics.command()
@click.option("--date-from", type=click.DateTime(formats=["%Y-%m-%d"]), help="Start date")
@click.option("--date-to", type=click.DateTime(formats=["%Y-%m-%d"]), help="End date")
@click.pass_context
def categories(
    ctx,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
):
    """Show spending breakdown by category."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        # Set default date range if not provided
        if not date_from or not date_to:
            today = date.today()
            date_from = datetime.combine(today.replace(day=1), datetime.min.time())
            date_to = datetime.combine(today, datetime.max.time())
        
        params = {
            "date_from": date_from.strftime("%Y-%m-%d"),
            "date_to": date_to.strftime("%Y-%m-%d"),
            "group_by": "category",
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Loading category breakdown...", total=None)
            stats = client.get_expense_statistics(params)
        
        category_breakdown = stats.get("category_breakdown", [])
        total_amount = stats.get("total_amount", 0)
        
        if not category_breakdown:
            console.print("[yellow]No category data available for the specified period.[/yellow]")
            return
        
        # Sort by amount descending
        category_breakdown.sort(key=lambda x: x["total_amount"], reverse=True)
        
        # Display category breakdown table
        table = Table(title=f"Category Breakdown ({date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')})")
        table.add_column("Category", style="magenta")
        table.add_column("Amount", style="green", justify="right")
        table.add_column("Transactions", style="blue", justify="right")
        table.add_column("Percentage", style="yellow", justify="right")
        table.add_column("Avg per Transaction", style="cyan", justify="right")
        
        for category_data in category_breakdown:
            percentage = (category_data["total_amount"] / total_amount * 100) if total_amount > 0 else 0
            avg_amount = category_data["total_amount"] / category_data["expense_count"] if category_data["expense_count"] > 0 else 0
            
            table.add_row(
                category_data["category_name"],
                f"{config.display.currency}{category_data['total_amount']:.2f}",
                str(category_data["expense_count"]),
                f"{percentage:.1f}%",
                f"{config.display.currency}{avg_amount:.2f}",
            )
        
        console.print(table)
        
        # Display summary
        console.print(f"\n[bold]Total:[/bold] {config.display.currency}{total_amount:.2f}")
        console.print(f"[bold]Categories:[/bold] {len(category_breakdown)}")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to get category breakdown: {e}")


@analytics.command()
@click.option("--period", type=click.Choice(["week", "month", "quarter", "year"]), default="month", help="Comparison period")
@click.option("--periods", type=int, default=3, help="Number of periods to compare")
@click.pass_context
def compare(
    ctx,
    period: str,
    periods: int,
):
    """Compare spending across different periods."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        today = date.today()
        period_data = []
        
        for i in range(periods):
            if period == "week":
                end_date = today - timedelta(weeks=i)
                start_date = end_date - timedelta(days=6)
                period_name = f"Week of {start_date.strftime('%Y-%m-%d')}"
            elif period == "month":
                if i == 0:
                    end_date = today
                    start_date = today.replace(day=1)
                else:
                    # Previous months
                    year = today.year
                    month = today.month - i
                    if month <= 0:
                        month += 12
                        year -= 1
                    start_date = date(year, month, 1)
                    # Last day of month
                    if month == 12:
                        end_date = date(year + 1, 1, 1) - timedelta(days=1)
                    else:
                        end_date = date(year, month + 1, 1) - timedelta(days=1)
                period_name = start_date.strftime("%B %Y")
            elif period == "quarter":
                quarter = ((today.month - 1) // 3) - i
                year = today.year
                if quarter < 0:
                    quarter += 4
                    year -= 1
                start_month = quarter * 3 + 1
                start_date = date(year, start_month, 1)
                end_date = date(year, start_month + 2, 1)
                # Last day of quarter
                if end_date.month == 12:
                    end_date = date(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(year, end_date.month + 1, 1) - timedelta(days=1)
                period_name = f"Q{quarter + 1} {year}"
            else:  # year
                year = today.year - i
                start_date = date(year, 1, 1)
                end_date = date(year, 12, 31)
                period_name = str(year)
            
            params = {
                "date_from": start_date.strftime("%Y-%m-%d"),
                "date_to": end_date.strftime("%Y-%m-%d"),
            }
            
            with Progress(
                SpinnerColumn(),
                TextColumn(f"[progress.description]Loading {period_name}..."),
                console=console,
            ) as progress:
                task = progress.add_task("", total=None)
                stats = client.get_expense_statistics(params)
            
            period_data.append({
                "name": period_name,
                "total_amount": stats.get("total_amount", 0),
                "expense_count": stats.get("expense_count", 0),
                "average_amount": stats.get("average_amount", 0),
            })
        
        # Display comparison table
        table = Table(title=f"{period.title()} Comparison")
        table.add_column("Period", style="cyan")
        table.add_column("Total Amount", style="green", justify="right")
        table.add_column("Transactions", style="blue", justify="right")
        table.add_column("Avg per Transaction", style="magenta", justify="right")
        table.add_column("Change", style="yellow", justify="right")
        
        for i, data in enumerate(period_data):
            change = ""
            if i > 0:
                prev_amount = period_data[i - 1]["total_amount"]
                if prev_amount > 0:
                    change_pct = ((data["total_amount"] - prev_amount) / prev_amount) * 100
                    if change_pct > 0:
                        change = f"+{change_pct:.1f}%"
                    else:
                        change = f"{change_pct:.1f}%"
            
            table.add_row(
                data["name"],
                f"{config.display.currency}{data['total_amount']:.2f}",
                str(data["expense_count"]),
                f"{config.display.currency}{data['average_amount']:.2f}",
                change,
            )
        
        console.print(table)
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to compare periods: {e}")


@analytics.command()
@click.pass_context
def dashboard(ctx):
    """Show analytics dashboard with key metrics."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Loading dashboard data...", total=None)
            dashboard_stats = client.get_dashboard_stats()
        
        # Create dashboard panels
        panels = []
        
        # Total expenses panel
        total_panel = Panel(
            f"[bold green]{dashboard_stats.get('total_expenses', 0)}[/bold green]\nTotal Expenses",
            title="📊 Expenses",
            border_style="green",
        )
        panels.append(total_panel)
        
        # Monthly spending panel
        monthly_spending = dashboard_stats.get('monthly_spending', 0)
        monthly_trend = dashboard_stats.get('monthly_trend', 0)
        trend_indicator = "📈" if monthly_trend > 0 else "📉" if monthly_trend < 0 else "➡️"
        
        monthly_panel = Panel(
            f"[bold blue]{config.display.currency}{monthly_spending:.2f}[/bold blue]\nThis Month\n{trend_indicator} {monthly_trend:+.1f}%",
            title="💰 Monthly",
            border_style="blue",
        )
        panels.append(monthly_panel)
        
        # Categories panel
        categories_panel = Panel(
            f"[bold magenta]{dashboard_stats.get('categories_count', 0)}[/bold magenta]\nActive Categories",
            title="🏷️ Categories",
            border_style="magenta",
        )
        panels.append(categories_panel)
        
        # Budget usage panel
        budget_usage = dashboard_stats.get('budget_usage', 0)
        budget_color = "red" if budget_usage > 90 else "yellow" if budget_usage > 75 else "green"
        
        budget_panel = Panel(
            f"[bold {budget_color}]{budget_usage:.1f}%[/bold {budget_color}]\nBudget Used",
            title="🎯 Budget",
            border_style=budget_color,
        )
        panels.append(budget_panel)
        
        # Display panels in columns
        console.print(Columns(panels, equal=True, expand=True))
        
        # Show recent activity summary
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        
        params = {
            "date_from": week_start.strftime("%Y-%m-%d"),
            "date_to": today.strftime("%Y-%m-%d"),
        }
        
        week_stats = client.get_expense_statistics(params)
        
        console.print(f"\n[bold]This Week Summary:[/bold]")
        console.print(f"[blue]Expenses:[/blue] {week_stats.get('expense_count', 0)}")
        console.print(f"[blue]Amount:[/blue] {config.display.currency}{week_stats.get('total_amount', 0):.2f}")
        console.print(f"[blue]Daily Average:[/blue] {config.display.currency}{week_stats.get('total_amount', 0) / 7:.2f}")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to load dashboard: {e}")


@analytics.command()
@click.option("--top", type=int, default=10, help="Number of top expenses to show")
@click.option("--period", type=click.Choice(["week", "month", "quarter", "year", "all"]), default="month", help="Time period")
@click.pass_context
def top(ctx, top: int, period: str):
    """Show top expenses by amount."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        # Calculate date range
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
        elif period == "year":
            date_from = today.replace(month=1, day=1)
            date_to = today
        else:  # all
            date_from = None
            date_to = None
        
        filters = {"size": top}
        if date_from and date_to:
            filters["date_from"] = date_from.strftime("%Y-%m-%d")
            filters["date_to"] = date_to.strftime("%Y-%m-%d")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Loading top expenses...", total=None)
            response = client.get_expenses(filters)
        
        expenses = response.get("items", [])
        
        # Sort by amount descending
        expenses.sort(key=lambda x: float(x.get("amount", 0)), reverse=True)
        expenses = expenses[:top]
        
        if not expenses:
            console.print(f"[yellow]No expenses found for {period}.[/yellow]")
            return
        
        table = Table(title=f"Top {len(expenses)} Expenses - {period.title()}")
        table.add_column("Rank", style="cyan", justify="right")
        table.add_column("Date", style="blue")
        table.add_column("Description", style="white")
        table.add_column("Category", style="magenta")
        table.add_column("Amount", style="green", justify="right")
        
        for i, expense in enumerate(expenses, 1):
            table.add_row(
                str(i),
                expense.get("date", ""),
                expense.get("description", "")[:40] + ("..." if len(expense.get("description", "")) > 40 else ""),
                expense.get("category", ""),
                f"{config.display.currency}{expense.get('amount', 0):.2f}",
            )
        
        console.print(table)
        
        # Show summary
        total_amount = sum(float(expense.get("amount", 0)) for expense in expenses)
        console.print(f"\n[bold]Total of top {len(expenses)}:[/bold] {config.display.currency}{total_amount:.2f}")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to get top expenses: {e}")