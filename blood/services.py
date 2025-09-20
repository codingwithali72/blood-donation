import math
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .models import Hospital, HospitalBloodStock
import logging

logger = logging.getLogger(__name__)

class LocationService:
    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """
        Calculate the great circle distance between two points 
        on the earth (specified in decimal degrees)
        """
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Radius of earth in kilometers
        return c * r
    
    @staticmethod
    def find_nearby_hospitals_with_blood(user_lat, user_lon, blood_group, radius_km=50):
        """
        Find hospitals within radius that have the required blood group
        """
        nearby_hospitals = []
        
        hospitals = Hospital.objects.filter(
            blood_bank_available=True,
            is_partner=True,
            latitude__isnull=False,
            longitude__isnull=False
        )
        
        for hospital in hospitals:
            distance = LocationService.calculate_distance(
                user_lat, user_lon, 
                float(hospital.latitude), float(hospital.longitude)
            )
            
            if distance <= radius_km and hospital.has_blood_type(blood_group):
                nearby_hospitals.append({
                    'hospital': hospital,
                    'distance': round(distance, 2),
                    'units_available': hospital.get_blood_units(blood_group)
                })
        
        # Sort by distance
        nearby_hospitals.sort(key=lambda x: x['distance'])
        return nearby_hospitals

class SMSService:
    @staticmethod
    def send_sms(phone_number, message):
        """
        Send SMS using Twilio (requires twilio package)
        """
        try:
            # Import twilio only when needed to avoid dependency issues
            from twilio.rest import Client
            
            account_sid = settings.TWILIO_ACCOUNT_SID
            auth_token = settings.TWILIO_AUTH_TOKEN
            from_phone = settings.TWILIO_PHONE_NUMBER
            
            if not account_sid or not auth_token or not from_phone:
                logger.warning("Twilio credentials not configured")
                return False
            
            client = Client(account_sid, auth_token)
            
            message = client.messages.create(
                body=message,
                from_=from_phone,
                to=phone_number
            )
            
            logger.info(f"SMS sent successfully to {phone_number}: {message.sid}")
            return True
            
        except ImportError:
            logger.error("Twilio package not installed. Please install: pip install twilio")
            return False
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
            return False

class NotificationService:
    @staticmethod
    def send_blood_availability_notification(user, blood_group, nearby_hospitals):
        """
        Send email and SMS notification about blood availability
        """
        if not nearby_hospitals:
            return False
        
        nearest_hospital = nearby_hospitals[0]
        hospital = nearest_hospital['hospital']
        distance = nearest_hospital['distance']
        units = nearest_hospital['units_available']
        
        # Email notification
        try:
            subject = f"Blood Available: {blood_group} at {hospital.name}"
            context = {
                'user': user,
                'blood_group': blood_group,
                'hospital': hospital,
                'distance': distance,
                'units': units,
                'all_hospitals': nearby_hospitals[:5]  # Top 5 nearest
            }
            
            html_message = render_to_string('blood/email/blood_availability.html', context)
            plain_message = f"""
Blood Available!

Dear {user.get_full_name() or user.username},

Good news! We found {blood_group} blood available at nearby hospitals:

Nearest Hospital: {hospital.name}
Distance: {distance} km
Available Units: {units} bags
Contact: {hospital.emergency_contact}
Address: {hospital.address}, {hospital.city}

Please contact the hospital immediately for urgent requirements.

Best regards,
Blood Bank Management System
            """.strip()
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            # SMS notification if user has mobile number
            mobile_number = None
            try:
                # Try to get mobile from patient or donor profile
                if hasattr(user, 'patient'):
                    mobile_number = user.patient.mobile
                elif hasattr(user, 'donor'):
                    mobile_number = user.donor.mobile
            except:
                pass
            
            if mobile_number:
                sms_message = f"""
Blood Available!
{blood_group} blood found at {hospital.name} ({distance}km away).
{units} bags available.
Contact: {hospital.emergency_contact}
                """.strip()
                
                SMSService.send_sms(mobile_number, sms_message)
            
            logger.info(f"Blood availability notification sent to {user.username}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send blood availability notification: {str(e)}")
            return False

class BloodRequestService:
    @staticmethod
    def process_blood_request(blood_request):
        """
        Process blood request and find nearby hospitals
        """
        if not blood_request.latitude or not blood_request.longitude:
            return None
        
        nearby_hospitals = LocationService.find_nearby_hospitals_with_blood(
            float(blood_request.latitude),
            float(blood_request.longitude),
            blood_request.bloodgroup
        )
        
        if nearby_hospitals:
            # Get user from request
            user = None
            if blood_request.request_by_patient:
                user = blood_request.request_by_patient.user
            elif blood_request.request_by_donor:
                user = blood_request.request_by_donor.user
            
            if user:
                NotificationService.send_blood_availability_notification(
                    user, blood_request.bloodgroup, nearby_hospitals
                )
        
        return nearby_hospitals