from flask import render_template, request, redirect, url_for, flash, jsonify, session, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, create_refresh_token
from werkzeug.security import check_password_hash, generate_password_hash
import requests
from app.auth import bp
from app.models import User
from app import db
from app.utils.email_service import EmailService
from app.utils.rate_limiter import rate_limiter
from email_validator import validate_email, EmailNotValidError


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Regular email/password login with admin identification"""
    # print(f"=== LOGIN REQUEST: {request.method} ===")  # Debug line
    
    if 'user_id' in session:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        # print(f"Login form data received: {dict(request.form)}")  # Debug line
        
        if request.is_json:
            # API login
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
        else:
            # Form login
            email = request.form.get('email')
            password = request.form.get('password')
        
        print(f"Login attempt - Email: {email}")  # Debug line
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.password_hash and user.check_password(password):
            # Check if user is admin based on email
            admin_email = current_app.config.get('ADMIN_EMAIL', 't.shakthi@gmail.com')
            is_admin_user = (user.email == admin_email)
            
            # Update user role and admin status
            user.role = 'admin' if is_admin_user else 'user'
            if hasattr(user, 'is_admin'):
                user.is_admin = is_admin_user
            db.session.commit()
            
            # Create JWT tokens
            access_token = create_access_token(
                identity=user.id,
                additional_claims={'role': user.role, 'username': user.username}
            )
            refresh_token = create_refresh_token(identity=user.id)
            
            # Store user info in session for templates and chatbot
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_email'] = user.email
            session['role'] = user.role
            session['is_admin'] = is_admin_user
            session['login_method'] = 'email'
            
            # print(f"Login successful for user: {user.username} (Admin: {is_admin_user})")  # Debug line
            
            if request.is_json:
                return jsonify({
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'role': user.role,
                        'is_admin': is_admin_user
                    }
                })
            else:
                flash('Login successful!', 'success')
                return redirect(url_for('main.index'))
        else:
            print("Login failed - Invalid credentials")  # Debug line
            if request.is_json:
                return jsonify({'error': 'Invalid email or password'}), 401
            else:
                flash('Invalid email or password', 'danger')
    
    return render_template('auth/login.html')


@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration with admin identification"""
    print(f"=== SIGNUP REQUEST: {request.method} ===")  # Debug line
    
    if 'user_id' in session:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        try:
            if request.is_json:
                data = request.get_json()
                username = data.get('username')
                email = data.get('email')
                password = data.get('password')
            else:
                username = request.form.get('username')
                email = request.form.get('email')
                password = request.form.get('password')
            
            # print(f"Extracted data - Username: {username}, Email: {email}, Password: {'***' if password else 'None'}")  # Debug line
            
            # Validate required fields
            if not username or not email or not password:
                print("Missing required fields")  # Debug line
                if request.is_json:
                    return jsonify({'error': 'All fields are required'}), 400
                else:
                    flash('All fields are required', 'danger')
                    return render_template('auth/signup.html')
            
            # Check if user already exists
            if User.query.filter_by(email=email).first():
                print("Email already registered")  # Debug line
                if request.is_json:
                    return jsonify({'error': 'Email already registered'}), 400
                else:
                    flash('Email already registered', 'danger')
                    return render_template('auth/signup.html')
            
            if User.query.filter_by(username=username).first():
                print("Username already taken")  # Debug line
                if request.is_json:
                    return jsonify({'error': 'Username already taken'}), 400
                else:
                    flash('Username already taken', 'danger')
                    return render_template('auth/signup.html')
            
            # Check if user is admin based on email
            admin_email = current_app.config.get('ADMIN_EMAIL', 't.shakthi@gmail.com')
            is_admin_user = (email == admin_email)
            
            # Create new user
            print("Creating new user...")  # Debug line
            user = User(
                username=username, 
                email=email,
                role='admin' if is_admin_user else 'user'
            )
            if hasattr(user, 'is_admin'):
                user.is_admin = is_admin_user
            
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            print(f"User created successfully with ID: {user.id} (Admin: {is_admin_user})")  # Debug line
            
            if request.is_json:
                return jsonify({'message': 'Registration successful'}), 201
            else:
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('auth.login'))
        
        except Exception as e:
            print(f"Error during signup: {str(e)}")  # Debug line
            db.session.rollback()
            if request.is_json:
                return jsonify({'error': 'Registration failed. Please try again.'}), 500
            else:
                flash('Registration failed. Please try again.', 'danger')
                return render_template('auth/signup.html')
    
    print("Rendering signup template")  # Debug line
    return render_template('auth/signup.html')


@bp.route('/github')
def github_login():
    """GitHub OAuth login with admin identification"""
    from app.config import Config
    
    github_client_id = Config.GITHUB_CLIENT_ID
    if not github_client_id:
        flash('GitHub login not configured', 'danger')
        return redirect(url_for('auth.login'))
    
    # Use the correct callback URL that matches GitHub settings
    return redirect(
        f'https://github.com/login/oauth/authorize?'
        f'client_id={github_client_id}&'
        f'redirect_uri={request.url_root}auth/callback/github&'
        f'scope=user:email'
    )


@bp.route('/callback/github')
def github_callback():
    """GitHub OAuth callback with admin identification"""
    from app.config import Config
    
    code = request.args.get('code')
    if not code:
        flash('GitHub authentication failed', 'danger')
        return redirect(url_for('auth.login'))
    
    try:
        # Exchange code for access token
        token_response = requests.post('https://github.com/login/oauth/access_token', {
            'client_id': Config.GITHUB_CLIENT_ID,
            'client_secret': Config.GITHUB_CLIENT_SECRET,
            'code': code,
        }, headers={'Accept': 'application/json'})
        
        token_data = token_response.json()
        access_token = token_data.get('access_token')
        
        if not access_token:
            flash('GitHub authentication failed', 'danger')
            return redirect(url_for('auth.login'))
        
        # Get user info from GitHub
        user_response = requests.get('https://api.github.com/user', 
            headers={'Authorization': f'token {access_token}'}
        )
        
        if not user_response.ok:
            flash('Failed to fetch user info from GitHub', 'danger')
            return redirect(url_for('auth.login'))
            
        user_data = user_response.json()
        github_username = user_data.get('login')
        github_id = str(user_data.get('id'))
        
        # Get user email
        email_response = requests.get('https://api.github.com/user/emails', 
            headers={'Authorization': f'token {access_token}'}
        )
        
        user_email = None
        if email_response.ok:
            emails = email_response.json()
            # Find primary verified email
            for email_record in emails:
                if email_record.get('primary') and email_record.get('verified'):
                    user_email = email_record.get('email')
                    break
        
        if not user_email:
            flash('Could not retrieve verified email from GitHub. Please ensure you have a verified primary email.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Check if admin email matches
        admin_email = Config.ADMIN_EMAIL or 't.shakthi@gmail.com'
        is_admin_user = (user_email == admin_email)
        
        print(f"GitHub login - Email: {user_email}, Admin: {is_admin_user}")  # Debug line
        
        # Check if user exists by GitHub ID first, then by email
        user = User.query.filter_by(github_id=github_id).first()
        if not user:
            user = User.query.filter_by(email=user_email).first()
        
        if not user:
            # Check if email already exists with different account
            existing_user = User.query.filter_by(email=user_email).first()
            if existing_user and not existing_user.github_id:
                # Link GitHub to existing email account
                existing_user.github_id = github_id
                existing_user.username = github_username
                existing_user.role = 'admin' if is_admin_user else 'user'
                if hasattr(existing_user, 'is_admin'):
                    existing_user.is_admin = is_admin_user
                db.session.commit()
                user = existing_user
                flash(f'GitHub account linked successfully! Welcome back {github_username}!', 'success')
            else:
                # Create new user
                user = User(
                    username=github_username,
                    email=user_email,
                    github_id=github_id,
                    role='admin' if is_admin_user else 'user',
                    password_hash=None  # No password for OAuth users
                )
                if hasattr(user, 'is_admin'):
                    user.is_admin = is_admin_user
                db.session.add(user)
                db.session.commit()
                flash(f'Welcome {github_username}! Account created successfully.', 'success')
        else:
            # Update existing user
            user.username = github_username  # Update username if changed
            user.email = user_email  # Update email if changed
            user.github_id = github_id  # Ensure GitHub ID is set
            user.role = 'admin' if is_admin_user else 'user'
            if hasattr(user, 'is_admin'):
                user.is_admin = is_admin_user
            db.session.commit()
            flash(f'Welcome back {github_username}!', 'success')
        
        # Set session data for chatbot identification
        session['user_id'] = user.id
        session['username'] = user.username
        session['user_email'] = user.email
        session['role'] = user.role
        session['is_admin'] = is_admin_user
        session['login_method'] = 'github'
        
        print(f"GitHub login successful for user: {user.username} (Admin: {is_admin_user})")  # Debug line
        
        return redirect(url_for('main.index'))
        
    except Exception as e:
        print(f"Error during GitHub authentication: {str(e)}")  # Debug line
        flash('GitHub authentication failed. Please try again.', 'danger')
        return redirect(url_for('auth.login'))


@bp.route('/logout')
def logout():
    """Logout user and clear session"""
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))


@bp.route('/profile')
def profile():
    """User profile page"""
    if 'user_id' not in session:
        flash('Please login to view your profile', 'warning')
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    return render_template('main/profile.html', user=user)


@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle password reset request"""
    if 'user_id' in session:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        # Validate email format
        try:
            validate_email(email)
        except EmailNotValidError:
            flash('Please provide a valid email address.', 'danger')
            return render_template('auth/forgot_password.html')
        
        # Check rate limiting
        if not rate_limiter.can_attempt_reset(email):
            flash('Too many password reset attempts. Please try again later.', 'warning')
            return render_template('auth/forgot_password.html')
        
        # Always show success message for security (don't reveal if email exists)
        user = User.query.filter_by(email=email).first()
        if user and user.password_hash:  # Only send reset for email/password users
            token = EmailService.generate_reset_token(email)
            if EmailService.send_password_reset_email(email, token):
                flash('Password reset instructions have been sent to your email address.', 'info')
            else:
                flash('Failed to send email. Please try again later.', 'danger')
        else:
            # Still show success message even if email doesn't exist or is OAuth user
            flash('If this email is registered with us, you will receive a password reset link shortly.', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html')


@bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Handle password reset with token"""
    token = request.args.get('token')
    
    if not token:
        flash('Invalid or missing reset token.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    # Verify token
    email = EmailService.verify_reset_token(token)
    if not email:
        flash('Invalid or expired reset token. Please request a new password reset.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    # Get user by email
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        # Validate password
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        # Update password using the user's method or direct hash
        if hasattr(user, 'set_password'):
            user.set_password(new_password)
        else:
            user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        flash('Your password has been updated successfully! Please login with your new password.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', token=token, email=email)
