"""
Report generation commands for the CLI.
"""
import click
import asyncio
from datetime import datetime, date, timedelta
from typing import Optional, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from pathlib import Path
import json

from cli.utils.api import ReportsAPI
from cli.utils.formatters import (
    format_currency, format_date, format_percentage, 
    format_category_breakdown, format_summary_stats
)
from cli.utils.validators import validate_date, validate_date_range

console = Console()


@click.group(name="reports")
def reports_group():
    """Generate various financial reports and summaries."""
    pass


@reports_group.command()
@click.option("--month", "-m", type=str, help="Month in YYYY-MM format (default: current month)")
@click.option("--category", "-c", type=str, help="Filter by category")
@click.option("--account", "-a", type=str, help="Filter by account")
@click.option("--format", type=click.Choice(["table", "json", "csv"]), default="table", help="Output format")
@click.option("--save", "-s", type=str, help="Save report to file")
@click.pass_context
def monthly(ctx, month: Optional[str], category: Optional[str], account: Optional[str], 
           format: str, save: Optional[str]):
    """Generate a monthly expense report."""
    
    # Determine date range
    if month:
        try:
            year, month_num = map(int, month.split('-'))
            start_date = date(year, month_num, 1)
            # Get last day of month
            if month_num == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month_num + 1, 1) - timedelta(days=1)
        except ValueError:
            console.print("[red]Error: Invalid month format. Use YYYY-MM[/red]")
            return
    else:
        # Current month
        today = date.today()
        start_date = date(today.year, today.month, 1)
        if today.month == 12:
            end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
    
    # Prepare filters
    filters = {
        'date_from': start_date.isoformat(),
        'date_to': end_date.isoformat()
    }
    if category:
        filters['category'] = category
    if account:
        filters['account'] = account
    
    async def generate_monthly_report():
        api = ReportsAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating monthly report...", total=None)
            
            try:
                report_data = await api.generate_report('monthly', filters, format)
                progress.update(task, description="✓ Monthly report generated")
                
                if format == "json":
                    output = json.dumps(report_data, indent=2, default=str)
                elif format == "csv":
                    # CSV format would be handled by the API
                    output = report_data.get('csv_data', 'CSV data not available')
                else:
                    # Table format
                    output = format_monthly_report_table(report_data, start_date, end_date)
                
                if save:
                    # Save to file
                    try:
                        with open(save, 'w') as f:
                            f.write(output)
                        console.print(f"[green]✓ Report saved to {save}[/green]")
                    except Exception as e:
                        console.print(f"[red]Error saving report: {e}[/red]")
                else:
                    # Display on console
                    console.print(output)
                
            except Exception as e:
                progress.update(task, description="✗ Failed to generate report")
                console.print(f"[red]Error generating monthly report: {e}[/red]")
    
    asyncio.run(generate_monthly_report())


@reports_group.command()
@click.option("--year", "-y", type=int, help="Year (default: current year)")
@click.option("--category", "-c", type=str, help="Filter by category")
@click.option("--format", type=click.Choice(["table", "json", "csv"]), default="table", help="Output format")
@click.option("--save", "-s", type=str, help="Save report to file")
@click.pass_context
def yearly(ctx, year: Optional[int], category: Optional[str], format: str, save: Optional[str]):
    """Generate a yearly expense report."""
    
    # Determine year
    if not year:
        year = date.today().year
    
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    
    # Prepare filters
    filters = {
        'date_from': start_date.isoformat(),
        'date_to': end_date.isoformat()
    }
    if category:
        filters['category'] = category
    
    async def generate_yearly_report():
        api = ReportsAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating yearly report...", total=None)
            
            try:
                report_data = await api.generate_report('yearly', filters, format)
                progress.update(task, description="✓ Yearly report generated")
                
                if format == "json":
                    output = json.dumps(report_data, indent=2, default=str)
                elif format == "csv":
                    output = report_data.get('csv_data', 'CSV data not available')
                else:
                    # Table format
                    output = format_yearly_report_table(report_data, year)
                
                if save:
                    try:
                        with open(save, 'w') as f:
                            f.write(output)
                        console.print(f"[green]✓ Report saved to {save}[/green]")
                    except Exception as e:
                        console.print(f"[red]Error saving report: {e}[/red]")
                else:
                    console.print(output)
                
            except Exception as e:
                progress.update(task, description="✗ Failed to generate report")
                console.print(f"[red]Error generating yearly report: {e}[/red]")
    
    asyncio.run(generate_yearly_report())


@reports_group.command()
@click.option("--start-date", type=str, required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end-date", type=str, required=True, help="End date (YYYY-MM-DD)")
@click.option("--category", "-c", type=str, help="Filter by category")
@click.option("--account", "-a", type=str, help="Filter by account")
@click.option("--format", type=click.Choice(["table", "json", "csv"]), default="table", help="Output format")
@click.option("--save", "-s", type=str, help="Save report to file")
@click.pass_context
def custom(ctx, start_date: str, end_date: str, category: Optional[str], 
          account: Optional[str], format: str, save: Optional[str]):
    """Generate a custom date range report."""
    
    # Validate dates
    if not validate_date(start_date):
        console.print("[red]Error: Invalid start date format. Use YYYY-MM-DD[/red]")
        return
    
    if not validate_date(end_date):
        console.print("[red]Error: Invalid end date format. Use YYYY-MM-DD[/red]")
        return
    
    if not validate_date_range(start_date, end_date):
        console.print("[red]Error: Start date must be before end date[/red]")
        return
    
    # Prepare filters
    filters = {
        'date_from': start_date,
        'date_to': end_date
    }
    if category:
        filters['category'] = category
    if account:
        filters['account'] = account
    
    async def generate_custom_report():
        api = ReportsAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating custom report...", total=None)
            
            try:
                report_data = await api.generate_report('custom', filters, format)
                progress.update(task, description="✓ Custom report generated")
                
                if format == "json":
                    output = json.dumps(report_data, indent=2, default=str)
                elif format == "csv":
                    output = report_data.get('csv_data', 'CSV data not available')
                else:
                    # Table format
                    output = format_custom_report_table(report_data, start_date, end_date)
                
                if save:
                    try:
                        with open(save, 'w') as f:
                            f.write(output)
                        console.print(f"[green]✓ Report saved to {save}[/green]")
                    except Exception as e:
                        console.print(f"[red]Error saving report: {e}[/red]")
                else:
                    console.print(output)
                
            except Exception as e:
                progress.update(task, description="✗ Failed to generate report")
                console.print(f"[red]Error generating custom report: {e}[/red]")
    
    asyncio.run(generate_custom_report())


@reports_group.command()
@click.option("--year", "-y", type=int, help="Tax year (default: current year)")
@click.option("--format", type=click.Choice(["table", "json", "csv"]), default="table", help="Output format")
@click.option("--save", "-s", type=str, help="Save report to file")
@click.pass_context
def tax(ctx, year: Optional[int], format: str, save: Optional[str]):
    """Generate a tax-focused expense report."""
    
    # Determine year
    if not year:
        year = date.today().year
    
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    
    filters = {
        'date_from': start_date.isoformat(),
        'date_to': end_date.isoformat(),
        'tax_categories_only': True
    }
    
    async def generate_tax_report():
        api = ReportsAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating tax report...", total=None)
            
            try:
                report_data = await api.generate_report('tax', filters, format)
                progress.update(task, description="✓ Tax report generated")
                
                if format == "json":
                    output = json.dumps(report_data, indent=2, default=str)
                elif format == "csv":
                    output = report_data.get('csv_data', 'CSV data not available')
                else:
                    # Table format
                    output = format_tax_report_table(report_data, year)
                
                if save:
                    try:
                        with open(save, 'w') as f:
                            f.write(output)
                        console.print(f"[green]✓ Tax report saved to {save}[/green]")
                    except Exception as e:
                        console.print(f"[red]Error saving report: {e}[/red]")
                else:
                    console.print(output)
                
            except Exception as e:
                progress.update(task, description="✗ Failed to generate report")
                console.print(f"[red]Error generating tax report: {e}[/red]")
    
    asyncio.run(generate_tax_report())


@reports_group.command()
@click.option("--format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def categories(ctx, format: str):
    """Generate a category breakdown report."""
    
    async def generate_category_report():
        api = ReportsAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating category report...", total=None)
            
            try:
                report_data = await api.generate_report('categories', {}, format)
                progress.update(task, description="✓ Category report generated")
                
                if format == "json":
                    console.print(json.dumps(report_data, indent=2, default=str))
                else:
                    # Table format
                    categories = report_data.get('categories', [])
                    if categories:
                        table = format_category_breakdown(categories)
                        console.print(f"\n[bold blue]Category Breakdown Report[/bold blue]")
                        console.print("=" * 50)
                        console.print(table)
                        
                        # Summary
                        total_amount = sum(c.get('amount', 0) for c in categories)
                        console.print(f"\n[bold]Total across all categories: {format_currency(total_amount)}[/bold]")
                    else:
                        console.print("[yellow]No category data found.[/yellow]")
                
            except Exception as e:
                progress.update(task, description="✗ Failed to generate report")
                console.print(f"[red]Error generating category report: {e}[/red]")
    
    asyncio.run(generate_category_report())


def format_monthly_report_table(report_data: dict, start_date: date, end_date: date) -> str:
    """Format monthly report as a table."""
    lines = []
    lines.append(f"\n📊 Monthly Expense Report")
    lines.append(f"📅 Period: {format_date(start_date.isoformat())} - {format_date(end_date.isoformat())}")
    lines.append("=" * 60)
    
    # Summary
    summary = report_data.get('summary', {})
    lines.append(f"\n💰 Total Expenses: {format_currency(summary.get('total_amount', 0))}")
    lines.append(f"📝 Total Transactions: {summary.get('transaction_count', 0):,}")
    lines.append(f"📈 Average Transaction: {format_currency(summary.get('average_amount', 0))}")
    lines.append(f"📊 Daily Average: {format_currency(summary.get('daily_average', 0))}")
    
    # Top categories
    categories = report_data.get('categories', [])
    if categories:
        lines.append(f"\n🏷️  Top Categories:")
        for i, category in enumerate(categories[:5], 1):
            lines.append(f"  {i}. {category.get('name', 'N/A')}: {format_currency(category.get('amount', 0))} ({category.get('count', 0)} transactions)")
    
    # Weekly breakdown
    weekly_data = report_data.get('weekly_breakdown', [])
    if weekly_data:
        lines.append(f"\n📅 Weekly Breakdown:")
        for week in weekly_data:
            lines.append(f"  Week {week.get('week_number', 'N/A')}: {format_currency(week.get('amount', 0))}")
    
    return "\n".join(lines)


def format_yearly_report_table(report_data: dict, year: int) -> str:
    """Format yearly report as a table."""
    lines = []
    lines.append(f"\n📊 Yearly Expense Report - {year}")
    lines.append("=" * 50)
    
    # Summary
    summary = report_data.get('summary', {})
    lines.append(f"\n💰 Total Expenses: {format_currency(summary.get('total_amount', 0))}")
    lines.append(f"📝 Total Transactions: {summary.get('transaction_count', 0):,}")
    lines.append(f"📈 Average Monthly: {format_currency(summary.get('monthly_average', 0))}")
    lines.append(f"📊 Average Transaction: {format_currency(summary.get('average_amount', 0))}")
    
    # Monthly breakdown
    monthly_data = report_data.get('monthly_breakdown', [])
    if monthly_data:
        lines.append(f"\n📅 Monthly Breakdown:")
        for month in monthly_data:
            month_name = datetime.strptime(f"{year}-{month.get('month', 1):02d}-01", "%Y-%m-%d").strftime("%B")
            lines.append(f"  {month_name}: {format_currency(month.get('amount', 0))}")
    
    # Top categories
    categories = report_data.get('categories', [])
    if categories:
        lines.append(f"\n🏷️  Top Categories:")
        for i, category in enumerate(categories[:10], 1):
            lines.append(f"  {i:2d}. {category.get('name', 'N/A')}: {format_currency(category.get('amount', 0))}")
    
    return "\n".join(lines)


def format_custom_report_table(report_data: dict, start_date: str, end_date: str) -> str:
    """Format custom report as a table."""
    lines = []
    lines.append(f"\n📊 Custom Expense Report")
    lines.append(f"📅 Period: {format_date(start_date)} - {format_date(end_date)}")
    lines.append("=" * 60)
    
    # Summary
    summary = report_data.get('summary', {})
    lines.append(f"\n💰 Total Expenses: {format_currency(summary.get('total_amount', 0))}")
    lines.append(f"📝 Total Transactions: {summary.get('transaction_count', 0):,}")
    lines.append(f"📈 Average Transaction: {format_currency(summary.get('average_amount', 0))}")
    
    # Calculate period length
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()
    days = (end - start).days + 1
    daily_avg = summary.get('total_amount', 0) / days if days > 0 else 0
    lines.append(f"📊 Daily Average: {format_currency(daily_avg)}")
    
    # Categories
    categories = report_data.get('categories', [])
    if categories:
        lines.append(f"\n🏷️  Category Breakdown:")
        for category in categories:
            lines.append(f"  • {category.get('name', 'N/A')}: {format_currency(category.get('amount', 0))} ({format_percentage(category.get('percentage', 0))})")
    
    return "\n".join(lines)


def format_tax_report_table(report_data: dict, year: int) -> str:
    """Format tax report as a table."""
    lines = []
    lines.append(f"\n🧾 Tax Expense Report - {year}")
    lines.append("=" * 50)
    
    # Summary
    summary = report_data.get('summary', {})
    lines.append(f"\n💰 Total Deductible Expenses: {format_currency(summary.get('total_deductible', 0))}")
    lines.append(f"📝 Total Transactions: {summary.get('transaction_count', 0):,}")
    
    # Tax categories
    tax_categories = report_data.get('tax_categories', [])
    if tax_categories:
        lines.append(f"\n🏷️  Deductible Categories:")
        for category in tax_categories:
            lines.append(f"  • {category.get('name', 'N/A')}: {format_currency(category.get('amount', 0))}")
            if category.get('description'):
                lines.append(f"    {category['description']}")
    
    # Important notes
    lines.append(f"\n⚠️  Important Notes:")
    lines.append(f"  • This report is for informational purposes only")
    lines.append(f"  • Consult a tax professional for official tax advice")
    lines.append(f"  • Keep all receipts and documentation")
    lines.append(f"  • Review categories for accuracy")
    
    return "\n".join(lines)