from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    EmergencyHospital, 
    EmergencyBloodStock, 
    EmergencyRequest, 
    EmergencyNotification,
    EmergencyAnalytics
)

@admin.register(EmergencyHospital)
class EmergencyHospitalAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'phone', 'emergency_phone', 'is_active', 'is_emergency_partner', 'operates_24x7']
    list_filter = ['is_active', 'is_emergency_partner', 'operates_24x7', 'city', 'state']
    search_fields = ['name', 'city', 'phone', 'emergency_phone']
    list_editable = ['is_active', 'is_emergency_partner']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'address', 'city', 'state')
        }),
        ('Contact Information', {
            'fields': ('phone', 'emergency_phone', 'email')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude')
        }),
        ('Operational Settings', {
            'fields': ('is_active', 'is_emergency_partner', 'operates_24x7', 'opening_time', 'closing_time')
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('hospital_blood_stock')

@admin.register(EmergencyBloodStock)
class EmergencyBloodStockAdmin(admin.ModelAdmin):
    list_display = ['hospital', 'blood_group', 'units_available', 'stock_status', 'last_updated']
    list_filter = ['blood_group', 'hospital__city', 'last_updated']
    search_fields = ['hospital__name', 'blood_group']
    list_editable = ['units_available']
    
    def stock_status(self, obj):
        if obj.units_available == 0:
            return format_html('<span style="color: red;">❌ Out of Stock</span>')
        elif obj.units_available <= 5:
            return format_html('<span style="color: orange;">⚠️ Low Stock</span>')
        else:
            return format_html('<span style="color: green;">✅ Available</span>')
    
    stock_status.short_description = 'Stock Status'

@admin.register(EmergencyRequest)
class EmergencyRequestAdmin(admin.ModelAdmin):
    list_display = ['request_id', 'blood_group', 'quantity_needed', 'status', 'urgency', 'notification_status', 'created_at']
    list_filter = ['status', 'urgency', 'blood_group', 'notification_sent', 'created_at']
    search_fields = ['request_id', 'contact_phone', 'contact_email', 'contact_name']
    readonly_fields = ['request_id', 'created_at', 'updated_at', 'ip_address', 'user_agent']
    
    fieldsets = (
        ('Request Information', {
            'fields': ('request_id', 'blood_group', 'quantity_needed', 'urgency', 'status')
        }),
        ('Location', {
            'fields': ('user_latitude', 'user_longitude', 'user_location_text')
        }),
        ('Contact Information', {
            'fields': ('contact_name', 'contact_phone', 'contact_email')
        }),
        ('System Information', {
            'fields': ('ip_address', 'user_agent', 'session_id'),
            'classes': ['collapse']
        }),
        ('Status Tracking', {
            'fields': ('notification_sent', 'sms_sent', 'email_sent', 'completed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ['collapse']
        }),
        ('Notes', {
            'fields': ('admin_notes', 'user_feedback'),
            'classes': ['collapse']
        })
    )
    
    def notification_status(self, obj):
        status_html = []
        if obj.sms_sent:
            status_html.append('<span style="color: green;">📱 SMS</span>')
        if obj.email_sent:
            status_html.append('<span style="color: blue;">📧 Email</span>')
        if not obj.notification_sent:
            status_html.append('<span style="color: red;">❌ None</span>')
        
        return format_html(' | '.join(status_html) if status_html else '❌ No notifications')
    
    notification_status.short_description = 'Notifications'
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('hospitals_found')

@admin.register(EmergencyNotification)
class EmergencyNotificationAdmin(admin.ModelAdmin):
    list_display = ['request', 'notification_type', 'recipient', 'status', 'sent_at']
    list_filter = ['notification_type', 'status', 'sent_at']
    search_fields = ['recipient', 'subject', 'request__request_id']
    readonly_fields = ['sent_at', 'delivered_at', 'created_at']
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('request', 'notification_type', 'recipient', 'status')
        }),
        ('Message Content', {
            'fields': ('subject', 'message')
        }),
        ('Tracking', {
            'fields': ('sent_at', 'delivered_at', 'provider_response', 'error_message')
        })
    )

@admin.register(EmergencyAnalytics)
class EmergencyAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['date', 'blood_group_display', 'city_display', 'total_requests', 'successful_requests', 'success_rate']
    list_filter = ['date', 'blood_group', 'city']
    search_fields = ['blood_group', 'city']
    date_hierarchy = 'date'
    
    def blood_group_display(self, obj):
        return obj.blood_group or 'All Groups'
    blood_group_display.short_description = 'Blood Group'
    
    def city_display(self, obj):
        return obj.city or 'All Cities'
    city_display.short_description = 'City'
    
    def success_rate(self, obj):
        if obj.total_requests > 0:
            rate = (obj.successful_requests / obj.total_requests) * 100
            color = 'green' if rate >= 80 else 'orange' if rate >= 60 else 'red'
            return format_html(f'<span style="color: {color};">{rate:.1f}%</span>')
        return '0%'
    success_rate.short_description = 'Success Rate'

# Customize admin site
admin.site.site_header = "🩸 Emergency Blood Bank Administration"
admin.site.site_title = "Emergency Blood Bank"
admin.site.index_title = "Emergency System Management"