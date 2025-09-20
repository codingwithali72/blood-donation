from django.urls import path
from . import views

app_name = 'emergency'

urlpatterns = [
    # Emergency Request System (No login required)
    path('', views.emergency_home, name='home'),
    path('request/', views.create_emergency_request, name='create_request'),
    path('status/<uuid:request_id>/', views.check_request_status, name='check_status'),
    
    # Public Transparency Dashboard
    path('hospitals/', views.public_hospital_inventory, name='hospital_inventory'),
    path('api/hospitals/', views.api_hospital_inventory, name='api_hospital_inventory'),
    
    # Analytics and Reports
    path('analytics/', views.emergency_analytics, name='analytics'),
    
    # Admin Views (Login required)
    path('admin/', views.emergency_admin_dashboard, name='admin_dashboard'),
]