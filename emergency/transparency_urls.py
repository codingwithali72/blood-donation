from django.urls import path
from . import stakeholder_views

app_name = 'transparency'

urlpatterns = [
    # Public Transparency Dashboard
    path('', stakeholder_views.public_transparency_dashboard, name='dashboard'),
    path('social-impact/', stakeholder_views.public_transparency_dashboard, name='social_impact'),
    
    # Public APIs for transparency
    path('api/public-stats/', stakeholder_views.stakeholder_analytics_api, name='public_stats'),
    
    # Rich vs Poor equality metrics
    path('equity-metrics/', stakeholder_views.public_transparency_dashboard, name='equity_metrics'),
]