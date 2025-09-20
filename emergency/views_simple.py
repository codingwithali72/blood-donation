from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.conf import settings
import json
import logging
from .models import EmergencyRequest, EmergencyHospital, EmergencyBloodStock, EmergencyNotification
from .services import NotificationService, LocationService

logger = logging.getLogger(__name__)

def emergency_home(request):
    """Emergency homepage with simple request interface"""
    blood_groups = EmergencyRequest.BLOOD_GROUPS
    
    context = {
        'blood_groups': blood_groups,
        'page_title': 'Emergency Blood Request',
        'is_emergency': True,
    }
    return render(request, 'emergency/emergency_home.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def create_emergency_request(request):
    """Create emergency request - simple version"""
    try:
        # Parse JSON data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        # Extract required information
        blood_group = data.get('blood_group')
        quantity = data.get('quantity')
        
        # Validation
        if not blood_group or not quantity:
            return JsonResponse({
                'success': False,
                'error': 'Blood group and quantity are required'
            }, status=400)
        
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'error': 'Invalid quantity. Please enter a valid number.'
            }, status=400)
        
        # Get location data
        user_lat = data.get('latitude')
        user_lng = data.get('longitude')
        location_text = data.get('location', '')
        
        # Contact information
        contact_phone = (data.get('phone') or '').strip()
        contact_email = (data.get('email') or '').strip() 
        contact_name = (data.get('name') or '').strip() or 'Web User'
        
        # Validate phone number
        if not contact_phone:
            return JsonResponse({
                'success': False,
                'error': 'Phone number is required for SMS notifications'
            }, status=400)
        
        # Clean up phone number format
        import re
        phone_clean = re.sub(r'[^0-9+]', '', contact_phone)
        if not phone_clean.startswith('+'):
            if phone_clean.startswith('91') and len(phone_clean) == 12:
                phone_clean = '+' + phone_clean
            elif len(phone_clean) == 10:
                phone_clean = '+91' + phone_clean
        
        contact_phone = phone_clean
        
        # Get client info for tracking
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        session_key = request.session.session_key or ''
        
        # Create emergency request
        emergency_request = EmergencyRequest.objects.create(
            blood_group=blood_group,
            quantity_needed=quantity,
            user_latitude=user_lat,
            user_longitude=user_lng,
            user_location_text=location_text,
            contact_phone=contact_phone,
            contact_email=contact_email,
            contact_name=contact_name,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_key,
        )
        
        # Immediate response for user
        response_data = {
            'success': True,
            'request_id': str(emergency_request.request_id),
            'message': 'Emergency request created successfully',
            'status': 'searching'
        }
        
        # Search for hospitals immediately
        try:
            search_hospitals_and_notify(emergency_request.id)
            response_data['hospitals_searched'] = True
        except Exception as e:
            logger.error(f"Error searching hospitals: {e}")
            response_data['hospitals_searched'] = False
            response_data['error'] = 'Could not search hospitals immediately'
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error creating emergency request: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error. Please try again.'
        }, status=500)

def search_hospitals_and_notify(request_id):
    """Search hospitals and send notifications - simple version"""
    try:
        emergency_request = EmergencyRequest.objects.get(id=request_id)
        emergency_request.status = 'SEARCHING'
        emergency_request.save()
        
        # Find nearby hospitals
        hospitals = emergency_request.get_nearby_hospitals()
        
        if hospitals:
            # Update status and associate hospitals
            emergency_request.status = 'FOUND'
            emergency_request.hospitals_found.set(hospitals)
            emergency_request.save()
            
            # Send notifications
            notification_service = NotificationService()
            
            # Send SMS if phone provided
            if emergency_request.contact_phone:
                sms_sent = notification_service.send_emergency_sms(emergency_request, hospitals)
                emergency_request.sms_sent = sms_sent
            
            # Send Email if email provided
            if emergency_request.contact_email:
                email_sent = notification_service.send_emergency_email(emergency_request, hospitals)
                emergency_request.email_sent = email_sent
            
            emergency_request.notification_sent = True
            emergency_request.status = 'NOTIFIED'
            emergency_request.save()
            
            # Reserve stock from first hospital
            try:
                stock = EmergencyBloodStock.objects.get(
                    hospital=hospitals[0], 
                    blood_group=emergency_request.blood_group
                )
                if stock.units_available >= emergency_request.quantity_needed:
                    stock.units_available -= emergency_request.quantity_needed
                    stock.save()
                    logger.info(f"Reserved {emergency_request.quantity_needed} bags from {hospitals[0].name}")
            except EmergencyBloodStock.DoesNotExist:
                logger.warning(f"Stock not found for {emergency_request.blood_group} at {hospitals[0].name}")
        
        else:
            # No hospitals found
            emergency_request.status = 'FAILED'
            emergency_request.save()
            
            # Send "no hospitals" notification
            notification_service = NotificationService()
            if emergency_request.contact_phone:
                message = f"No hospitals found with {emergency_request.blood_group} blood. Please contact nearby hospitals directly. Request ID: {emergency_request.request_id}"
                try:
                    from twilio.rest import Client
                    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                    client.messages.create(
                        body=message,
                        from_=settings.TWILIO_PHONE_NUMBER,
                        to=emergency_request.contact_phone
                    )
                except:
                    pass
        
        return True
        
    except Exception as e:
        logger.error(f"Error in search_hospitals_and_notify: {e}")
        return False

def check_request_status(request, request_id):
    """Check the status of an emergency request"""
    try:
        emergency_request = EmergencyRequest.objects.get(request_id=request_id)
        
        hospitals_data = []
        for hospital in emergency_request.hospitals_found.all():
            # Calculate distance if coordinates available
            distance = 0
            if emergency_request.user_latitude and emergency_request.user_longitude:
                distance = hospital.calculate_distance(
                    float(emergency_request.user_latitude),
                    float(emergency_request.user_longitude)
                )
            
            hospitals_data.append({
                'name': hospital.name,
                'address': hospital.address,
                'phone': hospital.phone,
                'emergency_phone': hospital.emergency_phone,
                'distance': f"{distance:.1f}" if distance else "N/A"
            })
        
        return JsonResponse({
            'success': True,
            'status': emergency_request.status,
            'hospitals': hospitals_data,
            'blood_group': emergency_request.blood_group,
            'quantity': emergency_request.quantity_needed,
            'created_at': emergency_request.created_at.isoformat(),
        })
        
    except EmergencyRequest.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Request not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error checking request status: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Request not found or error occurred'
        }, status=404)

def public_hospital_inventory(request):
    """Public hospital inventory dashboard"""
    hospitals = EmergencyHospital.objects.filter(is_active=True).prefetch_related('hospital_blood_stock')
    
    hospitals_data = []
    total_inventory = {'A+': 0, 'A-': 0, 'B+': 0, 'B-': 0, 'AB+': 0, 'AB-': 0, 'O+': 0, 'O-': 0}
    
    for hospital in hospitals:
        hospital_inventory = {}
        for stock in hospital.hospital_blood_stock.all():
            hospital_inventory[stock.blood_group] = stock.units_available
            total_inventory[stock.blood_group] += stock.units_available
        
        hospitals_data.append({
            'id': hospital.id,
            'name': hospital.name,
            'address': hospital.address,
            'city': hospital.city,
            'phone': hospital.phone,
            'operates_24x7': hospital.operates_24x7,
            'inventory': hospital_inventory,
            'total_units': sum(hospital_inventory.values()),
        })
    
    context = {
        'hospitals': hospitals_data,
        'total_inventory': total_inventory,
        'total_hospitals': len(hospitals_data),
        'total_units_available': sum(total_inventory.values()),
        'page_title': 'Hospital Blood Inventory',
        'last_updated': timezone.now(),
    }
    
    return render(request, 'emergency/hospital_inventory.html', context)

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip