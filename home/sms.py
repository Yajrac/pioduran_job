"""One place for sending SMS (registration OTP and application updates).

Provider is chosen with SMS_PROVIDER in .env:
    SMS_PROVIDER=semaphore   (default)  needs SEMAPHORE_API_KEY
    SMS_PROVIDER=iprog                  needs IPROG_SMS_API_TOKEN

With DEBUG=True and OTP_DEV_MODE=True nothing is sent: the message is
printed in the runserver terminal instead.

send_sms() never raises; check result.ok.
"""
import logging
from dataclasses import dataclass

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

SEMAPHORE_URL = "https://api.semaphore.co/api/v4/messages"
IPROG_URL = "https://www.iprogsms.com/api/v1/sms_messages"
TIMEOUT = 15


@dataclass
class SMSResult:
    ok: bool
    provider: str
    detail: str = ""


def format_ph_mobile(phone):
    """09171234567 / +639171234567 -> 639171234567"""
    phone = (phone or "").strip().replace(" ", "").replace("-", "")
    if phone.startswith("+63"):
        phone = phone[1:]
    elif phone.startswith("09"):
        phone = "63" + phone[1:]
    return phone


def _dev_mode():
    return settings.DEBUG and getattr(settings, "OTP_DEV_MODE", False)


def _send_semaphore(number, message):
    api_key = getattr(settings, "SEMAPHORE_API_KEY", "")
    if not api_key:
        return SMSResult(False, "semaphore", "SEMAPHORE_API_KEY is not set.")
    data = {"apikey": api_key, "number": number, "message": message}
    sender = getattr(settings, "SEMAPHORE_SENDER_NAME", "")
    if sender:
        data["sendername"] = sender
    response = requests.post(SEMAPHORE_URL, data=data, timeout=TIMEOUT)
    # Success is a JSON list of queued messages; errors come back as an object.
    try:
        body = response.json()
    except ValueError:
        body = None
    ok = response.status_code in (200, 201) and isinstance(body, list) and bool(body)
    return SMSResult(ok, "semaphore", "" if ok else f"HTTP {response.status_code}: {response.text[:300]}")


def _send_iprog(number, message):
    token = getattr(settings, "IPROG_SMS_API_TOKEN", "")
    if not token:
        return SMSResult(False, "iprog", "IPROG_SMS_API_TOKEN is not set.")
    response = requests.post(IPROG_URL, json={"api_token": token, "phone_number": number, "message": message},
                             timeout=TIMEOUT)
    ok = response.status_code in (200, 201)
    return SMSResult(ok, "iprog", "" if ok else f"HTTP {response.status_code}: {response.text[:300]}")


PROVIDERS = {"semaphore": _send_semaphore, "iprog": _send_iprog}


def send_sms(phone, message):
    provider = getattr(settings, "SMS_PROVIDER", "semaphore")
    if _dev_mode():
        print(f"[DEV SMS - not sent] to {phone}: {message}", flush=True)
        return SMSResult(True, "dev")
    sender = PROVIDERS.get(provider)
    if sender is None:
        result = SMSResult(False, provider, f"Unknown SMS_PROVIDER '{provider}'.")
    else:
        try:
            result = sender(format_ph_mobile(phone), message)
        except requests.RequestException as error:
            result = SMSResult(False, provider, f"Connection error: {error}")
    if not result.ok:
        logger.warning("SMS not sent via %s: %s", result.provider, result.detail)
    return result
