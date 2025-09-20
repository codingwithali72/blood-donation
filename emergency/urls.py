from django.urls import path, include
from . import views
from . import sms_handler
from . import stakeholder_views

app_name = 'emergency'

urlpatterns = [
    # Emergency Request System (No login required)
    path('', views.emergency_home, name='home'),
    path('request/', views.create_emergency_request, name='create_request'),
    path('status/<uuid:request_id>/', views.check_request_status, name='check_status'),
    
    # Public Transparency Dashboard
    path('hospitals/', views.public_hospital_inventory, name='hospital_inventory'),
    path('api/hospitals/', views.public_hospital_inventory, name='public_hospital_inventory'),
    
    # Enhanced Location-based APIs
    path('api/find-hospitals/', views.api_find_nearby_hospitals, name='api_find_hospitals'),
    path('api/live-inventory/', views.api_live_inventory, name='api_live_inventory'),
    path('api/enhanced-request/', views.api_enhanced_location_request, name='api_enhanced_request'),
    
    # SMS Webhook for two-way communication
    path('sms/webhook/', sms_handler.sms_webhook, name='sms_webhook'),
    path('sms/status/', sms_handler.SMSStatusHandler.status_callback, name='sms_status'),
    
    # Analytics and Reports
    path('analytics/', views.emergency_analytics, name='analytics'),
    
    # Stakeholder Features
    path('stakeholder-dashboard/', stakeholder_views.hospital_dashboard, name='stakeholder_dashboard'),
    path('api/stakeholder-analytics/', stakeholder_views.stakeholder_analytics_api, name='stakeholder_analytics_api'),
    path('api/update-inventory/', stakeholder_views.update_blood_inventory, name='update_inventory_api'),
    
    # Public Transparency
    path('transparency/', stakeholder_views.public_transparency_dashboard, name='transparency_dashboard'),
    
    # Quick Emergency (No-form)
    path('quick-request/', stakeholder_views.quick_emergency_request, name='quick_emergency_request'),
    
    # Admin Views (Login required)
    path('admin/', views.emergency_admin_dashboard, name='admin_dashboard'),
]
