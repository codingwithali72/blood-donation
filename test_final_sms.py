#!/usr/bin/env python
"""
Test SMS with new configuration
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bloodbankmanagement.settings')
django.setup()

from emergency.services import NotificationService
from emergency.models import EmergencyRequest
from django.utils import timezone

def test_sms():
    print("🧪 TESTING FINAL SMS CONFIGURATION")
    print("=" * 50)
    
    # Create a mock emergency request
    class MockEmergencyRequest:
        def __init__(self):
            self.contact_phone = "+919076316961"
            self.blood_group = "B+"
            self.quantity_needed = 3
            self.request_id = "test12345"
            self.created_at = timezone.now()
            self.user_latitude = 19.0330
            self.user_longitude = 73.1197
            
        def get_nearby_hospitals(self):
            # Mock hospital data
            class MockHospital:
                def __init__(self, name, phone, address):
                    self.name = name
                    self.emergency_phone = phone  
                    self.address = address
                
                def calculate_distance(self, lat, lng):
                    return 2.5  # Mock distance
            
            return [
                MockHospital("Noble Hospital, Panvel", "+91-022-27452000", "Sector 2, New Panvel, Maharashtra 410206"),
                MockHospital("Lions Blood Bank Panvel", "+91-022-27453000", "Panvel East, Maharashtra 410206"),
                MockHospital("Rotary Blood Bank New Panvel", "+91-022-27454000", "New Panvel, Maharashtra 410206")
            ]
    
    # Create notification service
    notification_service = NotificationService()
    
    # Create mock request
    mock_request = MockEmergencyRequest()
    hospitals = mock_request.get_nearby_hospitals()
    
    print(f"📱 Testing SMS to: {mock_request.contact_phone}")
    print(f"🩸 Blood Type: {mock_request.blood_group}")
    print(f"📦 Quantity: {mock_request.quantity_needed}")
    print(f"🏥 Hospitals Found: {len(hospitals)}")
    print()
    
    # Send SMS
    try:
        success = notification_service.send_emergency_sms(mock_request, hospitals)
        
        if success:
            print("🎉 SMS SENT SUCCESSFULLY!")
            print("📱 Check your phone for the emergency blood SMS!")
        else:
            print("❌ SMS FAILED")
            print("Check the logs above for error details")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_sms()