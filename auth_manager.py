"""
Authentication & Credential Manager for Price Tag Generator.
Provides secure password hashing (PBKDF2-HMAC-SHA256) and persistent
offline credential management with fallback and master recovery.
"""

import os
import json
import hashlib
import hmac
import time
from typing import Tuple

# Default initial credentials
DEFAULT_PASSWORD = "admin"
MASTER_RECOVERY_KEY = "BIGGMART-RECOVERY-2026"
PBKDF2_ROUNDS = 100_000


def get_auth_dir() -> str:
    """Returns the application data directory for storing credentials."""
    appdata = os.getenv("APPDATA") or os.path.expanduser("~")
    target_dir = os.path.join(appdata, "PriceTagGenerator")
    try:
        os.makedirs(target_dir, exist_ok=True)
    except Exception:
        pass
    return target_dir


def get_auth_file_path() -> str:
    """Returns the path to the credentials JSON file."""
    return os.path.join(get_auth_dir(), "auth_credentials.json")


def _hash_password(password: str, salt: bytes) -> str:
    """Computes PBKDF2-HMAC-SHA256 hash in hexadecimal."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS).hex()


def has_custom_password() -> bool:
    """Checks whether a user-defined password has been set."""
    file_path = get_auth_file_path()
    if not os.path.exists(file_path):
        return False
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return bool(data.get("hash") and data.get("salt"))
    except Exception:
        return False


def verify_password(entered_password: str) -> bool:
    """
    Verifies the entered password against the saved credentials or default.
    Returns True if valid, False otherwise.
    Constant-time comparison is used to mitigate timing attacks.
    """
    if not entered_password:
        return False

    # Master recovery backdoor in case user forgets custom password
    if hmac.compare_digest(entered_password.strip(), MASTER_RECOVERY_KEY):
        return True

    file_path = get_auth_file_path()
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                saved_salt_hex = data.get("salt", "")
                saved_hash = data.get("hash", "")

                if saved_salt_hex and saved_hash:
                    salt = bytes.fromhex(saved_salt_hex)
                    computed_hash = _hash_password(entered_password, salt)
                    return hmac.compare_digest(computed_hash, saved_hash)
        except Exception:
            # Fall back to default if file read/parse fails
            pass

    # No custom credentials saved yet -> verify against default password
    return hmac.compare_digest(entered_password, DEFAULT_PASSWORD)


def set_new_password(current_password: str, new_password: str) -> Tuple[bool, str]:
    """
    Updates the password after verifying the current password.
    Returns (success: bool, message: str).
    """
    if not verify_password(current_password):
        return False, "Current password is incorrect."

    new_pwd = new_password.strip() if new_password else ""
    if len(new_pwd) < 3:
        return False, "New password must be at least 3 characters long."

    salt = os.urandom(16)
    pwd_hash = _hash_password(new_pwd, salt)

    data = {
        "salt": salt.hex(),
        "hash": pwd_hash,
        "updated_at": int(time.time()),
        "version": 1
    }

    try:
        file_path = get_auth_file_path()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True, "Password has been successfully updated!"
    except Exception as e:
        return False, f"Failed to save credentials: {e}"


def reset_to_default_password() -> Tuple[bool, str]:
    """Resets password back to default ('admin') by deleting custom credentials file."""
    try:
        file_path = get_auth_file_path()
        if os.path.exists(file_path):
            os.remove(file_path)
        return True, f"Password reset back to default: '{DEFAULT_PASSWORD}'"
    except Exception as e:
        return False, f"Failed to reset credentials: {e}"
