"""
QIF (Quicken Interchange Format) statement parser implementation.
"""
import logging
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseParser, ParsedTransaction, ParseResult, ParserConfig
from .detection import file_detector

logger = logging.getLogger(__name__)


class QIFParser(BaseParser):
    """
    Parser for QIF (Quicken Interchange Format) financial statements.
    
    QIF is a text-based format used by Quicken and other financial software.
    Each transaction is represented by a series of lines with field codes.
    """
    
    def get_default_config(self) -> ParserConfig:
        """Get the default configuration for QIF parser."""
        return ParserConfig(
            name="qif_parser",
            description="Parser for QIF (Quicken Interchange Format) financial statements",
            supported_extensions=[".qif"],
            mime_types=["application/x-qif", "text/qif", "text/plain"],
            settings={
                "encoding": "utf-8",
                "fallback_encodings": ["latin-1", "cp1252", "iso-8859-1"],
                "date_formats": [
                    "%m/%d/%Y",
                    "%m/%d/%y", 
                    "%m-%d-%Y",
                    "%m-%d-%y",
                    "%d/%m/%Y",
                    "%d/%m/%y",
                    "%d-%m-%Y",
                    "%d-%m-%y",
                    "%Y-%m-%d",
                    "%Y/%m/%d"
                ],
                "field_codes": {
                    "D": "date",           # Date
                    "T": "amount",         # Transaction amount
                    "U": "amount_alt",     # Alternative amount format
                    "P": "payee",          # Payee/description
                    "M": "memo",           # Memo
                    "C": "cleared",        # Cleared status
                    "N": "number",         # Check/reference number
                    "L": "category",       # Category
                    "S": "split_category", # Split category
                    "E": "split_memo",     # Split memo
                    "$": "split_amount",   # Split amount
                    "A": "address",        # Address
                    "^": "end_transaction" # End of transaction marker
                },
                "account_types": {
                    "!Type:Bank": "bank",
                    "!Type:Cash": "cash",
                    "!Type:CCard": "credit_card",
                    "!Type:Invst": "investment",
                    "!Type:Oth A": "other_asset",
                    "!Type:Oth L": "other_liability"
                },
                "cleared_status": {
                    "c": "cleared",
                    "C": "cleared",
                    "R": "reconciled",
                    "r": "reconciled",
                    "*": "cleared",
                    "X": "reconciled",
                    "x": "reconciled"
                },
                "data_validation": {
                    "min_amount": -999999.99,
                    "max_amount": 999999.99,
                    "required_fields": ["date", "amount"],
                    "skip_empty_transactions": True
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
            
            # Try to detect QIF format by looking for QIF signatures
            return self._is_valid_qif_file(file_path)
            
        except Exception as e:
            self.logger.error(f"Error checking if can parse {file_path}: {e}")
            return False
    
    def _is_valid_qif_file(self, file_path: str) -> bool:
        """Check if file is a valid QIF file."""
        try:
            encodings = [self.config.settings["encoding"]] + self.config.settings["fallback_encodings"]
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read(1024)
                    
                    # Check for QIF signatures
                    qif_signatures = [
                        '!Type:',
                        '!Account',
                        '!Clear:AutoSwitch'
                    ]
                    
                    # Check for field codes at line beginnings
                    field_codes = ['D', 'T', 'P', 'M', 'L', 'C', 'N', '^']
                    lines = content.split('\n')
                    
                    has_signature = any(sig in content for sig in qif_signatures)
                    has_field_codes = any(
                        line.strip() and line.strip()[0] in field_codes 
                        for line in lines[:10]  # Check first 10 lines
                    )
                    
                    if has_signature or has_field_codes:
                        return True
                        
                except UnicodeDecodeError:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.debug(f"File {file_path} is not a valid QIF file: {e}")
            return False
    
    async def parse(self, file_path: str, **kwargs) -> ParseResult:
        """Parse a QIF file and extract transactions."""
        self.logger.info(f"Starting QIF parsing for: {file_path}")
        
        result = ParseResult(success=False)
        
        try:
            # Validate file
            is_valid, validation_errors = file_detector.validate_file(file_path)
            if not is_valid:
                result.errors.extend(validation_errors)
                return result
            
            # Read and parse QIF file
            qif_content = self._read_qif_file(file_path)
            if not qif_content:
                result.errors.append("Failed to read QIF file")
                return result
            
            # Parse QIF content
            accounts, transactions = self._parse_qif_content(qif_content)
            
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
                "parser": "qif_parser",
                "accounts": accounts,
                "total_transactions": len(transactions)
            }
            
            self.logger.info(f"QIF parsing completed: {len(transactions)} transactions from {len(accounts)} accounts")
            
        except Exception as e:
            error_msg = f"Error parsing QIF file {file_path}: {e}"
            self.logger.error(error_msg)
            result.errors.append(error_msg)
        
        return result
    
    def _read_qif_file(self, file_path: str) -> Optional[str]:
        """Read QIF file content with proper encoding detection."""
        encodings = [self.config.settings["encoding"]] + self.config.settings["fallback_encodings"]
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    self.logger.debug(f"Successfully read QIF file with encoding: {encoding}")
                    return content
                    
            except UnicodeDecodeError:
                self.logger.debug(f"Failed to decode with {encoding}, trying next encoding")
                continue
            except Exception as e:
                self.logger.error(f"Error reading QIF file with {encoding}: {e}")
                continue
        
        self.logger.error(f"Failed to read QIF file with any encoding: {encodings}")
        return None
    
    def _parse_qif_content(self, content: str) -> Tuple[List[Dict], List[ParsedTransaction]]:
        """Parse QIF file content and extract accounts and transactions."""
        lines = content.split('\n')
        accounts = []
        transactions = []
        current_account = None
        current_transaction = {}
        
        field_codes = self.config.settings["field_codes"]
        account_types = self.config.settings["account_types"]
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            if not line:
                continue
            
            try:
                # Handle account type declarations
                if line.startswith('!Type:'):
                    account_type = account_types.get(line, "unknown")
                    current_account = {
                        "type": account_type,
                        "declaration": line,
                        "line_number": line_num
                    }
                    accounts.append(current_account)
                    continue
                
                # Handle account information
                if line.startswith('!Account'):
                    # This is an account definition, skip for now
                    continue
                
                # Handle field codes
                if len(line) >= 2 and line[0] in field_codes:
                    field_code = line[0]
                    field_value = line[1:].strip()
                    field_name = field_codes[field_code]
                    
                    if field_code == '^':
                        # End of transaction - process it
                        if current_transaction:
                            transaction = self._build_transaction(current_transaction, current_account, line_num)
                            if transaction:
                                transactions.append(transaction)
                            current_transaction = {}
                    else:
                        # Add field to current transaction
                        if field_name in current_transaction:
                            # Handle multiple values (like splits)
                            if not isinstance(current_transaction[field_name], list):
                                current_transaction[field_name] = [current_transaction[field_name]]
                            current_transaction[field_name].append(field_value)
                        else:
                            current_transaction[field_name] = field_value
                
            except Exception as e:
                self.logger.warning(f"Error parsing line {line_num}: '{line}' - {e}")
                continue
        
        # Handle last transaction if file doesn't end with ^
        if current_transaction:
            transaction = self._build_transaction(current_transaction, current_account, len(lines))
            if transaction:
                transactions.append(transaction)
        
        return accounts, transactions
    
    def _safe_str(self, value) -> str:
        """Safely convert value to string, handling lists."""
        try:
            if isinstance(value, list):
                return str(value[0]).strip() if value else ""
            return str(value).strip() if value else ""
        except Exception as e:
            self.logger.error(f"Error in _safe_str with value {value} (type: {type(value)}): {e}")
            return ""
    
    def _build_transaction(self, qif_data: Dict, account: Optional[Dict], line_num: int) -> Optional[ParsedTransaction]:
        """Build a ParsedTransaction from QIF data."""
        try:
            # Skip empty transactions if configured
            if (self.config.settings["data_validation"]["skip_empty_transactions"] and 
                not qif_data.get("date") and not qif_data.get("amount")):
                return None
            
            # Parse date
            date_str = qif_data.get("date")
            if not date_str:
                self.logger.warning(f"Transaction at line {line_num} missing date")
                return None
            
            transaction_date = self._parse_qif_date(date_str)
            if not transaction_date:
                self.logger.warning(f"Could not parse date '{date_str}' at line {line_num}")
                return None
            
            # Parse amount
            amount = self._parse_qif_amount(qif_data)
            if amount is None:
                self.logger.warning(f"Transaction at line {line_num} missing or invalid amount")
                return None
            
            # Build description
            try:
                description = self._build_qif_description(qif_data)
            except Exception as e:
                self.logger.error(f"Error building description at line {line_num}: {e}")
                self.logger.error(f"QIF data: {qif_data}")
                description = "QIF Transaction"
            
            # Extract other fields using safe string conversion
            payee = self._safe_str(qif_data.get("payee", ""))
            memo = self._safe_str(qif_data.get("memo", ""))
            category = self._safe_str(qif_data.get("category", ""))
            reference = self._safe_str(qif_data.get("number", ""))
            cleared_status = self._safe_str(qif_data.get("cleared", ""))
            
            # Determine merchant (prefer payee over memo)
            merchant = payee if payee else (memo if memo else None)
            
            # Map cleared status
            cleared_mappings = self.config.settings["cleared_status"]
            cleared = cleared_mappings.get(cleared_status, cleared_status)
            
            # Create transaction
            try:
                transaction = ParsedTransaction(
                    date=transaction_date,
                    description=description,
                    amount=amount,
                    merchant=merchant,
                    category=category if category else None,
                    account=account.get("type") if account else None,
                    reference=reference if reference else None,
                    notes=memo if memo and memo != merchant else None,
                    raw_data={
                        "qif_data": qif_data,
                        "account_info": account,
                        "cleared_status": cleared,
                        "line_number": line_num
                    }
                )
            except Exception as e:
                self.logger.error(f"Error creating ParsedTransaction at line {line_num}: {e}")
                self.logger.error(f"Data types: payee={type(payee)}, memo={type(memo)}, category={type(category)}")
                raise
            
            return transaction
            
        except Exception as e:
            self.logger.warning(f"Error building transaction at line {line_num}: {e}")
            return None
    
    def _parse_qif_date(self, date_str: str) -> Optional[datetime.date]:
        """Parse QIF date string."""
        if not date_str:
            return None
        
        # Clean up date string
        date_str = date_str.strip().replace("'", "")
        
        # Try different date formats
        date_formats = self.config.settings["date_formats"]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        # Try to handle some common QIF date quirks
        try:
            # Handle dates like "1/1'25" (with apostrophe for year)
            if "'" in date_str:
                date_str = date_str.replace("'", "/20")
                return datetime.strptime(date_str, "%m/%d/%Y").date()
        except ValueError:
            pass
        
        self.logger.warning(f"Could not parse QIF date: {date_str}")
        return None
    
    def _parse_qif_amount(self, qif_data: Dict) -> Optional[Decimal]:
        """Parse QIF amount from transaction data."""
        # Try main amount field first
        amount_str = qif_data.get("amount")
        if not amount_str:
            # Try alternative amount field
            amount_str = qif_data.get("amount_alt")
        
        if not amount_str:
            return None
        
        try:
            # Clean up amount string
            cleaned = amount_str.strip().replace(",", "")
            
            # Handle negative amounts
            if cleaned.startswith("(") and cleaned.endswith(")"):
                cleaned = "-" + cleaned[1:-1]
            
            return Decimal(cleaned)
            
        except (InvalidOperation, ValueError) as e:
            self.logger.warning(f"Could not parse QIF amount: {amount_str} - {e}")
            return None
    
    def _build_qif_description(self, qif_data: Dict) -> str:
        """Build transaction description from QIF data."""
        parts = []
        
        # Add payee if available
        payee = self._safe_str(qif_data.get("payee", ""))
        if payee:
            parts.append(payee)
        
        # Add memo if available and different from payee
        memo = self._safe_str(qif_data.get("memo", ""))
        if memo and memo != payee:
            parts.append(memo)
        
        # Add reference number if available
        number = self._safe_str(qif_data.get("number", ""))
        if number:
            parts.append(f"#{number}")
        
        # Fallback to category if nothing else
        if not parts:
            category = self._safe_str(qif_data.get("category", ""))
            if category:
                parts.append(category)
        
        return " - ".join(parts) if parts else "QIF Transaction"