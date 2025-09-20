#!/bin/bash
# Production startup script for Blood Bank Management System

echo "🩸 Blood Bank Management System - Production Startup"
echo "=================================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate || venv\Scripts\activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Run database migrations
echo "🗄️ Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser (optional)
echo "👤 To create an admin user, run: python manage.py createsuperuser"

# Start production server
echo "🚀 Starting production server..."
echo "Access the application at: http://127.0.0.1:8000"
echo "=================================================="

# Use gunicorn for production
if command -v gunicorn &> /dev/null; then
    echo "🔥 Starting with Gunicorn (Production WSGI server)..."
    gunicorn bloodbankmanagement.wsgi:application --bind 0.0.0.0:8000 --workers 3
else
    echo "⚠️ Gunicorn not found, using Django development server..."
    echo "For production, install gunicorn: pip install gunicorn"
    python manage.py runserver 0.0.0.0:8000
fi