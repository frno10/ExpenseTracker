"""
Base parser interface and common functionality for statement parsing.
"""
import logging
from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class ParsedTransaction(BaseModel):
    """Represents a parsed transaction from a statement."""
    
    date: date
    description: str
    amount: Decimal
    merchant: Optional[str] = None
    category: Optional[str] = None
    account: Optional[str] = None
    reference: Optional[str] = None
    notes: Optional[str] = None
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    
    @validator("amount", pre=True)
    def validate_amount(cls, v):
        """Ensure amount is a valid Decimal."""
        if isinstance(v, str):
            # Remove common currency symbols and whitespace
            v = v.replace("$", "").replace(",", "").strip()
            # Handle negative amounts in parentheses
            if v.startswith("(") and v.endswith(")"):
                v = "-" + v[1:-1]
        return Decimal(str(v))
    
    @validator("date", pre=True)
    def validate_date(cls, v):
        """Parse date from various formats."""
        if isinstance(v, str):
            # Try common date formats
            formats = [
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%d/%m/%Y", 
                "%m-%d-%Y",
                "%d-%m-%Y",
                "%Y/%m/%d",
                "%m/%d/%y",
                "%d/%m/%y"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(v, fmt).date()
                except ValueError:
                    continue
            
            raise ValueError(f"Unable to parse date: {v}")
        
        return v


class ParseResult(BaseModel):
    """Result of parsing a statement file."""
    
    success: bool
    transactions: List[ParsedTransaction] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def transaction_count(self) -> int:
        """Number of successfully parsed transactions."""
        return len(self.transactions)
    
    @property
    def has_errors(self) -> bool:
        """Whether parsing encountered errors."""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Whether parsing encountered warnings."""
        return len(self.warnings) > 0


class ParserConfig(BaseModel):
    """Configuration for a parser."""
    
    name: str
    description: str
    supported_extensions: List[str]
    mime_types: List[str]
    settings: Dict[str, Any] = Field(default_factory=dict)


class BaseParser(ABC):
    """
    Abstract base class for all statement parsers.
    
    This class defines the interface that all parsers must implement
    and provides common functionality for parsing financial statements.
    """
    
    def __init__(self, config: Optional[ParserConfig] = None):
        """
        Initialize the parser with optional configuration.
        
        Args:
            config: Parser configuration
        """
        self.config = config or self.get_default_config()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def get_default_config(self) -> ParserConfig:
        """
        Get the default configuration for this parser.
        
        Returns:
            Default parser configuration
        """
        pass
    
    @abstractmethod
    def can_parse(self, file_path: str, mime_type: Optional[str] = None) -> bool:
        """
        Check if this parser can handle the given file.
        
        Args:
            file_path: Path to the file to parse
            mime_type: MIME type of the file (optional)
            
        Returns:
            True if this parser can handle the file
        """
        pass
    
    @abstractmethod
    async def parse(self, file_path: str, **kwargs) -> ParseResult:
        """
        Parse a statement file and extract transactions.
        
        Args:
            file_path: Path to the file to parse
            **kwargs: Additional parsing options
            
        Returns:
            Parse result with transactions and metadata
        """
        pass
    
    def _extract_merchant_name(self, description: str) -> Optional[str]:
        """
        Extract merchant name from transaction description.
        
        This is a basic implementation that can be overridden by specific parsers.
        
        Args:
            description: Transaction description
            
        Returns:
            Extracted merchant name or None
        """
        if not description:
            return None
        
        # Remove common prefixes and suffixes
        cleaned = description.strip()
        
        # Remove date patterns
        import re
        cleaned = re.sub(r'\d{2}/\d{2}/\d{2,4}', '', cleaned)
        cleaned = re.sub(r'\d{2}-\d{2}-\d{2,4}', '', cleaned)
        
        # Remove reference numbers
        cleaned = re.sub(r'#\d+', '', cleaned)
        cleaned = re.sub(r'REF\s*\d+', '', cleaned, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned if cleaned else None
    
    def _categorize_transaction(self, transaction: ParsedTransaction) -> Optional[str]:
        """
        Attempt to categorize a transaction based on description and merchant.
        
        This is a basic implementation that can be overridden by specific parsers.
        
        Args:
            transaction: Parsed transaction
            
        Returns:
            Suggested category or None
        """
        description = (transaction.description or "").lower()
        merchant = (transaction.merchant or "").lower()
        
        # Basic categorization rules
        if any(keyword in description for keyword in ["grocery", "supermarket", "food"]):
            return "Groceries"
        elif any(keyword in description for keyword in ["gas", "fuel", "station"]):
            return "Transportation"
        elif any(keyword in description for keyword in ["restaurant", "cafe", "dining"]):
            return "Dining"
        elif any(keyword in description for keyword in ["pharmacy", "medical", "doctor"]):
            return "Healthcare"
        elif any(keyword in description for keyword in ["amazon", "store", "retail"]):
            return "Shopping"
        
        return None
    
    def _validate_transaction(self, transaction: ParsedTransaction) -> List[str]:
        """
        Validate a parsed transaction and return any warnings.
        
        Args:
            transaction: Transaction to validate
            
        Returns:
            List of validation warnings
        """
        warnings = []
        
        # Check for required fields
        if not transaction.description:
            warnings.append("Transaction missing description")
        
        if transaction.amount == 0:
            warnings.append("Transaction has zero amount")
        
        # Check for reasonable date range (not too far in past/future)
        today = date.today()
        if transaction.date > today:
            warnings.append(f"Transaction date is in the future: {transaction.date}")
        
        # Check for very old transactions (more than 10 years)
        if (today - transaction.date).days > 3650:
            warnings.append(f"Transaction date is very old: {transaction.date}")
        
        return warnings


class ParserRegistry:
    """
    Registry for managing available statement parsers.
    
    This class maintains a registry of all available parsers and provides
    methods for finding the appropriate parser for a given file.
    """
    
    def __init__(self):
        """Initialize the parser registry."""
        self._parsers: Dict[str, BaseParser] = {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def register(self, parser: BaseParser) -> None:
        """
        Register a parser in the registry.
        
        Args:
            parser: Parser instance to register
        """
        name = parser.config.name
        if name in self._parsers:
            self.logger.warning(f"Parser '{name}' is already registered, overwriting")
        
        self._parsers[name] = parser
        self.logger.info(f"Registered parser: {name}")
    
    def unregister(self, name: str) -> None:
        """
        Unregister a parser from the registry.
        
        Args:
            name: Name of the parser to unregister
        """
        if name in self._parsers:
            del self._parsers[name]
            self.logger.info(f"Unregistered parser: {name}")
        else:
            self.logger.warning(f"Parser '{name}' not found in registry")
    
    def get_parser(self, name: str) -> Optional[BaseParser]:
        """
        Get a parser by name.
        
        Args:
            name: Name of the parser
            
        Returns:
            Parser instance or None if not found
        """
        return self._parsers.get(name)
    
    def list_parsers(self) -> List[str]:
        """
        Get a list of all registered parser names.
        
        Returns:
            List of parser names
        """
        return list(self._parsers.keys())
    
    def find_parser(self, file_path: str, mime_type: Optional[str] = None) -> Optional[BaseParser]:
        """
        Find the best parser for a given file.
        
        Args:
            file_path: Path to the file to parse
            mime_type: MIME type of the file (optional)
            
        Returns:
            Best matching parser or None if no parser can handle the file
        """
        for parser in self._parsers.values():
            if parser.can_parse(file_path, mime_type):
                self.logger.info(f"Found parser '{parser.config.name}' for file: {file_path}")
                return parser
        
        self.logger.warning(f"No parser found for file: {file_path}")
        return None
    
    def get_supported_extensions(self) -> List[str]:
        """
        Get all supported file extensions across all parsers.
        
        Returns:
            List of supported file extensions
        """
        extensions = set()
        for parser in self._parsers.values():
            extensions.update(parser.config.supported_extensions)
        return sorted(list(extensions))
    
    def get_supported_mime_types(self) -> List[str]:
        """
        Get all supported MIME types across all parsers.
        
        Returns:
            List of supported MIME types
        """
        mime_types = set()
        for parser in self._parsers.values():
            mime_types.update(parser.config.mime_types)
        return sorted(list(mime_types))