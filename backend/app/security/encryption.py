"""Field-level encryption for sensitive data."""
import base64
import hashlib
from typing import Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..core.config import settings


class FieldEncryption:
    """Field-level encryption for sensitive data."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        self.encryption_key = encryption_key or settings.FIELD_ENCRYPTION_KEY
        self._fernet = None
        self._setup_encryption()
    
    def _setup_encryption(self):
        """Set up encryption cipher."""
        if not self.encryption_key:
            raise ValueError("Encryption key is required")
        
        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'expense_tracker_salt',  # In production, use random salt per field
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key.encode()))
        self._fernet = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string value."""
        if not plaintext:
            return plaintext
        
        if not isinstance(plaintext, str):
            plaintext = str(plaintext)
        
        encrypted_bytes = self._fernet.encrypt(plaintext.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string value."""
        if not ciphertext:
            return ciphertext
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode('utf-8'))
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
        except Exception:
            # Return original value if decryption fails (for backward compatibility)
            return ciphertext
    
    def hash_value(self, value: str) -> str:
        """Create a hash of a value for searching encrypted fields."""
        if not value:
            return value
        
        return hashlib.sha256(
            (value + self.encryption_key).encode('utf-8')
        ).hexdigest()


# Global encryption instance
field_encryption = FieldEncryption()


class EncryptedField:
    """Descriptor for encrypted database fields."""
    
    def __init__(self, encryption: FieldEncryption = None):
        self.encryption = encryption or field_encryption
        self.name = None
    
    def __set_name__(self, owner, name):
        self.name = name
        self.private_name = f'_{name}'
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        
        encrypted_value = getattr(obj, self.private_name, None)
        if encrypted_value is None:
            return None
        
        return self.encryption.decrypt(encrypted_value)
    
    def __set__(self, obj, value):
        if value is None:
            setattr(obj, self.private_name, None)
        else:
            encrypted_value = self.encryption.encrypt(str(value))
            setattr(obj, self.private_name, encrypted_value)


def encrypt_sensitive_data(data: dict, sensitive_fields: list) -> dict:
    """Encrypt sensitive fields in a dictionary."""
    encrypted_data = data.copy()
    
    for field in sensitive_fields:
        if field in encrypted_data and encrypted_data[field]:
            encrypted_data[field] = field_encryption.encrypt(str(encrypted_data[field]))
    
    return encrypted_data


def decrypt_sensitive_data(data: dict, sensitive_fields: list) -> dict:
    """Decrypt sensitive fields in a dictionary."""
    decrypted_data = data.copy()
    
    for field in sensitive_fields:
        if field in decrypted_data and decrypted_data[field]:
            decrypted_data[field] = field_encryption.decrypt(decrypted_data[field])
    
    return decrypted_data


# Password hashing utilities
def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    import bcrypt
    
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    import bcrypt
    
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def generate_secure_token(length: int = 32) -> str:
    """Generate a secure random token."""
    import secrets
    return secrets.token_urlsafe(length)


def mask_sensitive_data(data: str, mask_char: str = '*', visible_chars: int = 4) -> str:
    """Mask sensitive data for logging/display."""
    if not data or len(data) <= visible_chars:
        return mask_char * len(data) if data else ''
    
    return data[:visible_chars] + mask_char * (len(data) - visible_chars)