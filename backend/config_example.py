#!/usr/bin/env python3
"""
Example script showing how to manage parser configurations.
"""

from app.parsers.config import config_manager

def show_current_configs():
    """Show all current configurations."""
    print("=== CURRENT PARSER SETTINGS ===")
    print(f"Enabled parsers: {config_manager.settings.enabled_parsers}")
    print(f"Max file size: {config_manager.settings.max_file_size_mb}MB")
    print(f"Default encoding: {config_manager.settings.default_encoding}")
    
    print("\n=== AVAILABLE BANK CONFIGS ===")
    banks = config_manager.list_bank_configs()
    for bank in banks:
        print(f"- {bank}")

def load_bank_config_example():
    """Example of loading a bank configuration."""
    print("\n=== CHASE BANK CONFIG ===")
    chase_config = config_manager.load_bank_config("chase")
    if chase_config:
        print("CSV Field Mappings:")
        for field, columns in chase_config["csv_config"]["field_mappings"].items():
            print(f"  {field}: {columns}")
        
        print("PDF Transaction Patterns:")
        for pattern in chase_config["pdf_config"]["transaction_patterns"]:
            print(f"  {pattern}")

def create_custom_bank_config():
    """Example of creating a custom bank configuration."""
    print("\n=== CREATING CUSTOM BANK CONFIG ===")
    
    custom_config = {
        "name": "My Credit Union",
        "csv_config": {
            "field_mappings": {
                "date": ["Trans Date", "Date"],
                "description": ["Description", "Memo"],
                "amount": ["Amount", "Transaction Amount"],
                "category": ["Category"],
                "reference": ["Reference", "Check Number"]
            },
            "date_formats": ["%Y-%m-%d", "%m/%d/%Y"],
            "amount_columns": {
                "single": True,
                "negative_debits": True
            }
        },
        "pdf_config": {
            "transaction_patterns": [
                r'(\d{4}-\d{2}-\d{2})\s+(.+?)\s+(\$?\s*-?\d+\.\d{2})'
            ],
            "date_formats": ["%Y-%m-%d"]
        }
    }
    
    # Save the configuration
    config_manager.save_bank_config("my_credit_union", custom_config)
    print("Custom bank configuration saved!")

def update_parser_settings():
    """Example of updating parser settings."""
    print("\n=== UPDATING PARSER SETTINGS ===")
    
    # Update CSV parser settings
    csv_settings = {
        "delimiter": ",",
        "encoding": "utf-8",
        "skip_rows": 1,  # Skip first row if it's not a header
        "date_formats": [
            "%Y-%m-%d",
            "%m/%d/%Y", 
            "%d/%m/%Y"
        ]
    }
    
    config_manager.update_parser_config("csv_parser", csv_settings)
    print("CSV parser settings updated!")
    
    # Update PDF parser settings
    pdf_settings = {
        "extraction_method": "pdfplumber",  # or "pypdf2"
        "table_extraction": {
            "enabled": True,
            "min_columns": 3
        }
    }
    
    config_manager.update_parser_config("pdf_parser", pdf_settings)
    print("PDF parser settings updated!")

if __name__ == "__main__":
    show_current_configs()
    load_bank_config_example()
    create_custom_bank_config()
    update_parser_settings()
    
    print("\n=== UPDATED BANK CONFIGS ===")
    banks = config_manager.list_bank_configs()
    for bank in banks:
        print(f"- {bank}")