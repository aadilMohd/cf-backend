import httpx
from app.config import settings

async def send_sms(phone_number: str, message: str) -> bool:
    """Sends an SMS via the configured OTP provider's general send API.
    Returns True on success, False on failure — callers decide how to handle failure."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.msg91.com/api/v5/flow/",  # adjust to your actual provider endpoint
                headers={"authkey": settings.otp_provider_api_key},
                json={
                    "mobiles": phone_number,
                    "message": message,
                },
                timeout=10.0,
            )
            return response.status_code == 200
    except httpx.RequestError:
        return False