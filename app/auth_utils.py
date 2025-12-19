"""
Authentication Utilities Module

This module provides secure password hashing using Argon2 with gradual migration
from legacy SHA-256 hashes. When a user with a legacy hash logs in successfully,
their password is automatically upgraded to Argon2.

Security references:
- OWASP Password Storage: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- NIST SP 800-63B: https://pages.nist.gov/800-63-4/sp800-63b.html
"""

import re
import hashlib
from passlib.context import CryptContext

# Password hashing context with Argon2 as the primary scheme
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

# Pattern to detect legacy SHA-256 hashes (64 hexadecimal characters)
SHA256_HEX_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Argon2 hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Verify a password against a stored hash.
    
    Supports both:
    - Legacy SHA-256 hashes (64 char hex string)
    - Modern Argon2 hashes (starts with $argon2)
    
    Args:
        plain_password: Plain text password to verify
        stored_hash: Stored hash from database
        
    Returns:
        True if password matches, False otherwise
    """
    if is_legacy_hash(stored_hash):
        # Legacy SHA-256 verification
        return hashlib.sha256(plain_password.encode()).hexdigest() == stored_hash
    
    # Modern Argon2 verification
    return pwd_context.verify(plain_password, stored_hash)


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
    Upgrade a legacy SHA-256 hash to Argon2 if the password is correct.
    
    This enables gradual migration: when a user with a legacy hash
    successfully logs in, their password is re-hashed with Argon2.
    
    Args:
        plain_password: Plain text password
        stored_hash: Current stored hash
        
    Returns:
        New Argon2 hash if upgrade is needed and password is correct,
        None otherwise (either already Argon2 or password incorrect)
    """
    if is_legacy_hash(stored_hash):
        # Verify with legacy method
        if hashlib.sha256(plain_password.encode()).hexdigest() == stored_hash:
            # Password correct, return new Argon2 hash
            return hash_password(plain_password)
    
    return None
