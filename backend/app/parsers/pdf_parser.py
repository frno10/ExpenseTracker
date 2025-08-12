"""
PDF statement parser implementation.
"""
import logging
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False
    PyPDF2 = None

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    pdfplumber = None

from .base import BaseParser, ParsedTransaction, ParseResult, ParserConfig
from .detection import file_detector

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    """
    Parser for PDF format financial statements.
    
    This parser can extract text from PDF files and parse transaction data
    using various extraction methods and pattern matching.
    """
    
    def get_default_config(self) -> ParserConfig:
        """Get the default configuration for PDF parser."""
        return ParserConfig(
            name="pdf_parser",
            description="Parser for PDF format financial statements",
            supported_extensions=[".pdf"],
            mime_types=["application/pdf"],
            settings={
                "extraction_method": "pdfplumber",  # "pdfplumber" or "pypdf2"
                "date_patterns": [
                    r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
                    r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',
                    r'\b(\w{3}\s+\d{1,2},?\s+\d{4})\b',
                    r'\b(\d{1,2}\s+\w{3}\s+\d{4})\b'
                ],
                "amount_patterns": [
                    r'\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',
                    r'\$?\s*(\d+\.\d{2})',
                    r'\(\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})\)',  # Negative amounts in parentheses
                    r'-\$?\s*(\d{1,3}(?:,\d{3})*\.\d{2})'     # Negative amounts with minus
                ],
                "transaction_patterns": [
                    # Pattern for typical bank statement lines
                    r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+(\$?\s*-?\d{1,3}(?:,\d{3})*\.\d{2})',
                    # Pattern with reference numbers
                    r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+(\#?\d+)?\s+(\$?\s*-?\d{1,3}(?:,\d{3})*\.\d{2})',
                ],
                "ignore_patterns": [
                    r'^\s*page\s+\d+',
                    r'^\s*statement\s+period',
                    r'^\s*account\s+number',
                    r'^\s*balance\s+forward',
                    r'^\s*total\s+',
                    r'^\s*subtotal\s+',
                ],
                "date_formats": [
                    "%m/%d/%Y",
                    "%m-%d-%Y",
                    "%d/%m/%Y",
                    "%d-%m-%Y",
                    "%Y-%m-%d",
                    "%Y/%m/%d",
                    "%m/%d/%y",
                    "%d/%m/%y",
                    "%b %d, %Y",
                    "%d %b %Y",
                    "%B %d, %Y",
                    "%d %B %Y"
                ],
                "table_extraction": {
                    "enabled": True,
                    "min_columns": 3,
                    "date_column_index": 0,
                    "description_column_index": 1,
                    "amount_column_index": -1  # Last column
                }
            }
        )
    
    def can_parse(self, file_path: str, mime_type: Optional[str] = None) -> bool:
        """Check if this parser can handle the given file."""
        try:
            # Check if PDF libraries are available
            if not (HAS_PYPDF2 or HAS_PDFPLUMBER):
                self.logger.warning("No PDF parsing libraries available (PyPDF2 or pdfplumber)")
                return False
            
            # Check file extension
            extension = Path(file_path).suffix.lower()
            if extension not in self.config.supported_extensions:
                return False
            
            # Check MIME type if provided
            if mime_type and mime_type not in self.config.mime_types:
                return False
            
            # Try to open the PDF to verify it's valid
            return self._is_valid_pdf(file_path)
            
        except Exception as e:
            self.logger.error(f"Error checking if can parse {file_path}: {e}")
            return False
    
    def _is_valid_pdf(self, file_path: str) -> bool:
        """Check if file is a valid PDF."""
        try:
            if HAS_PDFPLUMBER:
                with pdfplumber.open(file_path) as pdf:
                    return len(pdf.pages) > 0
            elif HAS_PYPDF2:
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    return len(reader.pages) > 0
            return False
        except Exception as e:
            self.logger.debug(f"Error validating PDF {file_path}: {e}")
            return False
    
    async def parse(self, file_path: str, **kwargs) -> ParseResult:
        """Parse a PDF statement file."""
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
            
            # Extract text from PDF
            text_content = await self._extract_text(file_path)
            if not text_content:
                result.errors.append("Could not extract text from PDF")
                return result
            
            result.metadata["text_length"] = len(text_content)
            
            # Try table extraction first (more structured)
            transactions = []
            if self.config.settings.get("table_extraction", {}).get("enabled", True):
                transactions = await self._extract_from_tables(file_path)
                if transactions:
                    result.metadata["extraction_method"] = "table"
            
            # Try ČSOB-specific parsing if this looks like a ČSOB statement
            if not transactions and self._is_csob_statement(text_content):
                transactions = self._extract_csob_transactions(text_content)
                if transactions:
                    result.metadata["extraction_method"] = "csob_specific"
            
            # Fallback to text pattern matching
            if not transactions:
                transactions = await self._extract_from_text(text_content)
                result.metadata["extraction_method"] = "text_patterns"
            
            result.transactions = transactions
            result.success = len(transactions) > 0
            
            if result.success:
                self.logger.info(f"Successfully parsed {len(transactions)} transactions from {file_path}")
            else:
                result.warnings.append("No transactions found in PDF")
            
        except Exception as e:
            error_msg = f"Error parsing PDF file {file_path}: {e}"
            self.logger.error(error_msg)
            result.errors.append(error_msg)
        
        return result
    
    async def _extract_text(self, file_path: str) -> str:
        """Extract text content from PDF."""
        try:
            method = self.config.settings.get("extraction_method", "pdfplumber")
            
            if method == "pdfplumber" and HAS_PDFPLUMBER:
                return await self._extract_text_pdfplumber(file_path)
            elif method == "pypdf2" and HAS_PYPDF2:
                return await self._extract_text_pypdf2(file_path)
            else:
                # Try both methods as fallback
                if HAS_PDFPLUMBER:
                    text = await self._extract_text_pdfplumber(file_path)
                    if text:
                        return text
                
                if HAS_PYPDF2:
                    return await self._extract_text_pypdf2(file_path)
            
            return ""
            
        except Exception as e:
            self.logger.error(f"Error extracting text from PDF: {e}")
            return ""
    
    async def _extract_text_pdfplumber(self, file_path: str) -> str:
        """Extract text using pdfplumber."""
        try:
            text_content = []
            
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        text = page.extract_text()
                        if text:
                            text_content.append(f"--- Page {page_num + 1} ---\n{text}\n")
                    except Exception as e:
                        self.logger.warning(f"Error extracting text from page {page_num + 1}: {e}")
                        continue
            
            return "\n".join(text_content)
            
        except Exception as e:
            self.logger.error(f"Error with pdfplumber extraction: {e}")
            return ""
    
    async def _extract_text_pypdf2(self, file_path: str) -> str:
        """Extract text using PyPDF2."""
        try:
            text_content = []
            
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                
                for page_num, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text()
                        if text:
                            text_content.append(f"--- Page {page_num + 1} ---\n{text}\n")
                    except Exception as e:
                        self.logger.warning(f"Error extracting text from page {page_num + 1}: {e}")
                        continue
            
            return "\n".join(text_content)
            
        except Exception as e:
            self.logger.error(f"Error with PyPDF2 extraction: {e}")
            return ""
    
    async def _extract_from_tables(self, file_path: str) -> List[ParsedTransaction]:
        """Extract transactions from PDF tables."""
        transactions = []
        
        if not HAS_PDFPLUMBER:
            return transactions
        
        try:
            table_settings = self.config.settings.get("table_extraction", {})
            min_columns = table_settings.get("min_columns", 3)
            date_col = table_settings.get("date_column_index", 0)
            desc_col = table_settings.get("description_column_index", 1)
            amount_col = table_settings.get("amount_column_index", -1)
            
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        tables = page.extract_tables()
                        
                        for table_num, table in enumerate(tables):
                            if not table or len(table) < 2:  # Need at least header + 1 row
                                continue
                            
                            # Skip tables with too few columns
                            if len(table[0]) < min_columns:
                                continue
                            
                            # Process table rows (skip header)
                            for row_num, row in enumerate(table[1:], 1):
                                try:
                                    if len(row) < min_columns:
                                        continue
                                    
                                    transaction = await self._parse_table_row(
                                        row, date_col, desc_col, amount_col, 
                                        page_num + 1, table_num + 1, row_num
                                    )
                                    
                                    if transaction:
                                        transactions.append(transaction)
                                        
                                except Exception as e:
                                    self.logger.debug(f"Error parsing table row: {e}")
                                    continue
                    
                    except Exception as e:
                        self.logger.warning(f"Error extracting tables from page {page_num + 1}: {e}")
                        continue
            
        except Exception as e:
            self.logger.error(f"Error extracting from tables: {e}")
        
        return transactions
    
    async def _parse_table_row(self, row: List[str], date_col: int, desc_col: int, 
                              amount_col: int, page_num: int, table_num: int, row_num: int) -> Optional[ParsedTransaction]:
        """Parse a single table row into a transaction."""
        try:
            # Extract date
            date_str = (row[date_col] or "").strip() if date_col < len(row) else ""
            if not date_str:
                return None
            
            transaction_date = self._parse_date(date_str)
            if not transaction_date:
                return None
            
            # Extract description
            description = (row[desc_col] or "").strip() if desc_col < len(row) else ""
            if not description:
                return None
            
            # Extract amount
            amount_str = (row[amount_col] or "").strip() if amount_col < len(row) else ""
            if not amount_str:
                return None
            
            amount = self._parse_amount(amount_str)
            if amount is None:
                return None
            
            # Extract merchant from description
            merchant = self._extract_merchant_name(description)
            
            # Auto-categorize
            temp_transaction = ParsedTransaction(
                date=transaction_date.date(),
                description=description,
                amount=amount,
                merchant=merchant
            )
            category = self._categorize_transaction(temp_transaction)
            
            transaction = ParsedTransaction(
                date=transaction_date.date(),
                description=description,
                amount=amount,
                merchant=merchant,
                category=category,
                raw_data={
                    "page": page_num,
                    "table": table_num,
                    "row": row_num,
                    "raw_row": row
                }
            )
            
            return transaction
            
        except Exception as e:
            self.logger.debug(f"Error parsing table row: {e}")
            return None
    
    async def _extract_from_text(self, text_content: str) -> List[ParsedTransaction]:
        """Extract transactions from raw text using pattern matching."""
        transactions = []
        
        try:
            # Split text into lines
            lines = text_content.split('\n')
            
            # Filter out lines that should be ignored
            ignore_patterns = self.config.settings.get("ignore_patterns", [])
            filtered_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if line should be ignored
                should_ignore = False
                for pattern in ignore_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        should_ignore = True
                        break
                
                if not should_ignore:
                    filtered_lines.append(line)
            
            # Try to extract transactions using patterns
            transaction_patterns = self.config.settings.get("transaction_patterns", [])
            
            for line_num, line in enumerate(filtered_lines):
                for pattern in transaction_patterns:
                    try:
                        match = re.search(pattern, line)
                        if match:
                            transaction = await self._parse_pattern_match(match, line, line_num + 1)
                            if transaction:
                                transactions.append(transaction)
                                break  # Found a match, move to next line
                    except Exception as e:
                        self.logger.debug(f"Error matching pattern on line {line_num + 1}: {e}")
                        continue
            
            # If no pattern matches worked, try a more general approach
            if not transactions:
                transactions = await self._extract_with_general_patterns(filtered_lines)
            
        except Exception as e:
            self.logger.error(f"Error extracting from text: {e}")
        
        return transactions
    
    async def _parse_pattern_match(self, match: re.Match, line: str, line_num: int) -> Optional[ParsedTransaction]:
        """Parse a regex match into a transaction."""
        try:
            groups = match.groups()
            
            if len(groups) < 3:
                return None
            
            # First group should be date
            date_str = groups[0].strip()
            transaction_date = self._parse_date(date_str)
            if not transaction_date:
                return None
            
            # Last group should be amount
            amount_str = groups[-1].strip()
            amount = self._parse_amount(amount_str)
            if amount is None:
                return None
            
            # Middle groups are description (and possibly reference)
            description_parts = [g.strip() for g in groups[1:-1] if g and g.strip()]
            description = " ".join(description_parts)
            
            if not description:
                return None
            
            # Extract merchant from description
            merchant = self._extract_merchant_name(description)
            
            # Auto-categorize
            temp_transaction = ParsedTransaction(
                date=transaction_date.date(),
                description=description,
                amount=amount,
                merchant=merchant
            )
            category = self._categorize_transaction(temp_transaction)
            
            transaction = ParsedTransaction(
                date=transaction_date.date(),
                description=description,
                amount=amount,
                merchant=merchant,
                category=category,
                raw_data={
                    "line_number": line_num,
                    "raw_line": line,
                    "pattern_match": groups
                }
            )
            
            return transaction
            
        except Exception as e:
            self.logger.debug(f"Error parsing pattern match: {e}")
            return None
    
    async def _extract_with_general_patterns(self, lines: List[str]) -> List[ParsedTransaction]:
        """Extract transactions using general date and amount patterns."""
        transactions = []
        
        try:
            date_patterns = self.config.settings.get("date_patterns", [])
            amount_patterns = self.config.settings.get("amount_patterns", [])
            
            for line_num, line in enumerate(lines):
                # Look for date patterns
                date_match = None
                for pattern in date_patterns:
                    match = re.search(pattern, line)
                    if match:
                        date_match = match
                        break
                
                if not date_match:
                    continue
                
                # Look for amount patterns
                amount_matches = []
                for pattern in amount_patterns:
                    matches = re.finditer(pattern, line)
                    amount_matches.extend(matches)
                
                if not amount_matches:
                    continue
                
                # Try to parse the line
                date_str = date_match.group(1)
                transaction_date = self._parse_date(date_str)
                if not transaction_date:
                    continue
                
                # Use the last amount found (usually the transaction amount)
                amount_match = amount_matches[-1]
                amount_str = amount_match.group(1)
                amount = self._parse_amount(amount_str)
                if amount is None:
                    continue
                
                # Extract description (text between date and amount)
                date_end = date_match.end()
                amount_start = amount_match.start()
                description = line[date_end:amount_start].strip()
                
                if not description:
                    continue
                
                # Clean up description
                description = re.sub(r'\s+', ' ', description)
                
                # Extract merchant from description
                merchant = self._extract_merchant_name(description)
                
                # Auto-categorize
                temp_transaction = ParsedTransaction(
                    date=transaction_date.date(),
                    description=description,
                    amount=amount,
                    merchant=merchant
                )
                category = self._categorize_transaction(temp_transaction)
                
                transaction = ParsedTransaction(
                    date=transaction_date.date(),
                    description=description,
                    amount=amount,
                    merchant=merchant,
                    category=category,
                    raw_data={
                        "line_number": line_num + 1,
                        "raw_line": line,
                        "extraction_method": "general_patterns"
                    }
                )
                
                transactions.append(transaction)
                
        except Exception as e:
            self.logger.error(f"Error with general pattern extraction: {e}")
        
        return transactions
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string using configured formats."""
        if not date_str:
            return None
        
        date_formats = self.config.settings.get('date_formats', [])
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        self.logger.debug(f"Could not parse date: {date_str}")
        return None
    
    def _parse_amount(self, amount_str: str) -> Optional[Decimal]:
        """Parse amount string to Decimal."""
        if not amount_str:
            return None
        
        try:
            # Remove currency symbols and whitespace
            cleaned = amount_str.replace('$', '').replace('€', '').replace('£', '').replace(',', '').strip()
            
            # Handle negative amounts in parentheses
            is_negative = False
            if cleaned.startswith('(') and cleaned.endswith(')'):
                cleaned = cleaned[1:-1]
                is_negative = True
            elif cleaned.startswith('-'):
                cleaned = cleaned[1:]
                is_negative = True
            
            amount = Decimal(cleaned)
            return -amount if is_negative else amount
            
        except (InvalidOperation, ValueError) as e:
            self.logger.debug(f"Could not parse amount '{amount_str}': {e}")
            return None
    
    # ČSOB Slovakia specific methods
    
    def _parse_csob_date(self, date_str: str, default_year: int = None) -> Optional[date]:
        """Parse ČSOB Slovakia date format (e.g., '2. 5.' -> May 2nd).
        
        Args:
            date_str: Date string in Slovak format like "2. 5."
            default_year: Year to use, if None will use current year
        """
        try:
            # Use current year if no default provided
            if default_year is None:
                from datetime import datetime
                default_year = datetime.now().year
            
            # Handle Slovak format "2. 5." (day. month.)
            if re.match(r'^\d{1,2}\.\s*\d{1,2}\.$', date_str.strip()):
                parts = date_str.replace('.', '').split()
                if len(parts) == 2:
                    day, month = int(parts[0]), int(parts[1])
                    # Validate date components
                    if 1 <= month <= 12 and 1 <= day <= 31:
                        return date(default_year, month, day)
            return None
        except (ValueError, IndexError):
            return None
    
    def _extract_year_from_csob_header(self, text_content: str) -> int:
        """Extract year from ČSOB PDF header like 'Obdobie: 1. 3. 2023 - 31. 3. 2023'."""
        try:
            # Look for "Obdobie: 1. 3. 2023 - 31. 3. 2023" pattern
            match = re.search(r'Obdobie:\s*\d{1,2}\.\s*\d{1,2}\.\s*(\d{4})', text_content)
            if match:
                return int(match.group(1))
            
            # Fallback: look for any 4-digit year in the first 1000 characters
            match = re.search(r'\b(20\d{2})\b', text_content[:1000])
            if match:
                return int(match.group(1))
                
        except (ValueError, AttributeError):
            pass
        
        # Default to current year if nothing found
        from datetime import datetime
        return datetime.now().year
    
    def _is_csob_statement(self, text_content: str) -> bool:
        """Check if this looks like a ČSOB Slovakia statement."""
        csob_indicators = [
            'VÝPIS Z ÚČTU',
            'ACCOUNT STATEMENT', 
            'ČSOB',
            'Československá obchodná banka',
            'CEKOSKBX',  # BIC code
            'Transakcia platobnou kartou',
            'Ref. platiteľa:',
            'Miesto:'
        ]
        
        # Check if at least 3 indicators are present
        found_indicators = sum(1 for indicator in csob_indicators if indicator in text_content)
        return found_indicators >= 3
    
    def _parse_csob_amount(self, amount_str: str) -> Optional[Decimal]:
        """Parse ČSOB Slovakia amount format (e.g., '-12,90' or '1 300,54').
        
        Handles:
        - Comma as decimal separator: '12,90' -> 12.90
        - Space as thousands separator: '1 300,54' -> 1300.54
        - Negative amounts: '-12,90' -> -12.90
        """
        if not amount_str:
            return None
            
        try:
            # Clean the amount string
            cleaned = amount_str.strip()
            
            # Handle negative amounts
            is_negative = cleaned.startswith('-')
            if is_negative:
                cleaned = cleaned[1:]
            
            # Remove spaces (thousands separator) and replace comma with dot
            cleaned = cleaned.replace(' ', '').replace(',', '.')
            
            # Validate the cleaned string looks like a number
            if not re.match(r'^\d+(\.\d+)?$', cleaned):
                return None
            
            amount = Decimal(cleaned)
            return -amount if is_negative else amount
            
        except (ValueError, InvalidOperation):
            self.logger.debug(f"Could not parse ČSOB amount: {amount_str}")
            return None
    
    def _split_csob_merchant_location(self, merchant_info: str) -> Tuple[Optional[str], Optional[str]]:
        """Split ČSOB merchant info into merchant name and location."""
        if not merchant_info:
            return None, None
        
        # Slovak city patterns - more comprehensive
        city_patterns = [
            r'\bKOSICE\b', r'\bBRATISLAVA\b', r'\bZILINA\b', r'\bPRESOV\b',
            r'\bNITRA\b', r'\bTRNAVA\b', r'\bBANSKA BYSTRICA\b',
            r'\bKE\b', r'\bBA\b', r'\bZA\b', r'\bPO\b', r'\bNR\b', r'\bTT\b', r'\bBB\b',
            r'\bLUXEMBOURG\b', r'\bPRAHA\b', r'\bBRNO\b'
        ]
        
        merchant = merchant_info.strip()
        location = None
        
        # Try to find location at the end of the string
        for pattern in city_patterns:
            match = re.search(pattern + r'\s*$', merchant_info, re.IGNORECASE)
            if match:
                location = match.group(0).strip()
                # Remove location from merchant name
                merchant = re.sub(pattern + r'\s*$', '', merchant_info, flags=re.IGNORECASE).strip()
                break
        
        # Clean up merchant name
        if merchant:
            # Remove extra spaces
            merchant = re.sub(r'\s+', ' ', merchant).strip()
            # Clean business suffixes but preserve the main name
            merchant = self._clean_csob_business_name(merchant)
        
        return merchant if merchant else None, location
    
    def _clean_csob_business_name(self, merchant_name: str) -> str:
        """Clean Slovak business names by removing common suffixes and formatting.
        
        Args:
            merchant_name: Raw merchant name from ČSOB statement
            
        Returns:
            Cleaned merchant name
        """
        if not merchant_name:
            return merchant_name
        
        # Common Slovak business suffixes to clean up
        suffixes_to_remove = [
            r'\s+s\.r\.o\.$',  # s.r.o. (Slovak LLC)
            r'\s+a\.s\.$',     # a.s. (Slovak joint stock company)
            r'\s+spol\.\s+s\s+r\.o\.$',  # spol. s r.o.
            r'\s+k\.s\.$',     # k.s. (limited partnership)
            r'\s+v\.o\.s\.$',  # v.o.s. (general partnership)
            r'\s+INC\.?$',     # INC. or INC
            r'\s+LLC$',        # LLC
            r'\s+LTD$',        # LTD
            r'\s+CORP$',       # CORP
        ]
        
        cleaned = merchant_name.strip()
        
        # Remove business suffixes
        for suffix_pattern in suffixes_to_remove:
            cleaned = re.sub(suffix_pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Clean up extra spaces and formatting
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Remove trailing punctuation
        cleaned = cleaned.rstrip('.,;:')
        
        return cleaned
    
    def _parse_csob_exchange_info(self, line: str) -> Optional[Tuple[Decimal, str, Optional[Decimal]]]:
        """Parse ČSOB exchange rate info from lines like 'Suma: 4.83 PLN 02.05.2025 Kurz: 4,2'."""
        match = re.search(r'Suma:\s*([\d,.]+)\s*(\w{3}).*?Kurz:\s*([\d,]+)', line)
        if match:
            try:
                original_amount = Decimal(match.group(1).replace(',', '.'))
                currency = match.group(2)
                exchange_rate = Decimal(match.group(3).replace(',', '.'))
                
                return original_amount, currency, exchange_rate
            except (ValueError, InvalidOperation):
                pass
        
        # Try without exchange rate (EUR transactions)
        match = re.search(r'Suma:\s*([\d,.]+)\s*(\w{3})', line)
        if match:
            try:
                original_amount = Decimal(match.group(1).replace(',', '.'))
                currency = match.group(2)
                return original_amount, currency, None
            except (ValueError, InvalidOperation):
                pass
        
        return None
    
    def _detect_csob_transaction_type(self, description: str) -> str:
        """Detect ČSOB transaction type from description."""
        if 'Čerpanie úveru plat.kartou' in description:
            return 'card_payment'
        elif 'Splatka istiny' in description:
            return 'payment'
        elif 'Prevod' in description:
            return 'transfer'
        else:
            return 'unknown'
    
    def _extract_csob_reference(self, line: str) -> Optional[str]:
        """Extract reference number from ČSOB lines."""
        if line.startswith('Ref. platiteľa:'):
            return line.replace('Ref. platiteľa:', '').strip()
        return None
    
    def _clean_csob_business_name(self, name: str) -> str:
        """Clean Slovak business names by removing common suffixes."""
        # First remove location (city names)
        city_patterns = [
            r'\s+KOSICE$', r'\s+BRATISLAVA$', r'\s+ZILINA$', r'\s+PRESOV$',
            r'\s+NITRA$', r'\s+TRNAVA$', r'\s+BANSKA BYSTRICA$'
        ]
        
        cleaned = name
        for pattern in city_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Then remove business suffixes (but keep SLOVAKIA in company names)
        business_cleanups = [
            (r'\s+S\.R\.O\.?$', ''),  # Remove S.R.O. suffix
            (r'\s+A\.S\.?$', ''),     # Remove A.S. suffix
            (r'\s*,.*$', ''),         # Remove everything after comma
        ]
        
        for pattern, replacement in business_cleanups:
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        
        # Clean up extra spaces and return
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
    
    def _extract_csob_transactions(self, text_content: str) -> List[ParsedTransaction]:
        """Extract transactions from ČSOB Slovakia PDF text."""
        transactions = []
        lines = text_content.split('\n')
        
        # Extract the year from the PDF header
        statement_year = self._extract_year_from_csob_header(text_content)
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for transaction date pattern: "2. 5. Čerpanie úveru plat.kartou -12,90"
            date_match = re.match(r'^(\d{1,2})\. (\d{1,2})\. (.+)', line)
            if date_match:
                try:
                    tx = self._parse_csob_transaction_block(date_match, lines, i, statement_year)
                    if tx:
                        transactions.append(tx)
                except Exception as e:
                    logger.warning(f"Error parsing ČSOB transaction at line {i}: {e}")
            
            i += 1
        
        return transactions
    
    def _parse_csob_transaction_block(self, date_match, lines: List[str], start_idx: int, statement_year: int) -> Optional[ParsedTransaction]:
        """Parse a single ČSOB transaction block."""
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
            amount = Decimal(amount_str)
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
                merchant, location = self._split_csob_merchant_location(merchant_info)
            
            # Extract exchange rate info
            if 'Suma:' in next_line and 'Kurz:' in next_line:
                exchange_info = self._parse_csob_exchange_info(next_line)
                if exchange_info:
                    original_amount, original_currency, exchange_rate = exchange_info
            
            j += 1
        
        # Validate we have required data
        if amount is None:
            return None
        
        # Create date with extracted year from PDF header
        transaction_date = date(statement_year, month, day)
        
        return ParsedTransaction(
            date=transaction_date,
            description=description,
            amount=amount,
            merchant=merchant,
            category=self._categorize_transaction_by_merchant(merchant or description),
            raw_data={
                'location': location,
                'reference': reference,
                'original_amount': original_amount,
                'original_currency': original_currency,
                'exchange_rate': exchange_rate,
                'transaction_type': transaction_type
            }
        )
    
    def _categorize_transaction_by_merchant(self, merchant_or_description: str) -> Optional[str]:
        """Categorize transaction based on merchant name or description."""
        if not merchant_or_description:
            return None
        
        merchant_lower = merchant_or_description.lower()
        
        # Grocery stores
        if any(keyword in merchant_lower for keyword in ['supermarket', 'kaufland', 'lidl', 'tesco', 'grocery']):
            return 'Groceries'
        
        # Gas stations
        if any(keyword in merchant_lower for keyword in ['omv', 'slovnaft', 'shell', 'bp', 'gas']):
            return 'Transportation'
        
        # Restaurants and food
        if any(keyword in merchant_lower for keyword in ['restaurant', 'pizza', 'mcdonald', 'kfc', 'burger', 'cafe', 'coffee']):
            return 'Dining'
        
        # Entertainment
        if any(keyword in merchant_lower for keyword in ['netflix', 'spotify', 'cinema', 'theater', 'game']):
            return 'Entertainment'
        
        # Shopping
        if any(keyword in merchant_lower for keyword in ['h&b', 'primark', 'zara', 'shop', 'store']):
            return 'Shopping'
        
        # Online services
        if any(keyword in merchant_lower for keyword in ['google', 'apple', 'microsoft', 'amazon']):
            return 'Online Services'
        
        return 'Other'
    
    def _create_transaction(self, date: date, description: str, amount: Decimal, 
                          merchant: Optional[str] = None, location: Optional[str] = None) -> ParsedTransaction:
        """Create a validated transaction object."""
        if not date or not description or amount is None:
            raise ValueError("Missing required transaction fields")
        
        return ParsedTransaction(
            date=date,
            description=description,
            amount=amount,
            merchant=merchant,
            category=self._categorize_transaction_by_merchant(merchant or description),
            raw_data={'location': location} if location else None
        )
    
    def _extract_csob_transactions(self, text_content: str) -> List[ParsedTransaction]:
        """Extract transactions from ČSOB Slovakia PDF using specific patterns.
        
        This method handles the multi-line transaction format used by ČSOB Slovakia:
        - Main transaction line: "1. 3. Transakcia platobnou kartou -2,04"
        - Reference line: "Ref. platiteľa: 123456789"
        - Location line: "Miesto: ALIEXPRESS.COM LUXEMBOURG"
        - Exchange info: "Suma: 2.13 USD 01.03.2023 Kurz: 1,0423"
        """
        transactions = []
        
        # Extract year from the PDF header
        statement_year = self._extract_year_from_csob_header(text_content)
        self.logger.debug(f"Extracted statement year: {statement_year}")
        
        lines = text_content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for transaction date pattern: "1. 3." (day. month.)
            date_match = re.match(r'^(\d{1,2})\.\s*(\d{1,2})\.\s*(.*)$', line)
            if date_match:
                try:
                    transaction = self._parse_csob_transaction_block(date_match, lines, i, statement_year)
                    if transaction:
                        transactions.append(transaction)
                        self.logger.debug(f"Parsed ČSOB transaction: {transaction.date} - {transaction.description} - {transaction.amount}")
                except Exception as e:
                    self.logger.warning(f"Error parsing ČSOB transaction at line {i}: {e}")
            
            i += 1
        
        self.logger.info(f"Extracted {len(transactions)} ČSOB transactions")
        return transactions
    
    def _parse_csob_transaction_block(self, date_match, lines: List[str], start_index: int, year: int) -> Optional[ParsedTransaction]:
        """Parse a ČSOB transaction block starting from the main transaction line."""
        try:
            day = int(date_match.group(1))
            month = int(date_match.group(2))
            main_line = date_match.group(3).strip()
            
            # Parse the main transaction line for description and amount
            # Format: "Transakcia platobnou kartou -2,04"
            amount_match = re.search(r'(-?\d+(?:[,\.]\d+)?)\s*$', main_line)
            if not amount_match:
                return None
            
            amount_str = amount_match.group(1)
            amount = self._parse_csob_amount(amount_str)
            if amount is None:
                return None
            
            # Extract description (everything before the amount)
            description = main_line[:amount_match.start()].strip()
            
            # Create transaction date
            transaction_date = date(year, month, day)
            
            # Look for additional info in following lines
            merchant = None
            reference = None
            i = start_index + 1
            
            # Check next few lines for merchant and reference info
            while i < len(lines) and i < start_index + 4:
                line = lines[i].strip()
                
                # Stop if we hit another transaction (starts with date pattern)
                if re.match(r'^\d{1,2}\.\s*\d{1,2}\.', line):
                    break
                
                # Extract merchant from "Miesto:" line
                if line.startswith('Miesto:'):
                    merchant_info = line[7:].strip()  # Remove "Miesto: "
                    merchant, _ = self._split_csob_merchant_location(merchant_info)
                    if merchant:
                        merchant = self._clean_csob_business_name(merchant)
                
                # Extract reference from "Ref. platiteľa:" line
                elif line.startswith('Ref. platiteľa:'):
                    reference = line[16:].strip()  # Remove "Ref. platiteľa: "
                
                i += 1
            
            # Auto-categorize based on description and merchant
            temp_transaction = ParsedTransaction(
                date=transaction_date,
                description=description,
                amount=amount,
                merchant=merchant
            )
            category = self._categorize_transaction(temp_transaction)
            
            return ParsedTransaction(
                date=transaction_date,
                description=description,
                amount=amount,
                merchant=merchant,
                category=category,
                reference=reference,
                raw_data={
                    "line_number": start_index + 1,
                    "raw_line": lines[start_index],
                    "extraction_method": "csob_specific"
                }
            )
            
        except Exception as e:
            self.logger.debug(f"Error parsing ČSOB transaction block: {e}")
            return None
    
    def _is_csob_statement(self, text_content: str) -> bool:
        """Check if this looks like a ČSOB Slovakia statement."""
        csob_indicators = [
            'VÝPIS Z ÚČTU',
            'ACCOUNT STATEMENT', 
            'ČSOB',
            'Československá obchodná banka',
            'CEKOSKBX',  # BIC code
            'Transakcia platobnou kartou',
            'Ref. platiteľa:',
            'Miesto:'
        ]
        
        # Check if at least 3 indicators are present
        found_indicators = sum(1 for indicator in csob_indicators if indicator in text_content)
        is_csob = found_indicators >= 3
        
        self.logger.debug(f"ČSOB statement detection: {found_indicators}/8 indicators found, is_csob={is_csob}")
        return is_csob
    
    def _extract_year_from_csob_header(self, text_content: str) -> int:
        """Extract year from ČSOB PDF header like 'Obdobie: 1. 3. 2023 - 31. 3. 2023'."""
        try:
            # Look for "Obdobie: 1. 3. 2023 - 31. 3. 2023" pattern
            match = re.search(r'Obdobie:\s*\d{1,2}\.\s*\d{1,2}\.\s*(\d{4})', text_content)
            if match:
                year = int(match.group(1))
                self.logger.debug(f"Found year in Obdobie header: {year}")
                return year
            
            # Fallback: look for any 4-digit year in the first 1000 characters
            match = re.search(r'\b(20\d{2})\b', text_content[:1000])
            if match:
                year = int(match.group(1))
                self.logger.debug(f"Found year in header fallback: {year}")
                return year
                
        except (ValueError, AttributeError) as e:
            self.logger.debug(f"Error extracting year from header: {e}")
        
        # Default to current year if nothing found
        from datetime import datetime
        current_year = datetime.now().year
        self.logger.debug(f"Using current year as fallback: {current_year}")
        return current_year
    
    def _clean_csob_business_name(self, merchant_name: str) -> str:
        """Clean Slovak business names by removing common suffixes and formatting.
        
        Args:
            merchant_name: Raw merchant name from ČSOB statement
            
        Returns:
            Cleaned merchant name
        """
        if not merchant_name:
            return merchant_name
        
        # Common Slovak business suffixes to clean up
        suffixes_to_remove = [
            r'\s+s\.r\.o\.$',  # s.r.o. (Slovak LLC)
            r'\s+a\.s\.$',     # a.s. (Slovak joint stock company)
            r'\s+spol\.\s+s\s+r\.o\.$',  # spol. s r.o.
            r'\s+k\.s\.$',     # k.s. (limited partnership)
            r'\s+v\.o\.s\.$',  # v.o.s. (general partnership)
            r'\s+INC\.?$',     # INC. or INC
            r'\s+LLC$',        # LLC
            r'\s+LTD$',        # LTD
            r'\s+CORP$',       # CORP
        ]
        
        cleaned = merchant_name.strip()
        
        # Remove business suffixes
        for suffix_pattern in suffixes_to_remove:
            cleaned = re.sub(suffix_pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Clean up extra spaces and formatting
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Remove trailing punctuation
        cleaned = cleaned.rstrip('.,;:')
        
        return cleaned