from flask import session, current_app
from app.models import User, Book, Order, OrderItem, GenreEnum
from app import db
from app.utils.ai_service import ai_service
from sqlalchemy import func
import re


class ChatbotService:
    def __init__(self):
        pass
    
    def get_admin_email(self):
        """Get admin email from config when needed"""
        try:
            return current_app.config.get('ADMIN_EMAIL', 't.shakthi@gmail.com')
        except RuntimeError:
            # Fallback if no app context
            return 't.shakthi@gmail.com'
    
    def is_admin(self, user_email):
        """Check if user is admin"""
        return user_email == self.get_admin_email()  # ✅ FIXED: Use method instead
    
    def process_message(self, message, user=None):
        """Process chatbot message and return response"""
        print(f"ChatbotService.process_message called with:")
        print(f"  Message: '{message}'")
        print(f"  User: {user.username if user else 'None'}")
        
        try:
            message_lower = message.lower().strip()
            
            # Initialize chat memory if not exists
            if 'chat_memory' not in session:
                session['chat_memory'] = {
                    'context': None,
                    'awaiting': None,
                    'last_query': None
                }
            
            # Handle non-logged-in users (only password reset)
            if not user:
                print("Processing as non-logged-in user")
                if any(phrase in message_lower for phrase in ['forgot password', 'reset password', 'password']):
                    return self._handle_password_reset_request(None)
                else:
                    # Use AI for polite redirect
                    print("Generating AI response for non-logged-in user")
                    ai_response = ai_service.generate_response(
                        "User is not logged in and asking about something other than password reset. Politely tell them they need to login first but can reset password if forgotten.",
                        username="Guest"
                    )
                    return {
                        'message': ai_response,
                        'type': 'login_required'
                    }
            
            # Handle logged-in users
            print(f"Processing as logged-in user: {user.username}")
            print(f"User email: {user.email}")
            
            # Check if admin
            is_admin = self.is_admin(user.email)
            print(f"User is admin: {is_admin}")
            
            # Check if message is BooksCart related
            print("Checking if message is BooksCart related...")
            if not ai_service.is_bookscart_related(message):
                print("Message is not BooksCart related - generating redirect response")
                ai_response = ai_service.generate_response(
                    f"User asked: '{message}' which is not related to BooksCart. Politely redirect them to ask about books, orders, or account topics.",
                    username=user.username
                )
                return {
                    'message': ai_response,
                    'type': 'off_topic'
                }
            
            # Password reset flow (for logged-in users too)
            if any(phrase in message_lower for phrase in ['forgot password', 'reset password']):
                print("Processing password reset request")
                return self._handle_password_reset_request(user)
            
            # Get relevant data based on message intent
            print("Gathering context data...")
            try:
                context_data = self._gather_context_data(message, user)
                print(f"Context data gathered: {len(context_data) if context_data else 0} characters")
            except Exception as e:
                print(f"ERROR gathering context data: {e}")
                context_data = ""
            
            # Generate AI response with context
            print("Generating AI response...")
            try:
                ai_response = ai_service.generate_response(
                    message,
                    context_data=context_data,
                    is_admin=is_admin,
                    username=user.username
                )
                print(f"AI response generated successfully")
            except Exception as e:
                print(f"ERROR generating AI response: {e}")
                return {
                    'message': f"I'm having trouble processing your request right now. Please try a simpler question.",
                    'type': 'ai_error'
                }
            
            return {
                'message': ai_response,
                'type': 'ai_response'
            }
            
        except Exception as e:
            print(f"ERROR in ChatbotService.process_message: {e}")
            import traceback
            traceback.print_exc()
            raise e
    
    def _handle_password_reset_request(self, user):
        """Handle password reset request"""
        return {
            'message': "I can help you reset your password! Please provide your registered email address and I'll send you a secure reset link.",
            'type': 'password_reset',
            'show_email_input': True
        }
    
    def _gather_context_data(self, message, user):
        """Gather relevant context data based on message content"""
        message_lower = message.lower()
        context_parts = []
        
        # Book-related queries
        if any(word in message_lower for word in ['book', 'title', 'author', 'available', 'stock']):
            context_parts.append(self._get_book_context(message))
        
        # Genre queries
        if 'genre' in message_lower:
            context_parts.append(self._get_genre_context())
        
        # Order queries
        if any(word in message_lower for word in ['order', 'purchase', 'bought', 'delayed']):
            if self.is_admin(user.email):
                # Check if admin is asking about specific user
                username = self._extract_username(message)
                if username:
                    context_parts.append(self._get_user_orders_context(username))
                else:
                    context_parts.append(self._get_user_orders_context(user.username))
            else:
                context_parts.append(self._get_user_orders_context(user.username))
        
        # Sales data (admin only)
        if self.is_admin(user.email) and any(word in message_lower for word in ['sales', 'revenue', 'total']):
            context_parts.append(self._get_sales_context())
        
        return '\n\n'.join(filter(None, context_parts))
    
    def _get_book_context(self, message):
        """Get book-related context"""
        book_info = self._extract_book_info(message)
        
        if book_info:
            books = Book.query.filter(
                db.or_(
                    Book.title.ilike(f'%{book_info}%'),
                    Book.author.ilike(f'%{book_info}%')
                )
            ).limit(10).all()
            
            if books:
                context = f"Books matching '{book_info}':\n"
                for book in books:
                    stock_status = "In Stock" if book.stock > 0 else "Out of Stock"
                    context += f"- {book.title} by {book.author} | Genre: {book.genre.value} | Price: ${book.price:.2f} | {stock_status} ({book.stock} available)\n"
                return context
        
        # General book inventory
        total_books = Book.query.count()
        return f"Total books in inventory: {total_books}"
    
    def _get_genre_context(self):
        """Get genre-related context"""
        genres = db.session.query(Book.genre, func.count(Book.id)).group_by(Book.genre).all()
        
        if genres:
            context = "Available genres:\n"
            for genre, count in genres:
                context += f"- {genre.value.title()}: {count} books\n"
            return context
        
        return "No genres available in current inventory."
    
    def _get_user_orders_context(self, username):
        """Get user order context"""
        user = User.query.filter_by(username=username).first()
        if not user:
            return f"No user found with username '{username}'"
        
        orders = Order.query.filter_by(user_id=user.id).order_by(Order.created_at.desc()).limit(10).all()
        
        if orders:
            context = f"Orders for {username}:\n"
            for order in orders:
                items_count = len(order.items)
                context += f"- Order #{order.id} | Date: {order.created_at.strftime('%Y-%m-%d')} | Status: {order.status} | Total: ${order.total_amount:.2f} | Items: {items_count}\n"
                
                # Add item details for recent orders
                if order.status == 'delayed':
                    context += f"  Delayed items: {', '.join([item.book.title for item in order.items[:3]])}\n"
            return context
        
        return f"No orders found for {username}"
    
    def _get_sales_context(self):
        """Get sales context (admin only)"""
        total_sales = db.session.query(func.sum(Order.total_amount)).scalar() or 0
        total_orders = Order.query.count()
        
        # Sales by status
        status_breakdown = db.session.query(
            Order.status, func.count(Order.id), func.sum(Order.total_amount)
        ).group_by(Order.status).all()
        
        context = f"Sales Summary:\n"
        context += f"- Total Revenue: ${total_sales:.2f}\n"
        context += f"- Total Orders: {total_orders}\n"
        context += f"Status Breakdown:\n"
        
        for status, count, amount in status_breakdown:
            context += f"  {status.title()}: {count} orders (${amount or 0:.2f})\n"
        
        return context
    
    def _extract_book_info(self, message):
        """Extract book title or author from message"""
        # Remove common words and extract meaningful terms
        stop_words = ['is', 'are', 'do', 'you', 'have', 'available', 'book', 'books', 'by', 'author', 'how', 'many']
        words = message.lower().split()
        meaningful_words = [word for word in words if word not in stop_words and len(word) > 2]
        
        if meaningful_words:
            return ' '.join(meaningful_words)
        return None
    
    def _extract_username(self, message):
        """Extract username from message"""
        patterns = [
            r'orders?\s+(?:by|for)\s+(\w+)',
            r'(\w+)\'?s?\s+orders?',
            r'user\s+(\w+)',
            r'customer\s+(\w+)',
            r'(?:test|mark|karthi|admin)\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message.lower())
            if match:
                return match.group(1) if match.lastindex else match.group(0)
        return None


chatbot_service = ChatbotService()
