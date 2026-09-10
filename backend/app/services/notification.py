import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger("oasis.notification")


class NotificationService:
    """
    Decoupled asynchronous notification task simulator for SMS (Twilio) and Email (SendGrid).
    Dispatches notifications non-blockingly via FastAPI BackgroundTasks or asyncio tasks.
    """

    @staticmethod
    async def dispatch_sms(phone_number: str, message: str) -> Dict[str, Any]:
        """Simulates Twilio SMS delivery with network latency."""
        await asyncio.sleep(0.05)  # Simulate network hop
        payload = {
            "channel": "SMS_TWILIO",
            "recipient": phone_number,
            "status": "SENT",
            "message_id": f"SM_{int(asyncio.get_event_loop().time() * 1000)}",
            "body": message
        }
        logger.info(f"[NOTIF-SMS] Sent confirmation to {phone_number}: '{message}'")
        return payload

    @staticmethod
    async def dispatch_email(recipient_name: str, email: str, subject: str, body: str) -> Dict[str, Any]:
        """Simulates SendGrid Email dispatch with network latency."""
        await asyncio.sleep(0.05)
        payload = {
            "channel": "EMAIL_SENDGRID",
            "recipient_name": recipient_name,
            "recipient_email": email,
            "subject": subject,
            "status": "DELIVERED",
            "message_id": f"SG_{int(asyncio.get_event_loop().time() * 1000)}"
        }
        logger.info(f"[NOTIF-EMAIL] Delivered email to {email} ('{subject}')")
        return payload

    @classmethod
    async def send_reservation_confirmation(
        cls,
        customer_name: str,
        customer_phone: str,
        restaurant_name: str,
        table_number: str,
        reservation_time: str,
        party_size: int,
        ref_id: int
    ) -> None:
        """Asynchronously dispatches both SMS and Email confirmations."""
        sms_body = (
            f"Oasis Confirmation #{ref_id}: Table {table_number} reserved at {restaurant_name} "
            f"for {party_size} guests on {reservation_time}."
        )
        email_body = (
            f"Dear {customer_name},\n\n"
            f"Your reservation at {restaurant_name} is confirmed!\n"
            f"- Table: {table_number}\n"
            f"- Time: {reservation_time}\n"
            f"- Party Size: {party_size}\n"
            f"Reference ID: OAS-{ref_id}\n\n"
            f"Thank you for booking with Oasis."
        )

        dummy_email = f"{customer_name.lower().replace(' ', '.')}@example.com"
        await asyncio.gather(
            cls.dispatch_sms(customer_phone, sms_body),
            cls.dispatch_email(customer_name, dummy_email, f"Confirmed: {restaurant_name} Table Booking", email_body),
            return_exceptions=True
        )


notification_service = NotificationService()
