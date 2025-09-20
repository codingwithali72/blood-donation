from django.core.management.base import BaseCommand
from emergency.models import EmergencyHospital, EmergencyBloodStock
import random

class Command(BaseCommand):
    help = 'Seed the database with Panvel and New Panvel area hospitals'

    def handle(self, *args, **options):
        self.stdout.write("🏥 Starting Panvel area hospitals seeding...")
        
        # Panvel and New Panvel area hospitals with real coordinates
        hospitals_data = [
            {
                'name': 'MGM Hospital, New Panvel',
                'address': 'Sector 18, New Panvel, Navi Mumbai, Maharashtra 410206',
                'lat': 19.0330,
                'lng': 73.1197,
                'phone': '+91-022-27471111',
                'email': 'info@mgmhospital.com',
                'emergency_contact': '+91-022-27471100'
            },
            {
                'name': 'Bethany Hospital, New Panvel',
                'address': 'Sector 6, New Panvel, Navi Mumbai, Maharashtra 410206',
                'lat': 19.0375,
                'lng': 73.1250,
                'phone': '+91-022-27450450',
                'email': 'contact@bethanyhospital.com',
                'emergency_contact': '+91-022-27450400'
            },
            {
                'name': 'Shree Hospital, Panvel',
                'address': 'Old Mumbai-Pune Highway, Panvel, Maharashtra 410206',
                'lat': 19.0030,
                'lng': 73.1089,
                'phone': '+91-022-27452200',
                'email': 'info@shreehospital.com',
                'emergency_contact': '+91-022-27452100'
            },
            {
                'name': 'Terna Sahyadri Speciality Hospital, Panvel',
                'address': 'Plot No. 12, Sector 23, New Panvel, Navi Mumbai, Maharashtra 410206',
                'lat': 19.0280,
                'lng': 73.1150,
                'phone': '+91-022-67001000',
                'email': 'info@sahyadrihospitals.com',
                'emergency_contact': '+91-022-67001001'
            },
            {
                'name': 'Apex Superspeciality Hospital, Panvel',
                'address': 'Plot No. 6, Sector 3A, New Panvel, Maharashtra 410206',
                'lat': 19.0395,
                'lng': 73.1205,
                'phone': '+91-022-27481234',
                'email': 'info@apexhospital.in',
                'emergency_contact': '+91-022-27481000'
            },
            {
                'name': 'Medipoint Hospital, Panvel',
                'address': 'Shop No. 1-6, Shivaji Chowk, Old Panvel, Maharashtra 410206',
                'lat': 19.0010,
                'lng': 73.1070,
                'phone': '+91-022-27452525',
                'email': 'contact@medipointhospital.com',
                'emergency_contact': '+91-022-27452500'
            },
            {
                'name': 'Apollo Hospitals, Panvel',
                'address': 'Plot No. 15, Sector 10, New Panvel, Navi Mumbai, Maharashtra 410206',
                'lat': 19.0340,
                'lng': 73.1180,
                'phone': '+91-022-39896969',
                'email': 'panvel@apollohospitals.com',
                'emergency_contact': '+91-022-39896900'
            },
            {
                'name': 'Criticare Hospital, New Panvel',
                'address': 'Plot No. 3, Sector 20, New Panvel, Maharashtra 410206',
                'lat': 19.0320,
                'lng': 73.1220,
                'phone': '+91-022-27451122',
                'email': 'info@criticarehospital.com',
                'emergency_contact': '+91-022-27451100'
            },
            {
                'name': 'Noble Hospital, Panvel',
                'address': 'Mumbai-Pune Highway, Near Railway Station, Panvel, Maharashtra 410206',
                'lat': 19.0020,
                'lng': 73.1100,
                'phone': '+91-022-27452233',
                'email': 'info@noblehospital.com',
                'emergency_contact': '+91-022-27452200'
            },
            {
                'name': 'Cloudnine Hospital, New Panvel',
                'address': 'Plot No. 5, Sector 7, New Panvel, Navi Mumbai, Maharashtra 410206',
                'lat': 19.0360,
                'lng': 73.1170,
                'phone': '+91-022-39401234',
                'email': 'panvel@cloudninehospitals.com',
                'emergency_contact': '+91-022-39401000'
            }
        ]
        
        blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        hospitals_created = 0
        blood_stock_created = 0
        total_blood_bags = 0
        
        for hospital_data in hospitals_data:
            # Check if hospital already exists
            if EmergencyHospital.objects.filter(name=hospital_data['name']).exists():
                self.stdout.write(f"⚠️  Hospital already exists: {hospital_data['name']}")
                continue
                
            # Create hospital with proper coordinates
            hospital = EmergencyHospital.objects.create(
                name=hospital_data['name'],
                address=hospital_data['address'],
                latitude=hospital_data['lat'],
                longitude=hospital_data['lng'],
                phone=hospital_data['phone'],
                emergency_phone=hospital_data['emergency_contact'],
                email=hospital_data['email'],
                is_active=True,
                is_emergency_partner=True,
                operates_24x7=True
            )
            
            self.stdout.write(f"✅ Created: {hospital.name}")
            hospitals_created += 1
            
            # Create blood stock for each blood type
            for blood_type in blood_types:
                # Generate realistic blood stock quantities
                if blood_type in ['O+', 'A+']:
                    # Common blood types - higher stock
                    units = random.randint(8, 25)
                elif blood_type in ['B+', 'AB+']:
                    # Moderate stock
                    units = random.randint(5, 15)
                else:
                    # Rare blood types - lower stock
                    units = random.randint(0, 8)
                
                stock = EmergencyBloodStock.objects.create(
                    hospital=hospital,
                    blood_group=blood_type,
                    units_available=units
                )
                
                blood_stock_created += 1
                total_blood_bags += units
                
                # Alert if stock is critically low
                if units <= 2:
                    self.stdout.write(
                        f"⚠️  Set low stock: {hospital.name} - {blood_type}: {units} bags"
                    )
        
        # Success message
        self.stdout.write("🎉 Panvel area hospitals seeding completed successfully!")
        self.stdout.write("📊 Summary:")
        self.stdout.write(f"   🏥 New hospitals created: {hospitals_created}")
        self.stdout.write(f"   🩸 Blood stock records: {blood_stock_created}")
        self.stdout.write(f"   📦 Total blood bags available: {total_blood_bags}")
        
        self.stdout.write("\n🚀 Ready for emergency requests in Panvel area!")
        
        # Provide sample Panvel coordinates for testing
        self.stdout.write("\n📍 Sample Panvel coordinates for testing:")
        self.stdout.write("   📌 New Panvel Central: 19.0350, 73.1200")
        self.stdout.write("   📌 Old Panvel Station: 19.0020, 73.1090")
        self.stdout.write("   📌 Sector 18, New Panvel: 19.0330, 73.1197")
        self.stdout.write("   📌 Panvel Railway Station: 19.0030, 73.1089")
        self.stdout.write("   📌 New Panvel Sector 10: 19.0340, 73.1180")
        
        self.stdout.write("\n✅ Use these coordinates in the emergency request form!")
        self.stdout.write("🔗 Test URL: http://localhost:8000/emergency/")
        
        # Display total hospital count
        total_hospitals = EmergencyHospital.objects.count()
        self.stdout.write(f"\n📈 Total hospitals in system: {total_hospitals}")