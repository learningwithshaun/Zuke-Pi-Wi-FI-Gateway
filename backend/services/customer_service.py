import re
import secrets
import datetime
import logging
from typing import Tuple, Dict, Any, Optional
from backend.database.db import get_db
from backend.services.gateway_service import get_gateway_service

logger = logging.getLogger(__name__)
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class CustomerService:
    @staticmethod
    def validate_registration_input(name: Any, email: Any) -> Tuple[bool, Optional[str]]:
        if name is None or not isinstance(name, str) or not name.strip():
            return False, "Please enter your name."
        cleaned_name = name.strip()
        if len(cleaned_name) < 1 or len(cleaned_name) > 100:
            return False, "Please enter a valid name (1-100 characters)."

        if email is None or not isinstance(email, str) or not email.strip():
            return False, "Please enter your email address."
        cleaned_email = email.strip()
        if len(cleaned_email) > 150 or not EMAIL_REGEX.match(cleaned_email):
            return False, "Please enter a valid email address."

        return True, None

    @classmethod
    def register_customer(
        cls,
        name: str,
        email: str,
        ip_address: str,
        marketing_consent: bool = False,
        session_duration_hours: int = 8
    ) -> Tuple[bool, Dict[str, Any], int]:
        is_valid, error_msg = cls.validate_registration_input(name, email)
        if not is_valid:
            logger.warning("[CustomerService] Validation failed: %s", error_msg)
            return False, {"success": False, "error": error_msg}, 400

        clean_name = name.strip()
        clean_email = email.strip().lower()
        clean_ip = ip_address.strip() if ip_address else "127.0.0.1"

        try:
            db = get_db()
            cursor = db.cursor()

            cursor.execute("SELECT id FROM customers WHERE email = ?", (clean_email,))
            existing = cursor.fetchone()

            if existing:
                customer_id = existing['id']
                cursor.execute(
                    """
                    UPDATE customers
                    SET name = ?, marketing_consent = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (clean_name, 1 if marketing_consent else 0, customer_id)
                )
            else:
                cursor.execute(
                    "INSERT INTO customers (name, email, marketing_consent) VALUES (?, ?, ?)",
                    (clean_name, clean_email, 1 if marketing_consent else 0)
                )
                customer_id = cursor.lastrowid

            session_token = secrets.token_urlsafe(32)
            duration_seconds = session_duration_hours * 3600
            now = datetime.datetime.now(datetime.timezone.utc)
            expires_at = now + datetime.timedelta(seconds=duration_seconds)
            expires_at_iso = expires_at.isoformat()

            cursor.execute(
                """
                INSERT INTO access_sessions (
                    customer_id, ip_address, session_token, authenticated, expires_at
                ) VALUES (?, ?, ?, 1, ?)
                """,
                (customer_id, clean_ip, session_token, expires_at_iso)
            )
            db.commit()

            gateway = get_gateway_service()
            gateway.authorize_device(clean_ip, duration_seconds=duration_seconds)

            logger.info("[CustomerService] Registered customer %s (IP: %s)", clean_email, clean_ip)

            return True, {
                "success": True,
                "message": "Internet access granted",
                "session": {
                    "token": session_token,
                    "ip_address": clean_ip,
                    "authenticated": True,
                    "expires_at": expires_at_iso
                }
            }, 200

        except Exception as e:
            logger.exception("[CustomerService] Database error: %s", e)
            return False, {"success": False, "error": "Unable to complete registration. Please try again."}, 500

    @classmethod
    def get_status(cls, ip_address: str, session_token: Optional[str] = None) -> Dict[str, Any]:
        clean_ip = ip_address.strip() if ip_address else "127.0.0.1"
        gateway = get_gateway_service()
        is_gw_authorized = gateway.is_authorized(clean_ip)

        db = get_db()
        cursor = db.cursor()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if session_token:
            cursor.execute(
                """
                SELECT id, ip_address, expires_at, authenticated
                FROM access_sessions
                WHERE session_token = ? AND expires_at > ? AND authenticated = 1
                ORDER BY id DESC LIMIT 1
                """,
                (session_token, now_iso)
            )
        else:
            cursor.execute(
                """
                SELECT id, ip_address, expires_at, authenticated
                FROM access_sessions
                WHERE ip_address = ? AND expires_at > ? AND authenticated = 1
                ORDER BY id DESC LIMIT 1
                """,
                (clean_ip, now_iso)
            )

        row = cursor.fetchone()
        is_db_authenticated = row is not None

        result: Dict[str, Any] = {
            "authenticated": is_gw_authorized or is_db_authenticated,
            "ip_address": clean_ip
        }
        if row:
            result["expires_at"] = row["expires_at"]

        return result
