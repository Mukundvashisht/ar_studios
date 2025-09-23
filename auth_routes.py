from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import User, Activity
from app import db
import requests
import json
import os
from oauthlib.oauth2 import WebApplicationClient

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

auth_bp = Blueprint('auth', __name__)

# Initialize OAuth client
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    client = WebApplicationClient(GOOGLE_CLIENT_ID)
else:
    client = None


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))

        if not email or not password:
            flash('Please fill in all fields.', 'error')
            return render_template('auth/login.html')

        user = User.query.filter_by(email=email).first()

        if user and user.password_hash and check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)

            # Log the login activity
            activity = Activity()
            activity.user_id = user.id
            activity.action = "User Login"
            activity.description = f"User {user.username} logged in"
            db.session.add(activity)
            db.session.commit()

            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Register as client"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        terms = request.form.get('terms')

        # Validation
        if not all([username, email, password, confirm_password]):
            flash('Please fill in all fields.', 'error')
            return render_template('auth/register.html')

        if not terms:
            flash('Please accept the Terms of Service and Privacy Policy.', 'error')
            return render_template('auth/register.html')

        # Username validation
        if len(username) < 3 or len(username) > 20:
            flash('Username must be between 3 and 20 characters long.', 'error')
            return render_template('auth/register.html')

        if not username.replace('_', '').isalnum():
            flash('Username can only contain letters, numbers, and underscores.', 'error')
            return render_template('auth/register.html')

        # Email validation
        if '@' not in email or '.' not in email:
            flash('Please enter a valid email address.', 'error')
            return render_template('auth/register.html')

        # Password validation
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('auth/register.html')

        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email address already registered.', 'error')
            return render_template('auth/register.html')

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
            return render_template('auth/register.html')

        # Create new user as client
        new_user = User()
        new_user.username = username
        new_user.email = email
        new_user.password_hash = generate_password_hash(password)
        new_user.avatar_url = f"https://ui-avatars.com/api/?name={username}&background=6366f1&color=fff"
        new_user.role = 'client'  # Default role for regular registration

        try:
            db.session.add(new_user)
            db.session.commit()

            # Log the registration activity
            activity = Activity()
            activity.user_id = new_user.id
            activity.action = "User Registration"
            activity.description = f"New client {username} registered"
            db.session.add(activity)
            db.session.commit()

            flash(
                'Registration successful! Please log in with your new account.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
            return render_template('auth/register.html')

    return render_template('auth/register.html')


@auth_bp.route('/register-design', methods=['GET', 'POST'])
def register_designer():
    """Register as designer"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        terms = request.form.get('terms')

        # Validation
        if not all([username, email, password, confirm_password]):
            flash('Please fill in all fields.', 'error')
            return render_template('auth/register_designer.html')

        if not terms:
            flash('Please accept the Terms of Service and Privacy Policy.', 'error')
            return render_template('auth/register_designer.html')

        # Username validation
        if len(username) < 3 or len(username) > 20:
            flash('Username must be between 3 and 20 characters long.', 'error')
            return render_template('auth/register_designer.html')

        if not username.replace('_', '').isalnum():
            flash('Username can only contain letters, numbers, and underscores.', 'error')
            return render_template('auth/register_designer.html')

        # Email validation
        if '@' not in email or '.' not in email:
            flash('Please enter a valid email address.', 'error')
            return render_template('auth/register_designer.html')

        # Password validation
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/register_designer.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('auth/register_designer.html')

        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email address already registered.', 'error')
            return render_template('auth/register_designer.html')

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
            return render_template('auth/register_designer.html')

        # Create new user as designer
        new_user = User()
        new_user.username = username
        new_user.email = email
        new_user.password_hash = generate_password_hash(password)
        new_user.avatar_url = f"https://ui-avatars.com/api/?name={username}&background=10b981&color=fff"
        new_user.role = 'designer'  # Designer role

        try:
            db.session.add(new_user)
            db.session.commit()

            # Log the registration activity
            activity = Activity()
            activity.user_id = new_user.id
            activity.action = "Designer Registration"
            activity.description = f"New designer {username} registered"
            db.session.add(activity)
            db.session.commit()

            flash(
                'Designer registration successful! Please log in with your new account.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
            return render_template('auth/register_designer.html')

    return render_template('auth/register_designer.html')


@auth_bp.route('/google_login')
def google_login():
    if not client:
        flash('Google OAuth is not configured.', 'error')
        return redirect(url_for('auth.login'))

    try:
        google_provider_cfg = requests.get(
            GOOGLE_DISCOVERY_URL, timeout=10).json()
        authorization_endpoint = google_provider_cfg["authorization_endpoint"]

        # Ensure redirect_uri exactly matches what will be used in the callback (no query string)
        if request.host.startswith('localhost') or request.host.startswith('127.0.0.1'):
            redirect_uri = url_for('auth.google_callback', _external=True)
        else:
            # For production, force https scheme in case proxy sets http internally
            redirect_uri = url_for('auth.google_callback', _external=True).replace(
                "http://", "https://")

        # ADD THIS DEBUG LINE
        print(f"DEBUG: Redirect URI being sent: {redirect_uri}")

        request_uri = client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=redirect_uri,
            scope=["openid", "email", "profile"],
        )
        return redirect(request_uri)
    except Exception as e:
        flash('Error connecting to Google. Please try again.', 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/google_login/callback')
def google_callback():
    if not client:
        flash('Google OAuth is not configured.', 'error')
        return redirect(url_for('auth.login'))

    try:
        code = request.args.get("code")
        google_provider_cfg = requests.get(
            GOOGLE_DISCOVERY_URL, timeout=10).json()
        token_endpoint = google_provider_cfg["token_endpoint"]

        # Build both URLs: base redirect (must match initial redirect_uri) and the full callback URL we actually received
        if request.host.startswith('localhost') or request.host.startswith('127.0.0.1'):
            redirect_base = url_for('auth.google_callback', _external=True)
            authorization_response_url = request.url
        else:
            redirect_base = url_for('auth.google_callback', _external=True).replace(
                "http://", "https://")
            authorization_response_url = request.url.replace(
                "http://", "https://")

        if not code:
            flash('Missing authorization code from Google.', 'error')
            return redirect(url_for('auth.login'))

        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=authorization_response_url,
            redirect_url=redirect_base,
            code=code,
        )

        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
            timeout=10
        )

        if not token_response.ok:
            print(
                f"Google token error {token_response.status_code}: {token_response.text}")
            flash('Could not obtain access token from Google.', 'error')
            return redirect(url_for('auth.login'))

        client.parse_request_body_response(json.dumps(token_response.json()))

        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(
            uri, headers=headers, data=body, timeout=10)

        if not userinfo_response.ok:
            print(
                f"Google userinfo error {userinfo_response.status_code}: {userinfo_response.text}")
            flash('Could not fetch user info from Google.', 'error')
            return redirect(url_for('auth.login'))

        userinfo = userinfo_response.json()

        # Fix: Handle the case where email_verified might not be present
        if userinfo.get("email"):
            users_email = userinfo["email"]
            users_name = userinfo.get(
                "given_name", userinfo.get("name", "Google User"))
        else:
            flash("User email not available from Google.", 'error')
            return redirect(url_for('auth.login'))

        # Check if user exists, if not create new user
        user = User.query.filter_by(email=users_email).first()
        if not user:
            # Generate a unique username
            base_username = users_name.replace(" ", "_").lower()
            username = base_username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}_{counter}"
                counter += 1

            user = User()
            user.username = username
            user.email = users_email
            user.avatar_url = userinfo.get(
                "picture", f"https://ui-avatars.com/api/?name={users_name}&background=6366f1&color=fff")

            db.session.add(user)
            db.session.commit()

            # Log registration activity
            activity = Activity()
            activity.user_id = user.id
            activity.action = "Google Registration"
            activity.description = f"User registered via Google: {users_name}"
            db.session.add(activity)
            db.session.commit()

        login_user(user)

        # Log login activity
        activity = Activity()
        activity.user_id = user.id
        activity.action = "Google Login"
        activity.description = f"User {user.username} logged in via Google"
        db.session.add(activity)
        db.session.commit()

        return redirect(url_for('dashboard'))

    except Exception as e:
        print(f"Google OAuth error: {e}")  # For debugging
        flash('Error during Google authentication. Please try again.', 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/logout')
@login_required
def logout():
    # Log logout activity
    activity = Activity()
    activity.user_id = current_user.id
    activity.action = "User Logout"
    activity.description = f"User {current_user.username} logged out"
    db.session.add(activity)
    db.session.commit()

    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()

        if user:
            # In a real application, you would send an email here
            flash(
                'If an account with that email exists, password reset instructions have been sent.', 'info')
        else:
            flash(
                'If an account with that email exists, password reset instructions have been sent.', 'info')

        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html')
