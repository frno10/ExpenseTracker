#!/usr/bin/env python3
"""
Interactive PDF parsing test script.
Run this to test PDF parsing with your own files!
"""

import asyncio
import json
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import print as rprint

from app.parsers.registry import initialize_parsers, parser_registry

console = Console()

async def test_pdf_parsing():
    """Interactive PDF parsing test."""
    
    # Initialize parsers
    console.print("🔧 Initializing parsers...", style="blue")
    initialize_parsers()
    
    # Get PDF parser
    pdf_parser = parser_registry.get_parser("pdf_parser")
    if not pdf_parser:
        console.print("❌ PDF parser not available!", style="red")
        return
    
    console.print("✅ PDF parser ready!", style="green")
    
    # Ask for PDF file
    console.print("\n📄 PDF Parsing Test", style="bold blue")
    console.print("Please provide the path to a PDF file to test:")
    console.print("(You can drag and drop a PDF file here, or type the path)")
    
    while True:
        pdf_path = input("\nPDF file path: ").strip().strip('"').strip("'")
        
        if not pdf_path:
            console.print("Please provide a file path.", style="yellow")
            continue
            
        pdf_file = Path(pdf_path)
        
        if not pdf_file.exists():
            console.print(f"❌ File not found: {pdf_path}", style="red")
            console.print("Please check the path and try again.")
            continue
            
        if not pdf_file.suffix.lower() == '.pdf':
            console.print("❌ File is not a PDF!", style="red")
            continue
            
        break
    
    # Test if parser can handle this PDF
    console.print(f"\n🔍 Checking if PDF parser can handle: {pdf_file.name}")
    
    can_parse = pdf_parser.can_parse(str(pdf_file))
    if not can_parse:
        console.print("❌ PDF parser cannot handle this file", style="red")
        console.print("This might be because:")
        console.print("  • The PDF is corrupted")
        console.print("  • The PDF is password protected")
        console.print("  • Required libraries are missing")
        return
    
    console.print("✅ PDF parser can handle this file!", style="green")
    
    # Parse the PDF
    console.print(f"\n⚡ Parsing PDF: {pdf_file.name}")
    
    try:
        with console.status("[bold green]Parsing PDF..."):
            result = await pdf_parser.parse(str(pdf_file))
        
        # Display results
        display_parse_results(result, pdf_file.name)
        
        # Ask if user wants to save results
        save_choice = input("\n💾 Save results to JSON file? (y/n): ").strip().lower()
        if save_choice in ['y', 'yes']:
            save_results_to_file(result, pdf_file.stem)
            
    except Exception as e:
        console.print(f"❌ Error parsing PDF: {e}", style="red")
        console.print("\nThis could be due to:")
        console.print("  • Unsupported PDF format")
        console.print("  • Complex PDF layout")
        console.print("  • Missing text content in PDF")

def display_parse_results(result, filename):
    """Display parsing results in a nice format."""
    
    # Summary panel
    if result.success:
        status = "✅ SUCCESS"
        status_style = "green"
    else:
        status = "❌ FAILED"
        status_style = "red"
    
    summary = f"""
📄 File: {filename}
🎯 Status: {status}
📊 Transactions Found: {result.transaction_count}
⚠️  Warnings: {len(result.warnings)}
❌ Errors: {len(result.errors)}
🔧 Extraction Method: {result.metadata.get('extraction_method', 'unknown')}
"""
    
    console.print(Panel(summary, title="📋 Parsing Summary", border_style=status_style))
    
    # Show errors if any
    if result.errors:
        console.print("\n❌ Errors:", style="red bold")
        for error in result.errors:
            console.print(f"  • {error}", style="red")
    
    # Show warnings if any
    if result.warnings:
        console.print("\n⚠️  Warnings:", style="yellow bold")
        for warning in result.warnings:
            console.print(f"  • {warning}", style="yellow")
    
    # Show transactions in a table
    if result.transactions:
        console.print(f"\n💰 Found {len(result.transactions)} Transactions:", style="green bold")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Date", style="cyan")
        table.add_column("Description", style="white", max_width=40)
        table.add_column("Amount", style="green", justify="right")
        table.add_column("Merchant", style="blue", max_width=20)
        table.add_column("Category", style="yellow", max_width=15)
        
        for tx in result.transactions[:10]:  # Show first 10
            table.add_row(
                str(tx.date),
                tx.description or "N/A",
                f"${tx.amount:,.2f}",
                tx.merchant or "N/A",
                tx.category or "N/A"
            )
        
        console.print(table)
        
        if len(result.transactions) > 10:
            console.print(f"\n... and {len(result.transactions) - 10} more transactions")
    
    # Show metadata
    if result.metadata:
        console.print(f"\n📊 Metadata:", style="blue bold")
        metadata_json = json.dumps(result.metadata, indent=2, default=str)
        syntax = Syntax(metadata_json, "json", theme="monokai", line_numbers=True)
        console.print(syntax)

def save_results_to_file(result, filename_stem):
    """Save parsing results to a JSON file."""
    
    # Convert result to dictionary
    result_dict = {
        "success": result.success,
        "transaction_count": result.transaction_count,
        "errors": result.errors,
        "warnings": result.warnings,
        "metadata": result.metadata,
        "transactions": [
            {
                "date": str(tx.date),
                "description": tx.description,
                "amount": float(tx.amount),
                "merchant": tx.merchant,
                "category": tx.category,
                "account": tx.account,
                "reference": tx.reference,
                "notes": tx.notes,
                "raw_data": tx.raw_data
            }
            for tx in result.transactions
        ]
    }
    
    # Save to file
    output_file = Path(f"{filename_stem}_parsed_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_dict, f, indent=2, ensure_ascii=False)
    
    console.print(f"💾 Results saved to: {output_file.absolute()}", style="green")

async def test_csv_parsing():
    """Test CSV parsing as well."""
    console.print("\n📊 CSV Parsing Test", style="bold blue")
    console.print("Want to test CSV parsing too? Provide a CSV file path:")
    
    csv_path = input("CSV file path (or press Enter to skip): ").strip().strip('"').strip("'")
    
    if not csv_path:
        return
    
    csv_file = Path(csv_path)
    if not csv_file.exists():
        console.print(f"❌ CSV file not found: {csv_path}", style="red")
        return
    
    # Get CSV parser
    csv_parser = parser_registry.get_parser("csv_parser")
    if not csv_parser:
        console.print("❌ CSV parser not available!", style="red")
        return
    
    console.print(f"⚡ Parsing CSV: {csv_file.name}")
    
    try:
        with console.status("[bold green]Parsing CSV..."):
            result = await csv_parser.parse(str(csv_file))
        
        display_parse_results(result, csv_file.name)
        
    except Exception as e:
        console.print(f"❌ Error parsing CSV: {e}", style="red")

def show_parser_info():
    """Show information about available parsers."""
    console.print("🔧 Available Parsers:", style="bold blue")
    
    parsers = parser_registry.list_parsers()
    for parser_name in parsers:
        parser = parser_registry.get_parser(parser_name)
        if parser:
            console.print(f"\n📦 {parser.config.name}")
            console.print(f"   Description: {parser.config.description}")
            console.print(f"   Extensions: {', '.join(parser.config.supported_extensions)}")
            console.print(f"   MIME Types: {', '.join(parser.config.mime_types)}")

async def main():
    """Main test function."""
    console.print("🎯 PDF/CSV Parser Testing Tool", style="bold green")
    console.print("=" * 50)
    
    show_parser_info()
    
    while True:
        console.print("\n🎮 What would you like to test?")
        console.print("1. Test PDF parsing")
        console.print("2. Test CSV parsing") 
        console.print("3. Show parser info")
        console.print("4. Exit")
        
        choice = input("\nChoice (1-4): ").strip()
        
        if choice == "1":
            await test_pdf_parsing()
        elif choice == "2":
            await test_csv_parsing()
        elif choice == "3":
            show_parser_info()
        elif choice == "4":
            console.print("👋 Goodbye!", style="green")
            break
        else:
            console.print("Invalid choice. Please try again.", style="yellow")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!", style="green")
    except Exception as e:
        console.print(f"\n❌ Unexpected error: {e}", style="red")
        sys.exit(1)