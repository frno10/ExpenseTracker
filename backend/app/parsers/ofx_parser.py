"""
OFX (Open Financial Exchange) statement parser implementation.
"""
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from ofxparse import OfxParser as OfxParseLib
    HAS_OFXPARSE = True
except ImportError:
    HAS_OFXPARSE = False
    OfxParseLib = None

from .base import BaseParser, ParsedTransaction, ParseResult, ParserConfig
from .detection import file_detector

logger = logging.getLogger(__name__)


class OFXParser(BaseParser):
    """
    Parser for OFX (Open Financial Exchange) format financial statements.
    
    OFX is a standard format used by many financial institutions for
    electronic data exchange. This parser handles both OFX 1.x (SGML-based)
    and OFX 2.x (XML-based) formats.
    """
    
    def get_default_config(self) -> ParserConfig:
        """Get the default configuration for OFX parser."""
        return ParserConfig(
            name="ofx_parser",
            description="Parser for OFX (Open Financial Exchange) format financial statements",
            supported_extensions=[".ofx", ".qfx"],
            mime_types=[
                "application/x-ofx",
                "application/ofx",
                "text/ofx",
                "application/vnd.intu.qfx"
            ],
            settings={
                "encoding": "utf-8",
                "fallback_encodings": ["latin-1", "cp1252", "iso-8859-1"],
                "transaction_types": {
                    "CREDIT": "credit",
                    "DEBIT": "debit", 
                    "INT": "interest",
                    "DIV": "dividend",
                    "FEE": "fee",
                    "SRVCHG": "service_charge",
                    "DEP": "deposit",
                    "ATM": "atm",
                    "POS": "point_of_sale",
                    "XFER": "transfer",
                    "CHECK": "check",
                    "PAYMENT": "payment",
                    "CASH": "cash",
                    "DIRECTDEP": "direct_deposit",
                    "DIRECTDEBIT": "direct_debit",
                    "REPEATPMT": "recurring_payment",
                    "OTHER": "other"
                },
                "data_validation": {
                    "min_amount": -999999.99,
                    "max_amount": 999999.99,
                    "required_fields": ["date", "amount"],
                    "skip_pending_transactions": False
                },
                "merchant_extraction": {
                    "clean_payee_names": True,
                    "extract_from_memo": True,
                    "remove_transaction_ids": True
                }
            }
        )
    
    def can_parse(self, file_path: str, mime_type: Optional[str] = None) -> bool:
        """Check if this parser can handle the given file."""
        try:
            # Check if ofxparse library is available
            if not HAS_OFXPARSE:
                self.logger.error("ofxparse library not available for OFX parsing")
                return False
            
            # Check file extension
            extension = Path(file_path).suffix.lower()
            if extension not in self.config.supported_extensions:
                return False
            
            # Check MIME type if provided
            if mime_type and mime_type not in self.config.mime_types:
                return False
            
            # Try to parse the file to verify it's valid OFX
            return self._is_valid_ofx_file(file_path)
            
        except Exception as e:
            self.logger.error(f"Error checking if can parse {file_path}: {e}")
            return False
    
    def _is_valid_ofx_file(self, file_path: str) -> bool:
        """Check if file is a valid OFX file."""
        try:
            # Try to read first few lines to check for OFX headers
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1024).upper()
                
            # Check for OFX signatures
            ofx_signatures = [
                'OFXHEADER:',
                '<OFX>',
                'DATA:OFXSGML',
                'VERSION:',
                '<BANKMSGSRSV1>',
                '<CREDITCARDMSGSRSV1>',
                '<STMTRS>'
            ]
            
            return any(sig in content for sig in ofx_signatures)
            
        except Exception as e:
            self.logger.debug(f"File {file_path} is not a valid OFX file: {e}")
            return False
    
    async def parse(self, file_path: str, **kwargs) -> ParseResult:
        """Parse an OFX file and extract transactions."""
        self.logger.info(f"Starting OFX parsing for: {file_path}")
        
        result = ParseResult(success=False)
        
        try:
            # Validate file
            is_valid, validation_errors = file_detector.validate_file(file_path)
            if not is_valid:
                result.errors.extend(validation_errors)
                return result
            
            # Parse OFX file
            ofx_data = self._parse_ofx_file(file_path)
            if not ofx_data:
                result.errors.append("Failed to parse OFX file")
                return result
            
            # Extract transactions from all accounts
            transactions = []
            account_info = []
            
            # Process bank accounts
            if hasattr(ofx_data, 'accounts') and ofx_data.accounts:
                for account in ofx_data.accounts:
                    account_transactions = self._process_bank_account(account)
                    transactions.extend(account_transactions)
                    account_info.append({
                        "type": "bank",
                        "account_id": getattr(account, 'account_id', 'unknown'),
                        "routing_number": getattr(account, 'routing_number', None),
                        "account_type": getattr(account, 'account_type', None),
                        "transaction_count": len(account_transactions)
                    })
            
            # Process credit card accounts
            if hasattr(ofx_data, 'credit_cards') and ofx_data.credit_cards:
                for card in ofx_data.credit_cards:
                    card_transactions = self._process_credit_card_account(card)
                    transactions.extend(card_transactions)
                    account_info.append({
                        "type": "credit_card",
                        "account_id": getattr(card, 'account_id', 'unknown'),
                        "transaction_count": len(card_transactions)
                    })
            
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
                "parser": "ofx_parser",
                "accounts": account_info,
                "total_transactions": len(transactions),
                "ofx_version": getattr(ofx_data, 'version', 'unknown')
            }
            
            self.logger.info(f"OFX parsing completed: {len(transactions)} transactions from {len(account_info)} accounts")
            
        except Exception as e:
            error_msg = f"Error parsing OFX file {file_path}: {e}"
            self.logger.error(error_msg)
            result.errors.append(error_msg)
        
        return result
    
    def _parse_ofx_file(self, file_path: str):
        """Parse OFX file using ofxparse library."""
        encodings = [self.config.settings["encoding"]] + self.config.settings["fallback_encodings"]
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    ofx_data = OfxParseLib.parse(f)
                    self.logger.debug(f"Successfully parsed OFX file with encoding: {encoding}")
                    return ofx_data
                    
            except UnicodeDecodeError:
                self.logger.debug(f"Failed to decode with {encoding}, trying next encoding")
                continue
            except Exception as e:
                self.logger.error(f"Error parsing OFX file with {encoding}: {e}")
                continue
        
        self.logger.error(f"Failed to parse OFX file with any encoding: {encodings}")
        return None
    
    def _process_bank_account(self, account) -> List[ParsedTransaction]:
        """Process transactions from a bank account."""
        transactions = []
        
        if not hasattr(account, 'statement') or not account.statement:
            return transactions
        
        statement = account.statement
        
        for ofx_transaction in statement.transactions:
            try:
                transaction = self._convert_ofx_transaction(ofx_transaction, account)
                if transaction:
                    transactions.append(transaction)
            except Exception as e:
                self.logger.warning(f"Error processing bank transaction: {e}")
                continue
        
        return transactions
    
    def _process_credit_card_account(self, card) -> List[ParsedTransaction]:
        """Process transactions from a credit card account."""
        transactions = []
        
        if not hasattr(card, 'statement') or not card.statement:
            return transactions
        
        statement = card.statement
        
        for ofx_transaction in statement.transactions:
            try:
                transaction = self._convert_ofx_transaction(ofx_transaction, card)
                if transaction:
                    transactions.append(transaction)
            except Exception as e:
                self.logger.warning(f"Error processing credit card transaction: {e}")
                continue
        
        return transactions
    
    def _convert_ofx_transaction(self, ofx_transaction, account) -> Optional[ParsedTransaction]:
        """Convert OFX transaction to ParsedTransaction."""
        try:
            # Skip pending transactions if configured
            if (self.config.settings["data_validation"]["skip_pending_transactions"] and 
                hasattr(ofx_transaction, 'status') and ofx_transaction.status == 'PENDING'):
                return None
            
            # Extract basic transaction data
            transaction_date = ofx_transaction.date.date() if ofx_transaction.date else None
            if not transaction_date:
                return None
            
            amount = Decimal(str(ofx_transaction.amount)) if ofx_transaction.amount else None
            if amount is None:
                return None
            
            # Extract description and payee
            description = self._build_description(ofx_transaction)
            merchant = self._extract_ofx_merchant(ofx_transaction)
            
            # Map transaction type
            transaction_type = self._map_transaction_type(ofx_transaction.type)
            
            # Extract account information
            account_id = getattr(account, 'account_id', None)
            account_type = getattr(account, 'account_type', None)
            
            # Create transaction
            transaction = ParsedTransaction(
                date=transaction_date,
                description=description,
                amount=amount,
                merchant=merchant,
                category=transaction_type,
                account=account_id,
                reference=getattr(ofx_transaction, 'id', None),
                raw_data={
                    "ofx_type": ofx_transaction.type,
                    "ofx_id": getattr(ofx_transaction, 'id', None),
                    "account_type": account_type,
                    "payee": getattr(ofx_transaction, 'payee', None),
                    "memo": getattr(ofx_transaction, 'memo', None),
                    "checknum": getattr(ofx_transaction, 'checknum', None)
                }
            )
            
            return transaction
            
        except Exception as e:
            self.logger.warning(f"Error converting OFX transaction: {e}")
            return None
    
    def _build_description(self, ofx_transaction) -> str:
        """Build transaction description from OFX data."""
        parts = []
        
        # Add payee if available
        if hasattr(ofx_transaction, 'payee') and ofx_transaction.payee:
            parts.append(ofx_transaction.payee.strip())
        
        # Add memo if available and different from payee
        if hasattr(ofx_transaction, 'memo') and ofx_transaction.memo:
            memo = ofx_transaction.memo.strip()
            if memo and (not parts or memo not in parts[0]):
                parts.append(memo)
        
        # Add check number if available
        if hasattr(ofx_transaction, 'checknum') and ofx_transaction.checknum:
            parts.append(f"Check #{ofx_transaction.checknum}")
        
        # Fallback to transaction type
        if not parts and hasattr(ofx_transaction, 'type'):
            parts.append(ofx_transaction.type)
        
        return " - ".join(parts) if parts else "Unknown Transaction"
    
    def _extract_ofx_merchant(self, ofx_transaction) -> Optional[str]:
        """Extract merchant name from OFX transaction."""
        merchant_config = self.config.settings["merchant_extraction"]
        
        # Try payee first
        if hasattr(ofx_transaction, 'payee') and ofx_transaction.payee:
            merchant = ofx_transaction.payee.strip()
            
            if merchant_config["clean_payee_names"]:
                merchant = self._clean_merchant_name(merchant)
            
            return merchant
        
        # Try memo if extract_from_memo is enabled
        if (merchant_config["extract_from_memo"] and 
            hasattr(ofx_transaction, 'memo') and ofx_transaction.memo):
            merchant = ofx_transaction.memo.strip()
            
            if merchant_config["clean_payee_names"]:
                merchant = self._clean_merchant_name(merchant)
            
            return merchant
        
        return None
    
    def _clean_merchant_name(self, merchant: str) -> str:
        """Clean merchant name by removing common artifacts."""
        if not merchant:
            return merchant
        
        # Remove transaction IDs if configured
        if self.config.settings["merchant_extraction"]["remove_transaction_ids"]:
            import re
            # Remove patterns that look like transaction IDs
            merchant = re.sub(r'\b\d{10,}\b', '', merchant)  # Long numbers
            merchant = re.sub(r'#\d+', '', merchant)  # Hash followed by numbers
            merchant = re.sub(r'REF\s*\d+', '', merchant, flags=re.IGNORECASE)  # Reference numbers
        
        # Remove extra whitespace
        merchant = ' '.join(merchant.split())
        
        return merchant
    
    def _map_transaction_type(self, ofx_type: str) -> Optional[str]:
        """Map OFX transaction type to category."""
        if not ofx_type:
            return None
        
        type_mappings = self.config.settings["transaction_types"]
        return type_mappings.get(ofx_type.upper(), ofx_type.lower())