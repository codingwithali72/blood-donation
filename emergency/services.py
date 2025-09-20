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
        """Send professional emergency SMS notification with distance information"""
        if not self.twilio_configured:
            logger.warning("Twilio not configured. SMS will be simulated.")
            return self._simulate_sms(emergency_request, hospitals)
        
        # Check if we've hit limits recently
        if self._check_recent_failures():
            logger.warning("Recent SMS failures detected. Checking account status...")
            return self._simulate_sms(emergency_request, hospitals)
        
        try:
            from twilio.rest import Client
            
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            
            # Create simple message
            message = self._create_simple_sms_message(emergency_request, hospitals)
            
            # Send SMS - try phone number first, fallback to verified caller ID
            from_number = settings.TWILIO_PHONE_NUMBER
            if not from_number:
                # Try to use verified caller ID as fallback
                try:
                    caller_ids = client.outgoing_caller_ids.list(limit=1)
                    if caller_ids:
                        from_number = caller_ids[0].phone_number
                        logger.info(f"Using verified caller ID as from number: {from_number}")
                except:
                    pass
            
            if not from_number:
                raise Exception("No Twilio phone number or verified caller ID available")
            
            message_response = client.messages.create(
                body=message,
                from_=from_number,
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
            error_message = str(e)
            logger.error(f"Error sending SMS: {error_message}")
            
            # Enhanced error handling for common Twilio issues
            if "exceeded" in error_message.lower():
                if "daily" in error_message.lower():
                    logger.warning("Twilio daily SMS limit reached. This is common with Trial accounts.")
                    print("\n*** TWILIO DAILY LIMIT REACHED ***")
                    print("Your Twilio Trial account has reached its daily SMS limit.")
                    print("Solutions:")
                    print("1. Wait for daily limit to reset (usually at midnight UTC)")
                    print("2. Upgrade to a paid Twilio account for higher limits")
                    print("3. Check Twilio Console for spending limits")
                    print("4. The system will continue to work, but SMS notifications are paused")
                    print("Current balance: Check your Twilio Console for balance info")
                else:
                    logger.warning("Twilio account limit exceeded (not daily limit)")
            elif "authentication" in error_message.lower():
                logger.error("Twilio authentication failed. Check credentials.")
            elif "phone number" in error_message.lower():
                logger.error("Phone number issue in Twilio request")
            else:
                logger.error(f"Unexpected Twilio error: {error_message}")
            
            # Log failed notification with enhanced error info
            EmergencyNotification.objects.create(
                request=emergency_request,
                notification_type='SMS',
                recipient=emergency_request.contact_phone,
                message=self._create_simple_sms_message(emergency_request, hospitals),
                status='FAILED',
                error_message=error_message[:500]  # Truncate very long error messages
            )
            
            return False
    
    def _create_simple_sms_message(self, emergency_request, hospitals):
        """Create SMS message matching user's exact format"""
        if not hospitals:
            return f"Sent from your Twilio trial account - No hospitals found with {emergency_request.blood_group} blood in your area. Contact local hospitals directly. Request ID: {str(emergency_request.request_id)[:8]}"
        
        # Get location name for dynamic area reference
        area_name = self._get_area_name(emergency_request)
        
        # Calculate distances and travel time
        primary_hospital = hospitals[0]
        if emergency_request.user_latitude and emergency_request.user_longitude:
            distance = primary_hospital.calculate_distance(
                float(emergency_request.user_latitude),
                float(emergency_request.user_longitude)
            )
            travel_time = int(distance * 4)  # Rough estimate: 4 minutes per km
        else:
            distance = 0.0
            travel_time = 5  # Default estimate
        
        # Build message exactly like user's sample
        message = f"Sent from your Twilio trial account - BLOOD AVAILABLE near {area_name}\n"
        message += f"{emergency_request.quantity_needed} bag {emergency_request.blood_group} found\n\n"
        
        # Primary hospital
        message += f"NEAREST HOSPITAL: {primary_hospital.name}\n"
        message += f"PHONE: {primary_hospital.emergency_phone}\n"
        message += f"ADDRESS: {primary_hospital.address}\n"
        message += f"DISTANCE: {distance:.1f}km (~{travel_time} minutes)\n\n"
        message += f"Contact: {primary_hospital.emergency_phone}\n\n"
        
        # Backup options (if available)
        if len(hospitals) > 1:
            message += "BACKUP OPTIONS:\n"
            for hospital in hospitals[1:3]:  # Next 2 hospitals
                if emergency_request.user_latitude and emergency_request.user_longitude:
                    backup_distance = hospital.calculate_distance(
                        float(emergency_request.user_latitude),
                        float(emergency_request.user_longitude)
                    )
                else:
                    backup_distance = 0.0
                
                message += f"{hospital.name} ({backup_distance:.1f}km) - {hospital.emergency_phone}\n"
            message += "\n"
        
        # Request ID and time
        request_id = str(emergency_request.request_id)[:8]  # Short ID like in sample
        current_time = emergency_request.created_at.strftime('%H:%M')
        message += f"Request ID: {request_id}\n"
        message += f"Time: {current_time} from {area_name}"
        
        return message
    
    def _get_area_name(self, emergency_request):
        """Get dynamic area name based on user location"""
        if not emergency_request.user_latitude or not emergency_request.user_longitude:
            return "your area"
        
        # Simple area detection based on coordinates
        lat = float(emergency_request.user_latitude)
        lng = float(emergency_request.user_longitude)
        
        # Mumbai area detection (you can expand this)
        if 18.9 <= lat <= 19.3 and 72.7 <= lng <= 73.2:
            if 18.9 <= lat <= 19.1 and 73.0 <= lng <= 73.2:
                return "Panvel area"
            elif 19.0 <= lat <= 19.2 and 72.8 <= lng <= 73.0:
                return "Mumbai Central area" 
            elif 19.1 <= lat <= 19.3 and 72.8 <= lng <= 73.0:
                return "Bandra-Andheri area"
            else:
                return "Mumbai area"
        else:
            return "your area"
    
    def send_emergency_email(self, emergency_request, hospitals):
        """Send professional emergency email notification with distance information"""
        try:
            subject = f"🚨 URGENT: Emergency Blood Request - {emergency_request.blood_group} ({emergency_request.quantity_needed} bags)"
            
            if not hospitals:
                message = self._create_no_hospitals_email(emergency_request)
            else:
                message = self._create_professional_email(emergency_request, hospitals)
            
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'emergency@bloodbank.com'),
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
    
    def _create_professional_email(self, emergency_request, hospitals):
        """Create professional email content with distance information"""
        # Calculate distances for hospitals
        hospital_distances = []
        for hospital in hospitals:
            if emergency_request.user_latitude and emergency_request.user_longitude:
                distance = hospital.calculate_distance(
                    float(emergency_request.user_latitude),
                    float(emergency_request.user_longitude)
                )
                hospital_distances.append((hospital, distance))
            else:
                hospital_distances.append((hospital, None))
        
        # Sort by distance if available
        hospital_distances.sort(key=lambda x: x[1] if x[1] is not None else float('inf'))
        
        message = f"""🚨 EMERGENCY BLOOD REQUEST - IMMEDIATE ACTION REQUIRED
===============================================================

Dear {emergency_request.contact_name or 'Emergency Contact'},

This is an URGENT notification regarding your emergency blood request.

📋 REQUEST DETAILS:
━━━━━━━━━━━━━━━━━━━
🩸 Blood Type Required: {emergency_request.blood_group}
📦 Quantity Needed: {emergency_request.quantity_needed} bags
🆔 Request ID: {emergency_request.request_id}
🕒 Request Time: {emergency_request.created_at.strftime('%H:%M on %B %d, %Y')}
📱 Contact Phone: {emergency_request.contact_phone}

🏥 AVAILABLE HOSPITALS (Ranked by Distance):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        
        # Add up to 5 hospitals with detailed information
        for i, (hospital, distance) in enumerate(hospital_distances[:5], 1):
            distance_text = f"{distance:.1f} km" if distance is not None else "Distance unknown"
            
            message += f"""🏥 #{i} - {hospital.name}
    📍 Distance: {distance_text}
    📞 Emergency Phone: {hospital.emergency_phone}
    📞 General Phone: {hospital.phone}
    🏠 Address: {hospital.address}, {hospital.city}
    ⏰ Operating Hours: {'24/7 Emergency Care' if hospital.operates_24x7 else 'Limited Hours'}

"""
        
        # Add additional hospitals count if more than 5
        if len(hospitals) > 5:
            message += f"➕ {len(hospitals)-5} additional hospitals available with {emergency_request.blood_group} blood."
        
        message += f"""

⚡ IMMEDIATE ACTION STEPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 📞 Call the NEAREST hospital immediately
2. 🆔 Quote your Request ID: {emergency_request.request_id}
3. 🩸 Confirm availability of {emergency_request.blood_group} blood ({emergency_request.quantity_needed} bags)
4. 🚗 Proceed to the hospital for immediate assistance

⚠️  IMPORTANT NOTES:
━━━━━━━━━━━━━━━━━━━━━
• Blood availability changes rapidly - call ahead to confirm
• Have proper identification and medical records ready
• In case of extreme emergency, call 108 (Emergency Services)
• This is a priority alert - hospitals have been notified

📞 EMERGENCY HELPLINE: 108 (National Emergency Number)
🌐 Track Status: Visit our emergency portal with Request ID

═══════════════════════════════════════════════════
Emergency Blood Bank Network
Saving Lives Through Rapid Blood Matching
🩸 Available 24/7 for Emergency Blood Requests
═══════════════════════════════════════════════════

This is an automated emergency alert. Please do not reply to this email.
For urgent assistance, contact the hospitals listed above directly.
"""
        
        return message
    
    def _create_no_hospitals_email(self, emergency_request):
        """Create email when no hospitals are available"""
        return f"""🚨 EMERGENCY BLOOD ALERT - NO IMMEDIATE MATCHES FOUND
════════════════════════════════════════════════════

Dear {emergency_request.contact_name or 'Emergency Contact'},

We regret to inform you that no hospitals in your immediate area currently have {emergency_request.blood_group} blood available in the quantity requested.

📋 YOUR REQUEST:
━━━━━━━━━━━━━━━━
🩸 Blood Type: {emergency_request.blood_group}
📦 Quantity: {emergency_request.quantity_needed} bags
🆔 Request ID: {emergency_request.request_id}
🕒 Time: {emergency_request.created_at.strftime('%H:%M on %B %d, %Y')}

⚡ IMMEDIATE ACTION REQUIRED:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 📞 Call 108 (National Emergency Services) IMMEDIATELY
2. 📋 Contact nearby hospitals directly (they may have updated stock)
3. 🏥 Consider expanding search radius to nearby cities
4. 🩸 Ask hospitals about compatible blood types as alternatives

📞 EMERGENCY CONTACTS:
━━━━━━━━━━━━━━━━━━━━━━
🚨 National Emergency: 108
🏥 Regional Blood Bank: [Contact your state blood bank]
🩸 Red Cross: [Local Red Cross chapter]

⚠️  Don't lose hope - blood availability changes rapidly.
Keep trying hospitals and emergency services.

═══════════════════════════════════════════════════
Emergency Blood Bank Network
Request ID: {emergency_request.request_id}
═══════════════════════════════════════════════════
"""
    
    def find_nearby_hospitals(self, latitude, longitude, blood_group):
        """Find nearby hospitals with required blood group"""
        from .models import EmergencyHospital
        
        hospitals = []
        all_hospitals = EmergencyHospital.objects.filter(
            is_active=True, 
            is_emergency_partner=True
        ).prefetch_related('hospital_blood_stock')
        
        for hospital in all_hospitals:
            # Check if hospital has the required blood type
            if hospital.has_sufficient_blood(blood_group, 1):
                distance = hospital.calculate_distance(latitude, longitude)
                hospitals.append({
                    'hospital': hospital,
                    'distance': distance,
                    'name': hospital.name,
                    'phone': hospital.phone,
                    'emergency_phone': hospital.emergency_phone,
                    'address': hospital.address,
                    'city': hospital.city
                })
        
        # Sort by distance and return top results
        hospitals.sort(key=lambda x: x['distance'])
        return hospitals
    
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
    
    def _check_recent_failures(self):
        """Check if there have been recent SMS failures due to limits"""
        try:
            from datetime import datetime, timedelta
            
            # Check last 3 failed notifications in the past hour
            one_hour_ago = datetime.now() - timedelta(hours=1)
            recent_failures = EmergencyNotification.objects.filter(
                notification_type='SMS',
                status='FAILED',
                created_at__gte=one_hour_ago,
                error_message__icontains='exceeded'
            ).count()
            
            if recent_failures >= 3:
                logger.warning(f"Found {recent_failures} recent SMS failures due to limits")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking recent failures: {e}")
            return False
    
    def get_sms_status_info(self):
        """Get SMS status and diagnostics info"""
        try:
            from twilio.rest import Client
            from datetime import datetime
            
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            
            # Get account info
            account = client.api.accounts(settings.TWILIO_ACCOUNT_SID).fetch()
            balance = client.api.accounts(settings.TWILIO_ACCOUNT_SID).balance.fetch()
            
            # Count recent notifications from our database
            today = datetime.now().date()
            today_notifications = EmergencyNotification.objects.filter(
                notification_type='SMS',
                created_at__date=today
            )
            
            return {
                'account_status': account.status,
                'account_type': account.type,
                'balance': f"${balance.balance} {balance.currency}",
                'sms_sent_today': today_notifications.filter(status='SENT').count(),
                'sms_failed_today': today_notifications.filter(status='FAILED').count(),
                'last_failure': today_notifications.filter(status='FAILED').order_by('-created_at').first()
            }
            
        except Exception as e:
            return {'error': str(e)}


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