"""
CSV statement parser implementation.
"""
import csv
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .base import BaseParser, ParsedTransaction, ParseResult, ParserConfig
from .detection import file_detector

logger = logging.getLogger(__name__)


class CSVParser(BaseParser):
    """
    Parser for CSV format financial statements.
    
    This parser can handle various CSV formats with configurable
    field mappings and data transformations.
    """
    
    def get_default_config(self) -> ParserConfig:
        """Get the default configuration for CSV parser."""
        return ParserConfig(
            name="csv_parser",
            description="Parser for CSV format financial statements",
            supported_extensions=[".csv", ".txt"],
            mime_types=["text/csv", "text/plain", "application/csv"],
            settings={
                "delimiter": ",",
                "quotechar": '"',
                "encoding": "utf-8",
                "skip_rows": 0,
                "header_row": 0,
                "date_formats": [
                    "%Y-%m-%d",
                    "%m/%d/%Y",
                    "%d/%m/%Y",
                    "%m-%d-%Y",
                    "%d-%m-%Y",
                    "%Y/%m/%d",
                    "%m/%d/%y",
                    "%d/%m/%y"
                ],
                "field_mappings": {
                    "date": ["date", "transaction_date", "posting_date", "Date", "Transaction Date"],
                    "description": ["description", "memo", "payee", "Description", "Memo", "Payee"],
                    "amount": ["amount", "debit", "credit", "Amount", "Debit", "Credit"],
                    "merchant": ["merchant", "payee", "vendor", "Merchant", "Payee", "Vendor"],
                    "category": ["category", "type", "Category", "Type"],
                    "account": ["account", "account_number", "Account", "Account Number"],
                    "reference": ["reference", "ref", "check_number", "Reference", "Ref", "Check Number"]
                },
                "amount_columns": {
                    "single": True,  # True if single amount column, False if separate debit/credit
                    "debit_column": "debit",
                    "credit_column": "credit",
                    "negative_debits": True  # True if debits should be negative
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
            
            # Try to detect if it's actually a CSV file
            return self._is_csv_file(file_path)
            
        except Exception as e:
            self.logger.error(f"Error checking if can parse {file_path}: {e}")
            return False
    
    def _is_csv_file(self, file_path: str) -> bool:
        """Check if file appears to be a valid CSV file."""
        try:
            # Detect encoding
            encoding = file_detector.detect_encoding(file_path)
            if not encoding:
                encoding = 'utf-8'
            
            # Try to read first few lines as CSV
            with open(file_path, 'r', encoding=encoding) as f:
                # Try different delimiters
                for delimiter in [',', ';', '\t', '|']:
                    f.seek(0)
                    sample = f.read(1024)
                    if not sample:
                        continue
                    
                    # Count delimiter occurrences in first few lines
                    lines = sample.split('\n')[:5]
                    delimiter_counts = []
                    
                    for line in lines:
                        if line.strip():
                            delimiter_counts.append(line.count(delimiter))
                    
                    # If delimiter appears consistently, likely a CSV
                    if delimiter_counts and len(set(delimiter_counts)) <= 2:  # Allow some variation
                        max_count = max(delimiter_counts)
                        if max_count >= 2:  # At least 3 columns
                            return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Error checking CSV format for {file_path}: {e}")
            return False
    
    async def parse(self, file_path: str, **kwargs) -> ParseResult:
        """Parse a CSV statement file."""
        result = ParseResult(success=False)
        
        try:
            # Validate file
            is_valid, errors = file_detector.validate_file(file_path)
            if not is_valid:
                result.errors.extend(errors)
                return result
            
            # Get file info
            file_info = file_detector.get_file_info(file_path)
            result.metadata["file_info"] = file_info
            
            # Detect encoding
            encoding = file_info.get('encoding') or self.config.settings.get('encoding', 'utf-8')
            
            # Try to parse with pandas first (more robust)
            df = await self._parse_with_pandas(file_path, encoding, **kwargs)
            
            if df is not None and not df.empty:
                # Convert DataFrame to transactions
                transactions = await self._dataframe_to_transactions(df)
                result.transactions = transactions
                result.success = True
                result.metadata["parser"] = "pandas"
                result.metadata["rows_processed"] = len(df)
                
                self.logger.info(f"Successfully parsed {len(transactions)} transactions from {file_path}")
            else:
                # Fallback to manual CSV parsing
                transactions = await self._parse_with_csv_reader(file_path, encoding, **kwargs)
                result.transactions = transactions
                result.success = len(transactions) > 0
                result.metadata["parser"] = "csv_reader"
                
                if result.success:
                    self.logger.info(f"Successfully parsed {len(transactions)} transactions from {file_path}")
                else:
                    result.errors.append("No transactions found in file")
            
        except Exception as e:
            error_msg = f"Error parsing CSV file {file_path}: {e}"
            self.logger.error(error_msg)
            result.errors.append(error_msg)
        
        return result
    
    async def _parse_with_pandas(self, file_path: str, encoding: str, **kwargs) -> Optional[pd.DataFrame]:
        """Parse CSV using pandas."""
        try:
            settings = self.config.settings
            
            # Try different delimiters
            delimiters = [
                kwargs.get('delimiter', settings.get('delimiter', ',')),
                ',', ';', '\t', '|'
            ]
            
            for delimiter in delimiters:
                try:
                    df = pd.read_csv(
                        file_path,
                        delimiter=delimiter,
                        encoding=encoding,
                        skiprows=settings.get('skip_rows', 0),
                        header=settings.get('header_row', 0),
                        quotechar=settings.get('quotechar', '"'),
                        na_values=['', 'N/A', 'NULL', 'null'],
                        keep_default_na=False
                    )
                    
                    # Check if we got reasonable data
                    if len(df.columns) >= 3 and len(df) > 0:
                        self.logger.debug(f"Successfully parsed CSV with delimiter '{delimiter}'")
                        return df
                        
                except Exception as e:
                    self.logger.debug(f"Failed to parse with delimiter '{delimiter}': {e}")
                    continue
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing with pandas: {e}")
            return None
    
    async def _parse_with_csv_reader(self, file_path: str, encoding: str, **kwargs) -> List[ParsedTransaction]:
        """Parse CSV using Python's csv module."""
        transactions = []
        
        try:
            settings = self.config.settings
            delimiter = kwargs.get('delimiter', settings.get('delimiter', ','))
            
            with open(file_path, 'r', encoding=encoding) as f:
                # Skip initial rows if configured
                for _ in range(settings.get('skip_rows', 0)):
                    next(f, None)
                
                reader = csv.DictReader(
                    f,
                    delimiter=delimiter,
                    quotechar=settings.get('quotechar', '"')
                )
                
                for row_num, row in enumerate(reader, 1):
                    try:
                        transaction = await self._parse_row(row, row_num)
                        if transaction:
                            transactions.append(transaction)
                    except Exception as e:
                        self.logger.warning(f"Error parsing row {row_num}: {e}")
                        continue
            
        except Exception as e:
            self.logger.error(f"Error parsing with csv reader: {e}")
        
        return transactions
    
    async def _dataframe_to_transactions(self, df: pd.DataFrame) -> List[ParsedTransaction]:
        """Convert pandas DataFrame to list of ParsedTransaction objects."""
        transactions = []
        
        # Map column names to standard fields
        column_mapping = self._map_columns(df.columns.tolist())
        
        for index, row in df.iterrows():
            try:
                transaction = await self._parse_dataframe_row(row, column_mapping, index + 1)
                if transaction:
                    transactions.append(transaction)
            except Exception as e:
                self.logger.warning(f"Error parsing DataFrame row {index + 1}: {e}")
                continue
        
        return transactions
    
    def _map_columns(self, columns: List[str]) -> Dict[str, str]:
        """Map CSV columns to standard transaction fields."""
        mapping = {}
        field_mappings = self.config.settings.get('field_mappings', {})
        
        for field, possible_names in field_mappings.items():
            for col in columns:
                if col.lower().strip() in [name.lower() for name in possible_names]:
                    mapping[field] = col
                    break
        
        self.logger.debug(f"Column mapping: {mapping}")
        return mapping
    
    async def _parse_row(self, row: Dict[str, str], row_num: int) -> Optional[ParsedTransaction]:
        """Parse a single CSV row into a ParsedTransaction."""
        try:
            # Map columns
            column_mapping = self._map_columns(list(row.keys()))
            
            # Extract date
            date_str = row.get(column_mapping.get('date', ''), '').strip()
            if not date_str:
                return None
            
            transaction_date = self._parse_date(date_str)
            if not transaction_date:
                return None
            
            # Extract amount
            amount = self._parse_amount(row, column_mapping)
            if amount is None:
                return None
            
            # Extract other fields
            description = row.get(column_mapping.get('description', ''), '').strip()
            merchant = row.get(column_mapping.get('merchant', ''), '').strip()
            category = row.get(column_mapping.get('category', ''), '').strip()
            account = row.get(column_mapping.get('account', ''), '').strip()
            reference = row.get(column_mapping.get('reference', ''), '').strip()
            
            # Extract merchant from description if not provided
            if not merchant and description:
                merchant = self._extract_merchant_name(description)
            
            # Auto-categorize if not provided
            if not category:
                temp_transaction = ParsedTransaction(
                    date=transaction_date,
                    description=description,
                    amount=amount,
                    merchant=merchant
                )
                category = self._categorize_transaction(temp_transaction)
            
            transaction = ParsedTransaction(
                date=transaction_date,
                description=description,
                amount=amount,
                merchant=merchant,
                category=category,
                account=account,
                reference=reference,
                raw_data=dict(row)
            )
            
            return transaction
            
        except Exception as e:
            self.logger.error(f"Error parsing row {row_num}: {e}")
            return None
    
    async def _parse_dataframe_row(self, row: pd.Series, column_mapping: Dict[str, str], row_num: int) -> Optional[ParsedTransaction]:
        """Parse a pandas Series row into a ParsedTransaction."""
        try:
            # Extract date
            date_col = column_mapping.get('date')
            if not date_col or pd.isna(row.get(date_col)):
                return None
            
            transaction_date = self._parse_date(str(row[date_col]))
            if not transaction_date:
                return None
            
            # Extract amount
            amount = self._parse_amount_from_series(row, column_mapping)
            if amount is None:
                return None
            
            # Extract other fields
            description = str(row.get(column_mapping.get('description', ''), '')).strip()
            merchant = str(row.get(column_mapping.get('merchant', ''), '')).strip()
            category = str(row.get(column_mapping.get('category', ''), '')).strip()
            account = str(row.get(column_mapping.get('account', ''), '')).strip()
            reference = str(row.get(column_mapping.get('reference', ''), '')).strip()
            
            # Clean up NaN values
            if description == 'nan':
                description = ''
            if merchant == 'nan':
                merchant = ''
            if category == 'nan':
                category = ''
            if account == 'nan':
                account = ''
            if reference == 'nan':
                reference = ''
            
            # Extract merchant from description if not provided
            if not merchant and description:
                merchant = self._extract_merchant_name(description)
            
            # Auto-categorize if not provided
            if not category:
                temp_transaction = ParsedTransaction(
                    date=transaction_date,
                    description=description,
                    amount=amount,
                    merchant=merchant
                )
                category = self._categorize_transaction(temp_transaction)
            
            transaction = ParsedTransaction(
                date=transaction_date,
                description=description,
                amount=amount,
                merchant=merchant,
                category=category,
                account=account,
                reference=reference,
                raw_data=row.to_dict()
            )
            
            return transaction
            
        except Exception as e:
            self.logger.error(f"Error parsing DataFrame row {row_num}: {e}")
            return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string using configured formats."""
        if not date_str or date_str.lower() in ['nan', 'null', '']:
            return None
        
        date_formats = self.config.settings.get('date_formats', [])
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        self.logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _parse_amount(self, row: Dict[str, str], column_mapping: Dict[str, str]) -> Optional[Decimal]:
        """Parse amount from CSV row."""
        try:
            amount_settings = self.config.settings.get('amount_columns', {})
            
            if amount_settings.get('single', True):
                # Single amount column
                amount_col = column_mapping.get('amount')
                if not amount_col:
                    return None
                
                amount_str = row.get(amount_col, '').strip()
                if not amount_str:
                    return None
                
                return self._clean_amount(amount_str)
            else:
                # Separate debit/credit columns
                debit_col = amount_settings.get('debit_column', 'debit')
                credit_col = amount_settings.get('credit_column', 'credit')
                negative_debits = amount_settings.get('negative_debits', True)
                
                debit_str = row.get(debit_col, '').strip()
                credit_str = row.get(credit_col, '').strip()
                
                debit_amount = self._clean_amount(debit_str) if debit_str else Decimal('0')
                credit_amount = self._clean_amount(credit_str) if credit_str else Decimal('0')
                
                if negative_debits:
                    return credit_amount - debit_amount
                else:
                    return debit_amount + credit_amount
                    
        except Exception as e:
            self.logger.error(f"Error parsing amount: {e}")
            return None
    
    def _parse_amount_from_series(self, row: pd.Series, column_mapping: Dict[str, str]) -> Optional[Decimal]:
        """Parse amount from pandas Series row."""
        try:
            amount_settings = self.config.settings.get('amount_columns', {})
            
            if amount_settings.get('single', True):
                # Single amount column
                amount_col = column_mapping.get('amount')
                if not amount_col or pd.isna(row.get(amount_col)):
                    return None
                
                amount_value = row[amount_col]
                if isinstance(amount_value, (int, float)):
                    return Decimal(str(amount_value))
                else:
                    return self._clean_amount(str(amount_value))
            else:
                # Separate debit/credit columns
                debit_col = amount_settings.get('debit_column', 'debit')
                credit_col = amount_settings.get('credit_column', 'credit')
                negative_debits = amount_settings.get('negative_debits', True)
                
                debit_value = row.get(debit_col, 0)
                credit_value = row.get(credit_col, 0)
                
                if pd.isna(debit_value):
                    debit_value = 0
                if pd.isna(credit_value):
                    credit_value = 0
                
                debit_amount = Decimal(str(debit_value))
                credit_amount = Decimal(str(credit_value))
                
                if negative_debits:
                    return credit_amount - debit_amount
                else:
                    return debit_amount + credit_amount
                    
        except Exception as e:
            self.logger.error(f"Error parsing amount from series: {e}")
            return None
    
    def _clean_amount(self, amount_str: str) -> Decimal:
        """Clean and convert amount string to Decimal."""
        if not amount_str or amount_str.lower() in ['nan', 'null', '']:
            return Decimal('0')
        
        # Remove currency symbols and whitespace
        cleaned = amount_str.replace('$', '').replace('€', '').replace('£', '').replace(',', '').strip()
        
        # Handle negative amounts in parentheses
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = '-' + cleaned[1:-1]
        
        # Handle negative amounts with trailing minus
        if cleaned.endswith('-'):
            cleaned = '-' + cleaned[:-1]
        
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            self.logger.warning(f"Could not parse amount: {amount_str}")
            return Decimal('0')