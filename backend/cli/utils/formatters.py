"""
Formatting utilities for CLI output.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from rich.table import Table
from rich.console import Console
import locale

# Try to set locale for currency formatting
try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    pass


def format_currency(amount: float) -> str:
    """Format amount as currency."""
    try:
        return locale.currency(amount, grouping=True)
    except:
        return f"${amount:,.2f}"


def format_date(date_str: str) -> str:
    """Format date string for display."""
    if not date_str:
        return "N/A"
    
    try:
        # Try parsing as ISO format first
        if 'T' in date_str:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        else:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            return dt.strftime('%Y-%m-%d')
    except ValueError:
        return date_str


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format value as percentage."""
    return f"{value:.{decimals}f}%"


def format_expense_table(expenses: List[Dict[str, Any]]) -> Table:
    """Format expenses as a rich table."""
    table = Table(show_header=True, header_style="bold blue")
    
    table.add_column("ID", style="dim", width=8)
    table.add_column("Date", style="cyan", width=12)
    table.add_column("Description", style="white", min_width=20)
    table.add_column("Category", style="green", width=15)
    table.add_column("Amount", style="bold yellow", justify="right", width=12)
    table.add_column("Account", style="magenta", width=12)
    
    for expense in expenses:
        table.add_row(
            str(expense.get('id', 'N/A'))[:8],
            format_date(expense.get('date', '')),
            expense.get('description', 'N/A'),
            expense.get('category', 'N/A'),
            format_currency(expense.get('amount', 0)),
            expense.get('account', 'N/A')
        )
    
    return table


def format_budget_table(budgets: List[Dict[str, Any]]) -> Table:
    """Format budgets as a rich table."""
    table = Table(show_header=True, header_style="bold blue")
    
    table.add_column("ID", style="dim", width=8)
    table.add_column("Name", style="white", min_width=15)
    table.add_column("Period", style="cyan", width=10)
    table.add_column("Limit", style="green", justify="right", width=12)
    table.add_column("Spent", style="yellow", justify="right", width=12)
    table.add_column("Remaining", style="bold", justify="right", width=12)
    table.add_column("Usage", style="bold", justify="center", width=8)
    
    for budget in budgets:
        limit = budget.get('total_limit', 0)
        spent = budget.get('spent_amount', 0)
        remaining = limit - spent
        usage_pct = (spent / limit * 100) if limit > 0 else 0
        
        # Color code the remaining amount and usage
        remaining_style = "red" if remaining < 0 else "green"
        usage_style = "red" if usage_pct > 100 else "yellow" if usage_pct > 80 else "green"
        
        table.add_row(
            str(budget.get('id', 'N/A'))[:8],
            budget.get('name', 'N/A'),
            budget.get('period', 'N/A'),
            format_currency(limit),
            format_currency(spent),
            f"[{remaining_style}]{format_currency(remaining)}[/{remaining_style}]",
            f"[{usage_style}]{format_percentage(usage_pct)}[/{usage_style}]"
        )
    
    return table


def format_category_breakdown(categories: List[Dict[str, Any]]) -> Table:
    """Format category breakdown as a rich table."""
    table = Table(show_header=True, header_style="bold blue")
    
    table.add_column("Category", style="white", min_width=20)
    table.add_column("Amount", style="bold yellow", justify="right", width=12)
    table.add_column("Count", style="cyan", justify="right", width=8)
    table.add_column("Percentage", style="green", justify="right", width=10)
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
    
    return table


def format_anomalies_table(anomalies: List[Dict[str, Any]]) -> Table:
    """Format anomalies as a rich table."""
    table = Table(show_header=True, header_style="bold blue")
    
    table.add_column("Date", style="cyan", width=12)
    table.add_column("Description", style="white", min_width=20)
    table.add_column("Amount", style="bold yellow", justify="right", width=12)
    table.add_column("Category", style="green", width=15)
    table.add_column("Severity", style="bold", justify="center", width=10)
    table.add_column("Type", style="magenta", width=15)
    
    for anomaly in anomalies:
        severity = anomaly.get('severity', 'low')
        severity_style = "red" if severity == 'high' else "yellow" if severity == 'medium' else "green"
        
        table.add_row(
            format_date(anomaly.get('date', '')),
            anomaly.get('description', 'N/A'),
            format_currency(anomaly.get('amount', 0)),
            anomaly.get('category', 'N/A'),
            f"[{severity_style}]{severity.upper()}[/{severity_style}]",
            anomaly.get('anomaly_type', 'N/A')
        )
    
    return table


def format_summary_stats(stats: Dict[str, Any]) -> str:
    """Format summary statistics as formatted text."""
    lines = []
    lines.append("📊 Summary Statistics")
    lines.append("=" * 40)
    
    if 'total_amount' in stats:
        lines.append(f"💰 Total Amount: {format_currency(stats['total_amount'])}")
    
    if 'count' in stats:
        lines.append(f"📝 Total Transactions: {stats['count']:,}")
    
    if 'average_amount' in stats:
        lines.append(f"📈 Average Amount: {format_currency(stats['average_amount'])}")
    
    if 'max_amount' in stats:
        lines.append(f"🔺 Largest Transaction: {format_currency(stats['max_amount'])}")
    
    if 'min_amount' in stats:
        lines.append(f"🔻 Smallest Transaction: {format_currency(stats['min_amount'])}")
    
    return "\n".join(lines)


def format_progress_bar(current: float, total: float, width: int = 20) -> str:
    """Format a simple progress bar."""
    if total == 0:
        percentage = 0
    else:
        percentage = min(current / total, 1.0)
    
    filled = int(width * percentage)
    bar = "█" * filled + "░" * (width - filled)
    
    return f"[{bar}] {percentage:.1%}"


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text to specified length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"