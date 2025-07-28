"""
File security service for virus scanning and validation.
"""
import hashlib
import logging
import mimetypes
import os
import tempfile
from typing import Dict, List, Optional, Tuple

import filetype
import magic
from PIL import Image

logger = logging.getLogger(__name__)


class FileSecurityService:
    """Service for file security validation and virus scanning."""
    
    # Maximum file sizes by type (in bytes)
    MAX_FILE_SIZES = {
        'pdf': 50 * 1024 * 1024,  # 50MB
        'csv': 10 * 1024 * 1024,  # 10MB
        'excel': 25 * 1024 * 1024,  # 25MB
        'image': 5 * 1024 * 1024,   # 5MB
        'text': 5 * 1024 * 1024,    # 5MB
        'default': 50 * 1024 * 1024  # 50MB default
    }
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        '.pdf', '.csv', '.xls', '.xlsx', '.ofx', '.qif', '.txt',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'  # For receipts
    }
    
    # Allowed MIME types
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'text/csv',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/x-ofx',
        'text/plain',
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/bmp',
        'image/tiff'
    }
    
    # Dangerous file signatures (magic bytes)
    DANGEROUS_SIGNATURES = [
        b'\x4d\x5a',  # PE executable
        b'\x7f\x45\x4c\x46',  # ELF executable
        b'\xca\xfe\xba\xbe',  # Java class file
        b'\xfe\xed\xfa\xce',  # Mach-O executable
        b'\x50\x4b\x03\x04',  # ZIP (could contain malware)
    ]
    
    def __init__(self):
        """Initialize the file security service."""
        self.magic_mime = magic.Magic(mime=True)
        self.magic_type = magic.Magic()
        
        # Try to initialize ClamAV
        self.clamav_available = self._check_clamav_availability()
        if not self.clamav_available:
            logger.warning("ClamAV not available - virus scanning disabled")
    
    def _check_clamav_availability(self) -> bool:
        """Check if ClamAV daemon is available."""
        try:
            import clamd
            cd = clamd.ClamdUnixSocket()
            cd.ping()
            return True
        except Exception as e:
            logger.debug(f"ClamAV not available: {e}")
            return False
    
    async def validate_file(
        self, 
        file_path: str, 
        original_filename: str,
        max_size_override: Optional[int] = None
    ) -> Tuple[bool, List[str]]:
        """
        Comprehensive file validation.
        
        Args:
            file_path: Path to the file to validate
            original_filename: Original filename from upload
            max_size_override: Override default max size
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                errors.append("File not found")
                return False, errors
            
            # Get file info
            file_size = os.path.getsize(file_path)
            file_extension = os.path.splitext(original_filename)[1].lower()
            
            # Validate file extension
            if file_extension not in self.ALLOWED_EXTENSIONS:
                errors.append(f"File extension '{file_extension}' not allowed")
            
            # Validate file size
            max_size = max_size_override or self._get_max_size_for_extension(file_extension)
            if file_size > max_size:
                errors.append(f"File size ({file_size} bytes) exceeds limit ({max_size} bytes)")
            
            # Validate MIME type
            try:
                detected_mime = self.magic_mime.from_file(file_path)
                if detected_mime not in self.ALLOWED_MIME_TYPES:
                    errors.append(f"MIME type '{detected_mime}' not allowed")
            except Exception as e:
                logger.warning(f"Failed to detect MIME type: {e}")
                errors.append("Could not determine file type")
            
            # Check file signature
            signature_valid, signature_errors = self._validate_file_signature(file_path)
            if not signature_valid:
                errors.extend(signature_errors)
            
            # Virus scan
            if self.clamav_available:
                virus_free, virus_errors = await self._scan_for_viruses(file_path)
                if not virus_free:
                    errors.extend(virus_errors)
            
            # Additional validation based on file type
            type_valid, type_errors = await self._validate_by_type(file_path, file_extension)
            if not type_valid:
                errors.extend(type_errors)
            
            return len(errors) == 0, errors
            
        except Exception as e:
            logger.error(f"Error during file validation: {e}")
            errors.append(f"Validation failed: {str(e)}")
            return False, errors
    
    def _get_max_size_for_extension(self, extension: str) -> int:
        """Get maximum file size for a given extension."""
        if extension == '.pdf':
            return self.MAX_FILE_SIZES['pdf']
        elif extension in ['.xls', '.xlsx']:
            return self.MAX_FILE_SIZES['excel']
        elif extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
            return self.MAX_FILE_SIZES['image']
        elif extension in ['.csv', '.txt', '.ofx', '.qif']:
            return self.MAX_FILE_SIZES['text']
        else:
            return self.MAX_FILE_SIZES['default']
    
    def _validate_file_signature(self, file_path: str) -> Tuple[bool, List[str]]:
        """Validate file signature (magic bytes)."""
        errors = []
        
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)  # Read first 16 bytes
            
            # Check for dangerous signatures
            for signature in self.DANGEROUS_SIGNATURES:
                if header.startswith(signature):
                    errors.append("File contains potentially dangerous signature")
                    break
            
            # Use filetype library for additional validation
            kind = filetype.guess(file_path)
            if kind is None:
                # This might be a text file, which is okay
                pass
            else:
                # Verify the detected type matches expected types
                allowed_types = ['pdf', 'csv', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']
                if kind.extension not in allowed_types:
                    errors.append(f"Detected file type '{kind.extension}' not allowed")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            logger.error(f"Error validating file signature: {e}")
            return False, [f"Signature validation failed: {str(e)}"]
    
    async def _scan_for_viruses(self, file_path: str) -> Tuple[bool, List[str]]:
        """Scan file for viruses using ClamAV."""
        errors = []
        
        try:
            import clamd
            cd = clamd.ClamdUnixSocket()
            
            # Scan the file
            result = cd.scan(file_path)
            
            if result is None:
                # No viruses found
                return True, []
            
            # Check scan results
            for file, status in result.items():
                if status[0] == 'FOUND':
                    errors.append(f"Virus detected: {status[1]}")
                elif status[0] == 'ERROR':
                    errors.append(f"Scan error: {status[1]}")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            logger.error(f"Error during virus scan: {e}")
            # Don't fail validation if virus scanning fails
            logger.warning("Virus scanning failed - proceeding without scan")
            return True, []
    
    async def _validate_by_type(self, file_path: str, extension: str) -> Tuple[bool, List[str]]:
        """Additional validation based on file type."""
        errors = []
        
        try:
            if extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
                # Validate image files
                try:
                    with Image.open(file_path) as img:
                        # Verify it's a valid image
                        img.verify()
                        
                        # Check image dimensions (prevent extremely large images)
                        if img.width > 10000 or img.height > 10000:
                            errors.append("Image dimensions too large")
                            
                except Exception as e:
                    errors.append(f"Invalid image file: {str(e)}")
            
            elif extension == '.pdf':
                # Basic PDF validation
                try:
                    with open(file_path, 'rb') as f:
                        header = f.read(8)
                        if not header.startswith(b'%PDF-'):
                            errors.append("Invalid PDF file format")
                except Exception as e:
                    errors.append(f"PDF validation failed: {str(e)}")
            
            elif extension in ['.csv', '.txt']:
                # Text file validation
                try:
                    # Try to read as text to ensure it's not binary
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        sample = f.read(1024)  # Read first 1KB
                        
                    # Check for excessive null bytes (sign of binary file)
                    null_count = sample.count('\x00')
                    if null_count > len(sample) * 0.1:  # More than 10% null bytes
                        errors.append("File appears to be binary, not text")
                        
                except Exception as e:
                    errors.append(f"Text file validation failed: {str(e)}")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            logger.error(f"Error in type-specific validation: {e}")
            return False, [f"Type validation failed: {str(e)}"]
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file."""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating file hash: {e}")
            return ""
    
    def get_file_metadata(self, file_path: str, original_filename: str) -> Dict:
        """Get comprehensive file metadata."""
        metadata = {
            'original_filename': original_filename,
            'file_size': 0,
            'file_hash': '',
            'mime_type': '',
            'file_type_description': '',
            'extension': '',
            'created_at': None,
            'modified_at': None
        }
        
        try:
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                metadata.update({
                    'file_size': stat.st_size,
                    'created_at': stat.st_ctime,
                    'modified_at': stat.st_mtime,
                    'extension': os.path.splitext(original_filename)[1].lower(),
                    'file_hash': self.calculate_file_hash(file_path)
                })
                
                # Get MIME type and description
                try:
                    metadata['mime_type'] = self.magic_mime.from_file(file_path)
                    metadata['file_type_description'] = self.magic_type.from_file(file_path)
                except Exception as e:
                    logger.warning(f"Failed to get file type info: {e}")
        
        except Exception as e:
            logger.error(f"Error getting file metadata: {e}")
        
        return metadata