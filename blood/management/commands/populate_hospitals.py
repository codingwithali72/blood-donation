from django.core.management.base import BaseCommand
from blood.models import Hospital, HospitalBloodStock
from decimal import Decimal
import random

class Command(BaseCommand):
    help = 'Populate sample hospital data with blood stock'
    
    def handle(self, *args, **options):
        # Sample hospitals data with realistic coordinates
        hospitals_data = [
            {
                'name': 'City General Hospital',
                'address': '123 Main St, Downtown',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'contact_phone': '+91-9876543210',
                'contact_email': 'emergency@citygeneral.com',
                'emergency_contact': '+91-9876543211',
                'latitude': Decimal('19.0760'),
                'longitude': Decimal('72.8777'),
            },
            {
                'name': 'St. Mary\'s Medical Center',
                'address': '456 Health Ave, Medical District',
                'city': 'Delhi',
                'state': 'Delhi',
                'contact_phone': '+91-9876543220',
                'contact_email': 'help@stmarys.org',
                'emergency_contact': '+91-9876543221',
                'latitude': Decimal('28.7041'),
                'longitude': Decimal('77.1025'),
            },
            {
                'name': 'Metro Blood Bank & Hospital',
                'address': '789 Care Blvd, Central Area',
                'city': 'Bangalore',
                'state': 'Karnataka',
                'contact_phone': '+91-9876543230',
                'contact_email': 'contact@metrohealth.in',
                'emergency_contact': '+91-9876543231',
                'latitude': Decimal('12.9716'),
                'longitude': Decimal('77.5946'),
            },
            {
                'name': 'Apollo Emergency Center',
                'address': '321 Apollo Road, Health City',
                'city': 'Chennai',
                'state': 'Tamil Nadu',
                'contact_phone': '+91-9876543240',
                'contact_email': 'emergency@apollo.com',
                'emergency_contact': '+91-9876543241',
                'latitude': Decimal('13.0827'),
                'longitude': Decimal('80.2707'),
            },
            {
                'name': 'Fortis Blood Center',
                'address': '654 Fortis Lane, Medical Hub',
                'city': 'Pune',
                'state': 'Maharashtra',
                'contact_phone': '+91-9876543250',
                'contact_email': 'bloodbank@fortis.in',
                'emergency_contact': '+91-9876543251',
                'latitude': Decimal('18.5204'),
                'longitude': Decimal('73.8567'),
            }
        ]
        
        blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        
        created_count = 0
        updated_count = 0
        
        for hospital_data in hospitals_data:
            hospital, created = Hospital.objects.get_or_create(
                name=hospital_data['name'],
                defaults={
                    **hospital_data,
                    'blood_bank_available': True,
                    'is_partner': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f"Created hospital: {hospital.name}")
            else:
                updated_count += 1
                # Update existing hospital data
                for key, value in hospital_data.items():
                    setattr(hospital, key, value)
                hospital.blood_bank_available = True
                hospital.is_partner = True
                hospital.save()
                self.stdout.write(f"Updated hospital: {hospital.name}")
            
            # Create blood stock for each hospital
            for blood_group in blood_groups:
                stock, stock_created = HospitalBloodStock.objects.get_or_create(
                    hospital=hospital,
                    blood_group=blood_group,
                    defaults={
                        'units_available': random.randint(5, 50)  # Random stock between 5-50 bags
                    }
                )
                
                if stock_created:
                    self.stdout.write(f"  Added {blood_group} stock: {stock.units_available} bags")
                else:
                    # Update stock with random amount
                    stock.units_available = random.randint(5, 50)
                    stock.save()
                    self.stdout.write(f"  Updated {blood_group} stock: {stock.units_available} bags")
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Created {created_count} hospitals, updated {updated_count} hospitals.\n'
                f'All hospitals now have blood stock data populated.'
            )
        )