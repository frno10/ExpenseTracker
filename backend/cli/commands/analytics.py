"""
Analytics commands for the CLI.
"""
import click
import asyncio
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
import json

from cli.utils.api import AnalyticsAPI
from cli.utils.formatters import (
    format_currency, format_date, format_percentage, 
    format_anomalies_table, format_summary_stats
)

console = Console()


@click.group(name="analytics")
def analytics_group():
    """Advanced analytics and insights for your expenses."""
    pass


@analytics_group.command()
@click.option("--period", "-p", type=int, default=30, help="Period in days (default: 30)")
@click.pass_context
def dashboard(ctx, period: int):
    """Show analytics dashboard with key metrics."""
    
    async def show_dashboard():
        api = AnalyticsAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Loading dashboard analytics...", total=None)
            
            try:
                dashboard_data = await api.get_dashboard_stats(period)
                progress.update(task, description="✓ Dashboard analytics loaded")
                
                console.print(f"\n[bold blue]📊 Analytics Dashboard - Last {period} Days[/bold blue]")
                console.print("=" * 60)
                
                # Key metrics
                summary = dashboard_data.get('summary', {})
                console.print(f"\n[bold]Key Metrics:[/bold]")
                console.print(f"💰 Total Spending: {format_currency(summary.get('total_spending', 0))}")
                console.print(f"📝 Transactions: {summary.get('transaction_count', 0):,}")
                console.print(f"📈 Average Transaction: {format_currency(summary.get('average_transaction', 0))}")
                console.print(f"📊 Daily Average: {format_currency(summary.get('daily_average', 0))}")
                
                # Trend
                trend = dashboard_data.get('trend', {})
                trend_direction = trend.get('direction', 'stable')
                trend_pct = trend.get('change_percentage', 0)
                
                if trend_direction == 'up':
                    trend_icon = "📈"
                    trend_color = "red"
                elif trend_direction == 'down':
                    trend_icon = "📉"
                    trend_color = "green"
                else:
                    trend_icon = "➡️"
                    trend_color = "yellow"
                
                console.print(f"\n[bold]Trend:[/bold]")
                console.print(f"{trend_icon} [{trend_color}]{trend_direction.title()} {abs(trend_pct):.1f}% vs previous period[/{trend_color}]")
                
                # Top categories
                categories = dashboard_data.get('category_breakdown', [])
                if categories:
                    console.print(f"\n[bold]Top Categories:[/bold]")
                    for i, category in enumerate(categories[:5], 1):
                        console.print(f"  {i}. {category.get('category', 'N/A')}: {format_currency(category.get('amount', 0))} ({format_percentage(category.get('percentage', 0))})")
                
                # Anomalies
                anomalies = dashboard_data.get('anomalies', [])
                if anomalies:
                    console.print(f"\n[bold]🚨 Anomalies Detected: {len(anomalies)}[/bold]")
                    for anomaly in anomalies[:3]:
                        severity = anomaly.get('severity', 'low')
                        severity_icon = "🔴" if severity == 'high' else "🟡" if severity == 'medium' else "🟢"
                        console.print(f"  {severity_icon} {anomaly.get('description', 'N/A')}")
                    
                    if len(anomalies) > 3:
                        console.print(f"  ... and {len(anomalies) - 3} more")
                
                # Insights
                insights = dashboard_data.get('insights', [])
                if insights:
                    console.print(f"\n[bold]💡 Insights:[/bold]")
                    for insight in insights[:3]:
                        console.print(f"  • {insight}")
                
                console.print()
                
            except Exception as e:
                progress.update(task, description="✗ Failed to load dashboard")
                console.print(f"[red]Error loading dashboard analytics: {e}[/red]")
    
    asyncio.run(show_dashboard())


@analytics_group.command()
@click.option("--period", "-p", type=int, default=90, help="Period in days (default: 90)")
@click.option("--category", "-c", type=str, help="Filter by category")
@click.option("--format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def trends(ctx, period: int, category: Optional[str], format: str):
    """Analyze spending trends over time."""
    
    filters = {'period_days': period}
    if category:
        filters['category'] = category
    
    async def show_trends():
        api = AnalyticsAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing spending trends...", total=None)
            
            try:
                trends_data = await api.get_spending_trends(filters)
                progress.update(task, description="✓ Trends analysis completed")
                
                if format == "json":
                    console.print(json.dumps(trends_data, indent=2, default=str))
                    return
                
                console.print(f"\n[bold blue]📈 Spending Trends Analysis - Last {period} Days[/bold blue]")
                if category:
                    console.print(f"Category: {category}")
                console.print("=" * 60)
                
                # Overall trend
                overall_trend = trends_data.get('overall_trend', {})
                direction = overall_trend.get('direction', 'stable')
                change_pct = overall_trend.get('change_percentage', 0)
                
                console.print(f"\n[bold]Overall Trend:[/bold]")
                if direction == 'increasing':
                    console.print(f"📈 [red]Spending is increasing by {change_pct:.1f}% per week[/red]")
                elif direction == 'decreasing':
                    console.print(f"📉 [green]Spending is decreasing by {abs(change_pct):.1f}% per week[/green]")
                else:
                    console.print(f"➡️ [yellow]Spending is stable (±{abs(change_pct):.1f}% variation)[/yellow]")
                
                # Weekly breakdown
                weekly_data = trends_data.get('weekly_breakdown', [])
                if weekly_data:
                    console.print(f"\n[bold]Weekly Breakdown:[/bold]")
                    
                    table = Table(show_header=True, header_style="bold blue")
                    table.add_column("Week", style="cyan", width=15)
                    table.add_column("Amount", style="bold yellow", justify="right", width=12)
                    table.add_column("Transactions", style="green", justify="right", width=12)
                    table.add_column("Change", style="magenta", justify="right", width=10)
                    
                    for i, week in enumerate(weekly_data):
                        change = week.get('change_from_previous', 0)
                        change_str = f"{change:+.1f}%" if change != 0 else "—"
                        change_color = "red" if change > 0 else "green" if change < 0 else "white"
                        
                        table.add_row(
                            f"Week {i + 1}",
                            format_currency(week.get('amount', 0)),
                            str(week.get('transaction_count', 0)),
                            f"[{change_color}]{change_str}[/{change_color}]"
                        )
                    
                    console.print(table)
                
                # Seasonal patterns
                seasonal = trends_data.get('seasonal_patterns', {})
                if seasonal:
                    console.print(f"\n[bold]Seasonal Patterns:[/bold]")
                    best_day = seasonal.get('best_day_of_week', 'N/A')
                    worst_day = seasonal.get('worst_day_of_week', 'N/A')
                    console.print(f"  📅 Lowest spending day: {best_day}")
                    console.print(f"  📅 Highest spending day: {worst_day}")
                    
                    if seasonal.get('monthly_pattern'):
                        console.print(f"  📊 Monthly pattern: {seasonal['monthly_pattern']}")
                
                console.print()
                
            except Exception as e:
                progress.update(task, description="✗ Failed to analyze trends")
                console.print(f"[red]Error analyzing trends: {e}[/red]")
    
    asyncio.run(show_trends())


@analytics_group.command()
@click.option("--period", "-p", type=int, default=30, help="Period in days (default: 30)")
@click.option("--format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def categories(ctx, period: int, format: str):
    """Analyze spending by category."""
    
    filters = {'period_days': period}
    
    async def show_category_analysis():
        api = AnalyticsAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing categories...", total=None)
            
            try:
                category_data = await api.get_category_breakdown(filters)
                progress.update(task, description="✓ Category analysis completed")
                
                if format == "json":
                    console.print(json.dumps(category_data, indent=2, default=str))
                    return
                
                console.print(f"\n[bold blue]🏷️ Category Analysis - Last {period} Days[/bold blue]")
                console.print("=" * 60)
                
                categories = category_data.get('categories', [])
                if not categories:
                    console.print("[yellow]No category data found.[/yellow]")
                    return
                
                # Summary
                total_amount = sum(c.get('amount', 0) for c in categories)
                console.print(f"\n[bold]Summary:[/bold]")
                console.print(f"💰 Total Spending: {format_currency(total_amount)}")
                console.print(f"🏷️ Categories: {len(categories)}")
                
                # Category table
                table = Table(show_header=True, header_style="bold blue")
                table.add_column("Category", style="white", min_width=20)
                table.add_column("Amount", style="bold yellow", justify="right", width=12)
                table.add_column("Transactions", style="green", justify="right", width=12)
                table.add_column("Percentage", style="cyan", justify="right", width=10)
                table.add_column("Avg/Transaction", style="magenta", justify="right", width=15)
                
                for category in categories:
                    amount = category.get('amount', 0)
                    count = category.get('count', 0)
                    percentage = category.get('percentage', 0)
                    avg_transaction = amount / count if count > 0 else 0
                    
                    table.add_row(
                        category.get('category', 'N/A'),
                        format_currency(amount),
                        str(count),
                        format_percentage(percentage),
                        format_currency(avg_transaction)
                    )
                
                console.print(f"\n[bold]Category Breakdown:[/bold]")
                console.print(table)
                
                # Top insights
                if len(categories) > 0:
                    top_category = categories[0]
                    console.print(f"\n[bold]💡 Insights:[/bold]")
                    console.print(f"  • Top category: {top_category.get('category', 'N/A')} ({format_percentage(top_category.get('percentage', 0))} of spending)")
                    
                    if len(categories) >= 3:
                        top_3_pct = sum(c.get('percentage', 0) for c in categories[:3])
                        console.print(f"  • Top 3 categories account for {format_percentage(top_3_pct)} of spending")
                
                console.print()
                
            except Exception as e:
                progress.update(task, description="✗ Failed to analyze categories")
                console.print(f"[red]Error analyzing categories: {e}[/red]")
    
    asyncio.run(show_category_analysis())


@analytics_group.command()
@click.option("--period", "-p", type=int, default=90, help="Period in days (default: 90)")
@click.option("--sensitivity", type=click.Choice(['low', 'medium', 'high']), default='medium', help="Anomaly detection sensitivity")
@click.option("--format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def anomalies(ctx, period: int, sensitivity: str, format: str):
    """Detect unusual spending patterns and anomalies."""
    
    filters = {
        'period_days': period,
        'sensitivity': sensitivity
    }
    
    async def detect_anomalies():
        api = AnalyticsAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Detecting anomalies...", total=None)
            
            try:
                anomalies = await api.get_anomalies(filters)
                progress.update(task, description="✓ Anomaly detection completed")
                
                if format == "json":
                    console.print(json.dumps(anomalies, indent=2, default=str))
                    return
                
                console.print(f"\n[bold blue]🚨 Spending Anomalies - Last {period} Days[/bold blue]")
                console.print(f"Sensitivity: {sensitivity.title()}")
                console.print("=" * 60)
                
                if not anomalies:
                    console.print("[green]✓ No anomalies detected! Your spending patterns look normal.[/green]")
                    return
                
                # Group by severity
                high_severity = [a for a in anomalies if a.get('severity') == 'high']
                medium_severity = [a for a in anomalies if a.get('severity') == 'medium']
                low_severity = [a for a in anomalies if a.get('severity') == 'low']
                
                console.print(f"\n[bold]Summary:[/bold]")
                console.print(f"🔴 High severity: {len(high_severity)}")
                console.print(f"🟡 Medium severity: {len(medium_severity)}")
                console.print(f"🟢 Low severity: {len(low_severity)}")
                
                # Show anomalies table
                if anomalies:
                    table = format_anomalies_table(anomalies)
                    console.print(f"\n[bold]Detected Anomalies:[/bold]")
                    console.print(table)
                
                # Recommendations
                if high_severity:
                    console.print(f"\n[bold red]⚠️ Recommendations:[/bold red]")
                    console.print("  • Review high-severity anomalies for potential fraud or errors")
                    console.print("  • Check if unusual transactions are legitimate")
                    console.print("  • Consider setting up budget alerts for affected categories")
                
                console.print()
                
            except Exception as e:
                progress.update(task, description="✗ Failed to detect anomalies")
                console.print(f"[red]Error detecting anomalies: {e}[/red]")
    
    asyncio.run(detect_anomalies())


@analytics_group.command()
@click.option("--period", "-p", type=int, default=30, help="Period in days (default: 30)")
@click.pass_context
def insights(ctx, period: int):
    """Get AI-generated insights about your spending."""
    
    async def get_insights():
        api = AnalyticsAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating insights...", total=None)
            
            try:
                dashboard_data = await api.get_dashboard_stats(period)
                progress.update(task, description="✓ Insights generated")
                
                console.print(f"\n[bold blue]💡 AI Insights - Last {period} Days[/bold blue]")
                console.print("=" * 50)
                
                insights = dashboard_data.get('insights', [])
                if insights:
                    for i, insight in enumerate(insights, 1):
                        console.print(f"\n[bold]{i}.[/bold] {insight}")
                else:
                    console.print("\n[yellow]No specific insights available at this time.[/yellow]")
                    console.print("Try increasing the analysis period or add more transaction data.")
                
                # General recommendations
                summary = dashboard_data.get('summary', {})
                if summary.get('total_spending', 0) > 0:
                    console.print(f"\n[bold]💡 General Recommendations:[/bold]")
                    
                    # Budget recommendation
                    daily_avg = summary.get('daily_average', 0)
                    monthly_projection = daily_avg * 30
                    console.print(f"  • Based on current spending, budget ~{format_currency(monthly_projection)} per month")
                    
                    # Category diversification
                    categories = dashboard_data.get('category_breakdown', [])
                    if categories and len(categories) > 0:
                        top_category_pct = categories[0].get('percentage', 0)
                        if top_category_pct > 50:
                            console.print(f"  • Consider diversifying spending - {categories[0].get('category')} accounts for {format_percentage(top_category_pct)}")
                    
                    # Anomaly check
                    anomalies = dashboard_data.get('anomalies', [])
                    if anomalies:
                        console.print(f"  • Review {len(anomalies)} detected anomalies for potential savings")
                
                console.print()
                
            except Exception as e:
                progress.update(task, description="✗ Failed to generate insights")
                console.print(f"[red]Error generating insights: {e}[/red]")
    
    asyncio.run(get_insights())


@analytics_group.command()
@click.option("--months", "-m", type=int, default=6, help="Number of months to forecast (default: 6)")
@click.option("--category", "-c", type=str, help="Forecast for specific category")
@click.pass_context
def forecast(ctx, months: int, category: Optional[str]):
    """Generate spending forecasts based on historical data."""
    
    filters = {'forecast_months': months}
    if category:
        filters['category'] = category
    
    async def generate_forecast():
        api = AnalyticsAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating forecast...", total=None)
            
            try:
                # This would call a forecast endpoint
                # For now, show a placeholder
                progress.update(task, description="✓ Forecast generated")
                
                console.print(f"\n[bold blue]🔮 Spending Forecast - Next {months} Months[/bold blue]")
                if category:
                    console.print(f"Category: {category}")
                console.print("=" * 50)
                
                console.print("\n[yellow]📊 Forecasting feature coming soon![/yellow]")
                console.print("This will provide:")
                console.print("  • Predicted monthly spending based on trends")
                console.print("  • Seasonal adjustments")
                console.print("  • Confidence intervals")
                console.print("  • Budget recommendations")
                console.print()
                
            except Exception as e:
                progress.update(task, description="✗ Failed to generate forecast")
                console.print(f"[red]Error generating forecast: {e}[/red]")
    
    asyncio.run(generate_forecast())