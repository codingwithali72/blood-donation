from django.urls import path
from . import stakeholder_views

app_name = 'quick'

urlpatterns = [
    # Ultra-quick emergency request (no form filling)
    path('', stakeholder_views.quick_emergency_request, name='quick_request'),
    path('emergency/', stakeholder_views.quick_emergency_request, name='emergency'),
    
    # Voice/QR code integration endpoints (future)
    # path('voice/', stakeholder_views.voice_emergency_request, name='voice_request'),
    # path('qr/', stakeholder_views.qr_emergency_request, name='qr_request'),
]