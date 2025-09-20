"""bloodbankmanagement URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.contrib.auth.views import LogoutView,LoginView
from django.conf import settings
from django.conf.urls.static import static
from blood import views
urlpatterns = [
    path('admin/', admin.site.urls),

    path('emergency/', include('emergency.urls')),  # Emergency system (no login required)
    path('chatbot/', include('chatbot.urls')),
    path('donor/',include('donor.urls')),
    path('patient/',include('patient.urls')),

    
    path('',views.home_view,name=''),
    path('loginregister', views.loginregister_view, name='loginregister'),
    path('logout', LogoutView.as_view(template_name='blood/logout.html'),name='logout'),

    path('afterlogin', views.afterlogin_view,name='afterlogin'),
    path('adminlogin', LoginView.as_view(template_name='blood/adminlogin.html'),name='adminlogin'),
    path('admin-dashboard', views.admin_dashboard_view,name='admin-dashboard'),
    path('admin-blood', views.admin_blood_view,name='admin-blood'),
    path('admin-donor', views.admin_donor_view,name='admin-donor'),
    path('admin-patient', views.admin_patient_view,name='admin-patient'),
    path('update-donor/<int:pk>', views.update_donor_view,name='update-donor'),
    path('delete-donor/<int:pk>', views.delete_donor_view,name='delete-donor'),
    path('admin-request', views.admin_request_view,name='admin-request'),
    path('update-patient/<int:pk>', views.update_patient_view,name='update-patient'),
    path('delete-patient/<int:pk>', views.delete_patient_view,name='delete-patient'),
    path('admin-donation', views.admin_donation_view,name='admin-donation'),
    path('approve-donation/<int:pk>', views.approve_donation_view,name='approve-donation'),
    path('reject-donation/<int:pk>', views.reject_donation_view,name='reject-donation'),
    path('admin-request-history', views.admin_request_history_view,name='admin-request-history'),
    path('update-approve-status/<int:pk>', views.update_approve_status_view,name='update-approve-status'),
    path('update-reject-status/<int:pk>', views.update_reject_status_view,name='update-reject-status'),
    
    # Gamification and Certificate URLs
    path('donor-certificates', views.donor_certificates_view, name='donor-certificates'),
    path('download-certificate/<str:certificate_id>', views.download_certificate_view, name='download-certificate'),
    
    # Blood Camp URLs
    path('admin-blood-camps', views.admin_blood_camps_view, name='admin-blood-camps'),
    path('add-blood-camp', views.add_blood_camp_view, name='add-blood-camp'),
    path('blood-camps', views.blood_camps_list_view, name='blood-camps'),
    path('register-camp/<int:camp_id>', views.register_for_camp_view, name='register-camp'),
    
    # Sponsor and Hospital URLs
    path('admin-sponsors', views.admin_sponsors_view, name='admin-sponsors'),
    path('admin-hospitals', views.admin_hospitals_view, name='admin-hospitals'),
    path('sponsors', views.sponsors_list_view, name='sponsors'),
    path('hospitals', views.hospitals_list_view, name='hospitals'),
    
    # Legal Pages
    path('blood/terms', views.terms_view, name='terms'),
    path('blood/privacy', views.privacy_view, name='privacy'),
   
]

# Serve static and media files
if settings.DEBUG:
    # Development - serve from STATICFILES_DIRS
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Production - serve from STATIC_ROOT
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
