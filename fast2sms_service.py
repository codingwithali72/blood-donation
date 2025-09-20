#!/usr/bin/env python
"""
Fast2SMS integration for Indian mobile numbers
"""

import requests
import json
from datetime import datetime

class Fast2SMS:
    """Fast2SMS service for Indian numbers"""
    
    def __init__(self, api_key=None):
        # You can get a FREE API key from https://www.fast2sms.com/
        self.api_key = api_key or "YOUR_FAST2SMS_API_KEY"  # Replace with real key
        self.base_url = "https://www.fast2sms.com/dev/bulkV2"
        self.headers = {
            'authorization': self.api_key,
            'Content-Type': "application/x-www-form-urlencoded",
            'Cache-Control': "no-cache",
        }
    
    def send_emergency_sms(self, phone_number, blood_group, quantity, hospitals):
        """Send emergency blood SMS using Fast2SMS"""
        
        # Clean phone number (remove +91)
        clean_number = phone_number.replace('+91', '').replace('-', '').replace(' ', '')
        
        # Create dynamic message like your sample
        current_time = datetime.now().strftime('%H:%M')
        area_name = self.get_area_name_from_location()
        
        if hospitals and len(hospitals) > 0:
            primary_hospital = hospitals[0]
            
            message = f"""BLOOD AVAILABLE near {area_name}
{quantity} bag {blood_group} found

NEAREST HOSPITAL: {primary_hospital.get('name', 'Unknown')}
PHONE: {primary_hospital.get('phone', 'N/A')}
ADDRESS: {primary_hospital.get('address', 'N/A')}
DISTANCE: {primary_hospital.get('distance', '0.0')}km (~{int(float(primary_hospital.get('distance', '0')) * 4)} minutes)

Contact: {primary_hospital.get('phone', 'N/A')}"""
            
            # Add backup options if available
            if len(hospitals) > 1:
                message += "\n\nBACKUP OPTIONS:"
                for hospital in hospitals[1:3]:  # Next 2 hospitals
                    message += f"\n{hospital.get('name', 'Unknown')} ({hospital.get('distance', '0.0')}km) - {hospital.get('phone', 'N/A')}"
            
            # Add request details
            request_id = str(hash(f"{phone_number}{current_time}"))[:8]
            message += f"\n\nRequest ID: {request_id}"
            message += f"\nTime: {current_time} from {area_name}"
            
        else:
            message = f"No hospitals found with {blood_group} blood in {area_name}. Contact local hospitals directly."
        
        # Send SMS
        payload = {
            'sender_id': 'FSTSMS',
            'message': message,
            'language': 'english',
            'route': 'p',
            'numbers': clean_number
        }
        
        try:
            print(f"📱 Sending SMS to: +91{clean_number}")
            print(f"📝 Message: {message[:100]}...")
            
            response = requests.post(self.base_url, data=payload, headers=self.headers)
            response_data = response.json()
            
            print(f"📊 Response: {response_data}")
            
            if response.status_code == 200 and response_data.get('return', False):
                print("✅ SMS sent successfully via Fast2SMS!")
                return True
            else:
                print(f"❌ SMS failed: {response_data}")
                return False
                
        except Exception as e:
            print(f"❌ Fast2SMS Error: {e}")
            return False
    
    def get_area_name_from_location(self):
        """Get area name - can be enhanced with actual location data"""
        return "your area"
    
    def send_simple_test(self, phone_number):
        """Send simple test SMS"""
        clean_number = phone_number.replace('+91', '').replace('-', '').replace(' ', '')
        current_time = datetime.now().strftime('%H:%M')
        
        message = f"""🩸 EMERGENCY BLOOD SYSTEM TEST

This is a test message from your Emergency Blood Bank System.

✅ Fast2SMS Integration: Working
📱 Your Number: +91{clean_number}  
🕒 Time: {current_time}

System ready for emergency alerts!"""
        
        payload = {
            'sender_id': 'FSTSMS',
            'message': message,
            'language': 'english',
            'route': 'p',
            'numbers': clean_number
        }
        
        try:
            print(f"📱 Sending test SMS to: +91{clean_number}")
            
            response = requests.post(self.base_url, data=payload, headers=self.headers)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get('return', False):
                print("✅ Test SMS sent successfully!")
                print("📱 Check your phone now!")
                return True
            else:
                print(f"❌ Test failed: {response_data}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

def test_fast2sms():
    """Test Fast2SMS with your number"""
    print("🧪 TESTING FAST2SMS FOR INDIAN NUMBERS")
    print("=" * 50)
    
    # You need to get API key from https://www.fast2sms.com/
    print("📋 TO GET FAST2SMS API KEY:")
    print("1. Go to: https://www.fast2sms.com/")
    print("2. Sign up (FREE)")
    print("3. Get API key from dashboard")
    print("4. Replace 'YOUR_FAST2SMS_API_KEY' below")
    print()
    
    # Your Fast2SMS API key
    api_key = "40DkTJlNExStWPRZzBaUgmYVpXrLyuIjfb8w1sK6CcdGvOiqheqGjtamVQR8NWLC6FidZPwHSfzOJkYe"
    
    if api_key == "YOUR_FAST2SMS_API_KEY":
        print("⚠️ PLEASE GET FAST2SMS API KEY FIRST")
        print("📱 Once you have the API key, I can send test SMS to +919320201572")
        return
    
    fast2sms = Fast2SMS(api_key)
    
    # Test with your number
    test_number = "+919320201572"
    success = fast2sms.send_simple_test(test_number)
    
    if success:
        print("\n🎉 Fast2SMS setup successful!")
        print("📱 You should receive the test SMS shortly")
    else:
        print("\n❌ Fast2SMS setup failed")
        print("Check API key and try again")

if __name__ == "__main__":
    test_fast2sms()