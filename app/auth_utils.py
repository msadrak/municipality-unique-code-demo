"""
Authentication Utilities Module

This module provides secure password hashing using PBKDF2 with gradual migration
from legacy SHA-256 hashes. When a user with a legacy hash logs in successfully,
their password is automatically upgraded to PBKDF2.

Security references:
- OWASP Password Storage: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- NIST SP 800-63B: https://pages.nist.gov/800-63-4/sp800-63b.html
"""

import re
import hashlib
import secrets
import base64

# PBKDF2 parameters
PBKDF2_ITERATIONS = 260000  # OWASP recommended for 2024
PBKDF2_SALT_LENGTH = 16

# Pattern to detect legacy SHA-256 hashes (64 hexadecimal characters)
SHA256_HEX_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def hash_password(password: str) -> str:
    """
    Hash a password using PBKDF2.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        PBKDF2 hashed password string (format: pbkdf2:sha256:iterations$salt$hash)
    """
    salt = secrets.token_bytes(PBKDF2_SALT_LENGTH)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, PBKDF2_ITERATIONS)
    salt_b64 = base64.b64encode(salt).decode('ascii')
    key_b64 = base64.b64encode(key).decode('ascii')
    return f"pbkdf2:sha256:{PBKDF2_ITERATIONS}${salt_b64}${key_b64}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Verify a password against a stored hash.
    
    Supports both:
    - Legacy SHA-256 hashes (64 char hex string)
    - Modern PBKDF2 hashes (starts with pbkdf2:)
    
    Args:
        plain_password: Plain text password to verify
        stored_hash: Stored hash from database
        
    Returns:
        True if password matches, False otherwise
    """
    if is_legacy_hash(stored_hash):
        # Legacy SHA-256 verification
        return hashlib.sha256(plain_password.encode()).hexdigest() == stored_hash
    
    # Modern PBKDF2 verification
    if stored_hash.startswith("pbkdf2:"):
        try:
            parts = stored_hash.split("$")
            if len(parts) != 3:
                return False
            header = parts[0]  # pbkdf2:sha256:iterations
            salt_b64 = parts[1]
            key_b64 = parts[2]
            
            # Parse iterations
            iterations = int(header.split(":")[2])
            salt = base64.b64decode(salt_b64)
            stored_key = base64.b64decode(key_b64)
            
            # Compute hash
            computed_key = hashlib.pbkdf2_hmac('sha256', plain_password.encode(), salt, iterations)
            return secrets.compare_digest(stored_key, computed_key)
        except (ValueError, IndexError):
            return False
    
    return False


def is_legacy_hash(stored_hash: str) -> bool:
    """
    Check if a hash is a legacy SHA-256 hash.
    
    Args:
        stored_hash: Hash string to check
        
    Returns:
        True if it's a legacy SHA-256 hash
    """
    return bool(SHA256_HEX_PATTERN.match(stored_hash))


def upgrade_hash_if_needed(plain_password: str, stored_hash: str) -> str | None:
    """
    Upgrade a legacy SHA-256 hash to PBKDF2 if the password is correct.
    
    This enables gradual migration: when a user with a legacy hash
    successfully logs in, their password is re-hashed with PBKDF2.
    
    Args:
        plain_password: Plain text password
        stored_hash: Current stored hash
        
    Returns:
        New PBKDF2 hash if upgrade is needed and password is correct,
        None otherwise (either already PBKDF2 or password incorrect)
    """
    if is_legacy_hash(stored_hash):
        # Verify with legacy method
        if hashlib.sha256(plain_password.encode()).hexdigest() == stored_hash:
            # Password correct, return new PBKDF2 hash
            return hash_password(plain_password)
    
    return None
