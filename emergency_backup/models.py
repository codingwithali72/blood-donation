from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
import uuid
from math import radians, cos, sin, asin, sqrt

class EmergencyHospital(models.Model):
    """Enhanced Hospital model with geolocation for emergency requests"""
    
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100, default="Mumbai")
    state = models.CharField(max_length=100, default="Maharashtra")
    
    # Contact Information
    phone = models.CharField(max_length=20)
    emergency_phone = models.CharField(max_length=20, help_text="24/7 Emergency contact")
    email = models.EmailField()
    
    # Geolocation (using decimal fields for simplicity)
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_emergency_partner = models.BooleanField(default=True)
    
    # Operational hours
    operates_24x7 = models.BooleanField(default=True)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Emergency Hospital"
        verbose_name_plural = "Emergency Hospitals"
    
    def __str__(self):
        return f"{self.name} - {self.city}"
    
    def calculate_distance(self, lat, lng):
        """Calculate distance from given coordinates using Haversine formula"""
        try:
            # Convert decimal degrees to radians
            lat1, lng1, lat2, lng2 = map(radians, [float(self.latitude), float(self.longitude), lat, lng])
            
            # Haversine formula
            dlat = lat2 - lat1
            dlng = lng2 - lng1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
            c = 2 * asin(sqrt(a))
            
            # Radius of earth in kilometers
            r = 6371
            return c * r
        except (ValueError, TypeError):
            return float('inf')  # Return infinity if calculation fails
    
    def get_available_blood_types(self):
        """Get all available blood types with their quantities"""
        stocks = self.hospital_blood_stock.filter(units_available__gt=0)
        return {stock.blood_group: stock.units_available for stock in stocks}
    
    def has_sufficient_blood(self, blood_group, quantity):
        """Check if hospital has sufficient blood of given type"""
        try:
            stock = self.hospital_blood_stock.get(blood_group=blood_group)
            return stock.units_available >= quantity
        except EmergencyBloodStock.DoesNotExist:
            return False

class EmergencyBloodStock(models.Model):
    """Blood stock management for emergency hospitals"""
    
    BLOOD_GROUPS = [
        ('A+', 'A Positive'),
        ('A-', 'A Negative'),
        ('B+', 'B Positive'),
        ('B-', 'B Negative'),
        ('AB+', 'AB Positive'),
        ('AB-', 'AB Negative'),
        ('O+', 'O Positive'),
        ('O-', 'O Negative'),
    ]
    
    hospital = models.ForeignKey(EmergencyHospital, on_delete=models.CASCADE, related_name='hospital_blood_stock')
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUPS)
    units_available = models.PositiveIntegerField(default=0, help_text="Available in bags")
    last_updated = models.DateTimeField(auto_now=True)
    
    # Expiration and batch tracking
    expiry_alert_threshold = models.PositiveIntegerField(default=7, help_text="Days before expiry to alert")
    
    class Meta:
        unique_together = ['hospital', 'blood_group']
        verbose_name = "Emergency Blood Stock"
        verbose_name_plural = "Emergency Blood Stocks"
    
    def __str__(self):
        return f"{self.hospital.name} - {self.blood_group}: {self.units_available} bags"
    
    @property
    def in_ml(self):
        """Convert bags to milliliters"""
        return self.units_available * getattr(settings, 'BLOOD_BAG_TO_ML_RATIO', 350)

class EmergencyRequest(models.Model):
    """Emergency blood request model - no login required"""
    
    BLOOD_GROUPS = [
        ('A+', 'A Positive'),
        ('A-', 'A Negative'),
        ('B+', 'B Positive'),
        ('B-', 'B Negative'),
        ('AB+', 'AB Positive'),
        ('AB-', 'AB Negative'),
        ('O+', 'O Positive'),
        ('O-', 'O Negative'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SEARCHING', 'Searching Hospitals'),
        ('FOUND', 'Hospitals Found'),
        ('NOTIFIED', 'User Notified'),
        ('COMPLETED', 'Request Completed'),
        ('FAILED', 'No Hospitals Available'),
    ]
    
    URGENCY_LEVELS = [
        ('CRITICAL', 'Critical - Life Threatening'),
        ('URGENT', 'Urgent - Within Hours'),
        ('ROUTINE', 'Routine - Within Day'),
    ]
    
    # Request ID for tracking
    request_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Required Information (minimal for 2-click)
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUPS)
    quantity_needed = models.PositiveIntegerField(help_text="Required quantity in bags")
    urgency = models.CharField(max_length=20, choices=URGENCY_LEVELS, default='URGENT')
    
    # Location Information
    user_latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    user_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    user_location_text = models.CharField(max_length=500, blank=True, help_text="Manual location if GPS unavailable")
    
    # Optional Contact Information (for follow-up)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_name = models.CharField(max_length=100, blank=True)
    
    # System Information
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_id = models.CharField(max_length=100, blank=True)
    
    # Status and Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    hospitals_found = models.ManyToManyField(EmergencyHospital, blank=True, related_name='emergency_requests')
    notification_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Notes and feedback
    admin_notes = models.TextField(blank=True)
    user_feedback = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Emergency Request"
        verbose_name_plural = "Emergency Requests"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Emergency: {self.blood_group} ({self.quantity_needed} bags) - {self.get_status_display()}"
    
    def get_nearby_hospitals(self, radius_km=None):
        """Find nearby hospitals with required blood type"""
        if not self.user_latitude or not self.user_longitude:
            return EmergencyHospital.objects.none()
        
        if radius_km is None:
            radius_km = getattr(settings, 'EMERGENCY_SEARCH_RADIUS_KM', 25)
        
        # Get all active hospitals
        hospitals = EmergencyHospital.objects.filter(
            is_active=True,
            is_emergency_partner=True
        )
        
        # Filter hospitals with required blood type and sufficient quantity
        available_hospitals = []
        for hospital in hospitals:
            if hospital.has_sufficient_blood(self.blood_group, self.quantity_needed):
                distance = hospital.calculate_distance(
                    float(self.user_latitude), 
                    float(self.user_longitude)
                )
                if distance <= radius_km:
                    available_hospitals.append((hospital, distance))
        
        # Sort by distance
        available_hospitals.sort(key=lambda x: x[1])
        
        # Return top results
        max_results = getattr(settings, 'MAX_EMERGENCY_RESULTS', 10)
        return [hospital for hospital, distance in available_hospitals[:max_results]]
    
    def mark_completed(self):
        """Mark request as completed"""
        self.status = 'COMPLETED'
        self.completed_at = timezone.now()
        self.save()
    
    def get_search_summary(self):
        """Get summary of search results"""
        hospitals = self.get_nearby_hospitals()
        return {
            'total_found': len(hospitals),
            'has_results': len(hospitals) > 0,
            'hospitals': hospitals
        }

class EmergencyNotification(models.Model):
    """Track notifications sent for emergency requests"""
    
    NOTIFICATION_TYPES = [
        ('SMS', 'SMS Message'),
        ('EMAIL', 'Email Message'),
        ('PUSH', 'Push Notification'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent Successfully'),
        ('FAILED', 'Failed to Send'),
        ('DELIVERED', 'Delivered'),
    ]
    
    request = models.ForeignKey(EmergencyRequest, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)
    recipient = models.CharField(max_length=200, help_text="Phone number or email")
    
    # Message Content
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    
    # Status Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Response Tracking
    provider_response = models.TextField(blank=True, help_text="Response from SMS/Email provider")
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Emergency Notification"
        verbose_name_plural = "Emergency Notifications"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type} to {self.recipient} - {self.get_status_display()}"

class EmergencyAnalytics(models.Model):
    """Track analytics for emergency system"""
    
    date = models.DateField()
    
    # Request Statistics
    total_requests = models.PositiveIntegerField(default=0)
    successful_requests = models.PositiveIntegerField(default=0)
    failed_requests = models.PositiveIntegerField(default=0)
    
    # Blood Type Demand
    blood_group = models.CharField(max_length=5, blank=True)
    demand_count = models.PositiveIntegerField(default=0)
    
    # Response Time (in minutes)
    avg_response_time = models.FloatField(default=0.0)
    
    # Location Statistics
    city = models.CharField(max_length=100, blank=True)
    requests_by_city = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Emergency Analytics"
        verbose_name_plural = "Emergency Analytics"
        unique_together = ['date', 'blood_group', 'city']
    
    def __str__(self):
        return f"Analytics for {self.date} - {self.blood_group or 'All'}"