"""
Authentication service for Linux VPN Gateway.
Implements PBKDF2-HMAC-SHA256 password hashing (Python stdlib, zero dependencies)
and secure token-based session management for single-admin appliance Web UI.
Supports first-run onboarding setup and password changes.
"""

import hashlib
import hmac
import json
import os
import platform
import secrets
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOCAL_CONFIG_DIR = BASE_DIR / "configs"
SYS_CONFIG_DIR = Path("/etc/vpn-gateway")

SESSION_TTL_SECONDS = 7 * 24 * 3600  # 7 days session lifetime


def get_config_dir() -> Path:
    """Determine active configuration directory (system or local dev)."""
    if platform.system() == "Linux" and SYS_CONFIG_DIR.exists():
        return SYS_CONFIG_DIR
    LOCAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return LOCAL_CONFIG_DIR


def get_auth_file() -> Path:
    return get_config_dir() / "auth.json"


# In-memory active session tokens: {token: {"username": "admin", "expires_at": float}}
_active_sessions: Dict[str, Dict[str, Any]] = {}


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations and random salt."""
    salt = secrets.token_hex(16)
    iterations = 100000
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations
    )
    return f"pbkdf2:sha256:{iterations}:{salt}:{derived.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify plain password against stored PBKDF2 hash."""
    try:
        parts = hashed.split(":")
        if len(parts) != 5:
            return False
        _, _, iterations_str, salt, target_hex = parts
        iterations = int(iterations_str)
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations
        )
        return hmac.compare_digest(derived.hex(), target_hex)
    except Exception:
        return False


def load_auth_record() -> Optional[Dict[str, Any]]:
    """Load credentials from auth.json."""
    auth_file = get_auth_file()
    if not auth_file.exists():
        return None
    try:
        with open(auth_file, "r") as f:
            return json.load(f)
    except Exception:
        return None


def save_auth_record(record: Dict[str, Any]) -> None:
    """Atomic write credentials with strict file permissions."""
    auth_file = get_auth_file()
    auth_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = auth_file.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(record, f, indent=2)
    os.replace(tmp, auth_file)
    try:
        os.chmod(auth_file, 0o600)
    except Exception:
        pass


def is_first_run() -> bool:
    """True if no admin password has been established yet."""
    record = load_auth_record()
    if not record or not record.get("password_hash"):
        return True
    return False


def setup_initial_password(password: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Set up the master admin password on first run. Returns (success, token, error)."""
    if len(password) < 6:
        return False, None, "Password must be at least 6 characters long."

    if not is_first_run():
        return False, None, "Initial setup has already been completed."

    hashed = hash_password(password)
    record = {
        "username": "admin",
        "password_hash": hashed,
        "created_at": time.time(),
        "last_login": time.time(),
    }
    save_auth_record(record)

    # Automatically issue session token
    token = create_session("admin")
    return True, token, None


def authenticate(password: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Verify admin login and issue session token."""
    record = load_auth_record()
    if not record or not record.get("password_hash"):
        return False, None, "Gateway is unconfigured. Please complete initial setup."

    if not verify_password(password, record["password_hash"]):
        return False, None, "Invalid admin password."

    # Update last login
    record["last_login"] = time.time()
    save_auth_record(record)

    token = create_session("admin")
    return True, token, None


def change_password(old_password: str, new_password: str) -> Tuple[bool, Optional[str]]:
    """Change current admin password."""
    if len(new_password) < 6:
        return False, "New password must be at least 6 characters long."

    record = load_auth_record()
    if not record or not record.get("password_hash"):
        return False, "Admin account not found."

    if not verify_password(old_password, record["password_hash"]):
        return False, "Current password is incorrect."

    record["password_hash"] = hash_password(new_password)
    record["password_updated_at"] = time.time()
    save_auth_record(record)
    return True, None


def create_session(username: str = "admin") -> str:
    """Create a new session token."""
    token = secrets.token_urlsafe(32)
    _active_sessions[token] = {
        "username": username,
        "expires_at": time.time() + SESSION_TTL_SECONDS,
    }
    return token


def verify_session(token: Optional[str]) -> bool:
    """Check if token is valid and unexpired."""
    if not token or token not in _active_sessions:
        return False

    session = _active_sessions[token]
    if time.time() > session.get("expires_at", 0):
        del _active_sessions[token]
        return False

    return True


def revoke_session(token: Optional[str]) -> None:
    """Invalidate active session."""
    if token and token in _active_sessions:
        del _active_sessions[token]


def get_auth_status(token: Optional[str] = None) -> Dict[str, Any]:
    """Return current auth state for UI display."""
    first_run = is_first_run()
    is_valid = verify_session(token) if token else False
    record = load_auth_record()

    return {
        "first_run": first_run,
        "authenticated": is_valid,
        "username": "admin",
        "created_at": record.get("created_at") if record else None,
        "last_login": record.get("last_login") if record else None,
    }
