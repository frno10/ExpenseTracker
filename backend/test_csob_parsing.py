#!/usr/bin/env python3
"""
Test ČSOB Slovakia PDF parsing with custom patterns.
"""

import asyncio
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from app.parsers.pdf_parser import PDFParser
from app.parsers.config import config_manager

console = Console()

async def test_csob_parsing():
    """Test parsing with ČSOB Slovakia configuration."""
    
    console.print("🏦 ČSOB Slovakia PDF Parser Test", style="bold blue")
    
    # Load ČSOB configuration
    csob_config = config_manager.load_bank_config("csob_slovakia")
    if not csob_config:
        console.print("❌ ČSOB Slovakia config not found!", style="red")
        return
    
    console.print("✅ Loaded ČSOB Slovakia configuration", style="green")
    
    # Get PDF file
    pdf_path = input("Enter ČSOB PDF file path: ").strip().strip('"').strip("'")
    
    if not pdf_path:
        console.print("No file path provided.", style="yellow")
        return
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        console.print(f"❌ File not found: {pdf_path}", style="red")
        return
    
    # Create parser with ČSOB config
    parser = PDFParser()
    
    # Update parser configuration with ČSOB settings
    if "pdf_config" in csob_config:
        pdf_settings = csob_config["pdf_config"]
        parser.config.settings.update(pdf_settings)
        console.print("🔧 Applied ČSOB-specific patterns", style="blue")
    
    # Parse the PDF
    console.print(f"\n⚡ Parsing ČSOB PDF: {pdf_file.name}")
    
    try:
        result = await parser.parse(str(pdf_file))
        
        # Display results
        display_csob_results(result, pdf_file.name)
        
        # Save results
        save_choice = input("\n💾 Save results to JSON? (y/n): ").strip().lower()
        if save_choice in ['y', 'yes']:
            save_csob_results(result, pdf_file.stem)
            
    except Exception as e:
        console.print(f"❌ Error parsing PDF: {e}", style="red")

def display_csob_results(result, filename):
    """Display ČSOB parsing results."""
    
    # Summary
    status = "✅ SUCCESS" if result.success else "❌ FAILED"
    status_style = "green" if result.success else "red"
    
    summary = f"""
🏦 Bank: ČSOB Slovakia
📄 File: {filename}
🎯 Status: {status}
📊 Transactions: {result.transaction_count}
⚠️  Warnings: {len(result.warnings)}
❌ Errors: {len(result.errors)}
"""
    
    console.print(Panel(summary, title="🏦 ČSOB Parsing Results", border_style=status_style))
    
    # Show errors and warnings
    if result.errors:
        console.print("\n❌ Errors:", style="red bold")
        for error in result.errors:
            console.print(f"  • {error}", style="red")
    
    if result.warnings:
        console.print("\n⚠️  Warnings:", style="yellow bold")
        for warning in result.warnings:
            console.print(f"  • {warning}", style="yellow")
    
    # Show transactions
    if result.transactions:
        console.print(f"\n💳 ČSOB Transactions ({len(result.transactions)}):", style="green bold")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Date", style="cyan")
        table.add_column("Description", style="white", max_width=50)
        table.add_column("Amount (EUR)", style="green", justify="right")
        table.add_column("Merchant", style="blue", max_width=30)
        
        total_amount = 0
        for tx in result.transactions:
            table.add_row(
                str(tx.date),
                tx.description or "N/A",
                f"{tx.amount:,.2f}",
                tx.merchant or "N/A"
            )
            total_amount += float(tx.amount)
        
        console.print(table)
        console.print(f"\n💰 Total Amount: {total_amount:,.2f} EUR", style="bold green")
    
    else:
        console.print("\n❌ No transactions found", style="red")
        console.print("This might be because:")
        console.print("  • The PDF format is different than expected")
        console.print("  • The parsing patterns need adjustment")
        console.print("  • The PDF contains no transaction data")

def save_csob_results(result, filename_stem):
    """Save ČSOB parsing results."""
    
    # Convert to dictionary
    result_dict = {
        "bank": "ČSOB Slovakia",
        "success": result.success,
        "transaction_count": result.transaction_count,
        "total_amount": sum(float(tx.amount) for tx in result.transactions),
        "currency": "EUR",
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
                "raw_data": tx.raw_data
            }
            for tx in result.transactions
        ]
    }
    
    # Save to file
    output_file = Path(f"csob_{filename_stem}_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_dict, f, indent=2, ensure_ascii=False)
    
    console.print(f"💾 ČSOB results saved to: {output_file.absolute()}", style="green")

async def main():
    """Main function."""
    try:
        await test_csob_parsing()
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!", style="green")
    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="red")

if __name__ == "__main__":
    asyncio.run(main())