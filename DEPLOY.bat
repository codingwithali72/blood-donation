@echo off
echo.
echo ================================
echo   BLOOD BANK MANAGEMENT SYSTEM
echo        DEPLOYMENT SCRIPT
echo ================================
echo.

echo [1/8] Checking Python installation...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo.
echo [2/8] Installing required packages...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install requirements
    pause
    exit /b 1
)

echo.
echo [3/8] Creating environment file...
if not exist .env (
    copy .env.example .env
    echo CREATED: .env file from template
    echo IMPORTANT: Edit .env file with your actual credentials!
) else (
    echo EXISTS: .env file already exists
)

echo.
echo [4/8] Making database migrations...
python manage.py makemigrations
python manage.py makemigrations blood
python manage.py makemigrations donor  
python manage.py makemigrations patient
python manage.py makemigrations chatbot
python manage.py makemigrations emergency

echo.
echo [5/8] Applying database migrations...
python manage.py migrate
if %errorlevel% neq 0 (
    echo ERROR: Database migration failed
    pause
    exit /b 1
)

echo.
echo [6/8] Collecting static files...
python manage.py collectstatic --noinput
if %errorlevel% neq 0 (
    echo WARNING: Static files collection failed (continuing...)
)

echo.
echo [7/8] Creating superuser (admin account)...
echo Creating admin account...
python manage.py shell -c "
from django.contrib.auth.models import User;
from django.contrib.auth.models import Group;

# Create groups
donor_group, created = Group.objects.get_or_create(name='DONOR')
patient_group, created = Group.objects.get_or_create(name='PATIENT')

# Create admin user if doesn't exist
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@bloodbank.com', 'admin123');
    print('Admin user created: username=admin, password=admin123')
else:
    print('Admin user already exists')
"

echo.
echo [8/8] Loading sample data...
python manage.py shell -c "
# Initialize blood stock if empty
from blood.models import Stock
if not Stock.objects.exists():
    blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    for bg in blood_groups:
        Stock.objects.create(bloodgroup=bg, unit=10)
    print('Blood stock initialized with 10 bags each')

# Load Mumbai hospitals for emergency system
from emergency.models import EmergencyHospital, EmergencyBloodStock
if not EmergencyHospital.objects.exists():
    # Sample Mumbai hospitals
    hospitals_data = [
        {'name': 'King Edward Memorial Hospital', 'address': 'Parel, Mumbai', 'phone': '+912224136051', 'emergency_phone': '+912224136000', 'email': 'kem@hospital.gov.in', 'latitude': 19.0330, 'longitude': 72.8427},
        {'name': 'Tata Memorial Hospital', 'address': 'Parel, Mumbai', 'phone': '+912224177000', 'emergency_phone': '+912224177111', 'email': 'tmc@tmc.gov.in', 'latitude': 19.0176, 'longitude': 72.8562},
        {'name': 'Sion Hospital', 'address': 'Sion, Mumbai', 'phone': '+912224076051', 'emergency_phone': '+912224076000', 'email': 'sion@hospital.gov.in', 'latitude': 19.0433, 'longitude': 72.8639},
        {'name': 'JJ Hospital', 'address': 'Byculla, Mumbai', 'phone': '+912223735555', 'emergency_phone': '+912223735000', 'email': 'jj@hospital.gov.in', 'latitude': 18.9736, 'longitude': 72.8323},
        {'name': 'Nair Hospital', 'address': 'Mumbai Central', 'phone': '+912223027643', 'emergency_phone': '+912223027600', 'email': 'nair@hospital.gov.in', 'latitude': 18.9694, 'longitude': 72.8186},
    ]
    
    for hospital_data in hospitals_data:
        hospital = EmergencyHospital.objects.create(**hospital_data)
        # Add blood stock for each hospital
        blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        for bg in blood_groups:
            EmergencyBloodStock.objects.create(
                hospital=hospital,
                blood_group=bg,
                units_available=5 + hash(hospital.name + bg) % 20  # Random stock 5-25
            )
    
    print(f'Loaded {len(hospitals_data)} Mumbai hospitals with blood stock')
"

echo.
echo ================================
echo   DEPLOYMENT COMPLETED! ✅
echo ================================
echo.
echo Your Blood Bank Management System is ready!
echo.
echo 🌐 Access URLs:
echo    Main System: http://127.0.0.1:8000/
echo    Admin Panel: http://127.0.0.1:8000/admin/
echo    Emergency:   http://127.0.0.1:8000/emergency/
echo.
echo 👤 Admin Login:
echo    Username: admin
echo    Password: admin123
echo.
echo 🔧 Next Steps:
echo    1. Edit .env file with your Twilio credentials
echo    2. Run: python manage.py runserver
echo    3. Open browser to http://127.0.0.1:8000/
echo.
echo Press any key to start the server...
pause >nul

echo.
echo Starting development server...
echo.
echo ================================
echo   SERVER STARTING...
echo   Press Ctrl+C to stop
echo ================================
echo.

python manage.py runserver 127.0.0.1:8000