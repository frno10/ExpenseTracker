#!/usr/bin/env python3
"""
Enhanced ČSOB parser with better data extraction, validation, and analysis.
"""

import asyncio
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

@dataclass
class Transaction:
    """Enhanced transaction data structure."""
    date: str
    description: str
    amount: float
    merchant: str
    location: Optional[str] = None
    reference: Optional[str] = None
    original_amount: Optional[float] = None
    original_currency: Optional[str] = None
    exchange_rate: Optional[float] = None
    transaction_type: Optional[str] = None

class EnhancedCSObParser:
    """Enhanced ČSOB Slovakia PDF parser with advanced features."""
    
    def __init__(self):
        self.transactions: List[Transaction] = []
        self.parsing_errors: List[str] = []
        self.warnings: List[str] = []
    
    async def parse_pdf(self, pdf_path: str) -> List[Transaction]:
        """Parse ČSOB PDF with enhanced logic."""
        
        console.print("📄 Extracting text from PDF...", style="blue")
        
        # Import here to avoid circular imports
        from app.parsers.pdf_parser import PDFParser
        parser = PDFParser()
        
        text_content = await parser._extract_text(pdf_path)
        if not text_content:
            raise ValueError("No text content extracted from PDF")
        
        console.print("🔍 Parsing transactions with enhanced logic...", style="blue")
        
        # Split into lines and process
        lines = text_content.split('\n')
        self._parse_transactions(lines)
        
        # Post-process and validate
        self._post_process_transactions()
        
        return self.transactions
    
    def _parse_transactions(self, lines: List[str]) -> None:
        """Parse transactions from text lines."""
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for transaction date pattern
            date_match = re.match(r'(\d{1,2}\. \d{1,2}\.)\\s+(.+)', line)
            if date_match:
                try:
                    transaction = self._parse_single_transaction(date_match, lines, i)
                    if transaction:
                        self.transactions.append(transaction)
                except Exception as e:
                    self.parsing_errors.append(f"Error parsing line {i}: {str(e)}")
            
            i += 1
    
    def _parse_single_transaction(self, date_match, lines: List[str], start_idx: int) -> Optional[Transaction]:
        """Parse a single transaction with enhanced data extraction."""
        
        date_str = date_match.group(1)
        description = date_match.group(2).strip()
        
        # Skip non-transaction lines
        skip_patterns = [
            'VÝPIS Z ÚČTU', 'Účet číslo', 'Splatka istiny', 'Prevádza sa',
            'Obdobie:', 'Strana:', 'ACCOUNT STATEMENT'
        ]
        
        if any(pattern in description for pattern in skip_patterns):
            return None
        
        # Initialize transaction data
        amount = None
        merchant = None
        location = None
        reference = None
        original_amount = None
        original_currency = None
        exchange_rate = None
        transaction_type = None
        
        # Extract transaction type
        if 'Čerpanie úveru plat.kartou' in description:
            transaction_type = 'card_payment'
            description = description.replace('Čerpanie úveru plat.kartou', '').strip()
        elif 'Splatka' in description:
            transaction_type = 'payment'
        
        # Look for amount in current line
        amount_match = re.search(r'(-?\d+[,.]\d*)\\s*$', description)
        if amount_match:
            amount = self._parse_amount(amount_match.group(1))
            description = description[:amount_match.start()].strip()
        
        # Look ahead for additional information
        j = start_idx + 1
        while j < len(lines) and j < start_idx + 10:  # Look ahead max 10 lines
            next_line = lines[j].strip()
            
            # Stop if we hit another transaction
            if re.match(r'\d{1,2}\. \d{1,2}\.', next_line):
                break
            
            # Extract merchant/location
            if next_line.startswith('Miesto:'):
                merchant_location = next_line.replace('Miesto:', '').strip()
                merchant, location = self._split_merchant_location(merchant_location)
            
            # Extract reference
            if '/VS' in next_line or 'Ref.' in next_line:
                reference = next_line.strip()
            
            # Extract exchange rate and original amount
            if 'Kurz:' in next_line:
                exchange_info = self._parse_exchange_info(next_line)
                if exchange_info:
                    original_amount, original_currency, exchange_rate = exchange_info
            
            # Extract amount if not found yet
            if amount is None:
                amount_match = re.search(r'(-?\d+[,.]\d*)', next_line)
                if amount_match and not any(skip in next_line for skip in ['Kurz:', 'Ref.']):
                    amount = self._parse_amount(amount_match.group(1))
            
            j += 1
        
        # Validate we have minimum required data
        if amount is None:
            self.warnings.append(f"No amount found for transaction: {description}")
            return None
        
        # Parse date
        try:
            day, month = date_str.replace('.', '').split()
            date_obj = f"2025-{int(month):02d}-{int(day):02d}"
        except Exception as e:
            self.parsing_errors.append(f"Error parsing date '{date_str}': {e}")
            return None
        
        return Transaction(
            date=date_obj,
            description=description,
            amount=amount,
            merchant=merchant or description,
            location=location,
            reference=reference,
            original_amount=original_amount,
            original_currency=original_currency,
            exchange_rate=exchange_rate,
            transaction_type=transaction_type
        )
    
    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount string to float."""
        try:
            return float(amount_str.replace(',', '.'))
        except ValueError:
            raise ValueError(f"Invalid amount format: {amount_str}")
    
    def _split_merchant_location(self, merchant_location: str) -> Tuple[str, Optional[str]]:
        """Split merchant and location from combined string."""
        
        # Common location patterns for Slovakia
        location_patterns = [
            r'\\b(KOSICE|BRATISLAVA|PRAHA|BRNO|ZILINA|PRESOV|NITRA|BANSKA BYSTRICA)\\b',
            r'\\b(KE|BA|PR|BR|ZA|PO|NR|BB)\\b',  # City abbreviations
            r'\\b\d{4}\\b',  # Postal codes
        ]
        
        merchant = merchant_location
        location = None
        
        for pattern in location_patterns:
            match = re.search(pattern, merchant_location, re.IGNORECASE)
            if match:
                location = match.group(1)
                # Remove location from merchant name
                merchant = re.sub(pattern, '', merchant_location, flags=re.IGNORECASE).strip()
                merchant = re.sub(r'\\s+', ' ', merchant).strip()  # Clean up spaces
                break
        
        return merchant, location
    
    def _parse_exchange_info(self, line: str) -> Optional[Tuple[float, str, float]]:
        """Parse exchange rate information."""
        
        # Pattern: "Suma: 4.83 PLN 02.05.2025 Kurz: 4,2"
        match = re.search(r'Suma:\\s*([\\d,.]*)\\s*(\\w{3}).*?Kurz:\\s*([\\d,]*)', line)
        if match:
            try:
                original_amount = float(match.group(1).replace(',', '.'))
                currency = match.group(2)
                exchange_rate = float(match.group(3).replace(',', '.'))
                return original_amount, currency, exchange_rate
            except ValueError:
                pass
        
        return None
    
    def _post_process_transactions(self) -> None:
        """Post-process transactions for validation and enhancement."""
        
        console.print("🔧 Post-processing transactions...", style="blue")
        
        # Check for duplicate transactions
        seen_transactions = set()
        duplicates = []
        
        for i, tx in enumerate(self.transactions):
            tx_key = (tx.date, tx.amount, tx.merchant)
            if tx_key in seen_transactions:
                duplicates.append(i)
            else:
                seen_transactions.add(tx_key)
        
        if duplicates:
            self.warnings.append(f"Found {len(duplicates)} potential duplicate transactions")
        
        # Enhance merchant names
        for tx in self.transactions:
            tx.merchant = self._clean_merchant_name(tx.merchant)
    
    def _clean_merchant_name(self, merchant: str) -> str:
        """Clean and standardize merchant names."""
        
        # Remove common prefixes/suffixes
        cleanups = [
            (r'^ČERPANIE ÚVERU PLAT\\.KARTOU\\s*', ''),
            (r'\\s*S\\.R\\.O\\.?$', ''),
            (r'\\s*A\\.S\\.?$', ''),
            (r'\\s*SLOVAKIA$', ''),
            (r'\\s*SK$', ''),
        ]
        
        cleaned = merchant
        for pattern, replacement in cleanups:
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()

async def main():
    """Main function to test enhanced parser."""
    
    console.print("🚀 Enhanced ČSOB Slovakia PDF Parser", style="bold blue")
    
    # Get PDF file
    pdf_path = input("Enter ČSOB PDF file path: ").strip().strip('"').strip("'")
    
    if not pdf_path:
        console.print("No file path provided.", style="yellow")
        return
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        console.print(f"❌ File not found: {pdf_path}", style="red")
        return
    
    try:
        # Parse with enhanced parser
        parser = EnhancedCSObParser()
        transactions = await parser.parse_pdf(str(pdf_file))
        
        # Display results
        display_enhanced_results(transactions, parser.warnings, parser.parsing_errors, pdf_file.name)
        
        # Offer analysis
        if transactions:
            analyze = input("\n🔍 Run detailed analysis? (y/n): ").lower().strip()
            if analyze == 'y':
                analyze_transactions(transactions)
        
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")

def display_enhanced_results(transactions: List[Transaction], warnings: List[str], errors: List[str], filename: str):
    """Display enhanced parsing results."""
    
    # Summary panel
    panel_content = f"""🏦 Bank: ČSOB Slovakia (Enhanced Parser)
📄 File: {filename}
🎯 Status: {'✅ SUCCESS' if transactions else '❌ FAILED'}
📊 Transactions: {len(transactions)}
⚠️  Warnings: {len(warnings)}
❌ Errors: {len(errors)}"""
    
    console.print(Panel(panel_content, title="🚀 Enhanced ČSOB Results", border_style="green"))
    
    if errors:
        console.print("\n❌ Parsing Errors:", style="red bold")
        for error in errors[:5]:  # Show first 5 errors
            console.print(f"  • {error}", style="red")
    
    if warnings:
        console.print("\n⚠️  Warnings:", style="yellow bold")
        for warning in warnings[:5]:  # Show first 5 warnings
            console.print(f"  • {warning}", style="yellow")
    
    if not transactions:
        return
    
    # Enhanced transaction table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Date", style="cyan")
    table.add_column("Merchant", style="white", max_width=25)
    table.add_column("Location", style="blue", max_width=15)
    table.add_column("Amount (EUR)", style="green", justify="right")
    table.add_column("Original", style="yellow", max_width=15)
    table.add_column("Rate", style="cyan", justify="right")
    
    total_amount = 0
    for tx in transactions[:20]:  # Show first 20
        original_info = ""
        if tx.original_amount and tx.original_currency:
            original_info = f"{tx.original_amount:.2f} {tx.original_currency}"
        
        rate_info = ""
        if tx.exchange_rate:
            rate_info = f"{tx.exchange_rate:.2f}"
        
        table.add_row(
            tx.date,
            tx.merchant,
            tx.location or "N/A",
            f"{tx.amount:,.2f}",
            original_info,
            rate_info
        )
        total_amount += tx.amount
    
    console.print(f"\n💳 Enhanced ČSOB Transactions ({len(transactions)}):")
    console.print(table)
    
    if len(transactions) > 20:
        console.print(f"\n... and {len(transactions) - 20} more transactions")
    
    console.print(f"\n💰 Total Amount: {total_amount:,.2f} EUR", style="bold green")

def analyze_transactions(transactions: List[Transaction]):
    """Perform detailed transaction analysis."""
    
    console.print("\n📊 Transaction Analysis", style="bold blue")
    
    # Spending by merchant
    merchant_spending = {}
    location_spending = {}
    currency_breakdown = {}
    
    for tx in transactions:
        # Merchant analysis (only negative amounts = spending)
        if tx.amount < 0:
            spending = abs(tx.amount)
            merchant_spending[tx.merchant] = merchant_spending.get(tx.merchant, 0) + spending
            
            # Location analysis
            if tx.location:
                location_spending[tx.location] = location_spending.get(tx.location, 0) + spending
            
            # Currency analysis
            currency = tx.original_currency or 'EUR'
            currency_breakdown[currency] = currency_breakdown.get(currency, 0) + spending
    
    # Top merchants
    console.print("\n🏪 Top Merchants by Spending:", style="blue bold")
    top_merchants = sorted(merchant_spending.items(), key=lambda x: x[1], reverse=True)[:10]
    for merchant, amount in top_merchants:
        console.print(f"  • {merchant}: €{amount:.2f}")
    
    # Top locations
    if location_spending:
        console.print("\n🌍 Spending by Location:", style="blue bold")
        top_locations = sorted(location_spending.items(), key=lambda x: x[1], reverse=True)[:5]
        for location, amount in top_locations:
            console.print(f"  • {location}: €{amount:.2f}")
    
    # Currency breakdown
    console.print("\n💱 Currency Breakdown:", style="blue bold")
    for currency, amount in sorted(currency_breakdown.items(), key=lambda x: x[1], reverse=True):
        console.print(f"  • {currency}: €{amount:.2f}")
    
    # Transaction types
    type_counts = {}
    for tx in transactions:
        tx_type = tx.transaction_type or 'unknown'
        type_counts[tx_type] = type_counts.get(tx_type, 0) + 1
    
    console.print("\n📋 Transaction Types:", style="blue bold")
    for tx_type, count in type_counts.items():
        console.print(f"  • {tx_type}: {count} transactions")

if __name__ == "__main__":
    asyncio.run(main())