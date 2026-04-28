"""Authentication handling for Garmin Connect.

Supports multiple authentication methods:
1. Existing tokens from GARMIN_TOKEN_DIR or ~/.garth/
2. Environment variables (GARMIN_EMAIL, GARMIN_PASSWORD)
3. Interactive prompt (CLI only)
"""

import os
from pathlib import Path
from typing import Callable, Optional

from garminconnect import Garmin


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


def get_token_dir() -> Path:
    """Get the token directory from environment or default."""
    env_dir = os.environ.get("GARMIN_TOKEN_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".garth"


def get_client(
    interactive: bool = False,
    prompt_credentials: Optional[Callable[[], tuple[str, str]]] = None,
    prompt_mfa: Optional[Callable[[], str]] = None,
) -> Garmin:
    """
    Get an authenticated Garmin Connect client.

    Authentication is attempted in this order:
    1. Resume from saved session tokens
    2. Use environment variables (GARMIN_EMAIL, GARMIN_PASSWORD)
    3. Interactive prompt (if enabled)

    Args:
        interactive: If True, allow interactive credential prompts
        prompt_credentials: Optional callback to get (email, password)
        prompt_mfa: Optional callback to get MFA code

    Returns:
        Authenticated Garmin client

    Raises:
        AuthenticationError: If all authentication methods fail
    """
    token_dir = get_token_dir()
    token_dir.mkdir(exist_ok=True)
    token_path = str(token_dir)

    # Try to resume from saved session
    token_file = token_dir / "garmin_tokens.json"
    if token_file.exists():
        try:
            client = Garmin()
            client.login(token_path)
            return client
        except Exception:
            pass  # Fall through to other methods

    # Try environment variables
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")

    if email and password:
        try:
            client = Garmin(email, password, prompt_mfa=prompt_mfa)
            client.login(token_path)
            return client
        except Exception as e:
            raise AuthenticationError(f"Authentication with environment credentials failed: {e}")

    # Interactive mode
    if interactive:
        if prompt_credentials:
            email, password = prompt_credentials()
        else:
            email = input("Email: ")
            password = input("Password: ")

        if not prompt_mfa:

            def prompt_mfa():
                return input("MFA code: ")

        try:
            client = Garmin(email, password, prompt_mfa=prompt_mfa)
            client.login(token_path)
            return client
        except Exception as e:
            raise AuthenticationError(f"Authentication failed: {e}")

    raise AuthenticationError(
        "No valid authentication found. "
        "Set GARMIN_EMAIL and GARMIN_PASSWORD environment variables, "
        "or ensure valid tokens exist in GARMIN_TOKEN_DIR or ~/.garth/"
    )
