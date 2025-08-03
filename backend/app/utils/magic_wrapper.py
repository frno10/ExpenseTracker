"""
Cross-platform wrapper for python-magic library.
Handles differences between Windows (python-magic-bin) and Linux (python-magic with libmagic).
"""
import logging
import platform
from typing import Optional

logger = logging.getLogger(__name__)


class MagicWrapper:
    """Cross-platform wrapper for python-magic."""
    
    def __init__(self):
        """Initialize the magic wrapper with platform-specific handling."""
        self.magic_mime = None
        self.magic_type = None
        self._initialize_magic()
    
    def _initialize_magic(self):
        """Initialize python-magic with platform-specific handling."""
        try:
            import magic
            
            # Try to initialize magic objects
            if platform.system() == "Windows":
                # On Windows, python-magic-bin should provide the binaries
                try:
                    self.magic_mime = magic.Magic(mime=True)
                    self.magic_type = magic.Magic()
                    logger.info("Initialized python-magic with Windows binaries")
                except Exception as e:
                    logger.warning(f"Failed to initialize python-magic on Windows: {e}")
                    self._fallback_initialization()
            else:
                # On Linux/Unix, use system libmagic
                try:
                    self.magic_mime = magic.Magic(mime=True)
                    self.magic_type = magic.Magic()
                    logger.info("Initialized python-magic with system libmagic")
                except Exception as e:
                    logger.warning(f"Failed to initialize python-magic on Linux: {e}")
                    self._fallback_initialization()
                    
        except ImportError:
            logger.error("python-magic not available")
            self._fallback_initialization()
    
    def _fallback_initialization(self):
        """Fallback initialization when python-magic is not available."""
        logger.warning("Using fallback MIME type detection")
        self.magic_mime = None
        self.magic_type = None
    
    def get_mime_type(self, file_path: str) -> Optional[str]:
        """Get MIME type of a file."""
        if self.magic_mime:
            try:
                return self.magic_mime.from_file(file_path)
            except Exception as e:
                logger.warning(f"Failed to get MIME type with python-magic: {e}")
        
        # Fallback to mimetypes module
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type
    
    def get_file_type(self, file_path: str) -> Optional[str]:
        """Get file type description."""
        if self.magic_type:
            try:
                return self.magic_type.from_file(file_path)
            except Exception as e:
                logger.warning(f"Failed to get file type with python-magic: {e}")
        
        # Fallback to basic file extension detection
        import os
        _, ext = os.path.splitext(file_path)
        return f"File with extension {ext}" if ext else "Unknown file type"
    
    def is_available(self) -> bool:
        """Check if python-magic is available and working."""
        return self.magic_mime is not None and self.magic_type is not None


# Global instance
magic_wrapper = MagicWrapper()