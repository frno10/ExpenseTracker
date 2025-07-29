"""
Import and export commands.
"""
import os
from pathlib import Path
from typing import Optional
import sys

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Confirm
import time

from ..api.client import APIClient
from ..utils.exceptions import ExpenseTrackerCLIError
from ..utils.serialization import format_output
from ..config import Config


@click.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--parser-type", type=click.Choice(["auto", "csv", "pdf", "excel", "ofx", "qif"]), default="auto", help="Parser type to use")
@click.option("--dry-run", is_flag=True, help="Preview import without saving")
@click.option("--auto-confirm", is_flag=True, help="Automatically confirm import")
@click.pass_context
def import_cmd(
    ctx,
    file_path: str,
    parser_type: str,
    dry_run: bool,
    auto_confirm: bool,
):
    """Import expenses from a file (CSV, PDF, Excel, OFX, QIF)."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        file_path = Path(file_path)
        if not file_path.exists():
            raise ExpenseTrackerCLIError(f"File not found: {file_path}")
        
        console.print(f"[blue]Importing from:[/blue] {file_path}")
        console.print(f"[blue]Parser type:[/blue] {parser_type}")
        console.print(f"[blue]File size:[/blue] {file_path.stat().st_size / 1024:.1f} KB")
        
        if dry_run:
            console.print("[yellow]DRY RUN MODE - No data will be saved[/yellow]")
        
        # Upload file
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            upload_task = progress.add_task("Uploading file...", total=100)
            
            with open(file_path, 'rb') as f:
                upload_response = client.upload_statement(
                    f, 
                    parser_type if parser_type != "auto" else None
                )
            
            progress.update(upload_task, completed=100)
        
        import_id = upload_response["import_id"]
        console.print(f"[green]✓[/green] File uploaded successfully (ID: {import_id})")
        
        # Monitor import progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            process_task = progress.add_task("Processing file...", total=100)
            
            while True:
                status = client.get_import_status(import_id)
                progress.update(process_task, completed=status["progress"])
                
                if status["status"] == "completed":
                    break
                elif status["status"] == "failed":
                    raise ExpenseTrackerCLIError(f"Import failed: {status.get('error', 'Unknown error')}")
                
                time.sleep(1)
        
        console.print(f"[green]✓[/green] File processed successfully")
        console.print(f"[blue]Transactions found:[/blue] {status['transactions_found']}")
        
        if status.get("errors"):
            console.print(f"[yellow]Warnings:[/yellow] {len(status['errors'])} issues found")
            for error in status["errors"][:5]:  # Show first 5 errors
                console.print(f"  • {error}")
            if len(status["errors"]) > 5:
                console.print(f"  ... and {len(status['errors']) - 5} more")
        
        if dry_run:
            console.print("[yellow]Dry run completed - no data was imported[/yellow]")
            return
        
        # Confirm import
        if not auto_confirm:
            if not Confirm.ask(f"Import {status['transactions_found']} transactions?"):
                console.print("[yellow]Import cancelled[/yellow]")
                return
        
        # Confirm import
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            confirm_task = progress.add_task("Importing transactions...", total=None)
            result = client.confirm_import(import_id, [])  # Import all transactions
        
        console.print(f"[green]✓[/green] Import completed successfully!")
        console.print(f"[blue]Imported:[/blue] {result.get('imported_count', 0)} transactions")
        console.print(f"[blue]Skipped:[/blue] {result.get('skipped_count', 0)} duplicates")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Import failed: {e}")


@click.command()
@click.option("--format", "export_format", type=click.Choice(["csv", "json", "xlsx"]), default="csv", help="Export format")
@click.option("--output", "-o", help="Output file path")
@click.option("--category", "-c", help="Filter by category")
@click.option("--account", "-a", help="Filter by account")
@click.option("--date-from", type=click.DateTime(formats=["%Y-%m-%d"]), help="Start date filter")
@click.option("--date-to", type=click.DateTime(formats=["%Y-%m-%d"]), help="End date filter")
@click.option("--min-amount", type=float, help="Minimum amount filter")
@click.option("--max-amount", type=float, help="Maximum amount filter")
@click.pass_context
def export(
    ctx,
    export_format: str,
    output: Optional[str],
    category: Optional[str],
    account: Optional[str],
    date_from: Optional[click.DateTime],
    date_to: Optional[click.DateTime],
    min_amount: Optional[float],
    max_amount: Optional[float],
):
    """Export expenses to a file."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        # Prepare export parameters
        params = {"format": export_format}
        if category:
            params["category"] = category
        if account:
            params["account"] = account
        if date_from:
            params["date_from"] = date_from.strftime("%Y-%m-%d")
        if date_to:
            params["date_to"] = date_to.strftime("%Y-%m-%d")
        if min_amount is not None:
            params["min_amount"] = min_amount
        if max_amount is not None:
            params["max_amount"] = max_amount
        
        # Generate output filename if not provided
        if not output:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = f"expenses_{timestamp}.{export_format}"
        
        console.print(f"[blue]Exporting to:[/blue] {output}")
        console.print(f"[blue]Format:[/blue] {export_format}")
        
        # Show filters if any
        filters_applied = []
        if category:
            filters_applied.append(f"category: {category}")
        if account:
            filters_applied.append(f"account: {account}")
        if date_from:
            filters_applied.append(f"from: {date_from.strftime('%Y-%m-%d')}")
        if date_to:
            filters_applied.append(f"to: {date_to.strftime('%Y-%m-%d')}")
        if min_amount is not None:
            filters_applied.append(f"min amount: {config.display.currency}{min_amount}")
        if max_amount is not None:
            filters_applied.append(f"max amount: {config.display.currency}{max_amount}")
        
        if filters_applied:
            console.print(f"[blue]Filters:[/blue] {', '.join(filters_applied)}")
        
        # Export data
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            export_task = progress.add_task("Exporting data...", total=None)
            export_data = client.export_expenses(params)
        
        # Write to file
        with open(output, 'wb') as f:
            f.write(export_data)
        
        file_size = os.path.getsize(output)
        console.print(f"[green]✓[/green] Export completed successfully!")
        console.print(f"[blue]File:[/blue] {output}")
        console.print(f"[blue]Size:[/blue] {file_size / 1024:.1f} KB")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Export failed: {e}")


@click.command()
@click.option("--format", "list_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def imports(ctx, list_format: str):
    """List recent import history."""
    config: Config = ctx.obj["config"]
    console: Console = ctx.obj["console"]
    
    try:
        client = APIClient(config)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Loading import history...", total=None)
            imports_data = client.get_import_history()
        
        imports_list = imports_data.get("imports", [])
        
        if not imports_list:
            console.print("[yellow]No import history found.[/yellow]")
            return
        
        if list_format == "table":
            table = Table(title="Import History")
            table.add_column("Date", style="cyan")
            table.add_column("File", style="white")
            table.add_column("Type", style="magenta")
            table.add_column("Status", style="green")
            table.add_column("Transactions", style="blue", justify="right")
            table.add_column("Imported", style="yellow", justify="right")
            
            for import_item in imports_list:
                status_color = "green" if import_item["status"] == "completed" else "red" if import_item["status"] == "failed" else "yellow"
                
                table.add_row(
                    import_item.get("created_at", "")[:10],
                    import_item.get("filename", ""),
                    import_item.get("parser_type", ""),
                    f"[{status_color}]{import_item.get('status', '')}[/{status_color}]",
                    str(import_item.get("transactions_found", 0)),
                    str(import_item.get("transactions_imported", 0)),
                )
            
            console.print(table)
        else:
            output = format_output(imports_list, list_format)
            console.print(output)
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to list imports: {e}")


@click.command()
@click.argument("template_name", type=click.Choice(["basic", "detailed", "categories", "accounts"]))
@click.option("--output", "-o", help="Output file path")
@click.pass_context
def template(ctx, template_name: str, output: Optional[str]):
    """Generate CSV import templates."""
    console: Console = ctx.obj["console"]
    
    templates = {
        "basic": "date,amount,description\n2024-01-15,25.50,Coffee shop\n2024-01-16,45.00,Grocery store\n",
        "detailed": "date,amount,description,category,account,payment_method,notes\n2024-01-15,25.50,Coffee shop,Food & Dining,Checking,Credit Card,Morning coffee\n2024-01-16,45.00,Grocery store,Groceries,Checking,Debit Card,Weekly shopping\n",
        "categories": "date,amount,description,category\n2024-01-15,25.50,Coffee shop,Food & Dining\n2024-01-16,45.00,Grocery store,Groceries\n2024-01-17,35.00,Gas station,Transportation\n",
        "accounts": "date,amount,description,account\n2024-01-15,25.50,Coffee shop,Checking\n2024-01-16,45.00,Grocery store,Savings\n2024-01-17,35.00,Gas station,Credit Card\n",
    }
    
    if not output:
        output = f"expense_template_{template_name}.csv"
    
    try:
        with open(output, 'w') as f:
            f.write(templates[template_name])
        
        console.print(f"[green]✓[/green] Template created: {output}")
        console.print(f"[blue]Template type:[/blue] {template_name}")
        console.print(f"[blue]Usage:[/blue] expense-tracker import {output}")
        
    except Exception as e:
        raise ExpenseTrackerCLIError(f"Failed to create template: {e}")


# Add the imports command to the export group
export.add_command(imports)
export.add_command(template)