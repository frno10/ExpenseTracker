#!/usr/bin/env python3
"""
Improved ČSOB Slovakia PDF parser with better pattern matching.
"""

import asyncio
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from app.parsers.base import ParsedTransaction, ParseResult
from app.parsers.pdf_parser import PDFParser

console = Console()

class ImprovedCSObParser(PDFParser):
    """Improved parser specifically for ČSOB Slovakia statements."""
    
    async def parse_csob_format(self, file_path: str) -> ParseResult:
        """Parse ČSOB PDF with improved logic."""
        
        result = ParseResult(success=False)
        
        try:
            # Extract text
            text_content = await self._extract_text(file_path)
            if not text_content:
                result.errors.append("Could not extract text from PDF")
                return result
            
            # Parse transactions with ČSOB-specific logic
            transactions = await self._parse_csob_transactions(text_content)
            
            result.transactions = transactions
            result.success = len(transactions) > 0
            result.metadata["extraction_method"] = "csob_improved"
            result.metadata["text_length"] = len(text_content)
            
            if not result.success:
                result.warnings.append("No transactions found with improved parser")
            
            return result
            
        except Exception as e:
            result.errors.append(f"Error in improved ČSOB parsing: {e}")
            return result
    
    async def _parse_csob_transactions(self, text_content: str) -> list:
        """Parse ČSOB transactions with improved logic."""
        
        transactions = []
        lines = text_content.split('\n')
        
        current_transaction = {}
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Look for transaction date and description pattern
            # Format: "2. 5. Čerpanie úveru plat.kartou -12,90"
            date_desc_amount_match = re.match(r'(\d{1,2}\.\s*\d{1,2}\.)\s+(.+?)\s+(-?\d+[,.]?\d*)\s*$', line)
            
            if date_desc_amount_match:
                # Save previous transaction if exists
                if current_transaction:
                    tx = self._create_transaction_from_data(current_transaction)
                    if tx:
                        transactions.append(tx)
                
                # Start new transaction
                date_str, description, amount_str = date_desc_amount_match.groups()
                
                current_transaction = {
                    'date_str': date_str,
                    'description': description.strip(),
                    'amount_str': amount_str,
                    'merchant': None,
                    'reference': None,
                    'location': None
                }
                continue
            
            # Look for merchant location: "Miesto: SUPERMARKET FRESH KOSICE"
            location_match = re.match(r'Miesto:\s+(.+)', line)
            if location_match and current_transaction:
                current_transaction['location'] = location_match.group(1).strip()
                current_transaction['merchant'] = location_match.group(1).strip()
                continue
            
            # Look for reference: "Ref. platiteľa: /VS205000121/SS3600268562/KS6178"
            ref_match = re.match(r'Ref\.\s+platiteľa:\s+(.+)', line)
            if ref_match and current_transaction:
                current_transaction['reference'] = ref_match.group(1).strip()
                continue
        
        # Don't forget the last transaction
        if current_transaction:
            tx = self._create_transaction_from_data(current_transaction)
            if tx:
                transactions.append(tx)
        
        return transactions
    
    def _create_transaction_from_data(self, tx_data: dict) -> ParsedTransaction:
        """Create a ParsedTransaction from extracted data."""
        
        try:
            # Parse date - add current year since ČSOB only provides day.month
            date_str = tx_data['date_str']
            # Remove extra spaces and parse
            date_clean = re.sub(r'\s+', '', date_str)  # "2.5." -> "2.5."
            
            # Parse day and month
            day_month_match = re.match(r'(\d{1,2})\.(\d{1,2})\.', date_clean)
            if day_month_match:
                day = int(day_month_match.group(1))
                month = int(day_month_match.group(2))
                # Use 2025 as the year (from the PDF header)
                transaction_date = date(2025, month, day)
            else:
                return None
            
            # Parse amount - handle Slovak decimal format
            amount_str = tx_data['amount_str']
            # Replace comma with dot for decimal parsing
            amount_clean = amount_str.replace(',', '.')
            amount = Decimal(amount_clean)
            
            # Get description and merchant
            description = tx_data['description']
            merchant = tx_data.get('merchant') or tx_data.get('location')
            
            # If no specific merchant, try to extract from description
            if not merchant and description:
                merchant = self._extract_merchant_name(description)
            
            # Create transaction
            transaction = ParsedTransaction(
                date=transaction_date,
                description=description,
                amount=amount,
                merchant=merchant,
                reference=tx_data.get('reference'),
                raw_data=tx_data
            )
            
            return transaction
            
        except Exception as e:
            console.print(f"Error creating transaction: {e}", style="red")
            return None

async def test_improved_csob():
    """Test the improved ČSOB parser."""
    
    console.print("🏦 Improved ČSOB Slovakia Parser Test", style="bold blue")
    
    # Get PDF file
    pdf_path = input("Enter ČSOB PDF file path: ").strip().strip('"').strip("'")
    
    if not pdf_path:
        console.print("No file path provided.", style="yellow")
        return
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        console.print(f"❌ File not found: {pdf_path}", style="red")
        return
    
    # Create improved parser
    parser = ImprovedCSObParser()
    
    console.print(f"\n⚡ Parsing with improved ČSOB logic: {pdf_file.name}")
    
    try:
        result = await parser.parse_csob_format(str(pdf_file))
        
        # Display results
        display_improved_results(result, pdf_file.name)
        
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")

def display_improved_results(result, filename):
    """Display improved parsing results."""
    
    status = "✅ SUCCESS" if result.success else "❌ FAILED"
    status_style = "green" if result.success else "red"
    
    summary = f"""
🏦 Bank: ČSOB Slovakia (Improved Parser)
📄 File: {filename}
🎯 Status: {status}
📊 Transactions: {result.transaction_count}
⚠️  Warnings: {len(result.warnings)}
❌ Errors: {len(result.errors)}
"""
    
    console.print(Panel(summary, title="🚀 Improved ČSOB Results", border_style=status_style))
    
    if result.errors:
        console.print("\n❌ Errors:", style="red bold")
        for error in result.errors:
            console.print(f"  • {error}", style="red")
    
    if result.warnings:
        console.print("\n⚠️  Warnings:", style="yellow bold")
        for warning in result.warnings:
            console.print(f"  • {warning}", style="yellow")
    
    if result.transactions:
        console.print(f"\n💳 Improved ČSOB Transactions ({len(result.transactions)}):", style="green bold")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Date", style="cyan")
        table.add_column("Description", style="white", max_width=30)
        table.add_column("Amount (EUR)", style="green", justify="right")
        table.add_column("Merchant/Location", style="blue", max_width=25)
        table.add_column("Reference", style="yellow", max_width=15)
        
        total_amount = Decimal('0')
        for tx in result.transactions[:20]:  # Show first 20
            table.add_row(
                str(tx.date),
                tx.description or "N/A",
                f"{tx.amount:,.2f}",
                tx.merchant or "N/A",
                (tx.reference or "N/A")[:15] + "..." if tx.reference and len(tx.reference) > 15 else (tx.reference or "N/A")
            )
            total_amount += tx.amount
        
        console.print(table)
        
        if len(result.transactions) > 20:
            console.print(f"\n... and {len(result.transactions) - 20} more transactions")
        
        console.print(f"\n💰 Total Amount: {total_amount:,.2f} EUR", style="bold green")
        
        # Show some statistics
        debits = [tx for tx in result.transactions if tx.amount < 0]
        credits = [tx for tx in result.transactions if tx.amount > 0]
        
        console.print(f"📊 Statistics:", style="blue bold")
        console.print(f"  • Debit transactions: {len(debits)}")
        console.print(f"  • Credit transactions: {len(credits)}")
        console.print(f"  • Average transaction: {total_amount / len(result.transactions):,.2f} EUR")

async def main():
    """Main function."""
    try:
        await test_improved_csob()
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!", style="green")
    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="red")

if __name__ == "__main__":
    asyncio.run(main())