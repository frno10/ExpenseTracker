"""
File format detection utilities for statement parsing.
"""
import logging
import mimetypes
import os
from pathlib import Path
from typing import Optional, Tuple

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
    magic = None

import chardet

logger = logging.getLogger(__name__)


class FileDetector:
    """
    Utility class for detecting file formats and properties.
    
    This class provides methods for detecting file types, MIME types,
    and encoding of files to help determine the appropriate parser.
    """
    
    def __init__(self):
        """Initialize the file detector."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        if HAS_MAGIC:
            try:
                self.magic_mime = magic.Magic(mime=True)
                self.magic_type = magic.Magic()
                self.logger.info("python-magic initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize python-magic: {e}")
                self.magic_mime = None
                self.magic_type = None
        else:
            self.logger.warning("python-magic not available, using fallback detection")
            self.magic_mime = None
            self.magic_type = None
    
    def detect_mime_type(self, file_path: str) -> Optional[str]:
        """
        Detect the MIME type of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            MIME type string or None if detection fails
        """
        try:
            # Try python-magic first (more accurate)
            if self.magic_mime:
                mime_type = self.magic_mime.from_file(file_path)
                if mime_type:
                    self.logger.debug(f"Detected MIME type (magic): {mime_type} for {file_path}")
                    return mime_type
            
            # Fallback to mimetypes module
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type:
                self.logger.debug(f"Detected MIME type (mimetypes): {mime_type} for {file_path}")
                return mime_type
            
            # Additional fallback based on file extension
            extension = Path(file_path).suffix.lower()
            extension_mime_map = {
                '.pdf': 'application/pdf',
                '.csv': 'text/csv',
                '.txt': 'text/plain',
                '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                '.xls': 'application/vnd.ms-excel',
                '.ofx': 'application/x-ofx',
                '.qif': 'application/x-qif',
            }
            
            if extension in extension_mime_map:
                mime_type = extension_mime_map[extension]
                self.logger.debug(f"Detected MIME type (extension): {mime_type} for {file_path}")
                return mime_type
            
            self.logger.warning(f"Could not detect MIME type for {file_path}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error detecting MIME type for {file_path}: {e}")
            return None
    
    def detect_encoding(self, file_path: str, sample_size: int = 8192) -> Optional[str]:
        """
        Detect the character encoding of a text file.
        
        Args:
            file_path: Path to the file
            sample_size: Number of bytes to sample for detection
            
        Returns:
            Encoding name or None if detection fails
        """
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(sample_size)
            
            if not sample:
                return None
            
            result = chardet.detect(sample)
            encoding = result.get('encoding')
            confidence = result.get('confidence', 0)
            
            if encoding and confidence > 0.7:
                self.logger.debug(f"Detected encoding: {encoding} (confidence: {confidence:.2f}) for {file_path}")
                return encoding
            
            # Fallback to common encodings
            for fallback_encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    with open(file_path, 'r', encoding=fallback_encoding) as f:
                        f.read(1024)  # Try to read a small sample
                    self.logger.debug(f"Using fallback encoding: {fallback_encoding} for {file_path}")
                    return fallback_encoding
                except UnicodeDecodeError:
                    continue
            
            self.logger.warning(f"Could not detect encoding for {file_path}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error detecting encoding for {file_path}: {e}")
            return None
    
    def get_file_info(self, file_path: str) -> dict:
        """
        Get comprehensive information about a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file information
        """
        try:
            path = Path(file_path)
            stat = path.stat()
            
            info = {
                'path': str(path.absolute()),
                'name': path.name,
                'extension': path.suffix.lower(),
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'mime_type': self.detect_mime_type(file_path),
                'encoding': None,
                'is_text': False,
                'is_binary': False,
            }
            
            # Detect encoding for text files
            mime_type = info['mime_type']
            if mime_type and (mime_type.startswith('text/') or mime_type in ['application/csv']):
                info['encoding'] = self.detect_encoding(file_path)
                info['is_text'] = True
            else:
                info['is_binary'] = True
            
            # Additional file type detection
            if self.magic_type:
                try:
                    file_type = self.magic_type.from_file(file_path)
                    info['file_type'] = file_type
                except Exception as e:
                    self.logger.debug(f"Could not get file type description: {e}")
            
            return info
            
        except Exception as e:
            self.logger.error(f"Error getting file info for {file_path}: {e}")
            return {'error': str(e)}
    
    def is_supported_format(self, file_path: str, supported_extensions: list, supported_mime_types: list) -> bool:
        """
        Check if a file format is supported based on extension and MIME type.
        
        Args:
            file_path: Path to the file
            supported_extensions: List of supported file extensions
            supported_mime_types: List of supported MIME types
            
        Returns:
            True if the file format is supported
        """
        try:
            # Check extension
            extension = Path(file_path).suffix.lower()
            if extension in supported_extensions:
                return True
            
            # Check MIME type
            mime_type = self.detect_mime_type(file_path)
            if mime_type and mime_type in supported_mime_types:
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking format support for {file_path}: {e}")
            return False
    
    def validate_file(self, file_path: str) -> Tuple[bool, list]:
        """
        Validate that a file exists and is readable.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            path = Path(file_path)
            
            # Check if file exists
            if not path.exists():
                errors.append(f"File does not exist: {file_path}")
                return False, errors
            
            # Check if it's a file (not a directory)
            if not path.is_file():
                errors.append(f"Path is not a file: {file_path}")
                return False, errors
            
            # Check if file is readable
            if not os.access(file_path, os.R_OK):
                errors.append(f"File is not readable: {file_path}")
                return False, errors
            
            # Check file size (warn if empty or very large)
            size = path.stat().st_size
            if size == 0:
                errors.append(f"File is empty: {file_path}")
                return False, errors
            
            if size > 100 * 1024 * 1024:  # 100MB
                errors.append(f"File is very large ({size / 1024 / 1024:.1f}MB): {file_path}")
                # Don't return False for large files, just warn
            
            return True, errors
            
        except Exception as e:
            errors.append(f"Error validating file {file_path}: {e}")
            return False, errors


# Global file detector instance
file_detector = FileDetector()