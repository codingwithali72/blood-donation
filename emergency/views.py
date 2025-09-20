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
from .admin_notifier import send_admin_notification

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
            
            # Send admin notification FIRST (to +919076316961)
            admin_notified = send_admin_notification(emergency_request, hospitals)
            
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
            
            # Send admin notification even when no hospitals found
            admin_notified = send_admin_notification(emergency_request, [])
            
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
        hospital_inventory_display = {}  # For display purposes
        hospital_inventory_status = {}   # For status classes
        
        # Initialize all blood types
        for blood_type in total_inventory.keys():
            hospital_inventory[blood_type] = 0
            hospital_inventory_display[blood_type] = '0'
            hospital_inventory_status[blood_type] = 'empty'
        
        for stock in hospital.hospital_blood_stock.all():
            units = stock.units_available
            hospital_inventory[stock.blood_group] = units
            total_inventory[stock.blood_group] += units
            
            # Special handling for O- blood type
            if stock.blood_group == 'O-' and units > 0 and units < 10:
                hospital_inventory_display[stock.blood_group] = 'less'
                hospital_inventory_status[stock.blood_group] = 'low'
            else:
                hospital_inventory_display[stock.blood_group] = str(units)
                
                # Determine status based on units
                if units == 0:
                    hospital_inventory_status[stock.blood_group] = 'empty'
                elif units <= 5:
                    hospital_inventory_status[stock.blood_group] = 'critical'
                elif units <= 15:
                    hospital_inventory_status[stock.blood_group] = 'low'
                else:
                    hospital_inventory_status[stock.blood_group] = 'available'
        
        # Get last updated time from any stock record
        last_updated = None
        if hospital.hospital_blood_stock.exists():
            last_updated = hospital.hospital_blood_stock.latest('last_updated').last_updated
        
        # Create template-friendly blood type list
        blood_types_data = []
        for blood_type in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']:
            blood_types_data.append({
                'type': blood_type,
                'count': hospital_inventory.get(blood_type, 0),
                'display': hospital_inventory_display.get(blood_type, '0'),
                'status': hospital_inventory_status.get(blood_type, 'empty')
            })
        
        hospitals_data.append({
            'id': hospital.id,
            'name': hospital.name,
            'address': hospital.address,
            'city': hospital.city,
            'phone': hospital.phone,
            'emergency_phone': hospital.emergency_phone,
            'operates_24x7': hospital.operates_24x7,
            'inventory': hospital_inventory,
            'inventory_display': hospital_inventory_display,
            'inventory_status': hospital_inventory_status,
            'blood_types': blood_types_data,
            'total_units': sum(hospital_inventory.values()),
            'last_updated': last_updated,
        })
    
    # Create template-friendly total inventory list
    total_inventory_list = []
    for blood_type in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']:
        total_inventory_list.append({
            'type': blood_type,
            'total': total_inventory.get(blood_type, 0)
        })
    
    context = {
        'hospitals': hospitals_data,
        'total_inventory': total_inventory,
        'total_inventory_list': total_inventory_list,
        'total_hospitals': len(hospitals_data),
        'total_units_available': sum(total_inventory.values()),
        'a_positive_count': total_inventory.get('A+', 0),
        'o_positive_count': total_inventory.get('O+', 0),
        'page_title': 'Hospital Blood Inventory',
        'last_updated': timezone.now(),
    }
    
    return render(request, 'emergency/hospital_inventory.html', context)

from django.contrib.admin.views.decorators import staff_member_required

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@staff_member_required
def emergency_analytics(request):
    """Analytics dashboard for emergency module"""
    # In a real application, you would gather and process data here
    # For now, return a simple placeholder response
    return JsonResponse({
        'success': True,
        'message': 'Emergency analytics dashboard (placeholder)',
        'data': {
            'total_requests': 0,
            'open_requests': 0,
            'closed_requests': 0,
            'hospitals_registered': 0,
            'average_response_time': 'N/A'
        }
    })

@staff_member_required
def emergency_admin_dashboard(request):
    """Admin dashboard for emergency module"""
    # In a real application, you would gather and process data here
    # For now, return a simple placeholder response
    return JsonResponse({
        'success': True,
        'message': 'Emergency analytics dashboard (placeholder)',
        'data': {
            'total_requests': 0,
            'open_requests': 0,
            'closed_requests': 0,
            'hospitals_registered': 0,
        }
    })

@csrf_exempt
@require_http_methods(["GET"])
def api_find_nearby_hospitals(request):
    """API endpoint to find nearby hospitals based on location and blood group"""
    try:
        # Get query parameters
        latitude = request.GET.get('latitude')
        longitude = request.GET.get('longitude')
        blood_group = request.GET.get('blood_group')

        if not all([latitude, longitude, blood_group]):
            return JsonResponse({
                'success': False,
                'error': 'Latitude, longitude, and blood_group are required.'
            }, status=400)

        # Convert to float
        latitude = float(latitude)
        longitude = float(longitude)

        # Use LocationService to find nearby hospitals
        location_service = LocationService()
        nearby_hospitals_data = location_service.find_nearby_hospitals(
            latitude, longitude, blood_group
        )

        return JsonResponse({
            'success': True,
            'hospitals': nearby_hospitals_data
        })

    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid latitude or longitude.'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in api_find_nearby_hospitals: {e}")
        return JsonResponse({
            'success': False,
            'error': 'An internal server error occurred.'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def api_live_inventory(request):
    """Enhanced API endpoint for location-based and hospital-wise blood inventory"""
    try:
        # Get optional city filter and user location
        city_filter = request.GET.get('city', '').strip()
        user_lat = request.GET.get('latitude')
        user_lng = request.GET.get('longitude')
        show_hospitals = request.GET.get('show_hospitals', 'true').lower() == 'true'
        
        # Get all active hospitals with their blood stock
        hospitals_query = EmergencyHospital.objects.filter(is_active=True).prefetch_related('hospital_blood_stock')
        
        # Apply city filter if specified
        if city_filter:
            hospitals_query = hospitals_query.filter(city__icontains=city_filter)
        
        hospitals = hospitals_query.all()
        
        # Group hospitals by city
        cities_data = {}
        total_inventory = {'A+': 0, 'A-': 0, 'B+': 0, 'B-': 0, 'AB+': 0, 'AB-': 0, 'O+': 0, 'O-': 0}
        all_hospitals_data = []
        
        for hospital in hospitals:
            city_name = hospital.city
            if city_name not in cities_data:
                cities_data[city_name] = {
                    'inventory': {'A+': 0, 'A-': 0, 'B+': 0, 'B-': 0, 'AB+': 0, 'AB-': 0, 'O+': 0, 'O-': 0},
                    'hospitals': [],
                    'total_units': 0,
                    'hospital_count': 0
                }
            
            # Calculate hospital inventory
            hospital_inventory = {}
            hospital_total = 0
            
            for stock in hospital.hospital_blood_stock.all():
                hospital_inventory[stock.blood_group] = stock.units_available
                cities_data[city_name]['inventory'][stock.blood_group] += stock.units_available
                total_inventory[stock.blood_group] += stock.units_available
                hospital_total += stock.units_available
            
            # Fill missing blood groups with 0
            for blood_type in total_inventory.keys():
                if blood_type not in hospital_inventory:
                    hospital_inventory[blood_type] = 0
            
            # Calculate distance if user location provided
            distance = None
            if user_lat and user_lng:
                try:
                    distance = hospital.calculate_distance(float(user_lat), float(user_lng))
                except (ValueError, TypeError):
                    distance = None
            
            hospital_data = {
                'id': hospital.id,
                'name': hospital.name,
                'city': hospital.city,
                'address': hospital.address,
                'phone': hospital.phone,
                'emergency_phone': hospital.emergency_phone,
                'inventory': hospital_inventory,
                'total_units': hospital_total,
                'operates_24x7': hospital.operates_24x7,
                'distance': f"{distance:.1f}" if distance else None
            }
            
            cities_data[city_name]['hospitals'].append(hospital_data)
            cities_data[city_name]['total_units'] += hospital_total
            cities_data[city_name]['hospital_count'] += 1
            all_hospitals_data.append(hospital_data)
        
        # Sort hospitals by distance if location provided
        if user_lat and user_lng:
            all_hospitals_data.sort(key=lambda x: float(x['distance']) if x['distance'] else float('inf'))
            for city in cities_data.values():
                city['hospitals'].sort(key=lambda x: float(x['distance']) if x['distance'] else float('inf'))
        
        # Calculate statistics
        total_units = sum(total_inventory.values())
        critical_blood_types = [bg for bg, count in total_inventory.items() if count < 10]
        available_blood_types = [bg for bg, count in total_inventory.items() if count > 0]
        
        # Determine primary city (largest inventory or filtered city)
        primary_city = city_filter if city_filter and city_filter in cities_data else None
        if not primary_city and cities_data:
            primary_city = max(cities_data.keys(), key=lambda city: cities_data[city]['total_units'])
        
        response_data = {
            'success': True,
            'data': {
                'total_inventory': total_inventory,
                'total_units_available': total_units,
                'total_hospitals': len(all_hospitals_data),
                'critical_blood_types': critical_blood_types,
                'available_blood_types': available_blood_types,
                'primary_city': primary_city,
                'cities': cities_data,
                'last_updated': timezone.now().isoformat(),
                'emergency_contact': '108',
                'user_location': {
                    'latitude': user_lat,
                    'longitude': user_lng
                } if user_lat and user_lng else None
            }
        }
        
        # Include detailed hospital list if requested
        if show_hospitals:
            response_data['data']['hospitals'] = all_hospitals_data
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error in api_live_inventory: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to fetch inventory data'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST", "GET"])
def api_enhanced_location_request(request):
    """Placeholder for API enhanced location request"""
    logger.info(f"Received {request.method} request for enhanced location.")
    return JsonResponse({
        'success': True,
        'message': 'Enhanced location request endpoint reached (placeholder).'
    }, status=200)
