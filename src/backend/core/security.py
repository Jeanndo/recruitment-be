"""Password hashing.

Passwords are never stored or logged in plain text.

Argon2 is the current recommendation of the Password Hashing and
is preferred over bcrypt.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Return an Argon2 hash for `password`.

    The returned string already contains the algorithm, the parameters and the
    salt, so no extra columns are needed in the database.
    """
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plain password against a stored hash.

    Returns False instead of raising when the hash is malformed, so a corrupt
    row cannot crash the login endpoint.
    """
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        # Wrong password, unsupported hash, or garbage in the column.
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """True when the hash was created with outdated Argon2 parameters.

    Login can use this to transparently upgrade old hashes after a successful
    check. It is here so the rule lives next to the hasher.
    """
    return _hasher.check_needs_rehash(password_hash)
