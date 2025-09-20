from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
import json
import uuid
# Optional imports for Google Generative AI
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None
from .models import ChatSession, ChatMessage
from .forms import ChatMessageForm
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyCHtgnihAZq6KC4r9B1vsayIT8wOJyYPXE"
if GEMINI_AVAILABLE and genai:
    genai.configure(api_key=GEMINI_API_KEY)

class ChatbotView(View):
    """Main chatbot view"""
    
    def get(self, request):
        """Render the chatbot interface"""
        form = ChatMessageForm()
        context = {
            'form': form,
            'page_title': 'Blood Bank Assistant',
            'page_description': 'Get instant help with blood donation queries'
        }
        return render(request, 'chatbot/chatbot.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def chat_api(request):
    """API endpoint for chat messages"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id', '')
        
        if not user_message:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        
        # Get or create session
        if not session_id:
            session_id = str(uuid.uuid4())
        
        session, created = ChatSession.objects.get_or_create(
            session_id=session_id,
            defaults={
                'user': request.user if request.user.is_authenticated else None,
                'is_active': True
            }
        )
        
        # Save user message
        ChatMessage.objects.create(
            session=session,
            message_type='user',
            content=user_message
        )
        
        # Generate bot response
        bot_response = generate_bot_response(user_message, session)
        
        # Save bot response
        ChatMessage.objects.create(
            session=session,
            message_type='bot',
            content=bot_response
        )
        
        return JsonResponse({
            'response': bot_response,
            'session_id': session_id,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Chat API error: {str(e)}")
        return JsonResponse({
            'error': 'Sorry, I encountered an error. Please try again.',
            'status': 'error'
        }, status=500)


def generate_bot_response(user_message, session):
    """Generate response using Gemini API with blood bank context"""
    
    # Blood bank context for the AI
    blood_bank_context = """
    You are a helpful assistant for a Blood Bank Management System. You help users with:
    
    BLOOD DONATION INFORMATION:
    - Blood donation eligibility requirements
    - Benefits of blood donation
    - Donation process and what to expect
    - Post-donation care instructions
    - Blood donation frequency guidelines
    
    BLOOD TYPES & COMPATIBILITY:
    - Blood group information (A+, A-, B+, B-, AB+, AB-, O+, O-)
    - Universal donors and recipients
    - Blood compatibility for transfusions
    
    BLOOD BANK SERVICES:
    - How to register as a donor
    - How to request blood
    - Blood camp information
    - Hospital partnerships
    - Certificate system for donors
    
    HEALTH & SAFETY:
    - Pre-donation health requirements
    - Safety measures during donation
    - When not to donate blood
    - Recovery after donation
    
    GENERAL GUIDELINES:
    - Keep responses helpful, accurate, and supportive
    - If medical advice is needed, recommend consulting healthcare professionals
    - Be encouraging about blood donation while emphasizing safety
    - Provide clear, easy-to-understand information
    
    Answer the user's question in a friendly, informative way focused on blood bank services.
    """
    
    try:
        # Check if Gemini is available
        if not GEMINI_AVAILABLE or not genai:
            raise Exception("Gemini API not available")
            
        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-pro')
        
        # Get conversation history for context
        recent_messages = ChatMessage.objects.filter(
            session=session
        ).order_by('-created_at')[:10]
        
        conversation_history = ""
        for msg in reversed(recent_messages):
            if msg.message_type == 'user':
                conversation_history += f"User: {msg.content}\n"
            elif msg.message_type == 'bot':
                conversation_history += f"Assistant: {msg.content}\n"
        
        # Construct the prompt
        prompt = f"""
        {blood_bank_context}
        
        Previous conversation:
        {conversation_history}
        
        Current user message: {user_message}
        
        Please provide a helpful response focused on blood bank services and information.
        """
        
        # Generate response
        response = model.generate_content(prompt)
        
        if response and response.text:
            return response.text.strip()
        else:
            return "I apologize, but I couldn't generate a response at the moment. Please try asking your question again."
            
    except Exception as e:
        logger.error(f"Gemini API error: {str(e)}")
        
        # Fallback responses for common queries
        user_message_lower = user_message.lower()
        
        if any(word in user_message_lower for word in ['donate', 'donation', 'donor']):
            return """
            🩸 **Blood Donation Information**
            
            To donate blood, you need to:
            - Be 18-65 years old
            - Weigh at least 50kg
            - Be in good health
            - Have not donated in the last 3 months
            
            Benefits of donating blood:
            - Save up to 3 lives with one donation
            - Regular health check-up
            - Earn certificates based on donations
            - Join our community of life-savers
            
            Would you like to know more about the donation process or how to register?
            """
        
        elif any(word in user_message_lower for word in ['blood type', 'blood group', 'compatible']):
            return """
            🩸 **Blood Types & Compatibility**
            
            **Blood Groups:** A+, A-, B+, B-, AB+, AB-, O+, O-
            
            **Universal Donors:**
            - O- can donate to anyone
            - O+ can donate to all positive types
            
            **Universal Recipients:**
            - AB+ can receive from anyone
            - AB- can receive from all negative types
            
            Need to know your blood type compatibility? I can help you understand transfusion compatibility!
            """
        
        elif any(word in user_message_lower for word in ['register', 'signup', 'account']):
            return """
            📝 **Registration Information**
            
            You can register as:
            
            **Donor:** To donate blood and help save lives
            - Fill donor registration form
            - Provide Aadhaar number for verification
            - Upload profile picture
            - Get dashboard to track donations
            
            **Patient:** To request blood when needed
            - Medical information required
            - Doctor details needed
            - Track request status
            
            Visit our registration page to get started!
            """
        
        else:
            return """
            Hello! I'm your Blood Bank Assistant. I can help you with:
            
            🩸 Blood donation information
            🏥 Blood bank services
            📝 Registration process
            🩸 Blood types and compatibility
            🏆 Certificate program for donors
            🏥 Hospital partnerships
            
            What would you like to know about?
            """


@require_http_methods(["GET"])
def chat_history(request, session_id):
    """Get chat history for a session"""
    try:
        session = get_object_or_404(ChatSession, session_id=session_id)
        
        # Check if user has access to this session
        if request.user.is_authenticated and session.user != request.user:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        messages = ChatMessage.objects.filter(session=session).order_by('created_at')
        
        history = []
        for message in messages:
            history.append({
                'type': message.message_type,
                'content': message.content,
                'timestamp': message.created_at.isoformat()
            })
        
        return JsonResponse({
            'history': history,
            'session_id': session_id,
            'status': 'success'
        })
        
    except Exception as e:
        logger.error(f"Chat history error: {str(e)}")
        return JsonResponse({'error': 'Failed to load chat history'}, status=500)


def clear_chat(request):
    """Clear current chat session"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id')
            
            if session_id:
                session = ChatSession.objects.filter(session_id=session_id).first()
                if session:
                    # Mark session as inactive instead of deleting
                    session.is_active = False
                    session.save()
            
            return JsonResponse({'status': 'success', 'message': 'Chat cleared'})
            
        except Exception as e:
            logger.error(f"Clear chat error: {str(e)}")
            return JsonResponse({'error': 'Failed to clear chat'}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)