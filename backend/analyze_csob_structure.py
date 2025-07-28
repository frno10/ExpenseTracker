#!/usr/bin/env python3
"""
Analyze ČSOB PDF structure to understand parsing issues.
"""

import asyncio
import re
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from app.parsers.pdf_parser import PDFParser

console = Console()

async def analyze_csob_structure():
    """Analyze the structure of ČSOB PDF to improve parsing."""
    
    console.print("🔍 ČSOB PDF Structure Analysis", style="bold blue")
    
    # Get PDF file
    pdf_path = input("Enter ČSOB PDF file path: ").strip().strip('"').strip("'")
    
    if not pdf_path:
        console.print("No file path provided.", style="yellow")
        return
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        console.print(f"❌ File not found: {pdf_path}", style="red")
        return
    
    # Extract text
    parser = PDFParser()
    text_content = await parser._extract_text(str(pdf_file))
    
    if not text_content:
        console.print("❌ Could not extract text", style="red")
        return
    
    console.print(f"📄 Extracted {len(text_content)} characters")
    
    # Show first few lines to understand structure
    lines = text_content.split('\n')
    console.print(f"📊 Total lines: {len(lines)}")
    
    # Find transaction patterns
    console.print("\n🔍 Looking for transaction patterns...")
    
    transaction_lines = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Look for date patterns
        if re.match(r'\d{1,2}\.\s*\d{1,2}\.', line):
            transaction_lines.append((i, line))
    
    console.print(f"Found {len(transaction_lines)} potential transaction lines")
    
    # Show some examples with context
    console.print("\n📋 Transaction Examples with Context:")
    
    for i, (line_num, tx_line) in enumerate(transaction_lines[:5]):
        console.print(f"\n--- Transaction {i+1} (Line {line_num}) ---")
        console.print(f"Transaction: {tx_line}", style="green")
        
        # Show next few lines for context
        for j in range(1, 6):
            if line_num + j < len(lines):
                context_line = lines[line_num + j].strip()
                if context_line:
                    console.print(f"  +{j}: {context_line}", style="dim")
                    
                    # Check for specific patterns
                    if context_line.startswith("Miesto:"):
                        console.print(f"    → Location found: {context_line}", style="blue")
                    elif context_line.startswith("Ref."):
                        console.print(f"    → Reference found: {context_line}", style="yellow")
                    elif "Kurz:" in context_line:
                        console.print(f"    → Exchange rate found: {context_line}", style="magenta")
                    elif context_line.startswith("Suma:"):
                        console.print(f"    → Amount info: {context_line}", style="cyan")
    
    # Look for exchange rate patterns
    console.print("\n💱 Exchange Rate Analysis:")
    exchange_lines = []
    for line in lines:
        if "Kurz:" in line:
            exchange_lines.append(line.strip())
    
    console.print(f"Found {len(exchange_lines)} lines with exchange rates")
    for ex_line in exchange_lines[:10]:
        console.print(f"  • {ex_line}", style="magenta")
    
    # Look for amount patterns
    console.print("\n💰 Amount Pattern Analysis:")
    amount_patterns = []
    for line in lines:
        # Look for various amount patterns
        amounts = re.findall(r'-?\d+[,.]?\d*\s*(?:EUR|PLN|USD)', line)
        if amounts:
            amount_patterns.append((line.strip(), amounts))
    
    console.print(f"Found {len(amount_patterns)} lines with currency amounts")
    for line, amounts in amount_patterns[:10]:
        console.print(f"  • {line} → {amounts}", style="cyan")
    
    # Analyze location patterns
    console.print("\n📍 Location Pattern Analysis:")
    location_lines = []
    for line in lines:
        if line.strip().startswith("Miesto:"):
            location_lines.append(line.strip())
    
    console.print(f"Found {len(location_lines)} location lines")
    for loc_line in location_lines[:10]:
        console.print(f"  • {loc_line}", style="blue")
    
    # Save sample text for analysis
    sample_file = "csob_sample_text.txt"
    with open(sample_file, 'w', encoding='utf-8') as f:
        f.write(text_content[:5000])  # First 5000 chars
    
    console.print(f"\n💾 Sample text saved to: {sample_file}")

async def main():
    """Main function."""
    try:
        await analyze_csob_structure()
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!", style="green")
    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="red")

if __name__ == "__main__":
    asyncio.run(main())