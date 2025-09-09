from flask import render_template, request, jsonify, session, redirect, url_for, flash
from app import csrf
from app.chatbot import bp
from app.models import User
from app.utils.chatbot_service import chatbot_service
from app.utils.email_service import EmailService
from app.utils.rate_limiter import rate_limiter
from email_validator import validate_email, EmailNotValidError


@bp.route('/api/message', methods=['POST'])
@csrf.exempt
def process_message():
    """Process chatbot messages - works for both logged-in and non-logged-in users"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        # Get current user if logged in
        user = None
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
        
        # Process message with chatbot service
        response = chatbot_service.process_message(message, user)
        
        return jsonify({
            'success': True,
            'response': response,
            'user_info': {
                'username': user.username if user else None,
                'is_admin': chatbot_service.is_admin(user.email) if user else False,
                'logged_in': user is not None
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/password-reset', methods=['POST'])
@csrf.exempt
def request_password_reset():
    """Handle password reset request from chatbot - works for non-logged-in users too"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip()
        
        # Validate email format
        try:
            validate_email(email)
        except EmailNotValidError:
            return jsonify({
                'success': False,
                'message': 'Please provide a valid email address.'
            })
        
        # Check rate limiting
        if not rate_limiter.can_attempt_reset(email):
            return jsonify({
                'success': False,
                'message': 'Too many password reset attempts. Please try again later.'
            })
        
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        if not user:
            # Don't reveal whether email exists or not for security
            return jsonify({
                'success': True,
                'message': 'If this email is registered with us, you will receive a password reset link shortly.'
            })
        
        # Generate token and send email
        token = EmailService.generate_reset_token(email)
        
        if EmailService.send_password_reset_email(email, token):
            return jsonify({
                'success': True,
                'message': 'Password reset instructions have been sent to your email address.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send email. Please try again later.'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your request.'
        }), 500


@bp.route('/api/chat-memory', methods=['POST'])
@csrf.exempt
def update_chat_memory():
    """Update chat session memory"""
    try:
        data = request.get_json()
        memory_data = data.get('memory', {})
        
        if 'chat_memory' not in session:
            session['chat_memory'] = {}
        
        session['chat_memory'].update(memory_data)
        session.permanent = True
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/clear-memory', methods=['POST'])
@csrf.exempt
def clear_chat_memory():
    """Clear chat session memory"""
    try:
        if 'chat_memory' in session:
            del session['chat_memory']
        
        return jsonify({'success': True, 'message': 'Chat memory cleared'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
