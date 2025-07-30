#!/usr/bin/env python3
"""
Debug QIF parser issue.
"""
import asyncio
import tempfile
from app.parsers.qif_parser import QIFParser

def create_simple_qif():
    qif_content = """!Type:Bank
D1/15/2025
T-4.50
PCOFFEE SHOP
MCoffee and pastry
^
D1/16/2025
T-85.32
PSUPERMARKET
MWeekly groceries
^"""
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.qif', delete=False)
    temp_file.write(qif_content)
    temp_file.close()
    return temp_file.name

async def debug_qif():
    test_file = create_simple_qif()
    parser = QIFParser()
    
    print(f"Testing QIF file: {test_file}")
    
    # Read content
    with open(test_file, 'r') as f:
        content = f.read()
    print(f"QIF Content:\n{content}")
    
    # Parse
    result = await parser.parse(test_file)
    print(f"Parse result: success={result.success}, transactions={len(result.transactions)}")
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")
    
    for i, tx in enumerate(result.transactions):
        print(f"Transaction {i}: {tx.date} | {tx.description} | {tx.amount}")

if __name__ == "__main__":
    asyncio.run(debug_qif())