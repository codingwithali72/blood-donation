from django.core.management.base import BaseCommand
from blood.models import Sponsor, Hospital

class Command(BaseCommand):
    help = 'Create sample sponsors and hospitals data'

    def handle(self, *args, **options):
        # Create sample sponsors
        sponsors_data = [
            {
                'name': 'LifeSaver Foundation',
                'description': 'Dedicated to supporting blood donation initiatives and saving lives through community outreach.',
                'website': 'https://lifesaver.org',
                'contact_email': 'contact@lifesaver.org',
                'contact_phone': '+91-9876543210',
                'address': '123 Medical Plaza, Health District',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'is_active': True
            },
            {
                'name': 'Red Cross Society',
                'description': 'International humanitarian organization providing emergency assistance and disaster relief.',
                'website': 'https://redcross.org',
                'contact_email': 'info@redcross.org',
                'contact_phone': '+91-9876543211',
                'address': '456 Charity Street, Social Welfare Area',
                'city': 'Delhi',
                'state': 'Delhi',
                'is_active': True
            },
            {
                'name': 'Blood Bank Equipment Suppliers',
                'description': 'Leading provider of medical equipment and supplies for blood banks and healthcare facilities.',
                'website': 'https://bbequipment.com',
                'contact_email': 'sales@bbequipment.com',
                'contact_phone': '+91-9876543212',
                'address': '789 Industrial Area, Medical Equipment Zone',
                'city': 'Pune',
                'state': 'Maharashtra',
                'is_active': True
            },
            {
                'name': 'Care & Cure Hospital',
                'description': 'Multi-specialty hospital committed to providing quality healthcare and supporting blood donation.',
                'website': 'https://careandcure.com',
                'contact_email': 'admin@careandcure.com',
                'contact_phone': '+91-9876543213',
                'address': '321 Hospital Road, Medical District',
                'city': 'Bangalore',
                'state': 'Karnataka',
                'is_active': True
            },
            {
                'name': 'Medical Volunteers Group',
                'description': 'Community organization of healthcare volunteers supporting blood donation drives.',
                'website': 'https://medicalgroup.org',
                'contact_email': 'volunteers@medicalgroup.org',
                'contact_phone': '+91-9876543214',
                'address': '654 Community Center, Volunteer District',
                'city': 'Hyderabad',
                'state': 'Telangana',
                'is_active': True
            },
            {
                'name': 'PixelHub',
                'description': 'Leading digital marketing and web development agency supporting healthcare initiatives through technology and community outreach.',
                'website': 'https://pixelhub.com',
                'contact_email': 'support@pixelhub.com',
                'contact_phone': '+91-9876543215',
                'address': '123 Technology Park, Digital Hub',
                'city': 'Bangalore',
                'state': 'Karnataka',
                'is_active': True
            }
        ]

        for sponsor_data in sponsors_data:
            sponsor, created = Sponsor.objects.get_or_create(
                name=sponsor_data['name'],
                defaults=sponsor_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created sponsor: {sponsor.name}')
                )

        # Create sample hospitals
        hospitals_data = [
            {
                'name': 'Apollo Hospital',
                'address': '15 Greams Lane, Off Greams Road',
                'city': 'Chennai',
                'state': 'Tamil Nadu',
                'contact_phone': '+91-9876543220',
                'contact_email': 'blood@apollo.com',
                'emergency_contact': '+91-44-28293333',
                'is_partner': True,
                'blood_bank_available': True
            },
            {
                'name': 'Fortis Hospital',
                'address': 'Sector 44, Golf Course Road',
                'city': 'Gurgaon',
                'state': 'Haryana',
                'contact_phone': '+91-9876543221',
                'contact_email': 'emergency@fortis.in',
                'emergency_contact': '+91-124-4962200',
                'is_partner': True,
                'blood_bank_available': True
            },
            {
                'name': 'AIIMS',
                'address': 'Ansari Nagar East',
                'city': 'New Delhi',
                'state': 'Delhi',
                'contact_phone': '+91-9876543222',
                'contact_email': 'blood@aiims.edu',
                'emergency_contact': '+91-112-26588500',
                'is_partner': True,
                'blood_bank_available': True
            },
            {
                'name': 'KEM Hospital',
                'address': 'Parel, Acharya Donde Marg',
                'city': 'Mumbai',
                'state': 'Maharashtra',
                'contact_phone': '+91-9876543223',
                'contact_email': 'bloodbank@kem.edu',
                'emergency_contact': '+91-22-24129884',
                'is_partner': True,
                'blood_bank_available': True
            },
            {
                'name': 'SGPGI',
                'address': 'Raebareli Road, Lucknow',
                'city': 'Lucknow',
                'state': 'Uttar Pradesh',
                'contact_phone': '+91-9876543224',
                'contact_email': 'transfusion@sgpgi.ac.in',
                'emergency_contact': '+91-522-2494333',
                'is_partner': True,
                'blood_bank_available': True
            },
            {
                'name': 'Manipal Hospital',
                'address': 'Tiger Circle Road, Madhav Nagar',
                'city': 'Manipal',
                'state': 'Karnataka',
                'contact_phone': '+91-9876543225',
                'contact_email': 'bloodcenter@manipal.edu',
                'emergency_contact': '+91-820-2570170',
                'is_partner': True,
                'blood_bank_available': True
            },
            {
                'name': 'Christian Medical College',
                'address': 'Ida Scudder Road',
                'city': 'Vellore',
                'state': 'Tamil Nadu',
                'contact_phone': '+91-9876543226',
                'contact_email': 'bloodbank@cmcvellore.ac.in',
                'emergency_contact': '+91-416-2284267',
                'is_partner': True,
                'blood_bank_available': True
            },
            {
                'name': 'Ruby Hall Clinic',
                'address': '40, Sassoon Road',
                'city': 'Pune',
                'state': 'Maharashtra',
                'contact_phone': '+91-9876543227',
                'contact_email': 'bloodservices@rubyhall.com',
                'emergency_contact': '+91-20-26127900',
                'is_partner': True,
                'blood_bank_available': True
            }
        ]

        for hospital_data in hospitals_data:
            hospital, created = Hospital.objects.get_or_create(
                name=hospital_data['name'],
                defaults=hospital_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created hospital: {hospital.name}')
                )

        self.stdout.write(
            self.style.SUCCESS('Sample data creation completed!')
        )