from flask import render_template, request, redirect, url_for, flash, jsonify, session
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, create_refresh_token
from werkzeug.security import check_password_hash
import requests
from app.auth import bp
from app.models import User
from app import db


@bp.route('/login', methods=['GET', 'POST'])
def login():
    print(f"=== LOGIN REQUEST: {request.method} ===")  # Debug line
    if request.method == 'POST':
        print(f"Login form data received: {dict(request.form)}")  # Debug line
        
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
        
        if user and user.check_password(password):
            access_token = create_access_token(
                identity=user.id,
                additional_claims={'role': user.role, 'username': user.username}
            )
            refresh_token = create_refresh_token(identity=user.id)
            
            # Store user info in session for templates
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            
            print(f"Login successful for user: {user.username}")  # Debug line
            
            if request.is_json:
                return jsonify({
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'role': user.role
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
    print(f"=== SIGNUP REQUEST: {request.method} ===")  # Debug line
    
    if request.method == 'POST':
        # print(f"Signup form data received: {dict(request.form)}")  # Debug line
        
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
            
            print(f"Extracted data - Username: {username}, Email: {email}, Password: {'***' if password else 'None'}")  # Debug line
            
            # Validate required fields
            if not username or not email or not password:
                print("Missing required fields")  # Debug line
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
            
            # Create new user
            print("Creating new user...")  # Debug line
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            print(f"User created successfully with ID: {user.id}")  # Debug line
            
            if request.is_json:
                return jsonify({'message': 'Registration successful'}), 201
            else:
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('auth.login'))
        
        except Exception as e:
            print(f"Error during signup: {str(e)}")  # Debug line
            db.session.rollback()
            flash('Registration failed. Please try again.', 'danger')
            return render_template('auth/signup.html')
    
    print("Rendering signup template")  # Debug line
    return render_template('auth/signup.html')


@bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))


@bp.route('/github')
def github_login():
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
    from app.config import Config
    
    code = request.args.get('code')
    if not code:
        flash('GitHub authentication failed', 'danger')
        return redirect(url_for('auth.login'))
    
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
    
    user_data = user_response.json()
    
    # Get user email
    email_response = requests.get('https://api.github.com/user/emails', 
        headers={'Authorization': f'token {access_token}'}
    )
    
    emails = email_response.json()
    primary_email = next((email['email'] for email in emails if email['primary']), None)
    
    if not primary_email:
        flash('Could not get email from GitHub', 'danger')
        return redirect(url_for('auth.login'))
    
    # Check if user exists
    user = User.query.filter_by(github_id=str(user_data['id'])).first()
    
    if not user:
        # Check if email already exists
        existing_user = User.query.filter_by(email=primary_email).first()
        if existing_user:
            flash('An account with this email already exists', 'danger')
            return redirect(url_for('auth.login'))
        
        # Create new user
        role = 'admin' if primary_email == Config.ADMIN_EMAIL else 'user'
        user = User(
            username=user_data['login'],
            email=primary_email,
            github_id=str(user_data['id']),
            role=role
        )
        db.session.add(user)
        db.session.commit()
    else:
        if user.email == Config.ADMIN_EMAIL:
            user.role = 'admin'
        db.session.commit()
    
    # Log user in
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    
    flash('Successfully logged in with GitHub!', 'success')
    return redirect(url_for('main.index'))


@bp.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please login to view your profile', 'warning')
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    return render_template('main/profile.html', user=user)
