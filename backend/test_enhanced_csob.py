#!/usr/bin/env python3
"""
Enhanced ČSOB parser test with better analysis and validation.
"""

import asyncio
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

@dataclass
class EnhancedTransaction:
    """Enhanced transaction with more detailed data."""
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

async def parse_enhanced_csob(pdf_path: str) -> List[EnhancedTransaction]:
    """Parse ČSOB PDF with enhanced data extraction."""
    
    console.print("📄 Extracting text from PDF...", style="blue")
    
    from app.parsers.pdf_parser import PDFParser
    parser = PDFParser()
    
    text_content = await parser._extract_text(pdf_path)
    if not text_content:
        raise ValueError("No text content extracted")
    
    console.print("🔍 Enhanced parsing with better logic...", style="blue")
    
    transactions = []
    lines = text_content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for date pattern
        date_match = re.match(r'(\d{1,2}\. \d{1,2}\.)\s+(.+)', line)
        if date_match:
            try:
                tx = parse_transaction_block(date_match, lines, i)
                if tx:
                    transactions.append(tx)
            except Exception as e:
                console.print(f"⚠️  Error parsing line {i}: {e}", style="yellow")
        
        i += 1
    
    return transactions

def parse_transaction_block(date_match, lines: List[str], start_idx: int) -> Optional[EnhancedTransaction]:
    """Parse a single transaction block with enhanced extraction."""
    
    date_str = date_match.group(1)
    description = date_match.group(2).strip()
    
    # Skip non-transaction lines
    skip_patterns = ['VÝPIS Z ÚČTU', 'Účet číslo', 'Prevádza sa', 'Obdobie:', 'Strana:']
    if any(pattern in description for pattern in skip_patterns):
        return None
    
    # Initialize data
    amount = None
    merchant = None
    location = None
    reference = None
    original_amount = None
    original_currency = None
    exchange_rate = None
    transaction_type = None
    
    # Determine transaction type
    if 'Čerpanie úveru plat.kartou' in description:
        transaction_type = 'card_payment'
        description = description.replace('Čerpanie úveru plat.kartou', '').strip()
    elif 'Splatka' in description:
        transaction_type = 'payment'
    
    # Look for amount in current line
    amount_match = re.search(r'(-?\d+[,.]\d*)\s*$', description)
    if amount_match:
        amount = parse_amount(amount_match.group(1))
        description = description[:amount_match.start()].strip()
    
    # Look ahead for more info
    j = start_idx + 1
    while j < len(lines) and j < start_idx + 8:
        next_line = lines[j].strip()
        
        # Stop at next transaction
        if re.match(r'\d{1,2}\. \d{1,2}\.', next_line):
            break
        
        # Extract merchant/location
        if next_line.startswith('Miesto:'):
            merchant_info = next_line.replace('Miesto:', '').strip()
            merchant, location = split_merchant_location(merchant_info)
        
        # Extract reference
        if '/VS' in next_line:
            reference = next_line.strip()
        
        # Extract exchange info
        if 'Kurz:' in next_line:
            exchange_info = parse_exchange_rate(next_line)
            if exchange_info:
                original_amount, original_currency, exchange_rate = exchange_info
        
        # Find amount if not found
        if amount is None:
            amount_match = re.search(r'(-?\d+[,.]\d*)', next_line)
            if amount_match and 'Kurz:' not in next_line:
                amount = parse_amount(amount_match.group(1))
        
        j += 1
    
    if amount is None:
        return None
    
    # Parse date
    try:
        day, month = date_str.replace('.', '').split()
        date_obj = f"2025-{int(month):02d}-{int(day):02d}"
    except:
        return None
    
    return EnhancedTransaction(
        date=date_obj,
        description=description,
        amount=amount,
        merchant=merchant or clean_merchant_name(description),
        location=location,
        reference=reference,
        original_amount=original_amount,
        original_currency=original_currency,
        exchange_rate=exchange_rate,
        transaction_type=transaction_type
    )

def parse_amount(amount_str: str) -> float:
    """Parse amount string to float."""
    return float(amount_str.replace(',', '.'))

def split_merchant_location(merchant_info: str) -> Tuple[str, Optional[str]]:
    """Split merchant name and location."""
    
    # Look for city patterns
    city_patterns = [
        r'\bKOSICE\b', r'\bBRATISLAVA\b', r'\bPRAHA\b', r'\bBRNO\b',
        r'\bZILINA\b', r'\bPRESOV\b', r'\bNITRA\b',
        r'\bKE\b', r'\bBA\b', r'\bPR\b', r'\bBR\b'
    ]
    
    merchant = merchant_info
    location = None
    
    for pattern in city_patterns:
        match = re.search(pattern, merchant_info, re.IGNORECASE)
        if match:
            location = match.group(0)
            merchant = re.sub(pattern, '', merchant_info, flags=re.IGNORECASE).strip()
            merchant = re.sub(r'\s+', ' ', merchant).strip()
            break
    
    return merchant, location

def parse_exchange_rate(line: str) -> Optional[Tuple[float, str, float]]:
    """Parse exchange rate from line like 'Suma: 4.83 PLN 02.05.2025 Kurz: 4,2'"""
    
    match = re.search(r'Suma:\s*([\d,.]+)\s*(\w{3}).*?Kurz:\s*([\d,]+)', line)
    if match:
        try:
            original_amount = float(match.group(1).replace(',', '.'))
            currency = match.group(2)
            exchange_rate = float(match.group(3).replace(',', '.'))
            return original_amount, currency, exchange_rate
        except:
            pass
    
    return None

def clean_merchant_name(merchant: str) -> str:
    """Clean merchant name."""
    
    # Remove common Slovak business suffixes
    cleanups = [
        (r'\s*S\.R\.O\.?$', ''),
        (r'\s*A\.S\.?$', ''),
        (r'\s*SLOVAKIA$', ''),
        (r'\s*SK$', ''),
    ]
    
    cleaned = merchant
    for pattern, replacement in cleanups:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    
    return cleaned.strip()

def display_enhanced_results(transactions: List[EnhancedTransaction], filename: str):
    """Display enhanced results with better formatting."""
    
    console.print(Panel(
        f"🏦 Bank: ČSOB Slovakia (Enhanced)\n"
        f"📄 File: {filename}\n"
        f"📊 Transactions: {len(transactions)}\n"
        f"🎯 Status: ✅ SUCCESS",
        title="🚀 Enhanced ČSOB Results",
        border_style="green"
    ))
    
    if not transactions:
        return
    
    # Create enhanced table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Date", style="cyan")
    table.add_column("Merchant", style="white", max_width=30)
    table.add_column("Location", style="blue", max_width=12)
    table.add_column("Amount (EUR)", style="green", justify="right")
    table.add_column("Original", style="yellow", max_width=12)
    table.add_column("Rate", style="cyan", justify="right")
    table.add_column("Type", style="magenta", max_width=10)
    
    total_amount = 0
    for tx in transactions[:25]:  # Show first 25
        original_info = ""
        if tx.original_amount and tx.original_currency:
            original_info = f"{tx.original_amount:.1f} {tx.original_currency}"
        
        rate_info = ""
        if tx.exchange_rate:
            rate_info = f"{tx.exchange_rate:.2f}"
        
        tx_type = tx.transaction_type or "other"
        tx_type = tx_type.replace("card_payment", "card").replace("payment", "pay")
        
        table.add_row(
            tx.date,
            tx.merchant,
            tx.location or "N/A",
            f"{tx.amount:,.2f}",
            original_info,
            rate_info,
            tx_type
        )
        total_amount += tx.amount
    
    console.print(f"\n💳 Enhanced ČSOB Transactions ({len(transactions)}):")
    console.print(table)
    
    if len(transactions) > 25:
        console.print(f"\n... and {len(transactions) - 25} more transactions")
    
    console.print(f"\n💰 Total Amount: {total_amount:,.2f} EUR", style="bold green")

def analyze_enhanced_transactions(transactions: List[EnhancedTransaction]):
    """Perform enhanced transaction analysis."""
    
    console.print("\n📊 Enhanced Transaction Analysis", style="bold blue")
    
    # Calculate spending (negative amounts only)
    spending_by_merchant = {}
    spending_by_location = {}
    currency_spending = {}
    total_spending = 0
    total_income = 0
    
    for tx in transactions:
        if tx.amount < 0:  # Spending
            spending = abs(tx.amount)
            total_spending += spending
            
            # By merchant
            spending_by_merchant[tx.merchant] = spending_by_merchant.get(tx.merchant, 0) + spending
            
            # By location
            if tx.location:
                spending_by_location[tx.location] = spending_by_location.get(tx.location, 0) + spending
            
            # By currency
            currency = tx.original_currency or 'EUR'
            currency_spending[currency] = currency_spending.get(currency, 0) + spending
        
        else:  # Income
            total_income += tx.amount
    
    # Display summary
    console.print(f"\n💰 Financial Summary:", style="green bold")
    console.print(f"  • Total Income: €{total_income:,.2f}")
    console.print(f"  • Total Spending: €{total_spending:,.2f}")
    console.print(f"  • Net Amount: €{total_income - total_spending:,.2f}")
    
    # Top merchants
    console.print(f"\n🏪 Top Merchants by Spending:", style="blue bold")
    top_merchants = sorted(spending_by_merchant.items(), key=lambda x: x[1], reverse=True)[:8]
    for merchant, amount in top_merchants:
        console.print(f"  • {merchant}: €{amount:.2f}")
    
    # Spending by location
    if spending_by_location:
        console.print(f"\n🌍 Spending by Location:", style="blue bold")
        top_locations = sorted(spending_by_location.items(), key=lambda x: x[1], reverse=True)[:5]
        for location, amount in top_locations:
            console.print(f"  • {location}: €{amount:.2f}")
    
    # Currency breakdown
    console.print(f"\n💱 Currency Breakdown:", style="blue bold")
    for currency, amount in sorted(currency_spending.items(), key=lambda x: x[1], reverse=True):
        console.print(f"  • {currency}: €{amount:.2f}")
    
    # Exchange rate transactions
    fx_transactions = [tx for tx in transactions if tx.exchange_rate]
    if fx_transactions:
        console.print(f"\n🔄 Foreign Exchange Transactions: {len(fx_transactions)}", style="blue bold")
        for tx in fx_transactions[:3]:  # Show first 3
            console.print(f"  • {tx.merchant}: {tx.original_amount:.2f} {tx.original_currency} @ {tx.exchange_rate:.2f}")

async def main():
    """Main function."""
    
    console.print("🚀 Enhanced ČSOB Slovakia PDF Parser", style="bold blue")
    
    pdf_path = input("Enter ČSOB PDF file path: ").strip().strip('"').strip("'")
    
    if not pdf_path:
        console.print("No file path provided.", style="yellow")
        return
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        console.print(f"❌ File not found: {pdf_path}", style="red")
        return
    
    try:
        transactions = await parse_enhanced_csob(str(pdf_file))
        display_enhanced_results(transactions, pdf_file.name)
        
        if transactions:
            analyze = input("\n🔍 Run detailed analysis? (y/n): ").lower().strip()
            if analyze == 'y':
                analyze_enhanced_transactions(transactions)
        
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())