import os
import logging

logger = logging.getLogger(__name__)

def send_sms_notification(phone_number: str, message: str) -> bool:
    """
    Dispatches SMS notifications.
    Supports environment gating for Twilio or MSG91 APIs.
    Falls back to mock console logs in MVP environments.
    """
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    msg91_auth_key = os.getenv("MSG91_AUTH_KEY")

    if twilio_sid and twilio_token:
        # Stub structure for Twilio request
        logger.info(f"[SMS Gateway - Twilio SID: {twilio_sid[:8]}...] Sending to {phone_number}: {message}")
        # Real integration would perform: requests.post(...)
        return True
    elif msg91_auth_key:
        # Stub structure for MSG91 request
        logger.info(f"[SMS Gateway - MSG91 Key: {msg91_auth_key[:8]}...] Sending to {phone_number}: {message}")
        # Real integration would perform: requests.post(...)
        return True
    else:
        # Default mock mode
        logger.info(f"[SMS Gateway - MOCK] Sending SMS to {phone_number}: {message}")
        return True
