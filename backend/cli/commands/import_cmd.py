"""
Import commands for the CLI.
"""
import click
import asyncio
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Confirm
from rich.table import Table
import json

from cli.utils.api import ImportAPI
from cli.utils.formatters import format_currency, format_date, format_file_size
from cli.utils.validators import validate_file_path

console = Console()


@click.group(name="import")
def import_group():
    """Import bank statements and transaction data."""
    pass


@import_group.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--type", "-t", type=click.Choice(['pdf', 'csv', 'excel', 'ofx', 'qif', 'auto']),
              default='auto', help="File type (auto-detect if not specified)")
@click.option("--account", "-a", type=str, help="Associate with specific account")
@click.option("--preview", "-p", is_flag=True, help="Preview transactions before importing")
@click.option("--auto-confirm", is_flag=True, help="Auto-confirm all transactions")
@click.pass_context
def file(ctx, file_path: str, type: str, account: Optional[str], preview: bool, auto_confirm: bool):
    """Import transactions from a bank statement file."""
    
    file_path_obj = Path(file_path)
    
    # Validate file
    if not file_path_obj.exists():
        console.print(f"[red]Error: File '{file_path}' does not exist[/red]")
        return
    
    if not file_path_obj.is_file():
        console.print(f"[red]Error: '{file_path}' is not a file[/red]")
        return
    
    file_size = file_path_obj.stat().st_size
    console.print(f"\n[bold blue]Importing Statement File[/bold blue]")
    console.print("=" * 40)
    console.print(f"File: {file_path_obj.name}")
    console.print(f"Size: {format_file_size(file_size)}")
    console.print(f"Type: {type}")
    if account:
        console.print(f"Account: {account}")
    
    async def import_file():
        api = ImportAPI(ctx.obj['config'])
        
        # Step 1: Upload file
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            upload_task = progress.add_task("Uploading file...", total=100)
            
            try:
                # Simulate upload progress
                for i in range(0, 101, 10):
                    progress.update(upload_task, completed=i)
                    await asyncio.sleep(0.1)
                
                # This would be the actual upload call
                import_result = await api.upload_statement(file_path, type)
                import_id = import_result.get('import_id', 'test-import-123')
                
                progress.update(upload_task, description="✓ File uploaded successfully")
                
            except Exception as e:
                progress.update(upload_task, description="✗ Upload failed")
                console.print(f"[red]Error uploading file: {e}[/red]")
                return
        
        # Step 2: Wait for processing
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            process_task = progress.add_task("Processing file...", total=None)
            
            try:
                # Poll for processing status
                for i in range(10):  # Max 10 attempts
                    status = await api.get_import_status(import_id)
                    
                    if status.get('status') == 'completed':
                        progress.update(process_task, description="✓ File processed successfully")
                        break
                    elif status.get('status') == 'failed':
                        progress.update(process_task, description="✗ Processing failed")
                        console.print(f"[red]Processing failed: {status.get('error', 'Unknown error')}[/red]")
                        return
                    
                    await asyncio.sleep(2)  # Wait 2 seconds between checks
                else:
                    progress.update(process_task, description="⚠ Processing timeout")
                    console.print("[yellow]Processing is taking longer than expected. Check status later.[/yellow]")
                    return
                
            except Exception as e:
                progress.update(process_task, description="✗ Processing failed")
                console.print(f"[red]Error processing file: {e}[/red]")
                return
        
        # Step 3: Get preview
        try:
            preview_data = await api.get_import_preview(import_id)
            transactions = preview_data.get('transactions', [])
            
            if not transactions:
                console.print("[yellow]No transactions found in the file.[/yellow]")
                return
            
            console.print(f"\n[bold green]✓ Found {len(transactions)} transactions[/bold green]")
            
            # Show preview if requested or if not auto-confirming
            if preview or not auto_confirm:
                console.print(f"\n[bold]Transaction Preview:[/bold]")
                
                table = Table(show_header=True, header_style="bold blue")
                table.add_column("Date", style="cyan", width=12)
                table.add_column("Description", style="white", min_width=25)
                table.add_column("Amount", style="bold yellow", justify="right", width=12)
                table.add_column("Category", style="green", width=15)
                table.add_column("Status", style="magenta", width=10)
                
                for i, transaction in enumerate(transactions[:10]):  # Show first 10
                    status = "✓ New" if transaction.get('is_new', True) else "⚠ Duplicate"
                    status_style = "green" if transaction.get('is_new', True) else "yellow"
                    
                    table.add_row(
                        format_date(transaction.get('date', '')),
                        transaction.get('description', 'N/A')[:25],
                        format_currency(transaction.get('amount', 0)),
                        transaction.get('category', 'N/A'),
                        f"[{status_style}]{status}[/{status_style}]"
                    )
                
                console.print(table)
                
                if len(transactions) > 10:
                    console.print(f"\n[dim]... and {len(transactions) - 10} more transactions[/dim]")
                
                # Summary
                total_amount = sum(t.get('amount', 0) for t in transactions)
                new_transactions = sum(1 for t in transactions if t.get('is_new', True))
                duplicates = len(transactions) - new_transactions
                
                console.print(f"\n[bold]Summary:[/bold]")
                console.print(f"  Total transactions: {len(transactions)}")
                console.print(f"  New transactions: [green]{new_transactions}[/green]")
                console.print(f"  Duplicates: [yellow]{duplicates}[/yellow]")
                console.print(f"  Total amount: {format_currency(total_amount)}")
            
            # Confirmation
            if auto_confirm or Confirm.ask(f"\nImport {len(transactions)} transactions?"):
                # Step 4: Confirm import
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    import_task = progress.add_task("Importing transactions...", total=None)
                    
                    try:
                        # Import all transactions (or just new ones)
                        transaction_ids = [t.get('id') for t in transactions if t.get('is_new', True)]
                        result = await api.confirm_import(import_id, transaction_ids)
                        
                        progress.update(import_task, description="✓ Import completed successfully")
                        
                        imported_count = result.get('imported_count', len(transaction_ids))
                        console.print(f"\n[bold green]✓ Successfully imported {imported_count} transactions![/bold green]")
                        
                        if result.get('skipped_count', 0) > 0:
                            console.print(f"[yellow]Skipped {result['skipped_count']} duplicate transactions[/yellow]")
                        
                    except Exception as e:
                        progress.update(import_task, description="✗ Import failed")
                        console.print(f"[red]Error importing transactions: {e}[/red]")
            else:
                console.print("[yellow]Import cancelled.[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Error getting preview: {e}[/red]")
    
    asyncio.run(import_file())


@import_group.command()
@click.argument("import_id", type=str)
@click.pass_context
def status(ctx, import_id: str):
    """Check the status of an import operation."""
    
    async def check_import_status():
        api = ImportAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Checking import status...", total=None)
            
            try:
                status_data = await api.get_import_status(import_id)
                progress.update(task, description="✓ Status retrieved")
                
                console.print(f"\n[bold blue]Import Status[/bold blue]")
                console.print("=" * 30)
                console.print(f"[bold]Import ID:[/bold] {import_id}")
                console.print(f"[bold]Status:[/bold] {status_data.get('status', 'Unknown')}")
                console.print(f"[bold]File Name:[/bold] {status_data.get('filename', 'N/A')}")
                console.print(f"[bold]File Size:[/bold] {format_file_size(status_data.get('file_size', 0))}")
                console.print(f"[bold]Created:[/bold] {format_date(status_data.get('created_at', ''))}")
                
                if status_data.get('status') == 'completed':
                    console.print(f"[bold]Transactions Found:[/bold] {status_data.get('transactions_found', 0)}")
                    console.print(f"[bold]Transactions Imported:[/bold] {status_data.get('transactions_imported', 0)}")
                    console.print(f"[bold]Duplicates Skipped:[/bold] {status_data.get('duplicates_skipped', 0)}")
                elif status_data.get('status') == 'failed':
                    console.print(f"[bold]Error:[/bold] [red]{status_data.get('error', 'Unknown error')}[/red]")
                elif status_data.get('status') == 'processing':
                    console.print(f"[bold]Progress:[/bold] {status_data.get('progress', 0)}%")
                
                console.print()
                
            except Exception as e:
                progress.update(task, description="✗ Failed to get status")
                console.print(f"[red]Error checking import status: {e}[/red]")
    
    asyncio.run(check_import_status())


@import_group.command()
@click.argument("import_id", type=str)
@click.option("--limit", "-l", type=int, default=20, help="Number of transactions to show")
@click.option("--format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def preview(ctx, import_id: str, limit: int, format: str):
    """Preview transactions from an import before confirming."""
    
    async def show_preview():
        api = ImportAPI(ctx.obj['config'])
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Loading preview...", total=None)
            
            try:
                preview_data = await api.get_import_preview(import_id)
                transactions = preview_data.get('transactions', [])
                progress.update(task, description="✓ Preview loaded")
                
                if not transactions:
                    console.print("[yellow]No transactions found in import.[/yellow]")
                    return
                
                if format == "json":
                    console.print(json.dumps(transactions[:limit], indent=2, default=str))
                else:
                    # Table format
                    table = Table(show_header=True, header_style="bold blue")
                    table.add_column("Date", style="cyan", width=12)
                    table.add_column("Description", style="white", min_width=25)
                    table.add_column("Amount", style="bold yellow", justify="right", width=12)
                    table.add_column("Category", style="green", width=15)
                    table.add_column("Status", style="magenta", width=12)
                    
                    for transaction in transactions[:limit]:
                        status = "✓ New" if transaction.get('is_new', True) else "⚠ Duplicate"
                        status_style = "green" if transaction.get('is_new', True) else "yellow"
                        
                        table.add_row(
                            format_date(transaction.get('date', '')),
                            transaction.get('description', 'N/A'),
                            format_currency(transaction.get('amount', 0)),
                            transaction.get('category', 'N/A'),
                            f"[{status_style}]{status}[/{status_style}]"
                        )
                    
                    console.print(f"\n[bold]Import Preview ({len(transactions)} total transactions)[/bold]")
                    console.print(table)
                    
                    if len(transactions) > limit:
                        console.print(f"\n[dim]Showing {limit} of {len(transactions)} transactions[/dim]")
                
            except Exception as e:
                progress.update(task, description="✗ Failed to load preview")
                console.print(f"[red]Error loading preview: {e}[/red]")
    
    asyncio.run(show_preview())


@import_group.command()
@click.argument("import_id", type=str)
@click.option("--all", "-a", is_flag=True, help="Confirm all transactions")
@click.option("--new-only", is_flag=True, help="Confirm only new transactions (skip duplicates)")
@click.pass_context
def confirm(ctx, import_id: str, all: bool, new_only: bool):
    """Confirm and finalize an import operation."""
    
    async def confirm_import():
        api = ImportAPI(ctx.obj['config'])
        
        try:
            # Get preview first
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Loading transactions...", total=None)
                preview_data = await api.get_import_preview(import_id)
                transactions = preview_data.get('transactions', [])
                progress.update(task, description="✓ Transactions loaded")
            
            if not transactions:
                console.print("[yellow]No transactions found in import.[/yellow]")
                return
            
            # Determine which transactions to import
            if all:
                transaction_ids = [t.get('id') for t in transactions]
                action_desc = "all transactions"
            elif new_only:
                transaction_ids = [t.get('id') for t in transactions if t.get('is_new', True)]
                action_desc = "new transactions only"
            else:
                # Interactive selection
                console.print(f"\n[bold]Select transactions to import:[/bold]")
                console.print("(Enter transaction numbers separated by commas, or 'all' for all, 'new' for new only)")
                
                # Show numbered list
                for i, transaction in enumerate(transactions, 1):
                    status = "NEW" if transaction.get('is_new', True) else "DUPLICATE"
                    status_style = "green" if transaction.get('is_new', True) else "yellow"
                    console.print(f"  {i:2d}. {format_date(transaction.get('date', ''))} - {transaction.get('description', 'N/A')[:30]} - {format_currency(transaction.get('amount', 0))} [{status_style}]{status}[/{status_style}]")
                
                selection = input("\nSelection: ").strip().lower()
                
                if selection == 'all':
                    transaction_ids = [t.get('id') for t in transactions]
                    action_desc = "all transactions"
                elif selection == 'new':
                    transaction_ids = [t.get('id') for t in transactions if t.get('is_new', True)]
                    action_desc = "new transactions only"
                else:
                    try:
                        indices = [int(x.strip()) - 1 for x in selection.split(',')]
                        transaction_ids = [transactions[i].get('id') for i in indices if 0 <= i < len(transactions)]
                        action_desc = f"{len(transaction_ids)} selected transactions"
                    except (ValueError, IndexError):
                        console.print("[red]Invalid selection. Please try again.[/red]")
                        return
            
            if not transaction_ids:
                console.print("[yellow]No transactions selected for import.[/yellow]")
                return
            
            # Confirm action
            if not Confirm.ask(f"Import {action_desc} ({len(transaction_ids)} transactions)?"):
                console.print("[yellow]Import cancelled.[/yellow]")
                return
            
            # Perform import
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Importing transactions...", total=None)
                
                result = await api.confirm_import(import_id, transaction_ids)
                progress.update(task, description="✓ Import completed")
                
                imported_count = result.get('imported_count', len(transaction_ids))
                console.print(f"\n[bold green]✓ Successfully imported {imported_count} transactions![/bold green]")
                
                if result.get('skipped_count', 0) > 0:
                    console.print(f"[yellow]Skipped {result['skipped_count']} transactions[/yellow]")
                
                if result.get('errors'):
                    console.print(f"[red]Errors: {len(result['errors'])}[/red]")
                    for error in result['errors'][:5]:  # Show first 5 errors
                        console.print(f"  • {error}")
            
        except Exception as e:
            console.print(f"[red]Error confirming import: {e}[/red]")
    
    asyncio.run(confirm_import())


@import_group.command()
@click.option("--limit", "-l", type=int, default=10, help="Number of recent imports to show")
@click.option("--status", type=click.Choice(['pending', 'processing', 'completed', 'failed']), help="Filter by status")
@click.pass_context
def history(ctx, limit: int, status: Optional[str]):
    """Show import history."""
    
    # This would typically call an API endpoint to get import history
    # For now, show a placeholder
    console.print(f"\n[bold blue]Import History[/bold blue]")
    console.print("=" * 30)
    console.print("[yellow]Import history feature not yet implemented.[/yellow]")
    console.print("This would show your recent import operations with their status.")
    console.print()


@import_group.command()
@click.pass_context
def formats(ctx):
    """Show supported file formats and their requirements."""
    
    console.print(f"\n[bold blue]Supported Import Formats[/bold blue]")
    console.print("=" * 40)
    
    formats_info = [
        {
            "format": "PDF",
            "extensions": ".pdf",
            "description": "Bank statement PDFs with text content",
            "notes": "Works best with text-based PDFs, not scanned images"
        },
        {
            "format": "CSV",
            "extensions": ".csv",
            "description": "Comma-separated values with transaction data",
            "notes": "Should include date, description, and amount columns"
        },
        {
            "format": "Excel",
            "extensions": ".xlsx, .xls",
            "description": "Excel spreadsheets with transaction data",
            "notes": "First row should contain column headers"
        },
        {
            "format": "OFX",
            "extensions": ".ofx",
            "description": "Open Financial Exchange format",
            "notes": "Standard format used by many banks"
        },
        {
            "format": "QIF",
            "extensions": ".qif",
            "description": "Quicken Interchange Format",
            "notes": "Legacy format, limited support"
        }
    ]
    
    for fmt in formats_info:
        console.print(f"\n[bold green]{fmt['format']}[/bold green] ({fmt['extensions']})")
        console.print(f"  {fmt['description']}")
        console.print(f"  [dim]{fmt['notes']}[/dim]")
    
    console.print(f"\n[bold]Tips for better import results:[/bold]")
    console.print("• Ensure files are not password protected")
    console.print("• Use the most recent statement format from your bank")
    console.print("• For CSV files, include headers: Date, Description, Amount")
    console.print("• Check the preview before confirming the import")
    console.print()