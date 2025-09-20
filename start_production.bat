@echo off
echo Starting Blood Bank Management System in Production Mode...
echo.

cd /d "e:\System.me\internal project\qocdrer\fr\ret"

echo Collecting static files...
python manage.py collectstatic --noinput
echo.

echo Running database migrations...
python manage.py migrate
echo.

echo Creating sample data (if needed)...
python manage.py create_sample_data
echo.

echo Starting production server...
echo Server will be available at: http://127.0.0.1:8000
echo Press Ctrl+C to stop the server
echo.
echo Note: This is production mode with DEBUG=False
echo All static files are served via WhiteNoise
echo.

python manage.py runserver 127.0.0.1:8000 --insecure
