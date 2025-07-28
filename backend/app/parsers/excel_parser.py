"""
Excel statement parser implementation.
"""
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False
    openpyxl = None

try:
    import xlrd
    HAS_XLRD = True
except ImportError:
    HAS_XLRD = False
    xlrd = None

import pandas as pd

from .base import BaseParser, ParsedTransaction, ParseResult, ParserConfig
from .detection import file_detector

logger = logging.getLogger(__name__)


class ExcelParser(BaseParser):
    """
    Parser for Excel format financial statements (.xlsx, .xls).
    
    This parser can handle both modern Excel files (.xlsx) using openpyxl
    and legacy Excel files (.xls) using xlrd, with configurable field mappings.
    """
    
    def get_default_config(self) -> ParserConfig:
        """Get the default configuration for Excel parser."""
        return ParserConfig(
            name="excel_parser",
            description="Parser for Excel format financial statements (.xlsx, .xls)",
            supported_extensions=[".xlsx", ".xls"],
            mime_types=[
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.ms-excel"
            ],
            settings={
                "sheet_name": 0,  # First sheet by default, can be name or index
                "header_row": 0,  # Row containing column headers
                "skip_rows": 0,   # Rows to skip before header
                "date_formats": [
                    "%Y-%m-%d",
                    "%m/%d/%Y",
                    "%d/%m/%Y",
                    "%m-%d-%Y",
                    "%d-%m-%Y",
                    "%Y/%m/%d",
                    "%m/%d/%y",
                    "%d/%m/%y",
                    "%b %d, %Y",
                    "%d %b %Y"
                ],
                "field_mappings": {
                    "date": [
                        "date", "transaction_date", "posting_date", "trans_date",
                        "Date", "Transaction Date", "Posting Date", "Trans Date",
                        "DATE", "TRANSACTION DATE", "POSTING DATE"
                    ],
                    "description": [
                        "description", "memo", "payee", "details", "transaction_details",
                        "Description", "Memo", "Payee", "Details", "Transaction Details",
                        "DESCRIPTION", "MEMO", "PAYEE", "DETAILS"
                    ],
                    "amount": [
                        "amount", "debit", "credit", "transaction_amount",
                        "Amount", "Debit", "Credit", "Transaction Amount",
                        "AMOUNT", "DEBIT", "CREDIT"
                    ],
                    "merchant": [
                        "merchant", "payee", "vendor", "business",
                        "Merchant", "Payee", "Vendor", "Business",
                        "MERCHANT", "PAYEE", "VENDOR"
                    ],
                    "category": [
                        "category", "type", "transaction_type", "expense_type",
                        "Category", "Type", "Transaction Type", "Expense Type",
                        "CATEGORY", "TYPE"
                    ],
                    "account": [
                        "account", "account_number", "account_name",
                        "Account", "Account Number", "Account Name",
                        "ACCOUNT", "ACCOUNT NUMBER"
                    ],
                    "reference": [
                        "reference", "ref", "check_number", "transaction_id", "ref_number",
                        "Reference", "Ref", "Check Number", "Transaction ID", "Ref Number",
                        "REFERENCE", "REF", "CHECK NUMBER"
                    ]
                },
                "amount_columns": {
                    "single": True,  # True if single amount column, False if separate debit/credit
                    "debit_column": "debit",
                    "credit_column": "credit",
                    "negative_debits": True  # True if debits should be negative
                },
                "data_validation": {
                    "min_amount": -999999.99,
                    "max_amount": 999999.99,
                    "required_fields": ["date", "amount"],
                    "skip_empty_rows": True,
                    "skip_total_rows": True  # Skip rows that look like totals/summaries
                }
            }
        )
    
    def can_parse(self, file_path: str, mime_type: Optional[str] = None) -> bool:
        """Check if this parser can handle the given file."""
        try:
            # Check file extension
            extension = Path(file_path).suffix.lower()
            if extension not in self.config.supported_extensions:
                return False
            
            # Check MIME type if provided
            if mime_type and mime_type not in self.config.mime_types:
                return False
            
            # Check if required libraries are available
            if extension == ".xlsx" and not HAS_OPENPYXL:
                self.logger.error("openpyxl library not available for .xlsx files")
                return False
            
            if extension == ".xls" and not HAS_XLRD:
                self.logger.error("xlrd library not available for .xls files")
                return False
            
            # Try to open the file to verify it's a valid Excel file
            return self._is_valid_excel_file(file_path)
            
        except Exception as e:
            self.logger.error(f"Error checking if can parse {file_path}: {e}")
            return False
    
    def _is_valid_excel_file(self, file_path: str) -> bool:
        """Check if file is a valid Excel file."""
        try:
            # Try to read with pandas (handles both .xlsx and .xls)
            pd.read_excel(file_path, nrows=1)
            return True
        except Exception as e:
            self.logger.debug(f"File {file_path} is not a valid Excel file: {e}")
            return False
    
    async def parse(self, file_path: str, **kwargs) -> ParseResult:
        """Parse an Excel file and extract transactions."""
        self.logger.info(f"Starting Excel parsing for: {file_path}")
        
        result = ParseResult(success=False)
        
        try:
            # Validate file
            is_valid, validation_errors = file_detector.validate_file(file_path)
            if not is_valid:
                result.errors.extend(validation_errors)
                return result
            
            # Read Excel file
            df = self._read_excel_file(file_path)
            if df is None or df.empty:
                result.errors.append("Failed to read Excel file or file is empty")
                return result
            
            # Process transactions
            transactions = self._process_dataframe(df, file_path)
            
            # Validate and enrich transactions
            for transaction in transactions:
                validation_warnings = self._validate_transaction(transaction)
                result.warnings.extend(validation_warnings)
                
                # Enrich transaction data
                if not transaction.merchant:
                    transaction.merchant = self._extract_merchant_name(transaction.description)
                
                if not transaction.category:
                    transaction.category = self._categorize_transaction(transaction)
            
            result.transactions = transactions
            result.success = True
            result.metadata = {
                "file_path": file_path,
                "parser": "excel_parser",
                "total_rows": len(df),
                "parsed_transactions": len(transactions),
                "sheet_name": self.config.settings.get("sheet_name", 0)
            }
            
            self.logger.info(f"Excel parsing completed: {len(transactions)} transactions parsed")
            
        except Exception as e:
            error_msg = f"Error parsing Excel file {file_path}: {e}"
            self.logger.error(error_msg)
            result.errors.append(error_msg)
        
        return result
    
    def _read_excel_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """Read Excel file into a pandas DataFrame."""
        try:
            settings = self.config.settings
            
            # Read Excel file
            df = pd.read_excel(
                file_path,
                sheet_name=settings.get("sheet_name", 0),
                header=settings.get("header_row", 0),
                skiprows=settings.get("skip_rows", 0)
            )
            
            # Clean column names (remove extra spaces, normalize case)
            df.columns = df.columns.str.strip()
            
            # Skip empty rows if configured
            if settings.get("data_validation", {}).get("skip_empty_rows", True):
                df = df.dropna(how='all')
            
            self.logger.debug(f"Read Excel file with {len(df)} rows and columns: {list(df.columns)}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error reading Excel file {file_path}: {e}")
            return None
    
    def _process_dataframe(self, df: pd.DataFrame, file_path: str) -> List[ParsedTransaction]:
        """Process DataFrame and extract transactions."""
        transactions = []
        field_mappings = self.config.settings["field_mappings"]
        
        # Find column mappings
        column_map = self._map_columns(df.columns, field_mappings)
        
        if not column_map.get("date") or not column_map.get("amount"):
            self.logger.error("Required columns (date, amount) not found in Excel file")
            return transactions
        
        # Process each row
        for index, row in df.iterrows():
            try:
                # Skip rows that look like totals or summaries
                if self._is_summary_row(row):
                    continue
                
                transaction = self._parse_row(row, column_map, index)
                if transaction:
                    transactions.append(transaction)
                    
            except Exception as e:
                self.logger.warning(f"Error parsing row {index} in {file_path}: {e}")
                continue
        
        return transactions
    
    def _map_columns(self, columns: List[str], field_mappings: Dict[str, List[str]]) -> Dict[str, str]:
        """Map DataFrame columns to transaction fields."""
        column_map = {}
        
        for field, possible_names in field_mappings.items():
            for col_name in columns:
                if col_name in possible_names:
                    column_map[field] = col_name
                    break
        
        self.logger.debug(f"Column mapping: {column_map}")
        return column_map
    
    def _is_summary_row(self, row: pd.Series) -> bool:
        """Check if row appears to be a summary/total row."""
        if self.config.settings.get("data_validation", {}).get("skip_total_rows", True):
            # Check for common summary indicators
            description = str(row.get("description", "")).lower()
            if any(keyword in description for keyword in ["total", "subtotal", "balance", "summary"]):
                return True
        
        return False
    
    def _parse_row(self, row: pd.Series, column_map: Dict[str, str], row_index: int) -> Optional[ParsedTransaction]:
        """Parse a single row into a transaction."""
        try:
            # Extract date
            date_col = column_map.get("date")
            if not date_col or pd.isna(row[date_col]):
                return None
            
            transaction_date = self._parse_date(row[date_col])
            if not transaction_date:
                return None
            
            # Extract amount
            amount = self._parse_amount(row, column_map)
            if amount is None:
                return None
            
            # Extract other fields
            description = self._get_field_value(row, column_map, "description", "")
            merchant = self._get_field_value(row, column_map, "merchant")
            category = self._get_field_value(row, column_map, "category")
            account = self._get_field_value(row, column_map, "account")
            reference = self._get_field_value(row, column_map, "reference")
            
            # Create transaction
            transaction = ParsedTransaction(
                date=transaction_date,
                description=description,
                amount=amount,
                merchant=merchant,
                category=category,
                account=account,
                reference=reference,
                raw_data={
                    "row_index": row_index,
                    "raw_row": row.to_dict()
                }
            )
            
            return transaction
            
        except Exception as e:
            self.logger.warning(f"Error parsing row {row_index}: {e}")
            return None
    
    def _parse_date(self, date_value: Any) -> Optional[datetime.date]:
        """Parse date from various formats."""
        if pd.isna(date_value):
            return None
        
        # If it's already a datetime object
        if isinstance(date_value, (datetime, pd.Timestamp)):
            return date_value.date()
        
        # If it's a string, try to parse it
        if isinstance(date_value, str):
            date_formats = self.config.settings["date_formats"]
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_value.strip(), fmt).date()
                except ValueError:
                    continue
        
        self.logger.warning(f"Could not parse date: {date_value}")
        return None
    
    def _parse_amount(self, row: pd.Series, column_map: Dict[str, str]) -> Optional[Decimal]:
        """Parse amount from row data."""
        amount_config = self.config.settings["amount_columns"]
        
        if amount_config["single"]:
            # Single amount column
            amount_col = column_map.get("amount")
            if not amount_col or pd.isna(row[amount_col]):
                return None
            
            return self._convert_to_decimal(row[amount_col])
        
        else:
            # Separate debit/credit columns
            debit_col = amount_config["debit_column"]
            credit_col = amount_config["credit_column"]
            
            debit_amount = self._convert_to_decimal(row.get(debit_col, 0))
            credit_amount = self._convert_to_decimal(row.get(credit_col, 0))
            
            if debit_amount and credit_amount:
                self.logger.warning(f"Row has both debit and credit amounts: {debit_amount}, {credit_amount}")
            
            if debit_amount:
                return -debit_amount if amount_config["negative_debits"] else debit_amount
            elif credit_amount:
                return credit_amount
            else:
                return None
    
    def _convert_to_decimal(self, value: Any) -> Optional[Decimal]:
        """Convert value to Decimal."""
        if pd.isna(value) or value == "":
            return None
        
        try:
            # Handle string values
            if isinstance(value, str):
                # Remove currency symbols and whitespace
                cleaned = value.replace("$", "").replace(",", "").strip()
                
                # Handle negative amounts in parentheses
                if cleaned.startswith("(") and cleaned.endswith(")"):
                    cleaned = "-" + cleaned[1:-1]
                
                if not cleaned:
                    return None
            else:
                cleaned = str(value)
            
            return Decimal(cleaned)
            
        except (InvalidOperation, ValueError) as e:
            self.logger.warning(f"Could not convert to decimal: {value} - {e}")
            return None
    
    def _get_field_value(self, row: pd.Series, column_map: Dict[str, str], field: str, default: Any = None) -> Any:
        """Get field value from row using column mapping."""
        col_name = column_map.get(field)
        if col_name and col_name in row and not pd.isna(row[col_name]):
            return str(row[col_name]).strip()
        return default