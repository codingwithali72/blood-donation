"""
Admin Notification System for Blood Requests
Sends notifications to a designated admin number when blood requests are made
"""

from django.conf import settings
import logging
from twilio.rest import Client

logger = logging.getLogger(__name__)

def send_admin_notification(emergency_request, hospitals=None):
    """
    Send notification to admin when a blood request is made
    Uses the EMERGENCY_NOTIFICATION_PHONE setting from .env
    """
    # Get admin notification number from settings
    admin_number = getattr(settings, 'EMERGENCY_NOTIFICATION_PHONE', '')
    
    if not admin_number:
        logger.warning("No admin notification number configured. Set EMERGENCY_NOTIFICATION_PHONE in .env")
        return False
    
    # Check if Twilio is configured
    if not (getattr(settings, 'TWILIO_ACCOUNT_SID', '') and 
            getattr(settings, 'TWILIO_AUTH_TOKEN', '') and 
            getattr(settings, 'TWILIO_PHONE_NUMBER', '')):
        logger.warning("Twilio not configured. Admin notification skipped.")
        return False
    
    try:
        # Create message for admin
        blood_info = f"{emergency_request.blood_group} ({emergency_request.quantity_needed} bags)"
        location_info = emergency_request.user_location_text or "Unknown location"
        time_info = emergency_request.created_at.strftime("%H:%M on %d-%b-%Y")
        
        message = (
            f"🚨 BLOOD REQUEST ALERT 🚨\n\n"
            f"Blood Type: {emergency_request.blood_group}\n"
            f"Quantity: {emergency_request.quantity_needed} bags\n"
            f"Location: {location_info}\n"
            f"Time: {time_info}\n"
            f"Contact: {emergency_request.contact_phone}\n"
            f"Request ID: {str(emergency_request.request_id)[:8]}"
        )
        
        # Add hospital information if available
        if hospitals and len(hospitals) > 0:
            message += f"\n\nNearest Hospital: {hospitals[0].name}"
            message += f"\nDistance: {hospitals[0].distance_km:.1f}km"
            message += f"\nPhone: {hospitals[0].emergency_phone}"
        
        # Send SMS via Twilio
        client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        
        message_response = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=admin_number
        )
        
        logger.info(f"Admin notification sent to {admin_number} for request {emergency_request.request_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending admin notification: {e}")
        return False