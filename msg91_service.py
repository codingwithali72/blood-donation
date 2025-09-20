#!/usr/bin/env python
"""
MSG91 SMS service integration for Indian numbers
"""

import requests
import json
from datetime import datetime

class MSG91SMS:
    """MSG91 SMS service for Indian numbers"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or "YOUR_MSG91_API_KEY"
        self.base_url = "https://api.msg91.com/api/v5/flow/"
    
    def send_emergency_sms(self, phone_number, blood_group, quantity, hospitals):
        """Send emergency blood SMS using MSG91"""
        
        # Clean phone number (remove +91)
        clean_number = phone_number.replace('+91', '').replace('-', '').replace(' ', '')
        
        # Create dynamic message
        current_time = datetime.now().strftime('%H:%M')
        area_name = "Panvel area"  # Can be made dynamic
        
        if hospitals and len(hospitals) > 0:
            primary_hospital = hospitals[0]
            
            message = f"""BLOOD AVAILABLE near {area_name}
{quantity} bag {blood_group} found

NEAREST HOSPITAL: {primary_hospital.get('name', 'Noble Hospital, Panvel')}
PHONE: {primary_hospital.get('phone', '+91-022-27452000')}
ADDRESS: {primary_hospital.get('address', 'Sector 2, New Panvel, Maharashtra 410206')}
DISTANCE: {primary_hospital.get('distance', '2.5')}km (~{int(float(primary_hospital.get('distance', '2.5')) * 4)} minutes)

Contact: {primary_hospital.get('phone', '+91-022-27452000')}"""
            
            # Add backup options if available
            if len(hospitals) > 1:
                message += "\n\nBACKUP OPTIONS:"
                for hospital in hospitals[1:3]:  # Next 2 hospitals
                    message += f"\n{hospital.get('name', 'Hospital')} ({hospital.get('distance', '3.0')}km) - {hospital.get('phone', '+91-XXXXXXXXX')}"
            
            # Add request details
            request_id = str(hash(f"{phone_number}{current_time}"))[:8]
            message += f"\n\nRequest ID: {request_id}"
            message += f"\nTime: {current_time} from {area_name}"
            
        else:
            message = f"No hospitals found with {blood_group} blood in {area_name}. Contact local hospitals directly."
        
        return self.send_sms(clean_number, message)
    
    def send_sms(self, mobile, message):
        """Send SMS using MSG91 simple API"""
        
        # Using simple SMS API that works immediately
        url = "https://api.msg91.com/api/sendhttp.php"
        
        payload = {
            'route': '4',
            'sender': 'MSGIND',
            'mobiles': f"91{mobile}",
            'authkey': self.api_key,
            'message': message,
            'country': '91'
        }
        
        try:
            print(f"📱 Sending SMS to: +91{mobile}")
            print(f"📝 Message preview: {message[:100]}...")
            
            response = requests.post(url, data=payload)
            
            print(f"📊 Response Status: {response.status_code}")
            print(f"📊 Response: {response.text}")
            
            if response.status_code == 200:
                response_data = response.text.strip()
                if response_data.startswith('5') or 'success' in response_data.lower():
                    print("✅ SMS sent successfully via MSG91!")
                    return True
                else:
                    print(f"❌ SMS failed: {response_data}")
                    return False
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ MSG91 Error: {e}")
            return False
    
    def send_test_sms(self, mobile):
        """Send test SMS"""
        current_time = datetime.now().strftime('%H:%M')
        
        message = f"""🩸 EMERGENCY BLOOD SYSTEM TEST

This is a test from your Emergency Blood Bank System.

✅ MSG91 Integration: Working
📱 Your Number: +91{mobile}
🕒 Time: {current_time}

System ready for emergency alerts!"""
        
        return self.send_sms(mobile, message)

def test_with_sample_data():
    """Test MSG91 with sample emergency data"""
    print("🧪 TESTING MSG91 SMS SERVICE")
    print("=" * 50)
    
    # Sample API key for demo - you need to get real one
    api_key = "YOUR_MSG91_API_KEY"  # Replace with real key
    
    if api_key == "YOUR_MSG91_API_KEY":
        print("📋 TO GET MSG91 API KEY:")
        print("1. Go to: https://msg91.com/")
        print("2. Sign up (FREE)")
        print("3. Go to API section in dashboard")
        print("4. Copy your API key")
        print("5. Paste it here")
        print()
        
        # For now, let's simulate what the SMS would look like
        print("📱 SAMPLE SMS FOR +919320201572:")
        print("-" * 40)
        
        current_time = datetime.now().strftime('%H:%M')
        sample_message = f"""BLOOD AVAILABLE near Panvel area
3 bag B+ found

NEAREST HOSPITAL: Noble Hospital, Panvel
PHONE: +91-022-27452000
ADDRESS: Sector 2, New Panvel, Maharashtra 410206
DISTANCE: 2.5km (~9 minutes)

Contact: +91-022-27452000

BACKUP OPTIONS:
Lions Blood Bank Panvel (2.8km) - +91-022-27453000
Rotary Blood Bank New Panvel (3.1km) - +91-022-27454000

Request ID: abc12345
Time: {current_time} from Panvel area"""
        
        print(sample_message)
        print("-" * 40)
        print("📱 This is exactly what will be sent to +919320201572!")
        print("\n💡 Get MSG91 API key to enable SMS sending")
        return
    
    # Test with real API key
    msg91 = MSG91SMS(api_key)
    
    # Test simple SMS first
    test_number = "9320201572"
    print(f"📱 Testing simple SMS to +91{test_number}...")
    
    success = msg91.send_test_sms(test_number)
    
    if success:
        print("\n✅ MSG91 Test successful!")
        print("📱 Check your phone for the SMS!")
        
        # Test emergency SMS
        print("\n🩸 Testing emergency blood SMS...")
        
        # Sample hospital data
        hospitals = [
            {
                'name': 'Noble Hospital, Panvel',
                'phone': '+91-022-27452000', 
                'address': 'Sector 2, New Panvel, Maharashtra 410206',
                'distance': '2.5'
            },
            {
                'name': 'Lions Blood Bank Panvel',
                'phone': '+91-022-27453000',
                'address': 'Panvel East, Maharashtra 410206', 
                'distance': '2.8'
            }
        ]
        
        emergency_success = msg91.send_emergency_sms(
            phone_number=f"+91{test_number}",
            blood_group="B+",
            quantity=3,
            hospitals=hospitals
        )
        
        if emergency_success:
            print("\n🎉 EMERGENCY SMS SENT!")
            print("📱 You should receive the emergency blood alert!")
        else:
            print("\n❌ Emergency SMS failed")
    else:
        print("\n❌ MSG91 Test failed")
        print("Check your API key and credits")

if __name__ == "__main__":
    test_with_sample_data()