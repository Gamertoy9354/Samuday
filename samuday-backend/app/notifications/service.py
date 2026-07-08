import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

async def send_sms_otp(phone_number: str, otp_code: str):
    """
    Dispatches a SMS containing verification OTP code.
    Mocks transmission via local console logging if settings.MOCK_OTP is enabled.
    """
    message = f"Your Samuday verification code is: {otp_code}. Valid for 5 minutes."
    
    if settings.MOCK_OTP:
        msg = f"\n========================================\n[SMS OTP MOCK] TO: {phone_number}\nMESSAGE: {message}\n========================================"
        logger.info(msg)
        print(msg)
    else:
        # Stub hook for production integration (e.g. MSG91, Twilio)
        logger.info(f"[SMS GATEWAY] Sending payload to external provider for: {phone_number}")
