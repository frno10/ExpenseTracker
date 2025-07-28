"""
Configuration management for statement parsers.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ParserSettings(BaseModel):
    """Settings for parser configuration."""
    
    enabled_parsers: list[str] = Field(default_factory=lambda: ["csv_parser", "pdf_parser"])
    default_encoding: str = "utf-8"
    max_file_size_mb: int = 100
    temp_directory: str = "/tmp/expense_tracker_parsing"
    
    # CSV Parser specific settings
    csv_settings: Dict[str, Any] = Field(default_factory=dict)
    
    # PDF Parser specific settings  
    pdf_settings: Dict[str, Any] = Field(default_factory=dict)
    
    # Bank-specific configurations
    bank_configs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class ConfigManager:
    """
    Manager for parser configurations.
    
    This class handles loading, saving, and managing parser configurations
    including bank-specific settings and custom field mappings.
    """
    
    def __init__(self, config_dir: str = "config/parsers"):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.settings_file = self.config_dir / "settings.yaml"
        self.bank_configs_dir = self.config_dir / "banks"
        self.bank_configs_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Load settings
        self.settings = self._load_settings()
    
    def _load_settings(self) -> ParserSettings:
        """Load parser settings from file."""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    return ParserSettings(**data)
            else:
                # Create default settings
                settings = ParserSettings()
                self._save_settings(settings)
                return settings
                
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
            return ParserSettings()
    
    def _save_settings(self, settings: ParserSettings) -> None:
        """Save parser settings to file."""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                yaml.dump(settings.model_dump(), f, default_flow_style=False)
            self.logger.info(f"Settings saved to {self.settings_file}")
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
    
    def get_parser_config(self, parser_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific parser.
        
        Args:
            parser_name: Name of the parser
            
        Returns:
            Parser configuration dictionary
        """
        if parser_name == "csv_parser":
            return self.settings.csv_settings
        elif parser_name == "pdf_parser":
            return self.settings.pdf_settings
        else:
            return {}
    
    def update_parser_config(self, parser_name: str, config: Dict[str, Any]) -> None:
        """
        Update configuration for a specific parser.
        
        Args:
            parser_name: Name of the parser
            config: New configuration dictionary
        """
        if parser_name == "csv_parser":
            self.settings.csv_settings.update(config)
        elif parser_name == "pdf_parser":
            self.settings.pdf_settings.update(config)
        
        self._save_settings(self.settings)
        self.logger.info(f"Updated configuration for {parser_name}")
    
    def load_bank_config(self, bank_name: str) -> Optional[Dict[str, Any]]:
        """
        Load bank-specific configuration.
        
        Args:
            bank_name: Name of the bank
            
        Returns:
            Bank configuration dictionary or None if not found
        """
        try:
            config_file = self.bank_configs_dir / f"{bank_name.lower()}.yaml"
            
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    self.logger.debug(f"Loaded bank config for {bank_name}")
                    return config
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error loading bank config for {bank_name}: {e}")
            return None
    
    def save_bank_config(self, bank_name: str, config: Dict[str, Any]) -> None:
        """
        Save bank-specific configuration.
        
        Args:
            bank_name: Name of the bank
            config: Bank configuration dictionary
        """
        try:
            config_file = self.bank_configs_dir / f"{bank_name.lower()}.yaml"
            
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            self.logger.info(f"Saved bank config for {bank_name}")
            
        except Exception as e:
            self.logger.error(f"Error saving bank config for {bank_name}: {e}")
    
    def list_bank_configs(self) -> list[str]:
        """
        List all available bank configurations.
        
        Returns:
            List of bank names with configurations
        """
        try:
            configs = []
            for config_file in self.bank_configs_dir.glob("*.yaml"):
                bank_name = config_file.stem.replace('_', ' ').title()
                configs.append(bank_name)
            return sorted(configs)
        except Exception as e:
            self.logger.error(f"Error listing bank configs: {e}")
            return []
    
    def create_default_bank_configs(self) -> None:
        """Create default bank configurations for common banks."""
        
        # Chase Bank configuration
        chase_config = {
            "name": "Chase Bank",
            "csv_config": {
                "field_mappings": {
                    "date": ["Transaction Date", "Post Date"],
                    "description": ["Description"],
                    "amount": ["Amount"],
                    "category": ["Category"],
                    "account": ["Account"]
                },
                "date_formats": ["%m/%d/%Y"],
                "amount_columns": {
                    "single": True,
                    "negative_debits": False
                }
            },
            "pdf_config": {
                "transaction_patterns": [
                    r'(\d{2}/\d{2})\s+(.+?)\s+(\$?\s*-?\d{1,3}(?:,\d{3})*\.\d{2})'
                ],
                "date_formats": ["%m/%d"]
            }
        }
        
        # Bank of America configuration
        boa_config = {
            "name": "Bank of America",
            "csv_config": {
                "field_mappings": {
                    "date": ["Date"],
                    "description": ["Description"],
                    "amount": ["Amount"],
                    "reference": ["Reference Number"]
                },
                "date_formats": ["%m/%d/%Y"],
                "amount_columns": {
                    "single": True,
                    "negative_debits": True
                }
            }
        }
        
        # Wells Fargo configuration
        wells_fargo_config = {
            "name": "Wells Fargo",
            "csv_config": {
                "field_mappings": {
                    "date": ["Date"],
                    "description": ["Description"],
                    "amount": ["Amount"]
                },
                "date_formats": ["%m/%d/%Y"],
                "amount_columns": {
                    "single": False,
                    "debit_column": "Debit",
                    "credit_column": "Credit",
                    "negative_debits": True
                }
            }
        }
        
        # American Express configuration
        amex_config = {
            "name": "American Express",
            "csv_config": {
                "field_mappings": {
                    "date": ["Date"],
                    "description": ["Description"],
                    "amount": ["Amount"],
                    "category": ["Category"]
                },
                "date_formats": ["%m/%d/%Y"],
                "amount_columns": {
                    "single": True,
                    "negative_debits": False
                }
            }
        }
        
        # Save default configurations
        configs = {
            "chase": chase_config,
            "bank_of_america": boa_config,
            "wells_fargo": wells_fargo_config,
            "american_express": amex_config
        }
        
        for bank_name, config in configs.items():
            config_file = self.bank_configs_dir / f"{bank_name}.yaml"
            if not config_file.exists():
                self.save_bank_config(bank_name, config)
        
        self.logger.info("Created default bank configurations")
    
    def get_field_mapping_suggestions(self, columns: list[str]) -> Dict[str, str]:
        """
        Get field mapping suggestions based on column names.
        
        Args:
            columns: List of column names from the file
            
        Returns:
            Dictionary mapping standard fields to suggested columns
        """
        suggestions = {}
        
        # Common field mappings
        field_patterns = {
            "date": [
                "date", "transaction_date", "posting_date", "post_date",
                "trans_date", "effective_date", "value_date"
            ],
            "description": [
                "description", "memo", "payee", "merchant", "details",
                "transaction_description", "reference"
            ],
            "amount": [
                "amount", "transaction_amount", "value", "sum", "total"
            ],
            "debit": [
                "debit", "withdrawal", "outgoing", "expense", "charge"
            ],
            "credit": [
                "credit", "deposit", "incoming", "income", "payment"
            ],
            "category": [
                "category", "type", "classification", "group"
            ],
            "account": [
                "account", "account_number", "account_name"
            ],
            "reference": [
                "reference", "ref", "check_number", "transaction_id", "id"
            ]
        }
        
        # Match columns to fields
        for field, patterns in field_patterns.items():
            for column in columns:
                column_lower = column.lower().strip()
                for pattern in patterns:
                    if pattern in column_lower:
                        suggestions[field] = column
                        break
                if field in suggestions:
                    break
        
        return suggestions
    
    def validate_config(self, config: Dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate a parser configuration.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # Check required fields
            if "field_mappings" not in config:
                errors.append("Missing 'field_mappings' section")
            else:
                mappings = config["field_mappings"]
                
                # Check for required mappings
                required_fields = ["date", "description", "amount"]
                for field in required_fields:
                    if field not in mappings or not mappings[field]:
                        errors.append(f"Missing mapping for required field: {field}")
            
            # Validate date formats
            if "date_formats" in config:
                date_formats = config["date_formats"]
                if not isinstance(date_formats, list) or not date_formats:
                    errors.append("'date_formats' must be a non-empty list")
            
            # Validate amount columns configuration
            if "amount_columns" in config:
                amount_config = config["amount_columns"]
                if not isinstance(amount_config, dict):
                    errors.append("'amount_columns' must be a dictionary")
                else:
                    if "single" not in amount_config:
                        errors.append("'amount_columns' must specify 'single' field")
                    elif not amount_config.get("single", True):
                        # Check for debit/credit columns
                        if "debit_column" not in amount_config:
                            errors.append("'debit_column' required when single=False")
                        if "credit_column" not in amount_config:
                            errors.append("'credit_column' required when single=False")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            errors.append(f"Error validating config: {e}")
            return False, errors


# Global configuration manager instance
config_manager = ConfigManager()