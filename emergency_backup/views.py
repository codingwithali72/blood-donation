from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
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
    """Emergency homepage with 2-click request interface"""
    blood_groups = EmergencyRequest.BLOOD_GROUPS
    
    context = {
        'blood_groups': blood_groups,
        'page_title': '🚨 Emergency Blood Request',
        'is_emergency': True,
    }
    return render(request, 'emergency/emergency_home.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def create_emergency_request(request):
    """Create emergency request with minimal information (2-click system)"""
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
        
        # Optional contact information
        contact_phone = data.get('phone', '')
        contact_email = data.get('email', '')
        contact_name = data.get('name', '')
        
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
        
        # Search for hospitals asynchronously (in background)
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
    """Search hospitals and send notifications"""
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
            
            # Deduct stock from hospitals (reserved for this request)
            for hospital in hospitals[:3]:  # Reserve from top 3 closest hospitals
                try:
                    stock = EmergencyBloodStock.objects.get(
                        hospital=hospital, 
                        blood_group=emergency_request.blood_group
                    )
                    if stock.units_available >= emergency_request.quantity_needed:
                        stock.units_available -= emergency_request.quantity_needed
                        stock.save()
                        break  # Successfully reserved from one hospital
                except EmergencyBloodStock.DoesNotExist:
                    continue
            
        else:
            # No hospitals found
            emergency_request.status = 'FAILED'
            emergency_request.save()
            
            # Send "no hospitals" notification
            notification_service = NotificationService()
            if emergency_request.contact_phone:
                notification_service.send_no_hospitals_sms(emergency_request)
            if emergency_request.contact_email:
                notification_service.send_no_hospitals_email(emergency_request)
        
        return True
        
    except Exception as e:
        logger.error(f"Error in search_hospitals_and_notify: {e}")
        return False

@require_http_methods(["GET"])
def check_request_status(request, request_id):
    """Check status of emergency request"""
    try:
        emergency_request = get_object_or_404(EmergencyRequest, request_id=request_id)
        
        hospitals_data = []
        for hospital in emergency_request.hospitals_found.all():
            distance = hospital.calculate_distance(
                float(emergency_request.user_latitude or 0),
                float(emergency_request.user_longitude or 0)
            ) if emergency_request.user_latitude and emergency_request.user_longitude else 0
            
            hospitals_data.append({
                'name': hospital.name,
                'address': hospital.address,
                'phone': hospital.phone,
                'emergency_phone': hospital.emergency_phone,
                'distance': round(distance, 2),
                'available_blood': hospital.get_available_blood_types()
            })
        
        return JsonResponse({
            'success': True,
            'request_id': str(emergency_request.request_id),
            'status': emergency_request.status,
            'blood_group': emergency_request.blood_group,
            'quantity': emergency_request.quantity_needed,
            'hospitals': hospitals_data,
            'notifications_sent': emergency_request.notification_sent,
            'created_at': emergency_request.created_at.isoformat(),
        })
        
    except Exception as e:
        logger.error(f"Error checking request status: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Request not found or error occurred'
        }, status=404)

def public_hospital_inventory(request):
    """Public transparency dashboard showing all hospital inventories"""
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
            'last_updated': max([stock.last_updated for stock in hospital.hospital_blood_stock.all()]) if hospital.hospital_blood_stock.exists() else None
        })
    
    context = {
        'hospitals': hospitals_data,
        'total_inventory': total_inventory,
        'total_hospitals': len(hospitals_data),
        'total_units_available': sum(total_inventory.values()),
        'page_title': 'Live Hospital Blood Inventory',
        'last_updated': timezone.now(),
    }
    
    return render(request, 'emergency/hospital_inventory.html', context)

@require_http_methods(["GET"])
def api_hospital_inventory(request):
    """API endpoint for real-time hospital inventory"""
    hospitals = EmergencyHospital.objects.filter(is_active=True).prefetch_related('hospital_blood_stock')
    
    inventory_data = []
    for hospital in hospitals:
        hospital_data = {
            'id': hospital.id,
            'name': hospital.name,
            'address': hospital.address,
            'city': hospital.city,
            'phone': hospital.phone,
            'emergency_phone': hospital.emergency_phone,
            'coordinates': {
                'latitude': float(hospital.latitude),
                'longitude': float(hospital.longitude)
            },
            'operates_24x7': hospital.operates_24x7,
            'inventory': {},
            'last_updated': None
        }
        
        for stock in hospital.hospital_blood_stock.all():
            hospital_data['inventory'][stock.blood_group] = {
                'units': stock.units_available,
                'in_ml': stock.in_ml,
                'last_updated': stock.last_updated.isoformat()
            }
        
        if hospital.hospital_blood_stock.exists():
            hospital_data['last_updated'] = max([stock.last_updated for stock in hospital.hospital_blood_stock.all()]).isoformat()
        
        inventory_data.append(hospital_data)
    
    return JsonResponse({
        'success': True,
        'timestamp': timezone.now().isoformat(),
        'hospitals': inventory_data,
        'total_hospitals': len(inventory_data)
    })

def emergency_analytics(request):
    """Emergency system analytics dashboard"""
    from django.db.models import Count, Avg, Sum
    from datetime import datetime, timedelta
    
    # Date ranges
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Basic stats
    total_requests = EmergencyRequest.objects.count()
    successful_requests = EmergencyRequest.objects.filter(status='COMPLETED').count()
    pending_requests = EmergencyRequest.objects.filter(status__in=['PENDING', 'SEARCHING', 'FOUND']).count()
    
    # Weekly trends
    weekly_requests = EmergencyRequest.objects.filter(created_at__date__gte=week_ago).extra({
        'day': "date(created_at)"
    }).values('day').annotate(count=Count('id')).order_by('day')
    
    # Blood group demand
    blood_demand = EmergencyRequest.objects.values('blood_group').annotate(
        count=Count('id'),
        total_quantity=Sum('quantity_needed')
    ).order_by('-count')
    
    # Response time analysis
    completed_requests = EmergencyRequest.objects.filter(status='COMPLETED', completed_at__isnull=False)
    
    response_times = []
    for req in completed_requests:
        time_diff = req.completed_at - req.created_at
        response_times.append(time_diff.total_seconds() / 60)  # in minutes
    
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    # Hospital utilization
    hospital_usage = EmergencyHospital.objects.annotate(
        request_count=Count('emergency_requests')
    ).order_by('-request_count')[:10]
    
    context = {
        'total_requests': total_requests,
        'successful_requests': successful_requests,
        'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0,
        'pending_requests': pending_requests,
        'weekly_requests': list(weekly_requests),
        'blood_demand': list(blood_demand),
        'avg_response_time': round(avg_response_time, 2),
        'top_hospitals': hospital_usage,
        'page_title': 'Emergency System Analytics'
    }
    
    return render(request, 'emergency/analytics.html', context)

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# Admin Views for Emergency Management
def emergency_admin_dashboard(request):
    """Admin dashboard for emergency system"""
    if not request.user.is_staff:
        return render(request, '403.html', status=403)
    
    # Recent requests
    recent_requests = EmergencyRequest.objects.order_by('-created_at')[:20]
    
    # Active requests needing attention
    active_requests = EmergencyRequest.objects.filter(
        status__in=['PENDING', 'SEARCHING', 'FOUND']
    ).order_by('-created_at')
    
    # Low stock alerts
    low_stock_alerts = EmergencyBloodStock.objects.filter(units_available__lte=5).select_related('hospital')
    
    context = {
        'recent_requests': recent_requests,
        'active_requests': active_requests,
        'low_stock_alerts': low_stock_alerts,
        'page_title': 'Emergency System Admin'
    }
    
    return render(request, 'emergency/admin_dashboard.html', context)