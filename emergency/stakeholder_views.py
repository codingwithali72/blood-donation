from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg
from django.db import transaction
from datetime import datetime, timedelta
import json
import logging

from .models import (
    EmergencyHospital, EmergencyBloodStock, EmergencyRequest, EmergencyNotification,
    HospitalRegistration, BloodInventoryUpdate, CriticalStockAlert, 
    SocialImpactMetrics, EmergencyAnalytics
)

logger = logging.getLogger(__name__)

def is_hospital_staff(user):
    """Check if user is hospital staff"""
    return user.is_authenticated and (
        user.groups.filter(name='Hospital_Staff').exists() or 
        user.is_staff or 
        user.is_superuser
    )

def is_government_official(user):
    """Check if user is government official"""
    return user.is_authenticated and (
        user.groups.filter(name='Government_Official').exists() or
        user.is_superuser
    )

@login_required
@user_passes_test(is_hospital_staff)
def hospital_dashboard(request):
    """Main hospital dashboard for inventory management"""
    try:
        # Get hospital registration for this user
        hospital_registration = HospitalRegistration.objects.filter(
            hospital__in=EmergencyHospital.objects.all()
        ).first()
        
        if not hospital_registration:
            messages.warning(request, "Your hospital is not registered in the system.")
            return redirect('hospital_registration')
        
        hospital = hospital_registration.hospital
        
        # Get current inventory
        blood_stocks = EmergencyBloodStock.objects.filter(hospital=hospital)
        
        # Get recent updates
        recent_updates = BloodInventoryUpdate.objects.filter(
            hospital=hospital
        ).order_by('-timestamp')[:10]
        
        # Get active alerts
        active_alerts = CriticalStockAlert.objects.filter(
            hospital=hospital,
            status='ACTIVE'
        )
        
        # Calculate statistics
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        total_inventory = blood_stocks.aggregate(
            total=Sum('units_available')
        )['total'] or 0
        
        weekly_updates = BloodInventoryUpdate.objects.filter(
            hospital=hospital,
            timestamp__date__gte=week_ago
        ).count()
        
        emergency_requests_served = EmergencyRequest.objects.filter(
            hospitals_found=hospital,
            status='COMPLETED',
            created_at__date__gte=week_ago
        ).count()
        
        context = {
            'hospital': hospital,
            'hospital_registration': hospital_registration,
            'blood_stocks': blood_stocks,
            'recent_updates': recent_updates,
            'active_alerts': active_alerts,
            'total_inventory': total_inventory,
            'weekly_updates': weekly_updates,
            'emergency_requests_served': emergency_requests_served,
            'page_title': f'{hospital.name} - Dashboard'
        }
        
        return render(request, 'emergency/hospital_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in hospital dashboard: {e}")
        messages.error(request, "Error loading dashboard. Please try again.")
        return render(request, 'emergency/hospital_dashboard.html', {})

@login_required
@user_passes_test(is_hospital_staff)
@csrf_exempt
@require_http_methods(["POST"])
def update_blood_inventory(request):
    """Update blood inventory with tracking"""
    try:
        data = json.loads(request.body)
        
        hospital_id = data.get('hospital_id')
        blood_group = data.get('blood_group')
        new_count = int(data.get('new_count', 0))
        change_reason = data.get('change_reason', '')
        
        # Get hospital and current stock
        hospital = get_object_or_404(EmergencyHospital, id=hospital_id)
        stock, created = EmergencyBloodStock.objects.get_or_create(
            hospital=hospital,
            blood_group=blood_group,
            defaults={'units_available': 0}
        )
        
        previous_count = stock.units_available
        
        # Update stock with transaction
        with transaction.atomic():
            stock.units_available = new_count
            stock.save()
            
            # Create update record for transparency
            BloodInventoryUpdate.objects.create(
                hospital=hospital,
                updated_by=request.user,
                blood_group=blood_group,
                previous_count=previous_count,
                new_count=new_count,
                change_reason=change_reason
            )
            
            # Check for critical stock and create alerts
            check_and_create_alerts(hospital, blood_group, new_count)
        
        return JsonResponse({
            'success': True,
            'message': f'Updated {blood_group} inventory from {previous_count} to {new_count} bags',
            'new_count': new_count,
            'alert_created': new_count < 10
        })
        
    except Exception as e:
        logger.error(f"Error updating inventory: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to update inventory'
        }, status=500)

def check_and_create_alerts(hospital, blood_group, current_stock):
    """Check stock levels and create critical alerts"""
    alert_level = None
    
    if current_stock == 0:
        alert_level = 'DEPLETED'
    elif current_stock < 2:
        alert_level = 'EMERGENCY'
    elif current_stock < 5:
        alert_level = 'CRITICAL'
    elif current_stock < 10:
        alert_level = 'LOW'
    
    if alert_level:
        # Check if alert already exists
        existing_alert = CriticalStockAlert.objects.filter(
            hospital=hospital,
            blood_group=blood_group,
            status='ACTIVE'
        ).first()
        
        if not existing_alert:
            CriticalStockAlert.objects.create(
                hospital=hospital,
                blood_group=blood_group,
                current_stock=current_stock,
                alert_level=alert_level
            )
            
            # Auto-escalate critical alerts
            if alert_level in ['EMERGENCY', 'DEPLETED']:
                # TODO: Send notifications to authorities
                logger.warning(f"CRITICAL ALERT: {hospital.name} - {blood_group} stock at {current_stock} bags")

@csrf_exempt
@require_http_methods(["GET"])
def stakeholder_analytics_api(request):
    """Real-time analytics API for stakeholders"""
    try:
        # Get date range
        days = int(request.GET.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # System-wide statistics
        total_hospitals = EmergencyHospital.objects.filter(is_active=True).count()
        total_inventory = EmergencyBloodStock.objects.aggregate(
            total=Sum('units_available')
        )['total'] or 0
        
        active_alerts = CriticalStockAlert.objects.filter(status='ACTIVE').count()
        
        # Recent requests statistics
        recent_requests = EmergencyRequest.objects.filter(
            created_at__date__gte=start_date
        )
        
        success_rate = 0
        if recent_requests.count() > 0:
            successful = recent_requests.filter(status='COMPLETED').count()
            success_rate = (successful / recent_requests.count()) * 100
        
        # Blood group demand analysis
        blood_demand = {}
        for blood_group, _ in EmergencyBloodStock.BLOOD_GROUPS:
            demand = recent_requests.filter(blood_group=blood_group).count()
            available = EmergencyBloodStock.objects.filter(
                blood_group=blood_group
            ).aggregate(total=Sum('units_available'))['total'] or 0
            
            blood_demand[blood_group] = {
                'demand': demand,
                'available': available,
                'ratio': available / max(demand, 1)
            }
        
        # Social impact metrics
        social_metrics = SocialImpactMetrics.objects.filter(
            date__gte=start_date
        ).aggregate(
            total_lives_saved=Sum('lives_saved'),
            avg_response_time=Avg('response_time_avg'),
            total_free_treatments=Sum('free_treatments'),
            total_emergency_cases=Sum('emergency_cases')
        )
        
        # City-wise distribution
        city_stats = EmergencyHospital.objects.values('city').annotate(
            hospital_count=Count('id'),
            total_inventory=Sum('hospital_blood_stock__units_available')
        ).order_by('-total_inventory')
        
        response_data = {
            'success': True,
            'data': {
                'system_overview': {
                    'total_hospitals': total_hospitals,
                    'total_inventory': total_inventory,
                    'active_alerts': active_alerts,
                    'success_rate': round(success_rate, 1),
                    'total_requests': recent_requests.count(),
                },
                'blood_demand_analysis': blood_demand,
                'social_impact': {
                    'lives_saved': social_metrics['total_lives_saved'] or 0,
                    'avg_response_time': round(social_metrics['avg_response_time'] or 0, 1),
                    'free_treatments': social_metrics['total_free_treatments'] or 0,
                    'emergency_cases': social_metrics['total_emergency_cases'] or 0,
                },
                'city_distribution': list(city_stats),
                'critical_alerts': list(
                    CriticalStockAlert.objects.filter(status='ACTIVE').values(
                        'hospital__name', 'hospital__city', 'blood_group', 
                        'current_stock', 'alert_level', 'created_at'
                    )
                ),
                'recent_updates': list(
                    BloodInventoryUpdate.objects.filter(
                        timestamp__date__gte=start_date
                    ).select_related('hospital', 'updated_by').values(
                        'hospital__name', 'blood_group', 'previous_count',
                        'new_count', 'change_reason', 'timestamp'
                    )[:50]
                ),
                'transparency_metrics': {
                    'verified_hospitals': HospitalRegistration.objects.filter(
                        registration_status='VERIFIED'
                    ).count(),
                    'pending_verifications': HospitalRegistration.objects.filter(
                        registration_status='PENDING'
                    ).count(),
                    'inventory_updates_today': BloodInventoryUpdate.objects.filter(
                        timestamp__date=end_date
                    ).count(),
                },
                'last_updated': timezone.now().isoformat(),
            }
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error in stakeholder analytics API: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to fetch analytics data'
        }, status=500)

def public_transparency_dashboard(request):
    """Public transparency dashboard for social impact"""
    try:
        # Get recent data
        today = timezone.now().date()
        month_ago = today - timedelta(days=30)
        
        # System transparency metrics
        total_hospitals = EmergencyHospital.objects.filter(is_active=True).count()
        verified_hospitals = HospitalRegistration.objects.filter(
            registration_status='VERIFIED'
        ).count()
        
        total_inventory = EmergencyBloodStock.objects.aggregate(
            total=Sum('units_available')
        )['total'] or 0
        
        # Social impact data
        recent_requests = EmergencyRequest.objects.filter(
            created_at__date__gte=month_ago
        )
        
        successful_requests = recent_requests.filter(status='COMPLETED').count()
        
        # Blood availability by type
        blood_availability = {}
        for blood_group, name in EmergencyBloodStock.BLOOD_GROUPS:
            available = EmergencyBloodStock.objects.filter(
                blood_group=blood_group
            ).aggregate(total=Sum('units_available'))['total'] or 0
            
            blood_availability[blood_group] = {
                'name': name,
                'available': available,
                'hospitals': EmergencyBloodStock.objects.filter(
                    blood_group=blood_group,
                    units_available__gt=0
                ).count()
            }
        
        # Success stories (anonymized)
        success_stories = recent_requests.filter(
            status='COMPLETED'
        ).values('blood_group', 'quantity_needed', 'created_at')[:10]
        
        context = {
            'total_hospitals': total_hospitals,
            'verified_hospitals': verified_hospitals,
            'verification_rate': round((verified_hospitals/max(total_hospitals, 1)) * 100, 1),
            'total_inventory': total_inventory,
            'successful_requests': successful_requests,
            'total_requests': recent_requests.count(),
            'success_rate': round((successful_requests/max(recent_requests.count(), 1)) * 100, 1),
            'blood_availability': blood_availability,
            'success_stories': success_stories,
            'last_updated': timezone.now(),
            'page_title': 'Public Transparency Dashboard'
        }
        
        return render(request, 'emergency/transparency_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in transparency dashboard: {e}")
        return render(request, 'emergency/transparency_dashboard.html', {
            'error': 'Unable to load transparency data'
        })

# Quick emergency access - no form version
@csrf_exempt
@require_http_methods(["POST"])
def quick_emergency_request(request):
    """Ultra-quick emergency request with minimal input"""
    try:
        data = json.loads(request.body)
        
        # Only require blood group and phone
        blood_group = data.get('blood_group')
        phone = data.get('phone')
        quantity = int(data.get('quantity', 1))
        
        # Auto-detect location if available
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not blood_group or not phone:
            return JsonResponse({
                'success': False,
                'error': 'Blood group and phone number required'
            }, status=400)
        
        # Create quick request
        emergency_request = EmergencyRequest.objects.create(
            blood_group=blood_group,
            quantity_needed=quantity,
            contact_phone=phone,
            contact_name='Quick Request',
            user_latitude=latitude,
            user_longitude=longitude,
            urgency='CRITICAL',  # All quick requests are critical
            ip_address=get_client_ip(request),
        )
        
        # Immediate processing
        from .views import search_hospitals_and_notify
        search_hospitals_and_notify(emergency_request.id)
        
        return JsonResponse({
            'success': True,
            'request_id': str(emergency_request.request_id),
            'message': 'Emergency request processed immediately',
            'sms_sent': True  # Quick requests always attempt SMS
        })
        
    except Exception as e:
        logger.error(f"Error in quick emergency request: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Emergency request failed'
        }, status=500)

def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip