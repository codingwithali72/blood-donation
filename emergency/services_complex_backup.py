from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
import logging
from .models import EmergencyNotification
from .location_utils import get_location_service, get_hospital_finder

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for sending emergency notifications via SMS and Email"""
    
    def __init__(self):
        self.twilio_configured = bool(
            getattr(settings, 'TWILIO_ACCOUNT_SID', '') and
            getattr(settings, 'TWILIO_AUTH_TOKEN', '') and
            getattr(settings, 'TWILIO_PHONE_NUMBER', '')
        )
    
    def send_emergency_sms(self, emergency_request, hospitals=None):
        """Send emergency SMS notification with enhanced location context"""
        if not self.twilio_configured:
            logger.warning("Twilio not configured. SMS will be simulated.")
            return self._simulate_sms(emergency_request, hospitals)
        
        try:
            # Import Twilio here to avoid dependency issues
            from twilio.rest import Client
            
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN,
                timeout=5  # 5 second timeout
            )
            
            # Get enhanced hospital information if not provided
            if hospitals is None:
                hospital_finder = get_hospital_finder()
                hospital_context = hospital_finder.find_nearby_hospitals_with_context(emergency_request)
                hospitals = [info['hospital'] for info in hospital_context]
            else:
                # Convert old format to new format for compatibility
                hospital_finder = get_hospital_finder()
                hospital_context = hospital_finder.find_nearby_hospitals_with_context(emergency_request)
            
            # Create enhanced SMS message
            message = self._create_enhanced_sms_message(emergency_request, hospital_context if hospitals else [])
            
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
            
            logger.info(f"Enhanced SMS sent successfully to {emergency_request.contact_phone}")
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
                message=self._create_enhanced_sms_message(emergency_request, []),
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
                settings.TWILIO_AUTH_TOKEN,
                timeout=5  # 5 second timeout
            )
            
            message = (f"BLOOD SEARCH ALERT: Currently, no nearby hospitals have {emergency_request.quantity_needed} "
                      f"bag {emergency_request.blood_group} available. We're expanding the search radius "
                      f"and will notify you if stock becomes available. For urgent needs, call 108 or visit the "
                      f"nearest hospital directly. Request ID: {str(emergency_request.request_id)[:8]}")
            
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
    
    def _create_enhanced_sms_message(self, emergency_request, hospital_context):
        """Create carrier-friendly SMS message that avoids spam filtering"""
        if not hospital_context:
            return self._create_no_hospitals_sms_message(emergency_request)
        
        primary_hospital_info = hospital_context[0]
        hospital = primary_hospital_info['hospital']
        
        # Create carrier-friendly version (minimal emojis, simple text)
        return self._create_carrier_friendly_sms(emergency_request, hospital_context)
        
        # Get user location context for personalized message
        user_area = "your area"
        if emergency_request.user_latitude and emergency_request.user_longitude:
            try:
                location_service = get_location_service()
                address = location_service.reverse_geocode(
                    float(emergency_request.user_latitude),
                    float(emergency_request.user_longitude)
                )
                if address and "Coordinates:" not in address:
                    # Extract neighborhood/area from address
                    area_parts = address.split(',')
                    user_area = area_parts[0].strip() if area_parts else "your location"
            except:
                pass
        elif emergency_request.user_location_text:
            user_area = emergency_request.user_location_text
        
        # Calculate time-sensitive messaging
        current_hour = timezone.now().hour
        time_context = "immediately" if 6 <= current_hour <= 22 else "urgently (after hours)"
        
        # Start with carrier-friendly alert (no emojis)
        message_parts = [
            f"BLOOD AVAILABLE near {user_area}",
            f"{emergency_request.quantity_needed} bag {emergency_request.blood_group} found",
            ""
        ]
        
        # Primary hospital - NEAREST with all contact details
        distance_km = primary_hospital_info.get('distance_km', 0)
        travel_time = primary_hospital_info.get('travel_time', f"{distance_km * 3:.0f}min")
        available_bags = primary_hospital_info.get('available_stock', {}).get(emergency_request.blood_group, "Available")
        
        message_parts.extend([
            f"NEAREST HOSPITAL: {hospital.name}",
            f"PHONE: {hospital.emergency_phone}",
            f"ADDRESS: {hospital.address[:50]}{'...' if len(hospital.address) > 50 else ''}",
            f"DISTANCE: {distance_km}km ({travel_time})",
            f"STOCK: {available_bags} {emergency_request.blood_group} bags",
            ""
        ])
        
        # Add emergency instructions based on urgency (carrier-friendly)
        urgency_instructions = {
            "CRITICAL": f"CRITICAL: Call {hospital.emergency_phone} NOW! Mention emergency blood request.",
            "URGENT": f"URGENT: Contact {hospital.emergency_phone} {time_context}",
            "ROUTINE": f"ROUTINE: Call {hospital.emergency_phone} during business hours"
        }
        
        message_parts.append(urgency_instructions.get(emergency_request.urgency, urgency_instructions["URGENT"]))
        message_parts.append("")
        
        # Add backup hospitals if available
        if len(hospital_context) > 1:
            message_parts.append(f"BACKUP OPTIONS ({len(hospital_context)-1} more):")
            for i, hospital_info in enumerate(hospital_context[1:3], 2):  # Show next 2 hospitals
                alt_hospital = hospital_info['hospital']
                alt_distance = hospital_info.get('distance_km', 0)
                message_parts.append(
                    f"{i}. {alt_hospital.name} ({alt_distance}km) - {alt_hospital.emergency_phone}"
                )
            message_parts.append("")
        
        # Add location-specific directions and tips
        if distance_km <= 5:
            message_parts.append("Very close! Drive carefully - blood emergency.")
        elif distance_km <= 15:
            message_parts.append(f"{travel_time} drive from {user_area}. Traffic may vary.")
        else:
            message_parts.append(f"{distance_km}km away. Consider closest option or call ambulance.")
        
        # Add request tracking and timestamp
        search_time = timezone.now().strftime('%H:%M')
        message_parts.extend([
            "",
            f"Request ID: {str(emergency_request.request_id)[:8]}",
            f"Found at {search_time} from {user_area}",
            "Reply HELP for more options"
        ])
        
        return "\n".join(message_parts)
    
    def _create_no_hospitals_sms_message(self, emergency_request):
        """Create dynamic SMS message when no hospitals are found based on user location"""
        location_service = get_location_service()
        
        # Get precise location context for personalized messaging
        user_area = "your area"
        search_radius = "nearby"
        
        if emergency_request.user_latitude and emergency_request.user_longitude:
            try:
                address = location_service.reverse_geocode(
                    float(emergency_request.user_latitude),
                    float(emergency_request.user_longitude)
                )
                if address and "Coordinates:" not in address:
                    area_parts = address.split(',')
                    user_area = area_parts[0].strip() if area_parts else "your location"
                    # Suggest wider search based on location
                    if len(area_parts) > 1:
                        broader_area = area_parts[1].strip()
                        search_radius = f"{user_area} and {broader_area}"
            except:
                pass
        elif emergency_request.user_location_text:
            user_area = emergency_request.user_location_text
            search_radius = f"{user_area} and surrounding areas"
        
        # Time-based urgency messaging
        current_hour = timezone.now().hour
        is_business_hours = 8 <= current_hour <= 18
        
        urgency_message = (
            "CALL 108 NOW - Services active 24/7" 
            if not is_business_hours 
            else "Call 108 OR contact hospitals directly"
        )
        
        message_parts = [
            f"NO {emergency_request.blood_group} FOUND in {user_area}",
            f"Searched for {emergency_request.quantity_needed} bag in immediate area",
            ""
        ]
        
        # Location-specific alternative actions
        if "mumbai" in user_area.lower():
            message_parts.extend([
                "TRY THESE MUMBAI HOSPITALS:",
                "KEM Hospital: +91-22-24136051",
                "Sion Hospital: +91-22-24076901",
                "Tata Memorial: +91-22-24177000",
                ""
            ])
        elif "delhi" in user_area.lower():
            message_parts.extend([
                "TRY THESE DELHI HOSPITALS:",
                "AIIMS: +91-11-26588500",
                "Safdarjung: +91-11-26165060",
                "GTB Hospital: +91-11-22590909",
                ""
            ])
        elif "bangalore" in user_area.lower() or "bengaluru" in user_area.lower():
            message_parts.extend([
                "TRY THESE BANGALORE HOSPITALS:",
                "Victoria Hospital: +91-80-26700447",
                "Bowring Hospital: +91-80-25588051",
                "KC General: +91-80-26842435",
                ""
            ])
        else:
            message_parts.extend([
                f"EXPANDING SEARCH to {search_radius}...",
                "Visit your nearest government hospital",
                "Ask for blood bank or transfusion center",
                ""
            ])
        
        # Add emergency alternatives with urgency context
        message_parts.extend([
            urgency_message,
            "Don't delay - time is critical!",
            "",
            f"Request: {str(emergency_request.request_id)[:8]}",
            f"Searched from: {user_area}",
            f"{timezone.now().strftime('%H:%M')} | We'll keep searching"
        ])
        
        return "\n".join(message_parts)
    
    def _create_carrier_friendly_sms(self, emergency_request, hospital_context):
        """Create SMS message optimized to avoid carrier spam filtering"""
        primary_hospital_info = hospital_context[0]
        hospital = primary_hospital_info['hospital']
        
        # Get user location context
        user_area = "your area"
        if emergency_request.user_latitude and emergency_request.user_longitude:
            try:
                location_service = get_location_service()
                address = location_service.reverse_geocode(
                    float(emergency_request.user_latitude),
                    float(emergency_request.user_longitude)
                )
                if address and "Coordinates:" not in address:
                    area_parts = address.split(',')
                    user_area = area_parts[0].strip() if area_parts else "your location"
            except:
                pass
        elif emergency_request.user_location_text:
            user_area = emergency_request.user_location_text
        
        # Simple, carrier-friendly format (no emojis, minimal formatting)
        distance_km = primary_hospital_info.get('distance_km', 0)
        travel_time = primary_hospital_info.get('travel_time', f"{distance_km * 3:.0f}min")
        
        message_parts = [
            f"BLOOD AVAILABLE near {user_area}",
            f"{emergency_request.quantity_needed} bag {emergency_request.blood_group} found",
            "",
            f"NEAREST HOSPITAL: {hospital.name}",
            f"PHONE: {hospital.emergency_phone}",
            f"ADDRESS: {hospital.address[:80]}",
            f"DISTANCE: {distance_km}km ({travel_time})",
            ""
        ]
        
        # Add urgency without medical keywords
        if emergency_request.urgency == 'CRITICAL':
            message_parts.append(f"URGENT: Call {hospital.emergency_phone} immediately")
        else:
            message_parts.append(f"Contact: {hospital.emergency_phone}")
        
        # Add backup hospitals if available
        if len(hospital_context) > 1:
            message_parts.append("")
            message_parts.append("BACKUP OPTIONS:")
            for i, hospital_info in enumerate(hospital_context[1:3], 2):
                alt_hospital = hospital_info['hospital']
                alt_distance = hospital_info.get('distance_km', 0)
                message_parts.append(f"{alt_hospital.name} ({alt_distance}km) - {alt_hospital.emergency_phone}")
        
        # Add simple tracking info
        message_parts.extend([
            "",
            f"Request ID: {str(emergency_request.request_id)[:8]}",
            f"Time: {timezone.now().strftime('%H:%M')} from {user_area}"
        ])
        
        return "\n".join(message_parts)
    
    def _create_sms_message(self, emergency_request, hospitals):
        """Carrier-friendly SMS message format - optimized to avoid spam filters"""
        if not hospitals:
            return f"No hospitals found for {emergency_request.blood_group} ({emergency_request.quantity_needed} bags)"
        
        hospital = hospitals[0]  # Primary hospital
        distance = hospital.calculate_distance(
            float(emergency_request.user_latitude or 0),
            float(emergency_request.user_longitude or 0)
        ) if emergency_request.user_latitude else 0
        
        # Use carrier-friendly format (no emojis, no medical keywords)
        message_parts = [
            f"BLOOD AVAILABLE near your area",
            f"{emergency_request.quantity_needed} bag {emergency_request.blood_group} found",
            "",
            f"NEAREST HOSPITAL: {hospital.name}",
            f"PHONE: {hospital.emergency_phone}",
            f"ADDRESS: {hospital.address[:80]}",
            f"DISTANCE: {distance:.1f}km"
        ]
        
        # Add urgency without triggering spam filters
        if emergency_request.urgency == 'CRITICAL':
            message_parts.append(f"URGENT: Call {hospital.emergency_phone} now")
        else:
            message_parts.append(f"Contact: {hospital.emergency_phone}")
        
        # Add backup hospitals
        if len(hospitals) > 1:
            message_parts.append("")
            message_parts.append(f"BACKUP: {len(hospitals)-1} more hospitals available")
        
        # Add tracking info
        message_parts.extend([
            "",
            f"Request ID: {str(emergency_request.request_id)[:8]}"
        ])
        
        return "\n".join(message_parts)
    
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
    
    def _simulate_sms(self, emergency_request, hospitals=None):
        """Simulate SMS sending for demo/development with enhanced context"""
        # Get enhanced hospital information if not provided
        if hospitals is None:
            hospital_finder = get_hospital_finder()
            hospital_context = hospital_finder.find_nearby_hospitals_with_context(emergency_request)
        else:
            # Convert old format to new format for compatibility
            hospital_finder = get_hospital_finder()
            hospital_context = hospital_finder.find_nearby_hospitals_with_context(emergency_request)
        
        message = self._create_enhanced_sms_message(emergency_request, hospital_context)
        
        # Log as if sent successfully
        EmergencyNotification.objects.create(
            request=emergency_request,
            notification_type='SMS',
            recipient=emergency_request.contact_phone,
            message=message,
            status='SENT',
            provider_response='SIMULATED_SMS'
        )
        
        logger.info(f"Enhanced SMS SIMULATED for {emergency_request.contact_phone}")
        print(f"\n=== SIMULATED SMS MESSAGE ===\nTo: {emergency_request.contact_phone}\n{message}\n=== END SMS ===\n")
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


class EnhancedNotificationService:
    """Enhanced notification service with real-time updates and follow-ups"""
    
    def __init__(self):
        self.base_service = NotificationService()
        self.location_service = get_location_service()
    
    def send_immediate_confirmation(self, emergency_request):
        """Send immediate confirmation SMS when request is created"""
        if not emergency_request.contact_phone:
            return False
        
        try:
            # Quick confirmation message
            location_text = emergency_request.user_location_text or "location detecting..."
            if emergency_request.user_latitude and emergency_request.user_longitude:
                location_text = self.location_service.reverse_geocode(
                    float(emergency_request.user_latitude),
                    float(emergency_request.user_longitude)
                )
            
            confirmation_message = (
                f"REQUEST CONFIRMED\n"
                f"{emergency_request.blood_group} - {emergency_request.quantity_needed} bag(s)\n"
                f"Location: {location_text}\n"
                f"ID: {str(emergency_request.request_id)[:8]}\n\n"
                f"Searching hospitals now...\n"
                f"Results will appear immediately!"
            )
            
            return self._send_quick_sms(emergency_request, confirmation_message)
            
        except Exception as e:
            logger.error(f"Error sending immediate confirmation: {e}")
            return False
    
    def send_search_progress_update(self, emergency_request, hospitals_found_count=0):
        """Send progress update during hospital search"""
        if not emergency_request.contact_phone:
            return False
        
        try:
            if hospitals_found_count > 0:
                message = (
                    f"HOSPITALS FOUND #{str(emergency_request.request_id)[:8]}\n"
                    f"Found {hospitals_found_count} hospitals with {emergency_request.blood_group}\n"
                    f"Check your browser for immediate details!\n"
                    f"Call now for urgent needs!"
                )
            else:
                message = (
                    f"Search Update #{str(emergency_request.request_id)[:8]}\n"
                    f"Expanding search radius...\n"
                    f"Checking more hospitals for {emergency_request.blood_group}"
                )
            
            return self._send_quick_sms(emergency_request, message)
            
        except Exception as e:
            logger.error(f"Error sending search progress update: {e}")
            return False
    
    def send_follow_up_reminder(self, emergency_request, minutes_elapsed=15):
        """Send follow-up reminder after some time"""
        if not emergency_request.contact_phone:
            return False
        
        try:
            hospitals_count = emergency_request.hospitals_found.count()
            
            if hospitals_count > 0:
                message = (
                    f"⏰ {minutes_elapsed}min Reminder\n"
                    f"🆔 Request: {str(emergency_request.request_id)[:8]}\n\n"
                    f"Have you contacted the {hospitals_count} hospitals?\n"
                    f"🩸 {emergency_request.blood_group} is critical - time matters!\n\n"
                    f"📞 If still needed, call 108 immediately\n"
                    f"🏥 Or visit nearest hospital directly"
                )
            else:
                message = (
                    f"⏰ {minutes_elapsed}min Update\n"
                    f"🆔 Request: {str(emergency_request.request_id)[:8]}\n\n"
                    f"Still searching for {emergency_request.blood_group}...\n"
                    f"🚨 For urgent needs: Call 108 NOW\n"
                    f"🏥 Visit nearest hospital immediately\n"
                    f"📱 We'll keep searching and notify you"
                )
            
            return self._send_quick_sms(emergency_request, message)
            
        except Exception as e:
            logger.error(f"Error sending follow-up reminder: {e}")
            return False
    
    def _send_quick_sms(self, emergency_request, message):
        """Send SMS using base service with error handling"""
        try:
            # In development/simulation mode
            EmergencyNotification.objects.create(
                request=emergency_request,
                notification_type='SMS',
                recipient=emergency_request.contact_phone,
                message=message,
                status='SENT',
                provider_response='SIMULATED_QUICK_SMS'
            )
            
            logger.info(f"Quick SMS to {emergency_request.contact_phone}: {message}")
            print(f"\n=== QUICK SMS ===\nTo: {emergency_request.contact_phone}\n{message}\n=== END ===\n")
            return True
                
        except Exception as e:
            logger.error(f"Error in quick SMS sending: {e}")
            return False
