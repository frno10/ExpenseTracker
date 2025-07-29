"""
Logging configuration for the CLI.
"""
import logging
import sys
from pathlib import Path


def setup_logging(debug: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    
    # Create logs directory
    log_dir = Path.home() / ".expense-tracker" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "cli.log"),
            logging.StreamHandler(sys.stderr) if debug else logging.NullHandler(),
        ]
    )
    
    # Reduce noise from requests library
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)