import base64
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import requests

from _setting.models import XenditSetting


class XenditError(Exception):
    """Base exception for Xendit integration failures."""


class XenditConfigurationError(XenditError):
    pass


class XenditAPIError(XenditError):
    pass


class XenditService:
    timeout = (5, 20)

    @classmethod
    def get_setting(cls):
        setting = XenditSetting.load()
        if not setting.is_active:
            raise XenditConfigurationError("Xendit is not active.")
        if not setting.api_key or not setting.api_url:
            raise XenditConfigurationError("Xendit API key and API URL are required.")
        return setting

    @staticmethod
    def _headers(api_key):
        encoded = base64.b64encode(f"{api_key}:".encode()).decode()
        return {"Authorization": f"Basic {encoded}", "Content-Type": "application/json"}

    @classmethod
    def _request(cls, method, url, *, api_key, payload=None):
        try:
            response = requests.request(
                method,
                url,
                json=payload,
                headers=cls._headers(api_key),
                timeout=cls.timeout,
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise XenditAPIError("Xendit returned an invalid JSON object.")
            return data
        except requests.RequestException as exc:
            status = getattr(exc.response, "status_code", None)
            detail = ""
            if exc.response is not None:
                try:
                    error = exc.response.json()
                    code = error.get("error_code")
                    message = error.get("message")
                    detail = ": ".join(str(value) for value in (code, message) if value)
                except (ValueError, AttributeError):
                    pass
            suffix = f": {detail}" if detail else "."
            raise XenditAPIError(
                f"Xendit request failed{f' ({status})' if status else ''}{suffix}"
            ) from exc
        except ValueError as exc:
            raise XenditAPIError("Xendit returned invalid JSON.") from exc

    @classmethod
    def create_invoice(
        cls,
        reference_id,
        amount,
        description,
        invoice_duration=None,
        currency="IDR",
        country="ID",
        success_return_url=None,
        cancel_return_url=None,
        allowed_payment_channels=None,
    ):
        setting = cls.get_setting()
        duration = invoice_duration or setting.session_duration
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=duration)).isoformat().replace("+00:00", "Z")
        decimal_amount = Decimal(str(amount))
        if decimal_amount <= 0 or decimal_amount != decimal_amount.to_integral_value():
            raise XenditAPIError("IDR payment amount must be a positive whole number.")
        payload = {
            "reference_id": reference_id,
            "session_type": "PAY",
            "mode": "PAYMENT_LINK",
            "amount": int(decimal_amount),
            "currency": currency,
            "country": country,
            "description": description,
            "expires_at": expires_at,
        }
        if success_return_url:
            payload["success_return_url"] = success_return_url
        if cancel_return_url:
            payload["cancel_return_url"] = cancel_return_url
        if allowed_payment_channels:
            payload["allowed_payment_channels"] = allowed_payment_channels
        return cls._request(
            "POST", f"{setting.api_url.rstrip('/')}/sessions", api_key=setting.api_key, payload=payload
        )

    @classmethod
    def get_session_status(cls, session_id):
        setting = cls.get_setting()
        return cls._request(
            "GET", f"{setting.api_url.rstrip('/')}/sessions/{session_id}", api_key=setting.api_key
        )
