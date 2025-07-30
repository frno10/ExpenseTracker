#!/usr/bin/env python3
"""
PDF Analysis Tool - Helps you understand PDF structure and create parsing patterns.
"""

import asyncio
import re
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from app.parsers.pdf_parser import PDFParser

console = Console()

async def analyze_pdf_structure(pdf_path: str):
    """Analyze PDF structure to help create parsing patterns."""
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        console.print(f"❌ File not found: {pdf_path}", style="red")
        return
    
    console.print(f"🔍 Analyzing PDF: {pdf_file.name}", style="blue bold")
    
    # Create PDF parser
    parser = PDFParser()
    
    # Extract raw text
    console.print("\n📄 Extracting text content...")
    text_content = await parser._extract_text(str(pdf_file))
    
    if not text_content:
        console.print("❌ No text content found in PDF", style="red")
        return
    
    console.print(f"✅ Extracted {len(text_content)} characters", style="green")
    
    # Show first 2000 characters
    console.print("\n📖 First 2000 characters of PDF content:")
    preview = text_content[:2000]
    console.print(Panel(preview, title="PDF Text Preview", border_style="blue"))
    
    # Analyze patterns
    console.print("\n🔍 Pattern Analysis:", style="blue bold")
    
    # Look for date patterns
    date_patterns = [
        (r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b', "MM/DD/YYYY or DD/MM/YYYY"),
        (r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b', "YYYY-MM-DD"),
        (r'\b(\d{1,2}\.\d{1,2}\.\d{2,4})\b', "DD.MM.YYYY"),
        (r'\b(\w{3}\s+\d{1,2},?\s+\d{4})\b', "Jan 15, 2024"),
    ]
    
    console.print("\n📅 Date Patterns Found:")
    for pattern, description in date_patterns:
        matches = re.findall(pattern, text_content)
        if matches:
            console.print(f"  ✅ {description}: {len(matches)} matches")
            console.print(f"     Examples: {matches[:5]}")
        else:
            console.print(f"  ❌ {description}: No matches")
    
    # Look for amount patterns
    amount_patterns = [
        (r'\$\s*(\d{1,3}(?:,\d{3})*\.\d{2})', "Dollar amounts ($1,234.56)"),
        (r'(\d{1,3}(?:,\d{3})*\.\d{2})', "Decimal amounts (1,234.56)"),
        (r'\(\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})\)', "Negative amounts in parentheses"),
        (r'-\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})', "Negative amounts with minus"),
    ]
    
    console.print("\n💰 Amount Patterns Found:")
    for pattern, description in amount_patterns:
        matches = re.findall(pattern, text_content)
        if matches:
            console.print(f"  ✅ {description}: {len(matches)} matches")
            console.print(f"     Examples: {matches[:5]}")
        else:
            console.print(f"  ❌ {description}: No matches")
    
    # Look for potential transaction lines
    console.print("\n📋 Potential Transaction Lines:")
    lines = text_content.split('\n')
    transaction_lines = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Look for lines with both date and amount patterns
        has_date = any(re.search(pattern, line) for pattern, _ in date_patterns)
        has_amount = any(re.search(pattern, line) for pattern, _ in amount_patterns)
        
        if has_date and has_amount:
            transaction_lines.append((i + 1, line))
    
    if transaction_lines:
        console.print(f"  ✅ Found {len(transaction_lines)} potential transaction lines:")
        for line_num, line in transaction_lines[:10]:  # Show first 10
            console.print(f"     Line {line_num}: {line[:80]}...")
    else:
        console.print("  ❌ No obvious transaction lines found")
    
    # Suggest patterns
    console.print("\n🎯 Suggested Parsing Patterns:", style="green bold")
    
    if transaction_lines:
        # Analyze the structure of transaction lines
        sample_line = transaction_lines[0][1]
        console.print(f"\nAnalyzing sample line: {sample_line}")
        
        # Try to create a pattern
        suggested_patterns = create_suggested_patterns(sample_line)
        
        console.print("\n📝 Suggested regex patterns:")
        for i, pattern in enumerate(suggested_patterns, 1):
            console.print(f"  {i}. {pattern}")
    
    # Save analysis to file
    save_analysis = input("\n💾 Save analysis to file? (y/n): ").strip().lower()
    if save_analysis in ['y', 'yes']:
        save_pdf_analysis(pdf_file.stem, text_content, transaction_lines)

def create_suggested_patterns(sample_line: str) -> list:
    """Create suggested regex patterns based on a sample transaction line."""
    
    patterns = []
    
    # Pattern 1: Date + Description + Amount
    patterns.append(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+(\$?\s*-?\d{1,3}(?:,\d{3})*\.\d{2})')
    
    # Pattern 2: Date + Description + Reference + Amount  
    patterns.append(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+(\#?\d+)?\s+(\$?\s*-?\d{1,3}(?:,\d{3})*\.\d{2})')
    
    # Pattern 3: More flexible date format
    patterns.append(r'(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\s+(.+?)\s+([+-]?\$?\s*\d{1,3}(?:,\d{3})*\.\d{2})')
    
    return patterns

def save_pdf_analysis(filename_stem: str, text_content: str, transaction_lines: list):
    """Save PDF analysis to files."""
    
    # Save raw text
    text_file = Path(f"{filename_stem}_extracted_text.txt")
    with open(text_file, 'w', encoding='utf-8') as f:
        f.write(text_content)
    
    # Save transaction lines
    if transaction_lines:
        lines_file = Path(f"{filename_stem}_transaction_lines.txt")
        with open(lines_file, 'w', encoding='utf-8') as f:
            f.write("Potential Transaction Lines:\n")
            f.write("=" * 50 + "\n\n")
            for line_num, line in transaction_lines:
                f.write(f"Line {line_num}: {line}\n")
    
    console.print(f"💾 Analysis saved to:", style="green")
    console.print(f"  📄 Raw text: {text_file.absolute()}")
    if transaction_lines:
        console.print(f"  📋 Transaction lines: {lines_file.absolute()}")

async def main():
    """Main analysis function."""
    console.print("🔍 PDF Structure Analysis Tool", style="bold green")
    console.print("=" * 50)
    
    pdf_path = input("Enter PDF file path: ").strip().strip('"').strip("'")
    
    if pdf_path:
        await analyze_pdf_structure(pdf_path)
    else:
        console.print("No file path provided.", style="yellow")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!", style="green")
    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="red")