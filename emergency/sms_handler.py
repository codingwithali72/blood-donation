"""
SMS Handler for Emergency Blood Bank System
Handles incoming SMS messages and creates emergency requests
"""

import re
import logging
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import EmergencyRequest
from .location_utils import get_location_service, get_hospital_finder
from .services import NotificationService
from .views import search_hospitals_and_notify

logger = logging.getLogger(__name__)


class SMSMessageParser:
    """Parse incoming SMS messages for blood requests"""
    
    # Blood group patterns - order matters! AB must come before B
    BLOOD_GROUP_PATTERNS = [
        r'(AB[\+\-])', # AB+, AB- (must come first)
        r'(A[\+\-])',  # A+, A-
        r'(B[\+\-])',  # B+, B-
        r'(O[\+\-])',  # O+, O-
        r'(AB)\s*(POS|POSITIVE)', # AB POSITIVE (must come before B)
        r'(AB)\s*(NEG|NEGATIVE)', # AB NEGATIVE (must come before B)
        r'(A)\s*(POS|POSITIVE)',  # A POSITIVE
        r'(A)\s*(NEG|NEGATIVE)',  # A NEGATIVE
        r'(B)\s*(POS|POSITIVE)',  # B POSITIVE
        r'(B)\s*(NEG|NEGATIVE)',  # B NEGATIVE
        r'(O)\s*(POS|POSITIVE)',  # O POSITIVE
        r'(O)\s*(NEG|NEGATIVE)',  # O NEGATIVE
    ]
    
    # Quantity patterns
    QUANTITY_PATTERNS = [
        r'\b(\d+)\s*(BAG|BAGS|UNIT|UNITS?|BOTTLE|BOTTLES?)\b',
        r'\b(\d+)\s*(?=\s|$)',  # Just a number
    ]
    
    # Location patterns
    LOCATION_PATTERNS = [
        r'\b(?:NEAR|AT|IN|FROM)\s+([A-Za-z\s,]+?)(?:\s*$|\s+(?:URGENT|CRITICAL|EMERGENCY))',
        r'(?:BAG|BAGS|UNIT|UNITS?)\s+([A-Za-z\s,]{3,}?)(?:\s*$|\s+(?:URGENT|CRITICAL))',
        r'\b([A-Za-z\s,]{5,})\s*$',  # Location at end of message
    ]
    
    # Urgency patterns
    URGENCY_PATTERNS = [
        (r'\b(?:CRITICAL|EMERGENCY|URGENT|ASAP|IMMEDIATE)\b', 'CRITICAL'),
        (r'\b(?:ROUTINE|NORMAL|REGULAR)\b', 'ROUTINE'),
    ]
    
    def parse_message(self, message_body: str, from_number: str) -> dict:
        """
        Parse SMS message and extract blood request information
        
        Expected formats:
        - "A+ 2 near Andheri"
        - "Need B- urgent 1 bag Bandra"
        - "Emergency O+ 3 units at Dadar station"
        - "AB+ 1"
        """
        message = message_body.upper().strip()
        
        result = {
            'success': False,
            'blood_group': None,
            'quantity': 1,  # default
            'location': None,
            'urgency': 'URGENT',  # default
            'from_number': from_number,
            'original_message': message_body,
            'error': None
        }
        
        try:
            # Extract blood group
            blood_group = self._extract_blood_group(message)
            if not blood_group:
                result['error'] = "Could not identify blood group. Please specify like 'A+', 'B-', 'O+', etc."
                return result
            
            result['blood_group'] = blood_group
            
            # Extract quantity
            quantity = self._extract_quantity(message)
            if quantity:
                result['quantity'] = quantity
            
            # Extract location
            location = self._extract_location(message)
            result['location'] = location
            
            # Extract urgency
            urgency = self._extract_urgency(message)
            if urgency:
                result['urgency'] = urgency
            
            result['success'] = True
            return result
            
        except Exception as e:
            logger.error(f"Error parsing SMS message: {e}")
            result['error'] = "Could not parse your message. Please try format: 'A+ 2 near Andheri'"
            return result
    
    def _extract_blood_group(self, message: str) -> str:
        """Extract blood group from message"""
        for pattern in self.BLOOD_GROUP_PATTERNS:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                blood_type = match.group(1).upper()
                
                # Check if already has sign (A+, B-, etc.)
                if len(blood_type) > 1 and blood_type[-1] in ['+', '-']:
                    blood_group = blood_type
                else:
                    # Check for separate sign in second group
                    if len(match.groups()) >= 2 and match.group(2):
                        sign_part = match.group(2).upper()
                        if 'POS' in sign_part or 'POSITIVE' in sign_part:
                            blood_group = blood_type + '+'
                        elif 'NEG' in sign_part or 'NEGATIVE' in sign_part:
                            blood_group = blood_type + '-'
                        else:
                            blood_group = blood_type + match.group(2)
                    else:
                        # Default case - shouldn't happen with our patterns
                        blood_group = blood_type
                
                # Validate blood group
                valid_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
                if blood_group in valid_groups:
                    return blood_group
        
        return None
    
    def _extract_quantity(self, message: str) -> int:
        """Extract quantity from message"""
        for pattern in self.QUANTITY_PATTERNS:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                try:
                    quantity = int(match.group(1))
                    if 1 <= quantity <= 10:  # reasonable range
                        return quantity
                except ValueError:
                    continue
        
        return 1  # default
    
    def _extract_location(self, message: str) -> str:
        """Extract location from message"""
        for pattern in self.LOCATION_PATTERNS:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                if len(location) >= 3:  # reasonable location length
                    return location.title()
        
        return None
    
    def _extract_urgency(self, message: str) -> str:
        """Extract urgency level from message"""
        for pattern, urgency in self.URGENCY_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                return urgency
        
        return 'URGENT'  # default


@csrf_exempt
@require_http_methods(["POST"])
def sms_webhook(request):
    """
    Webhook endpoint for Twilio SMS messages
    Handles incoming SMS requests for blood
    """
    try:
        # Extract Twilio parameters
        message_body = request.POST.get('Body', '').strip()
        from_number = request.POST.get('From', '')
        to_number = request.POST.get('To', '')
        message_sid = request.POST.get('MessageSid', '')
        
        logger.info(f"Received SMS from {from_number}: {message_body}")
        
        if not message_body:
            return _send_sms_response("Please send a blood request. Example: 'A+ 2 near Andheri'")
        
        # Check for help requests
        if any(word in message_body.upper() for word in ['HELP', 'INFO', 'FORMAT', 'HOW']):
            help_message = (
                "🩸 Emergency Blood Request Help:\n\n"
                "Format: [Blood Group] [Quantity] [Location]\n"
                "Examples:\n"
                "• A+ 2 near Andheri\n"
                "• O- urgent 1 bag Bandra\n"
                "• AB+ 3 at Dadar station\n\n"
                "Add 'urgent' or 'critical' for priority."
            )
            return _send_sms_response(help_message)
        
        # Parse the SMS message
        parser = SMSMessageParser()
        parsed = parser.parse_message(message_body, from_number)
        
        if not parsed['success']:
            error_response = (
                f"❌ {parsed['error']}\n\n"
                "Format: [Blood Group] [Quantity] [Location]\n"
                "Example: 'A+ 2 near Andheri'\n"
                "Send 'HELP' for more info."
            )
            return _send_sms_response(error_response)
        
        # Create emergency request
        emergency_request = _create_emergency_from_sms(parsed, request)
        
        if not emergency_request:
            return _send_sms_response(
                "❌ Could not create emergency request. Please try again or call 108 for immediate help."
            )
        
        # Send immediate confirmation
        confirmation_message = (
            f"✅ Emergency Request Created!\n"
            f"🩸 {parsed['blood_group']} - {parsed['quantity']} bag(s)\n"
            f"📍 {parsed.get('location', 'Location detecting...')}\n"
            f"🆔 ID: {str(emergency_request.request_id)[:8]}\n\n"
            f"🔍 Searching hospitals... You'll receive results shortly."
        )
        
        # Start hospital search in background
        try:
            search_hospitals_and_notify(emergency_request.id)
        except Exception as e:
            logger.error(f"Error in hospital search for SMS request: {e}")
            # Send fallback message
            fallback_message = (
                f"⚠️ Search in progress. If no response in 2 minutes, "
                f"call 108 or visit nearest hospital.\n"
                f"Request ID: {str(emergency_request.request_id)[:8]}"
            )
            return _send_sms_response(fallback_message)
        
        return _send_sms_response(confirmation_message)
        
    except Exception as e:
        logger.error(f"Error in SMS webhook: {e}")
        return _send_sms_response(
            "❌ System error. Please call 108 for immediate emergency assistance."
        )


def _create_emergency_from_sms(parsed_data: dict, request) -> 'EmergencyRequest':
    """Create emergency request from parsed SMS data"""
    try:
        # Get location service for enhanced location detection
        location_service = get_location_service()
        
        # Try to get location details
        location_info = location_service.get_location_details(
            request, 
            location_text=parsed_data.get('location')
        )
        
        # Create emergency request
        emergency_request = EmergencyRequest.objects.create(
            blood_group=parsed_data['blood_group'],
            quantity_needed=parsed_data['quantity'],
            urgency=parsed_data['urgency'],
            user_latitude=location_info.get('latitude'),
            user_longitude=location_info.get('longitude'),
            user_location_text=location_info.get('address') or parsed_data.get('location', ''),
            contact_phone=parsed_data['from_number'],
            contact_name=f"SMS User {parsed_data['from_number'][-4:]}",  # Last 4 digits
            ip_address=_get_client_ip(request),
            user_agent=f"SMS via {request.META.get('HTTP_USER_AGENT', 'Twilio')}",
            session_id=f"sms_{parsed_data.get('message_sid', 'unknown')}"
        )
        
        logger.info(f"Created emergency request {emergency_request.request_id} from SMS")
        return emergency_request
        
    except Exception as e:
        logger.error(f"Error creating emergency request from SMS: {e}")
        return None


def _send_sms_response(message: str) -> HttpResponse:
    """Send SMS response using TwiML"""
    twiml_response = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{message}</Message>
</Response>'''
    
    return HttpResponse(twiml_response, content_type='text/xml')


def _get_client_ip(request) -> str:
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


# Additional SMS utilities
class SMSStatusHandler:
    """Handle SMS delivery status updates from Twilio"""
    
    @staticmethod
    @csrf_exempt
    @require_http_methods(["POST"])
    def status_callback(request):
        """Handle SMS delivery status callbacks"""
        try:
            message_sid = request.POST.get('MessageSid', '')
            status = request.POST.get('MessageStatus', '')
            to_number = request.POST.get('To', '')
            
            logger.info(f"SMS Status Update: {message_sid} -> {status} (to {to_number})")
            
            # Update notification status in database
            from .models import EmergencyNotification
            try:
                notification = EmergencyNotification.objects.get(
                    provider_response=message_sid
                )
                
                status_mapping = {
                    'sent': 'SENT',
                    'delivered': 'DELIVERED',
                    'failed': 'FAILED',
                    'undelivered': 'FAILED'
                }
                
                if status in status_mapping:
                    notification.status = status_mapping[status]
                    if status == 'delivered':
                        notification.delivered_at = timezone.now()
                    notification.save()
                    
            except EmergencyNotification.DoesNotExist:
                logger.warning(f"Notification not found for SMS SID: {message_sid}")
            
            return HttpResponse('OK')
            
        except Exception as e:
            logger.error(f"Error handling SMS status callback: {e}")
            return HttpResponse('Error', status=500)


def send_follow_up_sms(emergency_request, message_type='update'):
    """Send follow-up SMS messages"""
    if not emergency_request.contact_phone:
        return False
    
    try:
        notification_service = NotificationService()
        
        if message_type == 'update':
            # Send status update
            hospitals_count = emergency_request.hospitals_found.count()
            if hospitals_count > 0:
                message = (
                    f"🔄 Update for Request {str(emergency_request.request_id)[:8]}:\n"
                    f"{hospitals_count} hospitals found with {emergency_request.blood_group}.\n"
                    f"Check your messages for details or call the hospitals directly."
                )
            else:
                message = (
                    f"🔄 Update for Request {str(emergency_request.request_id)[:8]}:\n"
                    f"Still searching for {emergency_request.blood_group}. "
                    f"Consider expanding search area or calling 108."
                )
        
        elif message_type == 'reminder':
            # Send reminder to contact hospitals
            message = (
                f"⏰ Reminder: Request {str(emergency_request.request_id)[:8]}\n"
                f"Have you contacted the hospitals? Time is critical for {emergency_request.blood_group}.\n"
                f"Call 108 if still needed."
            )
        
        else:
            return False
        
        # This would integrate with your existing SMS sending logic
        # For now, just log it
        logger.info(f"Follow-up SMS to {emergency_request.contact_phone}: {message}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending follow-up SMS: {e}")
        return False