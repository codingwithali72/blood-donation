#!/bin/bash

echo "Starting Railway deployment..."

# Install any new dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run database migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Create superuser and load data
echo "Setting up initial data..."
python manage.py shell -c "
import os
from django.contrib.auth.models import User, Group
from blood.models import Stock
from emergency.models import EmergencyHospital, EmergencyBloodStock

print('Creating user groups...')
Group.objects.get_or_create(name='DONOR')
Group.objects.get_or_create(name='PATIENT')

print('Creating admin user...')
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@bloodbank.com', 'admin123')
    print('Admin user created: admin/admin123')
else:
    print('Admin user already exists')

print('Initializing blood stock...')
if not Stock.objects.exists():
    blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    for bg in blood_groups:
        Stock.objects.create(bloodgroup=bg, unit=15)
    print(f'Blood stock initialized with {len(blood_groups)} types')
else:
    print('Blood stock already exists')

print('Loading Mumbai hospitals...')
if not EmergencyHospital.objects.exists():
    hospitals_data = [
        {'name': 'King Edward Memorial Hospital', 'address': 'Parel, Mumbai', 'phone': '+912224136051', 'emergency_phone': '+912224136000', 'email': 'kem@hospital.gov.in', 'latitude': 19.0330, 'longitude': 72.8427},
        {'name': 'Tata Memorial Hospital', 'address': 'Parel, Mumbai', 'phone': '+912224177000', 'emergency_phone': '+912224177111', 'email': 'tmc@tmc.gov.in', 'latitude': 19.0176, 'longitude': 72.8562},
        {'name': 'Sion Hospital', 'address': 'Sion, Mumbai', 'phone': '+912224076051', 'emergency_phone': '+912224076000', 'email': 'sion@hospital.gov.in', 'latitude': 19.0433, 'longitude': 72.8639},
        {'name': 'JJ Hospital', 'address': 'Byculla, Mumbai', 'phone': '+912223735555', 'emergency_phone': '+912223735000', 'email': 'jj@hospital.gov.in', 'latitude': 18.9736, 'longitude': 72.8323},
        {'name': 'Nair Hospital', 'address': 'Mumbai Central', 'phone': '+912223027643', 'emergency_phone': '+912223027600', 'email': 'nair@hospital.gov.in', 'latitude': 18.9694, 'longitude': 72.8186},
    ]
    
    for hospital_data in hospitals_data:
        hospital = EmergencyHospital.objects.create(**hospital_data)
        blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        for bg in blood_groups:
            EmergencyBloodStock.objects.create(
                hospital=hospital,
                blood_group=bg,
                units_available=15
            )
    
    print(f'Loaded {len(hospitals_data)} Mumbai hospitals with blood stock')
else:
    print('Hospitals already loaded')

print('Data setup completed successfully!')
"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the server
echo "Starting Gunicorn server..."
exec gunicorn bloodbankmanagement.wsgi:application --bind 0.0.0.0:$PORT --workers 3