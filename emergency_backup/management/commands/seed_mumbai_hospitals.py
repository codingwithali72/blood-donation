from django.core.management.base import BaseCommand
from django.utils import timezone
from emergency.models import EmergencyHospital, EmergencyBloodStock
import random

class Command(BaseCommand):
    help = 'Seed database with Mumbai hospitals and blood stock data for demo'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🏥 Starting Mumbai hospitals seeding...'))
        
        # Clear existing data
        EmergencyBloodStock.objects.all().delete()
        EmergencyHospital.objects.all().delete()
        
        # Mumbai hospitals with real coordinates
        hospitals_data = [
            {
                'name': 'Lilavati Hospital & Research Centre',
                'address': 'A-791, Bandra Reclamation, Bandra West, Mumbai',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'phone': '022-2656-8000',
                'emergency_phone': '022-2656-8008',
                'email': 'emergency@lilavatihospital.com',
                'latitude': 19.0550,
                'longitude': 72.8295,
            },
            {
                'name': 'KEM Hospital',
                'address': 'Acharya Donde Marg, Parel, Mumbai',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'phone': '022-2410-7000',
                'emergency_phone': '022-2410-7001',
                'email': 'emergency@kemhospital.org',
                'latitude': 19.0030,
                'longitude': 72.8434,
            },
            {
                'name': 'Fortis Hospital Mulund',
                'address': 'Mulund Goregaon Link Road, Mulund West, Mumbai',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'phone': '022-6799-4444',
                'emergency_phone': '022-6799-4445',
                'email': 'emergency@fortismulund.com',
                'latitude': 19.1728,
                'longitude': 72.9566,
            },
            {
                'name': 'JJ Hospital (Grant Medical College)',
                'address': 'JJ Marg, Nagpada, Mumbai Central, Mumbai',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'phone': '022-2373-5555',
                'emergency_phone': '022-2373-5556',
                'email': 'emergency@jjhospital.org',
                'latitude': 18.9697,
                'longitude': 72.8205,
            },
            {
                'name': 'Apollo Hospitals Navi Mumbai',
                'address': 'Plot # 13, Parsik Hill Road, Sector 23, CBD Belapur, Navi Mumbai',
                'city': 'Navi Mumbai',
                'state': 'Maharashtra',
                'phone': '022-3350-3350',
                'emergency_phone': '022-3350-3351',
                'email': 'emergency@apollonavin.com',
                'latitude': 19.0330,
                'longitude': 73.0290,
            },
            {
                'name': 'Kokilaben Dhirubhai Ambani Hospital',
                'address': 'Rao Saheb Achutrao Patwardhan Marg, Four Bunglows, Andheri West, Mumbai',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'phone': '022-4269-6969',
                'emergency_phone': '022-4269-6970',
                'email': 'emergency@kokilabenhospital.com',
                'latitude': 19.1210,
                'longitude': 72.8350,
            },
            {
                'name': 'Hinduja Hospital',
                'address': 'Veer Savarkar Marg, Mahim, Mumbai',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'phone': '022-2445-2222',
                'emergency_phone': '022-2445-2223',
                'email': 'emergency@hindujahospital.com',
                'latitude': 19.0430,
                'longitude': 72.8400,
            },
            {
                'name': 'Breach Candy Hospital',
                'address': '60A, Bhulabhai Desai Marg, Breach Candy, Mumbai',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'phone': '022-2367-8888',
                'emergency_phone': '022-2367-8889',
                'email': 'emergency@breachcandyhospital.org',
                'latitude': 18.9670,
                'longitude': 72.8098,
            },
            {
                'name': 'Tata Memorial Hospital',
                'address': 'Dr E Borges Marg, Parel, Mumbai',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'phone': '022-2417-7000',
                'emergency_phone': '022-2417-7001',
                'email': 'emergency@tmc.gov.in',
                'latitude': 19.0067,
                'longitude': 72.8381,
            },
            {
                'name': 'Jaslok Hospital',
                'address': '15, Dr. Gopalrao Deshmukh Marg, Pedder Road, Mumbai',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'phone': '022-6657-3333',
                'emergency_phone': '022-6657-3334',
                'email': 'emergency@jaslokhospital.net',
                'latitude': 18.9650,
                'longitude': 72.8080,
            },
            {
                'name': 'Global Hospitals Mumbai',
                'address': '35, Dr. E. Borges Road, Hospital Avenue, Opp Shirodkar High school, Parel, Mumbai',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'phone': '022-6700-7000',
                'emergency_phone': '022-6700-7001',
                'email': 'emergency@globalhospitalsindia.com',
                'latitude': 19.0093,
                'longitude': 72.8386,
            },
            {
                'name': 'Wockhardt Hospital Mumbai Central',
                'address': '1877, Dr Anand Rao Nair Road, Near Agripada Police Station, Mumbai Central, Mumbai',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'phone': '022-2659-8888',
                'emergency_phone': '022-2659-8889',
                'email': 'emergency@wockhardthospitals.com',
                'latitude': 18.9725,
                'longitude': 72.8207,
            }
        ]
        
        blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        
        hospitals_created = 0
        stock_created = 0
        
        for hospital_data in hospitals_data:
            # Create hospital
            hospital = EmergencyHospital.objects.create(**hospital_data)
            hospitals_created += 1
            
            # Create blood stock for each blood group
            for blood_group in blood_groups:
                # Generate realistic stock levels
                if blood_group in ['O+', 'A+']:  # Most common blood types
                    stock_range = (10, 30)
                elif blood_group in ['B+', 'AB+']:  # Moderately common
                    stock_range = (5, 20)
                else:  # Rarer blood types
                    stock_range = (2, 15)
                
                units = random.randint(*stock_range)
                
                EmergencyBloodStock.objects.create(
                    hospital=hospital,
                    blood_group=blood_group,
                    units_available=units
                )
                stock_created += 1
            
            self.stdout.write(f'✅ Created: {hospital.name}')
        
        # Create some low stock situations for demo
        low_stock_updates = [
            ('Lilavati Hospital & Research Centre', 'AB-', 1),
            ('KEM Hospital', 'O-', 2),
            ('Fortis Hospital Mulund', 'B-', 0),
            ('JJ Hospital (Grant Medical College)', 'AB-', 1),
        ]
        
        for hospital_name, blood_group, stock_level in low_stock_updates:
            try:
                hospital = EmergencyHospital.objects.get(name=hospital_name)
                stock = EmergencyBloodStock.objects.get(hospital=hospital, blood_group=blood_group)
                stock.units_available = stock_level
                stock.save()
                self.stdout.write(f'⚠️  Set low stock: {hospital_name} - {blood_group}: {stock_level} bags')
            except (EmergencyHospital.DoesNotExist, EmergencyBloodStock.DoesNotExist):
                continue
        
        # Summary
        total_stock = sum([stock.units_available for stock in EmergencyBloodStock.objects.all()])
        
        self.stdout.write(self.style.SUCCESS(f'🎉 Seeding completed successfully!'))
        self.stdout.write(self.style.SUCCESS(f'📊 Summary:'))
        self.stdout.write(f'   🏥 Hospitals created: {hospitals_created}')
        self.stdout.write(f'   🩸 Blood stock records: {stock_created}')
        self.stdout.write(f'   📦 Total blood bags available: {total_stock}')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('🚀 Ready for emergency requests demo!'))
        self.stdout.write('')
        
        # Show some sample coordinates for testing
        self.stdout.write(self.style.HTTP_INFO('📍 Sample coordinates for testing:'))
        sample_locations = [
            ('Dadar, Mumbai', '19.0176, 72.8562'),
            ('Andheri, Mumbai', '19.1136, 72.8697'),
            ('Bandra, Mumbai', '19.0596, 72.8295'),
            ('Lower Parel, Mumbai', '19.0008, 72.8300'),
            ('Powai, Mumbai', '19.1176, 72.9060'),
        ]
        
        for location, coords in sample_locations:
            self.stdout.write(f'   📌 {location}: {coords}')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ Use these coordinates in the emergency request form for demo!'))