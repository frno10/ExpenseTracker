#!/usr/bin/env python3
"""
Final enhanced ČSOB parser based on real PDF structure analysis.
"""

import re
import pdfplumber
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import json

console = Console()

@dataclass
class CSObTransaction:
    """ČSOB transaction with all extracted data."""
    date: str
    description: str
    amount: float
    merchant: Optional[str] = None
    location: Optional[str] = None
    reference: Optional[str] = None
    original_amount: Optional[float] = None
    original_currency: Optional[str] = None
    exchange_rate: Optional[float] = None
    transaction_type: str = "unknown"

class FinalCSObParser:
    """Final ČSOB parser with accurate pattern matching."""
    
    def __init__(self):
        self.transactions: List[CSObTransaction] = []
        self.warnings: List[str] = []
        self.errors: List[str] = []
    
    def parse_pdf(self, pdf_path: str) -> List[CSObTransaction]:
        """Parse ČSOB PDF with accurate patterns."""
        
        console.print("📄 Extracting text from ČSOB PDF...", style="blue")
        
        text = self._extract_text(pdf_path)
        if not text:
            raise ValueError("Could not extract text from PDF")
        
        console.print("🔍 Parsing ČSOB transactions...", style="blue")
        
        # Parse transactions from text
        self._parse_transactions(text)
        
        # Validate and clean up
        self._post_process()
        
        return self.transactions
    
    def _extract_text(self, pdf_path: str) -> str:
        """Extract text using pdfplumber."""
        
        try:
            text_content = []
            
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
            
            return "\n".join(text_content)
            
        except Exception as e:
            self.errors.append(f"Error extracting text: {e}")
            return ""
    
    def _parse_transactions(self, text: str) -> None:
        """Parse transactions from extracted text."""
        
        lines = text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for transaction date pattern: "2. 5. Čerpanie úveru plat.kartou -12,90"
            date_match = re.match(r'^(\d{1,2})\. (\d{1,2})\. (.+)', line)
            if date_match:
                try:
                    tx = self._parse_transaction_block(date_match, lines, i)
                    if tx:
                        self.transactions.append(tx)
                except Exception as e:
                    self.warnings.append(f"Error parsing transaction at line {i}: {e}")
            
            i += 1
    
    def _parse_transaction_block(self, date_match, lines: List[str], start_idx: int) -> Optional[CSObTransaction]:
        """Parse a single transaction block."""
        
        day = int(date_match.group(1))
        month = int(date_match.group(2))
        rest_of_line = date_match.group(3).strip()
        
        # Skip non-transaction lines
        skip_patterns = ['Prevádza sa', 'Začiatočný stav', 'Konečný stav', 'Debetný obrat', 'Kreditný obrat']
        if any(pattern in rest_of_line for pattern in skip_patterns):
            return None
        
        # Parse the transaction line
        amount = None
        description = rest_of_line
        transaction_type = "unknown"
        
        # Extract amount from the line
        amount_match = re.search(r'(-?\d+[,.]\d+)$', rest_of_line)
        if amount_match:
            amount_str = amount_match.group(1).replace(',', '.')
            amount = float(amount_str)
            description = rest_of_line[:amount_match.start()].strip()
        
        # Determine transaction type
        if 'Čerpanie úveru plat.kartou' in description:
            transaction_type = 'card_payment'
            description = description.replace('Čerpanie úveru plat.kartou', '').strip()
        elif 'Splatka istiny' in description:
            transaction_type = 'payment'
        
        # Look ahead for additional information
        merchant = None
        location = None
        reference = None
        original_amount = None
        original_currency = None
        exchange_rate = None
        
        j = start_idx + 1
        while j < len(lines) and j < start_idx + 6:  # Look ahead max 6 lines
            next_line = lines[j].strip()
            
            # Stop if we hit another transaction
            if re.match(r'^\d{1,2}\. \d{1,2}\.', next_line):
                break
            
            # Extract reference
            if next_line.startswith('Ref. platiteľa:'):
                reference = next_line.replace('Ref. platiteľa:', '').strip()
            
            # Extract merchant/location
            if next_line.startswith('Miesto:'):
                merchant_info = next_line.replace('Miesto:', '').strip()
                merchant, location = self._split_merchant_location(merchant_info)
            
            # Extract exchange rate info
            if 'Suma:' in next_line and 'Kurz:' in next_line:
                exchange_info = self._parse_exchange_info(next_line)
                if exchange_info:
                    original_amount, original_currency, exchange_rate = exchange_info
            
            j += 1
        
        # Validate we have required data
        if amount is None:
            self.warnings.append(f"No amount found for transaction: {description}")
            return None
        
        # Create date string (assuming 2025)
        date_str = f"2025-{month:02d}-{day:02d}"
        
        return CSObTransaction(
            date=date_str,
            description=description,
            amount=amount,
            merchant=merchant,
            location=location,
            reference=reference,
            original_amount=original_amount,
            original_currency=original_currency,
            exchange_rate=exchange_rate,
            transaction_type=transaction_type
        )
    
    def _split_merchant_location(self, merchant_info: str) -> Tuple[Optional[str], Optional[str]]:
        """Split merchant name and location."""
        
        # Common Slovak city patterns
        city_patterns = [
            r'\bKOSICE\b', r'\bBRATISLAVA\b', r'\bZILINA\b', r'\bPRESOV\b',
            r'\bNITRA\b', r'\bTRNAVA\b', r'\bBANSKA BYSTRICA\b',
            r'\bKE\b', r'\bBA\b', r'\bZA\b', r'\bPO\b', r'\bNR\b', r'\bTT\b', r'\bBB\b'
        ]
        
        merchant = merchant_info
        location = None
        
        for pattern in city_patterns:
            match = re.search(pattern, merchant_info, re.IGNORECASE)
            if match:
                location = match.group(0)
                # Remove location from merchant name
                merchant = re.sub(pattern, '', merchant_info, flags=re.IGNORECASE).strip()
                merchant = re.sub(r'\s+', ' ', merchant).strip()
                break
        
        return merchant, location
    
    def _parse_exchange_info(self, line: str) -> Optional[Tuple[float, str, float]]:
        """Parse exchange rate from line like 'Suma: 12.9 EUR 30.04.2025 Kurz:'"""
        
        # Pattern for: "Suma: 12.9 EUR 30.04.2025 Kurz:" or "Suma: 4.83 PLN 02.05.2025 Kurz: 4,2"
        match = re.search(r'Suma:\s*([\d,.]+)\s*(\w{3}).*?(?:Kurz:\s*([\d,]+))?', line)
        if match:
            try:
                original_amount = float(match.group(1).replace(',', '.'))
                currency = match.group(2)
                
                # Exchange rate might be empty for EUR transactions
                exchange_rate = None
                if match.group(3):
                    exchange_rate = float(match.group(3).replace(',', '.'))
                
                return original_amount, currency, exchange_rate
            except (ValueError, AttributeError):
                pass
        
        return None
    
    def _post_process(self) -> None:
        """Post-process transactions for validation and cleanup."""
        
        # Remove duplicates
        seen = set()
        unique_transactions = []
        
        for tx in self.transactions:
            key = (tx.date, tx.amount, tx.description)
            if key not in seen:
                seen.add(key)
                unique_transactions.append(tx)
            else:
                self.warnings.append(f"Removed duplicate transaction: {tx.description}")
        
        self.transactions = unique_transactions
        
        # Clean merchant names
        for tx in self.transactions:
            if tx.merchant:
                tx.merchant = self._clean_merchant_name(tx.merchant)
    
    def _clean_merchant_name(self, merchant: str) -> str:
        """Clean merchant name."""
        
        # Remove common Slovak business suffixes
        cleanups = [
            (r'\s*S\.R\.O\.?$', ''),
            (r'\s*A\.S\.?$', ''),
            (r'\s*SLOVAKIA$', ''),
            (r'\s*SK$', ''),
            (r'\s*,.*$', ''),  # Remove everything after comma
        ]
        
        cleaned = merchant
        for pattern, replacement in cleanups:
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()

def display_results(transactions: List[CSObTransaction], warnings: List[str], errors: List[str], filename: str):
    """Display parsing results."""
    
    # Summary panel
    status = "✅ SUCCESS" if transactions else "❌ FAILED"
    panel_content = f"""🏦 Bank: ČSOB Slovakia (Final Parser)
📄 File: {filename}
🎯 Status: {status}
📊 Transactions: {len(transactions)}
⚠️  Warnings: {len(warnings)}
❌ Errors: {len(errors)}"""
    
    console.print(Panel(panel_content, title="🚀 Final ČSOB Results", border_style="green"))
    
    if errors:
        console.print("\n❌ Errors:", style="red bold")
        for error in errors[:5]:
            console.print(f"  • {error}", style="red")
    
    if warnings:
        console.print("\n⚠️  Warnings:", style="yellow bold")
        for warning in warnings[:5]:
            console.print(f"  • {warning}", style="yellow")
    
    if not transactions:
        return
    
    # Enhanced transaction table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Date", style="cyan")
    table.add_column("Merchant", style="white", max_width=30)
    table.add_column("Location", style="blue", max_width=12)
    table.add_column("Amount (EUR)", style="green", justify="right")
    table.add_column("Original", style="yellow", max_width=12)
    table.add_column("Rate", style="cyan", justify="right")
    table.add_column("Type", style="magenta", max_width=8)
    
    total_amount = 0
    for tx in transactions[:25]:  # Show first 25
        original_info = ""
        if tx.original_amount and tx.original_currency:
            original_info = f"{tx.original_amount:.1f} {tx.original_currency}"
        
        rate_info = ""
        if tx.exchange_rate:
            rate_info = f"{tx.exchange_rate:.2f}"
        
        tx_type = tx.transaction_type.replace("card_payment", "card").replace("payment", "pay")
        
        table.add_row(
            tx.date,
            tx.merchant or tx.description[:25],
            tx.location or "N/A",
            f"{tx.amount:,.2f}",
            original_info,
            rate_info,
            tx_type
        )
        total_amount += tx.amount
    
    console.print(f"\n💳 Final ČSOB Transactions ({len(transactions)}):")
    console.print(table)
    
    if len(transactions) > 25:
        console.print(f"\n... and {len(transactions) - 25} more transactions")
    
    console.print(f"\n💰 Total Amount: {total_amount:,.2f} EUR", style="bold green")

def analyze_transactions(transactions: List[CSObTransaction]):
    """Analyze transactions with enhanced insights."""
    
    console.print("\n📊 Enhanced Transaction Analysis", style="bold blue")
    
    # Financial summary
    total_spending = sum(abs(tx.amount) for tx in transactions if tx.amount < 0)
    total_income = sum(tx.amount for tx in transactions if tx.amount > 0)
    net_amount = total_income - total_spending
    
    console.print(f"\n💰 Financial Summary:", style="green bold")
    console.print(f"  • Total Income: €{total_income:,.2f}")
    console.print(f"  • Total Spending: €{total_spending:,.2f}")
    console.print(f"  • Net Amount: €{net_amount:,.2f}")
    
    # Spending by merchant
    merchant_spending = {}
    for tx in transactions:
        if tx.amount < 0 and tx.merchant:
            merchant = tx.merchant
            merchant_spending[merchant] = merchant_spending.get(merchant, 0) + abs(tx.amount)
    
    if merchant_spending:
        console.print(f"\n🏪 Top Merchants by Spending:", style="blue bold")
        top_merchants = sorted(merchant_spending.items(), key=lambda x: x[1], reverse=True)[:8]
        for merchant, amount in top_merchants:
            console.print(f"  • {merchant}: €{amount:.2f}")
    
    # Location analysis
    location_spending = {}
    for tx in transactions:
        if tx.amount < 0 and tx.location:
            location_spending[tx.location] = location_spending.get(tx.location, 0) + abs(tx.amount)
    
    if location_spending:
        console.print(f"\n🌍 Spending by Location:", style="blue bold")
        for location, amount in sorted(location_spending.items(), key=lambda x: x[1], reverse=True):
            console.print(f"  • {location}: €{amount:.2f}")
    
    # Currency analysis
    currency_spending = {}
    for tx in transactions:
        if tx.amount < 0:
            currency = tx.original_currency or 'EUR'
            currency_spending[currency] = currency_spending.get(currency, 0) + abs(tx.amount)
    
    console.print(f"\n💱 Currency Breakdown:", style="blue bold")
    for currency, amount in sorted(currency_spending.items(), key=lambda x: x[1], reverse=True):
        console.print(f"  • {currency}: €{amount:.2f}")
    
    # Exchange rate transactions
    fx_transactions = [tx for tx in transactions if tx.exchange_rate]
    if fx_transactions:
        console.print(f"\n🔄 Foreign Exchange Transactions: {len(fx_transactions)}", style="blue bold")
        for tx in fx_transactions[:3]:
            console.print(f"  • {tx.merchant}: {tx.original_amount:.2f} {tx.original_currency} @ {tx.exchange_rate:.2f}")

def save_results(transactions: List[CSObTransaction], filename_stem: str):
    """Save results to JSON."""
    
    data = {
        "bank": "ČSOB Slovakia",
        "parser": "Final Enhanced Parser",
        "total_transactions": len(transactions),
        "total_amount": sum(tx.amount for tx in transactions),
        "transactions": [
            {
                "date": tx.date,
                "description": tx.description,
                "amount": tx.amount,
                "merchant": tx.merchant,
                "location": tx.location,
                "reference": tx.reference,
                "original_amount": tx.original_amount,
                "original_currency": tx.original_currency,
                "exchange_rate": tx.exchange_rate,
                "transaction_type": tx.transaction_type
            }
            for tx in transactions
        ]
    }
    
    output_file = Path(f"final_csob_{filename_stem}_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    console.print(f"💾 Results saved to: {output_file.absolute()}", style="green")

def main():
    """Main function."""
    
    console.print("🚀 Final Enhanced ČSOB Slovakia PDF Parser", style="bold blue")
    
    pdf_path = input("Enter ČSOB PDF file path: ").strip().strip('"').strip("'")
    
    if not pdf_path:
        console.print("No file path provided.", style="yellow")
        return
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        console.print(f"❌ File not found: {pdf_path}", style="red")
        return
    
    try:
        parser = FinalCSObParser()
        transactions = parser.parse_pdf(str(pdf_file))
        
        display_results(transactions, parser.warnings, parser.errors, pdf_file.name)
        
        if transactions:
            # Offer analysis
            analyze_choice = input("\n🔍 Run detailed analysis? (y/n): ").lower().strip()
            if analyze_choice == 'y':
                analyze_transactions(transactions)
            
            # Offer to save
            save_choice = input("\n💾 Save results to JSON? (y/n): ").lower().strip()
            if save_choice == 'y':
                save_results(transactions, pdf_file.stem)
        
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()