from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from .models import EmergencyNotification
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    """Simple notification service - back to basics"""
    
    def __init__(self):
        self.twilio_configured = bool(
            getattr(settings, 'TWILIO_ACCOUNT_SID', '') and
            getattr(settings, 'TWILIO_AUTH_TOKEN', '') and
            getattr(settings, 'TWILIO_PHONE_NUMBER', '')
        )
    
    def send_emergency_sms(self, emergency_request, hospitals):
        """Send simple emergency SMS notification"""
        if not self.twilio_configured:
            logger.warning("Twilio not configured. SMS will be simulated.")
            return self._simulate_sms(emergency_request, hospitals)
        
        try:
            from twilio.rest import Client
            
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            
            # Create simple message
            message = self._create_simple_sms_message(emergency_request, hospitals)
            
            # Send SMS
            message_response = client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=emergency_request.contact_phone
            )
            
            # Log notification
            EmergencyNotification.objects.create(
                request=emergency_request,
                notification_type='SMS',
                recipient=emergency_request.contact_phone,
                message=message,
                status='SENT',
                provider_response=message_response.sid
            )
            
            logger.info(f"SMS sent successfully to {emergency_request.contact_phone}")
            return True
            
        except ImportError:
            logger.warning("Twilio library not installed. SMS simulated.")
            return self._simulate_sms(emergency_request, hospitals)
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            
            # Log failed notification
            EmergencyNotification.objects.create(
                request=emergency_request,
                notification_type='SMS',
                recipient=emergency_request.contact_phone,
                message=self._create_simple_sms_message(emergency_request, hospitals),
                status='FAILED',
                error_message=str(e)
            )
            
            return False
    
    def _create_simple_sms_message(self, emergency_request, hospitals):
        """Create simple SMS message - back to basics"""
        if not hospitals:
            return f"No hospitals found for {emergency_request.blood_group} ({emergency_request.quantity_needed} bags). Please contact nearby hospitals directly."
        
        hospital = hospitals[0]  # First hospital
        
        # Simple message format
        message = (
            f"EMERGENCY BLOOD REQUEST\n"
            f"Blood Type: {emergency_request.blood_group}\n"
            f"Quantity: {emergency_request.quantity_needed} bags\n\n"
            f"NEAREST HOSPITAL:\n"
            f"{hospital.name}\n"
            f"Phone: {hospital.emergency_phone}\n"
            f"Address: {hospital.address}\n\n"
            f"Request ID: {emergency_request.request_id}\n"
            f"Contact hospital immediately!"
        )
        
        if len(hospitals) > 1:
            message += f"\n\n{len(hospitals)-1} more hospitals available."
        
        return message
    
    def send_emergency_email(self, emergency_request, hospitals):
        """Send simple emergency email notification"""
        try:
            subject = f"Emergency Blood Alert: {emergency_request.blood_group}"
            
            # Simple email content
            message = f"""
Emergency Blood Request

Blood Type: {emergency_request.blood_group}
Quantity: {emergency_request.quantity_needed} bags
Request ID: {emergency_request.request_id}

"""
            
            if hospitals:
                message += "Available Hospitals:\n\n"
                for i, hospital in enumerate(hospitals[:3], 1):
                    message += f"{i}. {hospital.name}\n"
                    message += f"   Phone: {hospital.emergency_phone}\n"
                    message += f"   Address: {hospital.address}\n\n"
            else:
                message += "No hospitals currently have the requested blood type available."
            
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@emergency.com'),
                recipient_list=[emergency_request.contact_email],
                fail_silently=False,
            )
            
            # Log notification
            EmergencyNotification.objects.create(
                request=emergency_request,
                notification_type='EMAIL',
                recipient=emergency_request.contact_email,
                subject=subject,
                message=message,
                status='SENT'
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def _simulate_sms(self, emergency_request, hospitals):
        """Simulate SMS sending for development"""
        message = self._create_simple_sms_message(emergency_request, hospitals)
        
        # Log as if sent successfully
        EmergencyNotification.objects.create(
            request=emergency_request,
            notification_type='SMS',
            recipient=emergency_request.contact_phone,
            message=message,
            status='SENT',
            provider_response='SIMULATED'
        )
        
        logger.info(f"SMS SIMULATED for {emergency_request.contact_phone}")
        print(f"\n=== SIMULATED SMS ===\nTo: {emergency_request.contact_phone}\n{message}\n=== END ===\n")
        return True


class LocationService:
    """Simple location service"""
    
    @staticmethod
    def get_coordinates_from_address(address):
        """Simple coordinate lookup"""
        return None, None
    
    @staticmethod
    def get_address_from_coordinates(lat, lng):
        """Simple address lookup"""
        return f"Coordinates: {lat}, {lng}"
    
    @staticmethod
    def calculate_distance(lat1, lng1, lat2, lng2):
        """Calculate distance using Haversine formula"""
        from math import radians, cos, sin, asin, sqrt
        
        try:
            # Convert decimal degrees to radians
            lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
            
            # Haversine formula
            dlng = lng2 - lng1
            dlat = lat2 - lat1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
            c = 2 * asin(sqrt(a))
            r = 6371  # Radius of earth in kilometers
            
            return c * r
            
        except (ValueError, TypeError):
            return 0


# Simple factory functions
def get_notification_service():
    """Get notification service instance"""
    return NotificationService()

def get_location_service():
    """Get location service instance"""
    return LocationService()