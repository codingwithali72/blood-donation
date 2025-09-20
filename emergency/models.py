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

class HospitalRegistration(models.Model):
    """Hospital/Blood Bank Registration with Government Authentication"""
    
    REGISTRATION_STATUS = [
        ('PENDING', 'Pending Verification'),
        ('VERIFIED', 'Government Verified'),
        ('REJECTED', 'Verification Failed'),
        ('SUSPENDED', 'Temporarily Suspended'),
    ]
    
    FACILITY_TYPES = [
        ('HOSPITAL', 'General Hospital'),
        ('BLOOD_BANK', 'Blood Bank'),
        ('TRAUMA_CENTER', 'Trauma Center'),
        ('SPECIALTY', 'Specialty Hospital'),
        ('GOVERNMENT', 'Government Hospital'),
        ('PRIVATE', 'Private Hospital'),
    ]
    
    # Basic Information
    hospital = models.OneToOneField(EmergencyHospital, on_delete=models.CASCADE, related_name='registration')
    
    # Government Authentication
    government_reg_number = models.CharField(max_length=100, unique=True, help_text="Government Registration Number")
    medical_license_number = models.CharField(max_length=100, help_text="Medical Council License Number")
    blood_bank_license = models.CharField(max_length=100, blank=True, help_text="Blood Bank License (if applicable)")
    
    # Facility Details
    facility_type = models.CharField(max_length=20, choices=FACILITY_TYPES, default='HOSPITAL')
    bed_capacity = models.PositiveIntegerField(help_text="Total bed capacity")
    blood_bank_capacity = models.PositiveIntegerField(default=0, help_text="Blood storage capacity in bags")
    
    # Verification Documents
    registration_certificate = models.FileField(upload_to='hospital_docs/certificates/', help_text="Government Registration Certificate")
    medical_license_doc = models.FileField(upload_to='hospital_docs/licenses/', help_text="Medical License Document")
    authorization_letter = models.FileField(upload_to='hospital_docs/letters/', help_text="Government Authorization Letter")
    
    # Contact Person
    authorized_person_name = models.CharField(max_length=200, help_text="Name of Authorized Person")
    authorized_person_designation = models.CharField(max_length=100, help_text="Designation (e.g., Medical Director)")
    authorized_person_phone = models.CharField(max_length=20)
    authorized_person_email = models.EmailField()
    
    # Status and Verification
    registration_status = models.CharField(max_length=20, choices=REGISTRATION_STATUS, default='PENDING')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="Government Official who verified")
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)
    
    # Social Impact Metrics
    serves_underprivileged = models.BooleanField(default=False, help_text="Serves underprivileged patients")
    free_emergency_quota = models.PositiveIntegerField(default=0, help_text="Free emergency blood bags per month")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Hospital Registration"
        verbose_name_plural = "Hospital Registrations"
    
    def __str__(self):
        return f"{self.hospital.name} - {self.get_registration_status_display()}"

class BloodInventoryUpdate(models.Model):
    """Track hospital inventory updates for transparency"""
    
    hospital = models.ForeignKey(EmergencyHospital, on_delete=models.CASCADE)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, help_text="Hospital staff who updated")
    
    # Previous and New Inventory
    blood_group = models.CharField(max_length=5, choices=EmergencyBloodStock.BLOOD_GROUPS)
    previous_count = models.PositiveIntegerField()
    new_count = models.PositiveIntegerField()
    change_reason = models.CharField(max_length=200, help_text="Reason for inventory change")
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_updates')
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Blood Inventory Update"
        verbose_name_plural = "Blood Inventory Updates"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.hospital.name} - {self.blood_group}: {self.previous_count} → {self.new_count}"

class CriticalStockAlert(models.Model):
    """Critical blood stock alerts with escalation"""
    
    ALERT_LEVELS = [
        ('LOW', 'Low Stock (< 10 bags)'),
        ('CRITICAL', 'Critical Stock (< 5 bags)'),
        ('EMERGENCY', 'Emergency Stock (< 2 bags)'),
        ('DEPLETED', 'Completely Depleted (0 bags)'),
    ]
    
    ALERT_STATUS = [
        ('ACTIVE', 'Active Alert'),
        ('ACKNOWLEDGED', 'Acknowledged'),
        ('RESOLVED', 'Resolved'),
        ('ESCALATED', 'Escalated to Authorities'),
    ]
    
    hospital = models.ForeignKey(EmergencyHospital, on_delete=models.CASCADE)
    blood_group = models.CharField(max_length=5, choices=EmergencyBloodStock.BLOOD_GROUPS)
    current_stock = models.PositiveIntegerField()
    alert_level = models.CharField(max_length=20, choices=ALERT_LEVELS)
    status = models.CharField(max_length=20, choices=ALERT_STATUS, default='ACTIVE')
    
    # Escalation
    authorities_notified = models.BooleanField(default=False)
    escalation_timestamp = models.DateTimeField(null=True, blank=True)
    
    # Resolution
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Critical Stock Alert"
        verbose_name_plural = "Critical Stock Alerts"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.hospital.name} - {self.blood_group} ({self.get_alert_level_display()})"

class SocialImpactMetrics(models.Model):
    """Track social impact and transparency metrics"""
    
    date = models.DateField()
    hospital = models.ForeignKey(EmergencyHospital, on_delete=models.CASCADE, null=True, blank=True)
    
    # Equity Metrics
    total_requests = models.PositiveIntegerField(default=0)
    free_treatments = models.PositiveIntegerField(default=0)
    paid_treatments = models.PositiveIntegerField(default=0)
    
    # Demographics
    rural_patients = models.PositiveIntegerField(default=0)
    urban_patients = models.PositiveIntegerField(default=0)
    emergency_cases = models.PositiveIntegerField(default=0)
    
    # Success Metrics
    lives_saved = models.PositiveIntegerField(default=0)
    response_time_avg = models.FloatField(default=0.0, help_text="Average response time in minutes")
    
    # Transparency Metrics
    public_inventory_views = models.PositiveIntegerField(default=0)
    successful_matches = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Social Impact Metrics"
        verbose_name_plural = "Social Impact Metrics"
        unique_together = ['date', 'hospital']
    
    def __str__(self):
        hospital_name = self.hospital.name if self.hospital else "System-wide"
        return f"{hospital_name} - {self.date}"

class EmergencyAnalytics(models.Model):
    """Enhanced analytics for emergency system with stakeholder insights"""
    
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
    
    # Stakeholder Metrics
    hospitals_active = models.PositiveIntegerField(default=0)
    total_inventory_system = models.PositiveIntegerField(default=0)
    critical_alerts_generated = models.PositiveIntegerField(default=0)
    
    # System Health
    api_response_time = models.FloatField(default=0.0)
    sms_success_rate = models.FloatField(default=0.0)
    
    # Twilio Balance Tracking (when city='TWILIO_BALANCE')
    balance_amount = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="Twilio account balance in USD")
    sms_credits_remaining = models.PositiveIntegerField(null=True, blank=True, help_text="Approximate SMS credits remaining")
    notes = models.TextField(blank=True, help_text="Additional notes or system messages")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Emergency Analytics"
        verbose_name_plural = "Emergency Analytics"
        unique_together = ['date', 'blood_group', 'city']
    
    def __str__(self):
        return f"Analytics for {self.date} - {self.blood_group or 'All'}"
