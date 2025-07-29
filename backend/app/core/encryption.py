"""
Data encryption utilities for sensitive fields.
"""
import base64
import logging
import os
from typing import Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import secrets

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Encryption-related error."""
    pass


class FieldEncryption:
    """
    Utility class for encrypting/decrypting sensitive database fields.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize field encryption.
        
        Args:
            encryption_key: Base64-encoded encryption key. If None, generates a new key.
        """
        if encryption_key:
            try:
                self.key = base64.urlsafe_b64decode(encryption_key.encode())
                if len(self.key) != 32:
                    raise ValueError("Encryption key must be 32 bytes")
            except Exception as e:
                raise EncryptionError(f"Invalid encryption key: {e}")
        else:
            # Generate a new key (for development/testing only)
            self.key = Fernet.generate_key()
            logger.warning("Generated new encryption key - this should not happen in production!")
        
        self.fernet = Fernet(base64.urlsafe_b64encode(self.key))
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string value.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64-encoded encrypted string
            
        Raises:
            EncryptionError: If encryption fails
        """
        if not isinstance(plaintext, str):
            raise EncryptionError("Can only encrypt string values")
        
        if not plaintext:
            return ""
        
        try:
            encrypted_bytes = self.fernet.encrypt(plaintext.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Encryption failed: {e}")
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a string value.
        
        Args:
            ciphertext: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            EncryptionError: If decryption fails
        """
        if not isinstance(ciphertext, str):
            raise EncryptionError("Ciphertext must be a string")
        
        if not ciphertext:
            return ""
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode('utf-8'))
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError(f"Decryption failed: {e}")
    
    def encrypt_dict(self, data: dict, fields_to_encrypt: list) -> dict:
        """
        Encrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing data
            fields_to_encrypt: List of field names to encrypt
            
        Returns:
            Dictionary with encrypted fields
        """
        encrypted_data = data.copy()
        
        for field in fields_to_encrypt:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = self.encrypt(str(encrypted_data[field]))
        
        return encrypted_data
    
    def decrypt_dict(self, data: dict, fields_to_decrypt: list) -> dict:
        """
        Decrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing encrypted data
            fields_to_decrypt: List of field names to decrypt
            
        Returns:
            Dictionary with decrypted fields
        """
        decrypted_data = data.copy()
        
        for field in fields_to_decrypt:
            if field in decrypted_data and decrypted_data[field]:
                try:
                    decrypted_data[field] = self.decrypt(decrypted_data[field])
                except EncryptionError:
                    # Field might not be encrypted (backward compatibility)
                    logger.warning(f"Failed to decrypt field {field}, leaving as-is")
        
        return decrypted_data


class TokenEncryption:
    """
    Utility class for encrypting/decrypting tokens and sensitive strings.
    """
    
    def __init__(self, secret_key: str):
        """
        Initialize token encryption.
        
        Args:
            secret_key: Secret key for encryption
        """
        # Derive encryption key from secret
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'expense_tracker_salt',  # In production, use a random salt
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(secret_key.encode())
        self.fernet = Fernet(base64.urlsafe_b64encode(key))
    
    def encrypt_token(self, token: str, ttl: Optional[int] = None) -> str:
        """
        Encrypt a token with optional TTL.
        
        Args:
            token: Token to encrypt
            ttl: Time-to-live in seconds
            
        Returns:
            Encrypted token
        """
        try:
            if ttl:
                encrypted = self.fernet.encrypt_at_time(token.encode(), int(time.time()))
            else:
                encrypted = self.fernet.encrypt(token.encode())
            
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            raise EncryptionError(f"Token encryption failed: {e}")
    
    def decrypt_token(self, encrypted_token: str, ttl: Optional[int] = None) -> str:
        """
        Decrypt a token with optional TTL validation.
        
        Args:
            encrypted_token: Encrypted token
            ttl: Time-to-live in seconds for validation
            
        Returns:
            Decrypted token
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_token.encode())
            
            if ttl:
                import time
                decrypted = self.fernet.decrypt_at_time(encrypted_bytes, ttl, int(time.time()))
            else:
                decrypted = self.fernet.decrypt(encrypted_bytes)
            
            return decrypted.decode()
        except Exception as e:
            raise EncryptionError(f"Token decryption failed: {e}")


class SecureStorage:
    """
    Secure storage for sensitive configuration and secrets.
    """
    
    def __init__(self, master_key: str):
        """
        Initialize secure storage.
        
        Args:
            master_key: Master key for encrypting stored values
        """
        self.encryption = FieldEncryption(master_key)
        self._storage = {}
    
    def store(self, key: str, value: str) -> None:
        """
        Store a value securely.
        
        Args:
            key: Storage key
            value: Value to store
        """
        encrypted_value = self.encryption.encrypt(value)
        self._storage[key] = encrypted_value
    
    def retrieve(self, key: str) -> Optional[str]:
        """
        Retrieve a stored value.
        
        Args:
            key: Storage key
            
        Returns:
            Decrypted value or None if not found
        """
        encrypted_value = self._storage.get(key)
        if encrypted_value:
            return self.encryption.decrypt(encrypted_value)
        return None
    
    def delete(self, key: str) -> bool:
        """
        Delete a stored value.
        
        Args:
            key: Storage key
            
        Returns:
            True if deleted, False if not found
        """
        if key in self._storage:
            del self._storage[key]
            return True
        return False
    
    def list_keys(self) -> list:
        """
        List all storage keys.
        
        Returns:
            List of storage keys
        """
        return list(self._storage.keys())


def generate_encryption_key() -> str:
    """
    Generate a new encryption key.
    
    Returns:
        Base64-encoded encryption key
    """
    key = Fernet.generate_key()
    return base64.urlsafe_b64encode(key).decode()


def hash_sensitive_data(data: str, salt: Optional[bytes] = None) -> tuple:
    """
    Hash sensitive data with salt.
    
    Args:
        data: Data to hash
        salt: Salt bytes (generates random if None)
        
    Returns:
        Tuple of (hash, salt)
    """
    if salt is None:
        salt = secrets.token_bytes(32)
    
    digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
    digest.update(salt)
    digest.update(data.encode('utf-8'))
    hash_bytes = digest.finalize()
    
    return base64.b64encode(hash_bytes).decode(), base64.b64encode(salt).decode()


def verify_hashed_data(data: str, hash_value: str, salt: str) -> bool:
    """
    Verify hashed data.
    
    Args:
        data: Original data
        hash_value: Base64-encoded hash
        salt: Base64-encoded salt
        
    Returns:
        True if data matches hash
    """
    try:
        salt_bytes = base64.b64decode(salt.encode())
        computed_hash, _ = hash_sensitive_data(data, salt_bytes)
        return secrets.compare_digest(hash_value, computed_hash)
    except Exception:
        return False


# Global encryption instance (initialized from settings)
_field_encryption: Optional[FieldEncryption] = None


def get_field_encryption() -> FieldEncryption:
    """
    Get the global field encryption instance.
    
    Returns:
        FieldEncryption instance
    """
    global _field_encryption
    
    if _field_encryption is None:
        # Initialize from environment or settings
        encryption_key = os.getenv('FIELD_ENCRYPTION_KEY')
        if not encryption_key:
            logger.warning("No FIELD_ENCRYPTION_KEY found, generating temporary key")
        
        _field_encryption = FieldEncryption(encryption_key)
    
    return _field_encryption


def encrypt_field(value: str) -> str:
    """
    Encrypt a field value using the global encryption instance.
    
    Args:
        value: Value to encrypt
        
    Returns:
        Encrypted value
    """
    return get_field_encryption().encrypt(value)


def decrypt_field(encrypted_value: str) -> str:
    """
    Decrypt a field value using the global encryption instance.
    
    Args:
        encrypted_value: Encrypted value
        
    Returns:
        Decrypted value
    """
    return get_field_encryption().decrypt(encrypted_value)