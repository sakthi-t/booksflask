import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain.schema import HumanMessage, SystemMessage
from flask import current_app

load_dotenv()


class AIService:
    def __init__(self):
        self.client = ChatOpenAI(
            api_key=os.environ.get('OPENAI_API_KEY'),
            model=os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
            temperature=float(os.environ.get('OPENAI_TEMPERATURE', 0.7)),
            max_tokens=int(os.environ.get('OPENAI_MAX_TOKENS', 500))
        )
    
    def get_system_prompt(self, is_admin=False, username=None):
        """Get system prompt based on user type"""
        base_prompt = """You are Taylor, a helpful assistant for BooksCart, an online bookstore. 

IMPORTANT RULES:
1. You ONLY help with BooksCart-related topics: books, orders, accounts, and password resets
2. You NEVER generate images, write code, or help with topics outside BooksCart
3. You are friendly, professional, and concise
4. If asked about anything unrelated to BooksCart, politely redirect to bookstore topics

AVAILABLE INFORMATION:
- Book inventory and availability
- Order status and history
- Account management
- Password reset assistance
"""
        
        if is_admin:
            base_prompt += """
ADMIN PRIVILEGES:
- You can access sales data and revenue information
- You can view any user's order history when asked
- You can provide business analytics and statistics
"""
        else:
            base_prompt += """
USER LIMITATIONS:
- You can only access the current user's own order information
- You cannot view other users' data
- You cannot access sales or business data
"""
        
        base_prompt += f"""
Current user: {username if username else 'Guest'}
Respond naturally and helpfully within these guidelines."""
        
        return base_prompt
    
    def generate_response(self, message, context_data=None, is_admin=False, username=None):
        """Generate AI response using LangChain"""
        try:
            # Create system message
            system_prompt = self.get_system_prompt(is_admin, username)
            
            # Add context data if available
            if context_data:
                system_prompt += f"\n\nCONTEXT DATA:\n{context_data}"
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=message)
            ]
            
            # Generate response
            response = self.client.invoke(messages)
            return response.content
            
        except Exception as e:
            current_app.logger.error(f"AI Service error: {e}")
            return "I'm sorry, I'm having trouble processing your request right now. Please try again later."
    
    def is_bookscart_related(self, message):
        """Check if message is related to BooksCart topics"""
        bookscart_keywords = [
            'book', 'order', 'cart', 'purchase', 'buy', 'genre', 'author', 'title',
            'account', 'password', 'login', 'signup', 'payment', 'shipping',
            'delayed', 'delivered', 'cancelled', 'refund', 'stock', 'available',
            'sales', 'revenue', 'customer', 'user'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in bookscart_keywords)


ai_service = AIService()
