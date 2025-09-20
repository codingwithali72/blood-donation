from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging
from .models import EmergencyNotification

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for sending emergency notifications via SMS and Email"""
    
    def __init__(self):
        self.twilio_configured = bool(
            getattr(settings, 'TWILIO_ACCOUNT_SID', '') and
            getattr(settings, 'TWILIO_AUTH_TOKEN', '') and
            getattr(settings, 'TWILIO_PHONE_NUMBER', '')
        )
    
    def send_emergency_sms(self, emergency_request, hospitals):
        """Send emergency SMS notification"""
        if not self.twilio_configured:
            logger.warning("Twilio not configured. SMS will be simulated.")
            return self._simulate_sms(emergency_request, hospitals)
        
        try:
            # Import Twilio here to avoid dependency issues
            from twilio.rest import Client
            
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            
            # Create SMS message
            message = self._create_sms_message(emergency_request, hospitals)
            
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
                message=self._create_sms_message(emergency_request, hospitals),
                status='FAILED',
                error_message=str(e)
            )
            
            return False
    
    def send_emergency_email(self, emergency_request, hospitals):
        """Send emergency email notification"""
        try:
            # Create email content
            subject = f"🚨 Emergency Blood Alert: {emergency_request.blood_group} ({emergency_request.quantity_needed} bags)"
            
            # HTML email template
            html_message = render_to_string('emergency/email_templates/emergency_notification.html', {
                'emergency_request': emergency_request,
                'hospitals': hospitals,
                'blood_group': emergency_request.blood_group,
                'quantity': emergency_request.quantity_needed
            })
            
            # Plain text fallback
            plain_message = strip_tags(html_message)
            
            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=getattr(settings, 'EMERGENCY_NOTIFICATION_FROM', settings.DEFAULT_FROM_EMAIL),
                recipient_list=[emergency_request.contact_email],
                fail_silently=False,
            )
            
            # Log notification
            EmergencyNotification.objects.create(
                request=emergency_request,
                notification_type='EMAIL',
                recipient=emergency_request.contact_email,
                subject=subject,
                message=plain_message,
                status='SENT'
            )
            
            logger.info(f"Email sent successfully to {emergency_request.contact_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            
            # Log failed notification
            EmergencyNotification.objects.create(
                request=emergency_request,
                notification_type='EMAIL',
                recipient=emergency_request.contact_email,
                subject=f"Emergency Blood Alert: {emergency_request.blood_group}",
                message=self._create_email_message(emergency_request, hospitals),
                status='FAILED',
                error_message=str(e)
            )
            
            return False
    
    def send_no_hospitals_sms(self, emergency_request):
        """Send SMS when no hospitals are available"""
        if not self.twilio_configured:
            return self._simulate_no_hospitals_sms(emergency_request)
        
        try:
            from twilio.rest import Client
            
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            
            message = (f"🚨 BLOOD ALERT: Currently, no nearby hospitals have {emergency_request.quantity_needed} "
                      f"bag(s) of {emergency_request.blood_group} available. We're expanding the search radius "
                      f"and will notify you if stock becomes available. For urgent needs, call 108 or visit the "
                      f"nearest hospital directly. Request ID: {emergency_request.request_id}")
            
            message_response = client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=emergency_request.contact_phone
            )
            
            EmergencyNotification.objects.create(
                request=emergency_request,
                notification_type='SMS',
                recipient=emergency_request.contact_phone,
                message=message,
                status='SENT',
                provider_response=message_response.sid
            )
            
            return True
            
        except ImportError:
            return self._simulate_no_hospitals_sms(emergency_request)
        except Exception as e:
            logger.error(f"Error sending no-hospitals SMS: {e}")
            return False
    
    def send_no_hospitals_email(self, emergency_request):
        """Send email when no hospitals are available"""
        try:
            subject = f"🚨 Blood Search Alert: {emergency_request.blood_group} - No Immediate Availability"
            
            html_message = render_to_string('emergency/email_templates/no_hospitals_notification.html', {
                'emergency_request': emergency_request,
            })
            
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=getattr(settings, 'EMERGENCY_NOTIFICATION_FROM', settings.DEFAULT_FROM_EMAIL),
                recipient_list=[emergency_request.contact_email],
                fail_silently=False,
            )
            
            EmergencyNotification.objects.create(
                request=emergency_request,
                notification_type='EMAIL',
                recipient=emergency_request.contact_email,
                subject=subject,
                message=plain_message,
                status='SENT'
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending no-hospitals email: {e}")
            return False
    
    def _create_sms_message(self, emergency_request, hospitals):
        """Create SMS message content"""
        if not hospitals:
            return f"No hospitals found for {emergency_request.blood_group} ({emergency_request.quantity_needed} bags)"
        
        hospital = hospitals[0]  # Primary hospital
        distance = hospital.calculate_distance(
            float(emergency_request.user_latitude or 0),
            float(emergency_request.user_longitude or 0)
        ) if emergency_request.user_latitude else 0
        
        message = (
            f"🚨 EMERGENCY BLOOD ALERT\\n"
            f"{emergency_request.quantity_needed} bag(s) of {emergency_request.blood_group} available!\\n\\n"
            f"📍 {hospital.name}\\n"
            f"📞 {hospital.emergency_phone}\\n"
            f"📍 {hospital.address}\\n"
            f"🚗 {distance:.1f} km away\\n\\n"
            f"⏰ Contact immediately!\\n"
            f"Request ID: {emergency_request.request_id}"
        )
        
        if len(hospitals) > 1:
            message += f"\\n\\n+{len(hospitals)-1} more hospitals available"
        
        return message
    
    def _create_email_message(self, emergency_request, hospitals):
        """Create email message content"""
        message = f"Emergency blood request for {emergency_request.blood_group} ({emergency_request.quantity_needed} bags)\\n\\n"
        
        if hospitals:
            message += "Available hospitals:\\n"
            for i, hospital in enumerate(hospitals[:3], 1):
                distance = hospital.calculate_distance(
                    float(emergency_request.user_latitude or 0),
                    float(emergency_request.user_longitude or 0)
                ) if emergency_request.user_latitude else 0
                
                message += f"{i}. {hospital.name}\\n"
                message += f"   Phone: {hospital.emergency_phone}\\n"
                message += f"   Address: {hospital.address}\\n"
                message += f"   Distance: {distance:.1f} km\\n\\n"
        else:
            message += "No hospitals currently have the requested blood type available."
        
        return message
    
    def _simulate_sms(self, emergency_request, hospitals):
        """Simulate SMS sending for demo/development"""
        message = self._create_sms_message(emergency_request, hospitals)
        
        # Log as if sent successfully
        EmergencyNotification.objects.create(
            request=emergency_request,
            notification_type='SMS',
            recipient=emergency_request.contact_phone,
            message=message,
            status='SENT',
            provider_response='SIMULATED_SMS'
        )
        
        logger.info(f"SMS SIMULATED for {emergency_request.contact_phone}: {message}")
        return True
    
    def _simulate_no_hospitals_sms(self, emergency_request):
        """Simulate no-hospitals SMS for demo/development"""
        message = f"No hospitals found for {emergency_request.blood_group} ({emergency_request.quantity_needed} bags)"
        
        EmergencyNotification.objects.create(
            request=emergency_request,
            notification_type='SMS',
            recipient=emergency_request.contact_phone,
            message=message,
            status='SENT',
            provider_response='SIMULATED_SMS'
        )
        
        logger.info(f"No-hospitals SMS SIMULATED for {emergency_request.contact_phone}")
        return True


class LocationService:
    """Service for location-based operations"""
    
    @staticmethod
    def get_coordinates_from_address(address):
        """Get coordinates from address using geocoding service"""
        # This would integrate with Google Maps API or similar
        # For now, return None to use manual location input
        return None, None
    
    @staticmethod
    def get_address_from_coordinates(lat, lng):
        """Get address from coordinates using reverse geocoding"""
        # This would integrate with Google Maps API or similar
        return f"Coordinates: {lat}, {lng}"
    
    @staticmethod
    def calculate_distance(lat1, lng1, lat2, lng2):
        """Calculate distance between two points using Haversine formula"""
        from math import radians, cos, sin, asin, sqrt
        
        try:
            # Convert decimal degrees to radians
            lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
            
            # Haversine formula
            dlat = lat2 - lat1
            dlng = lng2 - lng1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
            c = 2 * asin(sqrt(a))
            
            # Radius of earth in kilometers
            r = 6371
            return c * r
        except (ValueError, TypeError):
            return float('inf')


class AnalyticsService:
    """Service for emergency system analytics"""
    
    @staticmethod
    def update_daily_analytics(date=None):
        """Update analytics for a specific date"""
        from django.utils import timezone
        from django.db.models import Count, Avg
        from .models import EmergencyRequest, EmergencyAnalytics
        
        if date is None:
            date = timezone.now().date()
        
        # Get requests for the date
        requests = EmergencyRequest.objects.filter(created_at__date=date)
        
        # Overall statistics
        total_requests = requests.count()
        successful_requests = requests.filter(status='COMPLETED').count()
        failed_requests = requests.filter(status='FAILED').count()
        
        # Calculate average response time
        completed_requests = requests.filter(
            status='COMPLETED',
            completed_at__isnull=False
        )
        
        response_times = []
        for req in completed_requests:
            time_diff = req.completed_at - req.created_at
            response_times.append(time_diff.total_seconds() / 60)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Update or create analytics record
        analytics, created = EmergencyAnalytics.objects.get_or_create(
            date=date,
            blood_group='',  # Overall stats
            city='',
            defaults={
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'avg_response_time': avg_response_time
            }
        )
        
        if not created:
            analytics.total_requests = total_requests
            analytics.successful_requests = successful_requests
            analytics.failed_requests = failed_requests
            analytics.avg_response_time = avg_response_time
            analytics.save()
        
        # Blood group specific analytics
        for blood_group, _ in EmergencyRequest.BLOOD_GROUPS:
            blood_requests = requests.filter(blood_group=blood_group)
            if blood_requests.exists():
                analytics, created = EmergencyAnalytics.objects.get_or_create(
                    date=date,
                    blood_group=blood_group,
                    city='',
                    defaults={
                        'demand_count': blood_requests.count()
                    }
                )
                if not created:
                    analytics.demand_count = blood_requests.count()
                    analytics.save()
        
        return True