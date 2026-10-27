import base64
import hashlib
import hmac
import secrets


ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 310_000


def hash_password(password: str) -> str:
    """Return a salted PBKDF2 hash suitable for database storage."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERATIONS,
    )
    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii")
    encoded_digest = base64.urlsafe_b64encode(digest).decode("ascii")
    return f"{ALGORITHM}${ITERATIONS}${encoded_salt}${encoded_digest}"


def is_password_hash(value: str) -> bool:
    return value.startswith(f"{ALGORITHM}$")


def verify_password(password: str, stored_value: str) -> bool:
    """Verify a password hash while allowing legacy plaintext records."""
    if not is_password_hash(stored_value):
        return hmac.compare_digest(
            password.encode("utf-8"),
            stored_value.encode("utf-8"),
        )

    try:
        algorithm, iterations_text, encoded_salt, encoded_digest = stored_value.split("$")
        if algorithm != ALGORITHM:
            return False
        iterations = int(iterations_text)
        if not 10_000 <= iterations <= 2_000_000:
            return False
        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected_digest = base64.urlsafe_b64decode(encoded_digest.encode("ascii"))
    except (ValueError, TypeError):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest)
