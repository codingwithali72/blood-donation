@echo off
cls
echo.
echo =========================================
echo   🩸 BLOOD BANK MANAGEMENT SYSTEM
echo        SERVER STARTING...
echo =========================================
echo.
echo 🌐 Your system will be available at:
echo.
echo    📍 Main System:    http://127.0.0.1:8000/
echo    🏥 Emergency:      http://127.0.0.1:8000/emergency/
echo    👤 Admin Panel:    http://127.0.0.1:8000/admin/
echo    🤖 Chatbot:        http://127.0.0.1:8000/chatbot/
echo.
echo 👤 Admin Login Credentials:
echo    Username: admin
echo    Password: admin123
echo.
echo ⚡ Features Available:
echo    ✅ 2-Click Emergency Blood Requests
echo    ✅ Real-Time Hospital Network (18 hospitals loaded)
echo    ✅ Live Blood Inventory (8 blood types)
echo    ✅ SMS Notifications (Simulated)
echo    ✅ Digital Certificates
echo    ✅ AI Chatbot Integration
echo    ✅ Mobile-Responsive Design
echo.
echo 🚨 Press Ctrl+C to stop the server
echo =========================================
echo.
python manage.py runserver 127.0.0.1:8000