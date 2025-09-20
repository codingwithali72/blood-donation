from django.urls import path
from . import stakeholder_views

app_name = 'stakeholder'

urlpatterns = [
    # Hospital Dashboard
    path('', stakeholder_views.hospital_dashboard, name='dashboard'),
    path('hospital-dashboard/', stakeholder_views.hospital_dashboard, name='hospital_dashboard'),
    
    # Inventory Management
    path('update-inventory/', stakeholder_views.update_blood_inventory, name='update_inventory'),
    
    # Real-time Analytics API
    path('api/analytics/', stakeholder_views.stakeholder_analytics_api, name='analytics_api'),
    path('api/real-time-stats/', stakeholder_views.stakeholder_analytics_api, name='real_time_stats'),
    
    # Hospital Registration (for new hospitals)
    # path('register/', stakeholder_views.hospital_registration, name='hospital_registration'),
    # path('verify/', stakeholder_views.verify_hospital_registration, name='verify_registration'),
]