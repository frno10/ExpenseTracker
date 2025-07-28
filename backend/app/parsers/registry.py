"""
Global parser registry instance and initialization.
"""
import logging

from .base import ParserRegistry

logger = logging.getLogger(__name__)

# Global parser registry instance
parser_registry = ParserRegistry()


def initialize_parsers():
    """
    Initialize and register all available parsers.
    
    This function imports and registers all parser implementations.
    It should be called during application startup.
    """
    try:
        # Import and register CSV parser
        from .csv_parser import CSVParser
        parser_registry.register(CSVParser())
        
        # Import and register PDF parser
        from .pdf_parser import PDFParser
        parser_registry.register(PDFParser())
        
        # Import and register Excel parser
        from .excel_parser import ExcelParser
        parser_registry.register(ExcelParser())
        
        # Import and register OFX parser
        from .ofx_parser import OFXParser
        parser_registry.register(OFXParser())
        
        # Import and register QIF parser
        from .qif_parser import QIFParser
        parser_registry.register(QIFParser())
        
        logger.info("All parsers initialized successfully")
        
    except ImportError as e:
        logger.error(f"Failed to import parser: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize parsers: {e}")


def get_parser_info():
    """
    Get information about all registered parsers.
    
    Returns:
        Dictionary with parser information
    """
    parsers_info = {}
    
    for name in parser_registry.list_parsers():
        parser = parser_registry.get_parser(name)
        if parser:
            parsers_info[name] = {
                "name": parser.config.name,
                "description": parser.config.description,
                "supported_extensions": parser.config.supported_extensions,
                "mime_types": parser.config.mime_types,
                "settings": parser.config.settings
            }
    
    return parsers_info