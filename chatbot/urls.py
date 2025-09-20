from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('', views.ChatbotView.as_view(), name='chatbot'),
    path('api/chat/', views.chat_api, name='chat_api'),
    path('api/history/<str:session_id>/', views.chat_history, name='chat_history'),
    path('api/clear/', views.clear_chat, name='clear_chat'),
]