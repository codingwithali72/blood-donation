"""
Test script for SMS and Email notifications
Run this to test the notification system without creating actual blood requests
"""

from django.test import TestCase
from django.contrib.auth.models import User
from .models import Hospital, HospitalBloodStock, BloodRequest
from .services import LocationService, NotificationService, SMSService
from patient.models import Patient
from donor.models import Donor
from decimal import Decimal

class NotificationTestCase(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testpatient',
            email='test@example.com',
            first_name='Test',
            last_name='Patient'
        )
        
        # Create test patient
        self.patient = Patient.objects.create(
            user=self.user,
            age=30,
            bloodgroup='O+',
            disease='Test condition',
            doctorname='Dr. Test',
            address='Test Address',
            mobile='+919876543210'
        )
        
        # Create test hospital
        self.hospital = Hospital.objects.create(
            name='Test Hospital',
            address='123 Test St',
            city='Mumbai',
            state='Maharashtra',
            contact_phone='+919876543200',
            contact_email='hospital@test.com',
            emergency_contact='+919876543201',
            blood_bank_available=True,
            is_partner=True,
            latitude=Decimal('19.0760'),
            longitude=Decimal('72.8777')
        )
        
        # Create blood stock
        self.stock = HospitalBloodStock.objects.create(
            hospital=self.hospital,
            blood_group='O+',
            units_available=10
        )
    
    def test_location_service(self):
        """Test location calculation"""
        # Test coordinates near Mumbai
        user_lat = 19.0850
        user_lon = 72.8800
        
        nearby = LocationService.find_nearby_hospitals_with_blood(
            user_lat, user_lon, 'O+'
        )
        
        self.assertGreater(len(nearby), 0)
        self.assertEqual(nearby[0]['hospital'].name, 'Test Hospital')
        print(f"Found {len(nearby)} nearby hospitals")
        print(f"Distance to nearest: {nearby[0]['distance']} km")
    
    def test_sms_service(self):
        """Test SMS service (will log warning if Twilio not configured)"""
        result = SMSService.send_sms(
            '+919876543210',
            'Test SMS from Blood Bank Management System'
        )
        # Should return False if Twilio not configured, True if sent
        print(f"SMS send result: {result}")
    
    def test_notification_service(self):
        """Test notification service"""
        # Find nearby hospitals
        nearby = LocationService.find_nearby_hospitals_with_blood(
            19.0850, 72.8800, 'O+'
        )
        
        if nearby:
            result = NotificationService.send_blood_availability_notification(
                self.user, 'O+', nearby
            )
            print(f"Notification send result: {result}")
        else:
            print("No nearby hospitals found for notification test")

# Manual test function (can be called from Django shell)
def run_notification_test():
    """
    Run this function from Django shell to test notifications:
    
    python manage.py shell
    >>> from blood.test_notifications import run_notification_test
    >>> run_notification_test()
    """
    
    # Create test data if needed
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    
    if created:
        print("Created test user")
    
    # Test SMS
    sms_result = SMSService.send_sms(
        '+919876543210',
        'Blood Bank System Test: This is a test SMS message.'
    )
    print(f"SMS test result: {sms_result}")
    
    # Test location service
    mumbai_lat = 19.0760
    mumbai_lon = 72.8777
    
    nearby_hospitals = LocationService.find_nearby_hospitals_with_blood(
        mumbai_lat, mumbai_lon, 'O+'
    )
    
    print(f"Found {len(nearby_hospitals)} hospitals with O+ blood near Mumbai")
    
    for hospital_info in nearby_hospitals[:3]:  # Show top 3
        hospital = hospital_info['hospital']
        distance = hospital_info['distance']
        units = hospital_info['units_available']
        
        print(f"  - {hospital.name}: {distance} km away, {units} bags available")
    
    # Test email notification
    if nearby_hospitals:
        notification_result = NotificationService.send_blood_availability_notification(
            user, 'O+', nearby_hospitals
        )
        print(f"Email notification result: {notification_result}")
    
    print("Test completed!")

if __name__ == '__main__':
    # Can be run as a script for quick testing
    print("Run this from Django shell using: python manage.py shell")
    print(">>> from blood.test_notifications import run_notification_test")
    print(">>> run_notification_test()")