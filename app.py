from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import re
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import urllib.parse as up
from sqlalchemy import text

import time
import logging
from sqlalchemy.exc import OperationalError
import pymysql
from flask_migrate import Migrate
import os
from dotenv import load_dotenv
# Add these imports with your other imports
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import jwt
import requests
from datetime import datetime, timedelta
from functools import wraps
import json
import socket
from urllib.parse import urlparse


def get_base_url():
    """
    Smart function to detect the correct base URL for the application
    Works in: localhost, Docker, Railway, Render, Heroku, etc.
    """
    # Priority 1: Explicit environment variable (most reliable)
    explicit_url = os.environ.get('APP_URL')
    if explicit_url:
        return explicit_url.rstrip('/')
    
    # Priority 2: Platform-specific environment variables
    platform_urls = [
        os.environ.get('RAILWAY_STATIC_URL'),        # Railway
        os.environ.get('RENDER_EXTERNAL_URL'),       # Render
        os.environ.get('HEROKU_APP_NAME'),           # Heroku (needs https:// prefix)
    ]
    
    for url in platform_urls:
        if url:
            # For Heroku, construct the URL
            if url == os.environ.get('HEROKU_APP_NAME'):
                return f"https://{url}.herokuapp.com"
            return url.rstrip('/')
    
    # Priority 3: Check if running in Docker container
    if os.path.exists('/.dockerenv'):
        # In Docker, we need to use the service name or external IP
        docker_host = os.environ.get('DOCKER_HOST_IP', 'localhost')
        docker_port = os.environ.get('PORT', '5000')
        return f"http://{docker_host}:{docker_port}"
    
    # Priority 4: Try to detect from current request (for runtime)
    try:
        if request and request.host_url:
            # Remove port if it's the standard HTTP/HTTPS port
            parsed = urlparse(request.host_url)
            if (parsed.scheme == 'http' and parsed.port == 80) or \
               (parsed.scheme == 'https' and parsed.port == 443):
                return f"{parsed.scheme}://{parsed.hostname}".rstrip('/')
            return request.host_url.rstrip('/')
    except:
        pass
    
    # Priority 5: Local development fallback
    return "http://localhost:5000"

def generate_external_url(endpoint, **kwargs):
    """
    Generate external URL that works in all environments
    Usage: generate_external_url('confirm_email', token=token)
    """
    base_url = get_base_url()
    
    # Map endpoint names to URL paths
    endpoint_map = {
        'confirm_email': '/confirm/{token}',
        'reset_password': '/reset_password/{token}',
        'login': '/login',
        'index': '/',
        'forgot_password': '/forgot_password',
        'register': '/register',
        'dashboard': '/dashboard',
    }
    
    if endpoint in endpoint_map:
        path_template = endpoint_map[endpoint]
        try:
            # Format the path with provided kwargs
            path = path_template.format(**kwargs)
            return f"{base_url}{path}"
        except KeyError:
            # If formatting fails, fall back to url_for
            from flask import url_for
            return url_for(endpoint, **kwargs, _external=True)
    
    # Fallback to Flask's url_for
    from flask import url_for
    return url_for(endpoint, **kwargs, _external=True)

# Load environment variables from .env file
load_dotenv()


pymysql.install_as_MySQLdb()

app = Flask(__name__)
bcrypt = Bcrypt(app)

 # Secret key and email credentials should be environment variables (for security)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_default_secret_key')  # Add default for development

# Smart configuration based on environment
is_production = os.environ.get('FLASK_ENV') == 'production' or os.environ.get('RAILWAY_ENVIRONMENT') == 'production'

if is_production:
    # Production settings
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_SAMESITE'] = "Lax"
    app.config['REMEMBER_COOKIE_SECURE'] = True
    print("🚀 Running in PRODUCTION mode")
else:
    # Development settings
    app.config['PREFERRED_URL_SCHEME'] = 'http'
    print("🔧 Running in DEVELOPMENT mode")

# Add ProxyFix for production behind reverse proxy
if is_production:
    from werkzeug.middleware.proxy_fix import ProxyFix  # ADD THIS LINE
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,      # Trust one proxy (Railway/Render)
        x_proto=1,    # Trust X-Forwarded-Proto header
        x_host=1,     # Trust X-Forwarded-Host header
        x_port=1      # Trust X-Forwarded-Port header
    )

app.config.update(
    MAIL_SERVER='smtp.mail.yahoo.com',
    MAIL_PORT=465,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME', 'oscarkyamuweno@yahoo.com'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD', 'Godjesus44me.')
) 

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def wait_for_db(max_retries=30, delay=2):
    """Wait for database to be ready before creating tables."""
    from sqlalchemy import text
    
    for attempt in range(max_retries):
        try:
            # Test connection first
            with app.app_context():
                db.session.execute(text('SELECT 1'))
                logger.info("✓ Database connection established")
                
                # Then create tables if they don't exist
                db.create_all()
                logger.info("✓ Database tables created/checked")
            return True
        except OperationalError as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries}: Database not ready - {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
    logger.error("✗ Could not connect to database after multiple attempts")
    return False

# Database Configuration
# Database Configuration - Simple and flexible
def get_database_uri():
    """Get database URI from environment with sensible defaults."""
    # Priority 1: Direct DATABASE_URL (for production)
    if os.environ.get("MYSQLHOST"):
        user = os.environ.get("MYSQLUSER")
        password = os.environ.get("MYSQLPASSWORD")
        host = os.environ.get("MYSQLHOST")
        port = os.environ.get("MYSQLPORT", "3306")
        db = os.environ.get("MYSQLDATABASE")

        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}"
    
    # Priority 2: Individual components with defaults for Docker
    if os.path.exists('/.dockerenv'):
        # Docker environment
        username = os.getenv('MYSQL_USER', 'root')
        password = os.getenv('MYSQL_PASSWORD', 'password')
        host = os.getenv('MYSQL_HOST', 'db')  # 'db' is Docker service name
        port = os.getenv('MYSQL_PORT', '3306')
        database = os.getenv('MYSQL_DATABASE', 'elehere')
    else:
        # Local development (outside Docker)
        username = os.getenv('MYSQL_USER', 'root')
        password = os.getenv('MYSQL_PASSWORD', 'password')
        host = os.getenv('MYSQL_HOST', 'localhost')  # 'localhost' for local
        port = os.getenv('MYSQL_PORT', '3307')       # Port 3307 (mapped from Docker)
        database = os.getenv('MYSQL_DATABASE', 'elehere')
    
    return f'mysql+pymysql://{username}:{password}@{host}:{port}/{database}'

# After initializing db, add this:
def initialize_database():
    """Initialize database - should only run once."""
    from sqlalchemy import inspect, text
    
    try:
        with app.app_context():
            # Check if any table exists to avoid repeated creation
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if not tables:
                db.create_all()
                logger.info("✓ Database tables created")
            else:
                logger.info("✓ Database tables already exist")
    except Exception as e:
        logger.warning(f"⚠ Could not initialize database: {e}")

# Set database URI
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return Doctor.query.get(int(user_id))


@app.route('/ping')
def ping():
    """Simple ping endpoint."""
    return 'pong', 200


# Update Doctor model to work with Flask-Login
class Doctor(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    confirmed = db.Column(db.Boolean, default=False)
    google_id = db.Column(db.String(100), unique=True, nullable=True)  # NEW: For Google login
    profile_picture = db.Column(db.String(500), nullable=True)  # NEW: Store Google profile picture
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)  # Add this
    
    @staticmethod
    def get_or_create_google_user(google_data):
        """Find or create doctor from Google data"""
        # Check if doctor exists by google_id
        doctor = Doctor.query.filter_by(google_id=google_data['sub']).first()
        
        if not doctor:
            # Check if doctor exists by email
            doctor = Doctor.query.filter_by(email=google_data['email']).first()
            if doctor:
                # Existing doctor, add google_id
                doctor.google_id = google_data['sub']
                doctor.profile_picture = google_data.get('picture', '')
                doctor.confirmed = True  # Google emails are verified
                doctor.confirmed_at = datetime.utcnow()
            else:
                # Create new doctor
                doctor = Doctor(
                    username=google_data['email'].split('@')[0],  # Use email prefix as username
                    email=google_data['email'],
                    google_id=google_data['sub'],
                    profile_picture=google_data.get('picture', ''),
                    confirmed=True,  # Google emails are verified
                    password=''  # No password for Google users
                )
                db.session.add(doctor)
        
        doctor.last_login = datetime.utcnow()
        db.session.commit()
        return doctor
# Creates the MySQL database tables (if they don't exist)
"""# Only create tables if we're not using migrations or in development
if os.environ.get('FLASK_ENV') == 'development' and not os.environ.get('USE_MIGRATIONS'):
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables created/checked")
        except Exception as e:
            print(f"⚠ Could not create tables: {e}")"""

# Route for the home page
@app.route('/')
def index():
    return render_template('index.html')



# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

def verify_google_token(token):
    try:
        response = requests.get(f'https://oauth2.googleapis.com/tokeninfo?id_token={token}', timeout=10)
        if response.status_code != 200:
            print("Google token verification failed:", response.text)
            return None

        token_data = response.json()

        # Must match your production Google Client ID
        if token_data.get('aud') != GOOGLE_CLIENT_ID:
            print(f"Token audience mismatch. Expected {GOOGLE_CLIENT_ID}, got {token_data.get('aud')}")
            return None

        # Verify email
        if token_data.get('email_verified') != 'true':
            print("Email not verified:", token_data.get('email'))
            return None

        return {
            'sub': token_data['sub'],
            'email': token_data['email'],
            'name': token_data.get('name', ''),
            'picture': token_data.get('picture', ''),
            'email_verified': True
        }

    except Exception as e:
        print("Error verifying Google token:", e)
        return None


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        content_type = request.headers.get('Content-Type', '')

        # ---- GOOGLE SIGN-IN JSON ----
        if content_type.startswith('application/json'):
            try:
                data = request.get_json()
                if not data or 'credential' not in data:
                    return jsonify({'success': False, 'message': 'No credential provided'}), 400

                credential = data['credential']
                google_data = verify_google_token(credential)

                if not google_data:
                    return jsonify({'success': False, 'message': 'Invalid Google token'}), 401

                doctor = Doctor.get_or_create_google_user(google_data)

                login_user(doctor, remember=True)
                session['loggedin'] = True
                session['doctor_id'] = doctor.id
                session['username'] = doctor.username
                session['is_google_user'] = True

                return jsonify({
                    'success': True,
                    'redirect': url_for('dashboard', _external=True)
                })

            except Exception as e:
                print("GOOGLE LOGIN ERROR:", repr(e))
                return jsonify({
                    'success': False,
                    'message': 'Server error during Google login',
                    'error': str(e)
                }), 500

        # ---- NORMAL FORM LOGIN ----
        else:
            ...



# Health check with user info
@app.route('/health')
def health():
    try:
        db.session.execute(text('SELECT 1'))
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {e}"
    
    user_info = None
    if current_user.is_authenticated:
        user_info = {
            'id': current_user.id,
            'username': current_user.username,
            'is_google_user': bool(current_user.google_id)
        }
    
    return jsonify({
        "status": "healthy",
        "database": db_status,
        "service": "elehere",
        "user": user_info,
        "timestamp": datetime.utcnow().isoformat()
    })

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.mail.yahoo.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = 'oscarkyamuwendo@yahoo.com'
app.config['MAIL_PASSWORD'] = 'vdvifzmtxjyigmse'

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)


# Set up token serializer
def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])

def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt=app.config['SECURITY_PASSWORD_SALT'], max_age=expiration)
    except:
        return False
    return email



# Forgot password configuration
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = Doctor.query.filter_by(email=email).first()  # Check if user exists

        if user:
            # Generate a secure token for password reset
            token = generate_password_reset_token(user.id)
            reset_url = url_for('reset_password', token=token, _external=True)

            # Send reset email
            msg = Message("Password Reset Request",
                          sender= ("Elehere Support","oscarkyamuwendo@yahoo.com"),
                          recipients=[email])
            msg.body = f"To reset your password, visit the following link: {reset_url}"
            mail.send(msg)
            
            flash("A password reset link has been sent to your email.", "success")
            return redirect(url_for('login'))
        else:
            flash("Email not found. Please check and try again.", "danger")
            return redirect(url_for('forgot_password'))

                                        # Render the forgot_password form on a GET request
    return render_template('forgot_password.html')


# Function to generate reset token
def generate_password_reset_token(user_id):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(user_id, salt='password-reset-salt')


# Function to verify the reset token
def verify_reset_token(token, expiration=3600):  # Expiration time is 1 hour (3600 seconds)
    s = URLSafeTimedSerializer(app.secret_key)
    try:
        doctor_id = s.loads(token, salt='password-reset-salt', max_age=expiration)
    except:
        return None
    return doctor_id

# send reset email
def send_reset_email(email, token):
    reset_url = url_for('reset_password', token=token, _external=True)
    msg = Message('Password Reset Request', 
                  sender= ("Elehere Support","oscarkyamuwendo@yahoo.com"),  # Replace with your sender email
                  recipients=[email])
    msg.body = f'''To reset your password, visit the following link:
{reset_url}

If you did not make this request, simply ignore this email and no changes will be made.
'''
    mail.send(msg)

# password reset route
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    doctor_id = verify_reset_token(token)
    if not doctor_id:
        flash('Invalid or expired token', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('reset_password', token=token))

        # Update password
        doctor = Doctor.query.get(doctor_id)
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        doctor.password = hashed_password
        db.session.commit()

        flash('Your password has been updated!', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html')


# Route for registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['reg-username']
        password = request.form['reg-password']
        confirm_password = request.form['confirm-password']
        email = request.form['email'].lower()  # Normalize email to lowercase

        # Check if email is already registered via Google
        existing_google_user = Doctor.query.filter_by(email=email).filter(Doctor.google_id.isnot(None)).first()
        if existing_google_user:
            return render_template(
                'register.html',
                title="Account Already Exists",
                message=f"This email is already registered with Google Sign-In. Please use the 'Sign in with Google' button on the login page.",
                suggestion="If you want to add a password to this account, please contact support."
            )

        # Check if username exists (regular or Google user)
        existing_username = Doctor.query.filter_by(username=username).first()
        if existing_username:
            return render_template(
                'register.html',
                title="Username Taken",
                message="This username is already taken. Please choose another username."
            )

        # Check if email exists (non-Google user)
        existing_email = Doctor.query.filter_by(email=email).filter(Doctor.google_id.is_(None)).first()
        if existing_email:
            return render_template(
                'register.html',
                title="Email Already Registered",
                message="This email is already registered. Please use a different email or try logging in."
            )

        if password != confirm_password:
            return render_template(
                'register.html',
                title="Error",
                message="Passwords do not match! Please try again."
            )

        # Password strength validation (optional but recommended)
        if len(password) < 8:
            return render_template(
                'register.html',
                title="Weak Password",
                message="Password must be at least 8 characters long."
            )

        # Create new doctor
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_doctor = Doctor(
            username=username, 
            email=email, 
            password=hashed_password, 
            confirmed=False,
            google_id=None,  # Explicitly set to None for clarity
            profile_picture=None
        )
        
        try:
            db.session.add(new_doctor)
            db.session.commit()
            
            # Generate confirmation token and send email
            token = serializer.dumps(email, salt='email-confirmation-salt')
            confirm_url = generate_external_url('confirm_email', token=token)
            
            msg = Message(
                'Confirm Your Account - ELEHERE EHR System',
                sender=("Elehere Support", "oscarkyamuwendo@yahoo.com"),
                recipients=[email]
            )
            
            # Create a nicer email template
            msg.html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                    <h2 style="color: #4a6fa5;">Welcome to ELEHERE EHR System!</h2>
                    <p>Thank you for registering as a doctor on our platform.</p>
                    <p>Please confirm your email address by clicking the button below:</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{confirm_url}" style="background-color: #4a6fa5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;">
                            Confirm Email Address
                        </a>
                    </div>
                    
                    <p>Or copy and paste this link in your browser:</p>
                    <p style="background-color: #f5f5f5; padding: 10px; border-radius: 3px; word-break: break-all;">
                        {confirm_url}
                    </p>
                    
                    <p>This link will expire in 1 hour.</p>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    
                    <p style="font-size: 12px; color: #666;">
                        If you did not create an account with ELEHERE, please ignore this email.<br>
                        This is an automated message, please do not reply to this email.
                    </p>
                </div>
            </body>
            </html>
            """
            
            # Plain text fallback
            msg.body = f"""Welcome to ELEHERE EHR System!

Thank you for registering as a doctor on our platform.

Please confirm your email address by clicking this link:
{confirm_url}

This link will expire in 1 hour.

If you did not create an account with ELEHERE, please ignore this email.
This is an automated message, please do not reply to this email.
            """
            
            mail.send(msg)
            
            # Log the registration attempt
            logger.info(f"New registration: {email} (username: {username})")
            
            # Return success message
            return render_template(
                'register.html',
                title="Registration Successful!",
                message="""Your account has been created successfully! 
                Please check your email for the activation link.
                
                <strong>Important:</strong> The activation link will expire in 1 hour.
                If you don't see the email, please check your spam folder.""",
                email_sent=True
            )
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error for {email}: {e}")
            
            return render_template(
                'register.html',
                title="Registration Error",
                message=f"An error occurred during registration. Please try again. Error: {str(e)[:100]}..."
            )

    return render_template('register.html')



@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = serializer.loads(token, salt='email-confirmation-salt', max_age=3600)
    except Exception as e:
        logger.warning(f"Invalid confirmation token: {e}")
        return render_template('activation_failed.html', 
                             message="The confirmation link is invalid or has expired.",
                             suggestion="Please request a new confirmation email from the login page.")

    doctor = Doctor.query.filter_by(email=email).first()
    
    if not doctor:
        logger.warning(f"Doctor not found for email: {email}")
        return render_template('activation_failed.html',
                             message="No account found for this email.",
                             suggestion="Please register first.")
    
    # Check if this is a Google user
    if doctor.google_id:
        return render_template('activation_success.html',
                             message="""Your Google account is already active! 
                             <br><br>
                             <strong>Note:</strong> Since you registered with Google, your email was automatically verified.
                             <br>
                             Please use the 'Sign in with Google' button to log in.""",
                             is_google_user=True)
    
    if doctor.confirmed:
        return render_template('activation_success.html',
                             message="Your account is already confirmed. Please log in.",
                             login_url=url_for('login'))
    
    # Activate the account
    doctor.confirmed = True
    doctor.confirmed_at = datetime.utcnow()  # Add this field to your model if you want
    
    try:
        db.session.commit()
        
        # Send welcome email (optional)
        send_welcome_email(doctor.email, doctor.username)
        
        logger.info(f"Account confirmed: {email}")
        
        return render_template('activation_success.html',
                             message="""Your account has been activated successfully! 
                             <br><br>
                             <strong>You can now log in to access your dashboard.</strong>""",
                             login_url = generate_external_url('login'),
                             username=doctor.username)
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to confirm account {email}: {e}")
        return render_template('activation_failed.html',
                             message="An error occurred while activating your account.",
                             suggestion="Please try again or contact support.")
    

def send_welcome_email(email, username):
   
        try:
            msg = Message(
                'Welcome to ELEHERE EHR System!',
                sender=("Elehere Support", "oscarkyamuwendo@yahoo.com"),
                recipients=[email]
            )
            
            msg.html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #4a6fa5;">Welcome to ELEHERE, Dr. {username}!</h2>
                    
                    <p>Your account has been successfully activated and you can now access all features:</p>
                    
                    <ul>
                        <li>Patient record management</li>
                        <li>Medical history tracking</li>
                        <li>Lab results and imaging</li>
                        <li>Secure patient data storage</li>
                    </ul>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{url_for('login', _external=True)}" 
                        style="background-color: #4a6fa5; color: white; padding: 12px 24px; 
                                text-decoration: none; border-radius: 4px; font-weight: bold;">
                            Log In to Your Dashboard
                        </a>
                    </div>
                    
                    <p><strong>Need help getting started?</strong></p>
                    <ul>
                        <li><a href="{generate_external_url('about')}">View our tutorial</a></li>
                        <li>Contact support: oscarkyamuwendo@yahoo.com</li>
                    </ul>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    
                    <p style="font-size: 12px; color: #666;">
                        This is an automated message from ELEHERE EHR System.<br>
                        Please do not reply to this email.
                    </p>
                </div>
            </body>
            </html>
            """
            
            mail.send(msg)
            logger.info(f"Welcome email sent to: {email}")
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to {email}: {e}")
    


@app.route('/doctors')
def view_doctors():
    if 'loggedin' in session:  # Optional: Only allow logged-in users to view this page
        doctors = Doctor.query.all()  # Fetch all doctors from the database
        return render_template('doctors.html', doctors=doctors)
    else:
        return redirect(url_for('login'))


# Route for doctor dashboard after login
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    doctor_id = current_user.id if current_user.is_authenticated else session.get('doctor_id')
    if 'loggedin' in session:
        # Get search parameters from request args
        name_query = request.args.get('name')
        age_query = request.args.get('age')

        # Start with a query filtering by doctor_id
        query = Patient.query.filter_by(doctor_id=session['doctor_id'])

        # Apply filters based on search criteria
        if name_query:
            query = query.filter(Patient.name.ilike(f"%{name_query}%"))  # Case-insensitive search
        if age_query:
            query = query.filter(Patient.age == age_query)

        # Execute the query
        patients = query.all()
        
        return render_template('dashboard.html', patients=patients)

        if not doctor_id:
            flash('Please log in to access the dashboard.', 'danger')
            return redirect(url_for('login'))
        
        # Get search parameters from request args
        name_query = request.args.get('name')
        age_query = request.args.get('age')

        # Start with a query filtering by doctor_id
        query = Patient.query.filter_by(doctor_id=doctor_id)

        # Apply filters based on search criteria
        if name_query:
            query = query.filter(Patient.name.ilike(f"%{name_query}%"))
        if age_query:
            query = query.filter(Patient.age == age_query)

        # Execute the query
        patients = query.all()
        
        return render_template('dashboard.html', 
                            patients=patients,
                            current_user=current_user)
    
    
    else:
        flash('Please log in to access the dashboard.', 'danger')
        return redirect(url_for('login'))


# Logout
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('doctor_id', None)
    session.pop('username', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

# patient model
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    
    # Demographics and basic information
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float, nullable=True)
    gender = db.Column(db.String(10), nullable=True)  # Add gender field
    
    # Medical history and conditions
    medical_history = db.Column(db.Text, nullable=True)
    medication = db.Column(db.String(200), nullable=True)
    allergies = db.Column(db.String(200), nullable=True)
    immunization_status = db.Column(db.String(200), nullable=True)
    
    # Other health records
    lab_results = db.Column(db.Text, nullable=True)
    radiology_images = db.Column(db.String(100), nullable=True)
    vital_signs = db.Column(db.String(200), nullable=True)
    
    # Additional fields for this project
    billing_info = db.Column(db.String(100), nullable=True)
    last_visit_date = db.Column(db.Date, nullable=True)

    doctor = db.relationship('Doctor', backref=db.backref('patients', lazy=True))


try:
    with app.app_context():
         # Check if columns exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('doctor')]
        
        if 'google_id' not in columns:
            print("Adding Google login columns...")
      
        db.create_all()  # Create tables in the database if they don't exist
        print("✅ Database tables created/checked")
except Exception as e:
    print(f"⚠ Could not create tables: {e}")
    print("App will start without database initialization")

# Configure the upload folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = 'static/uploads'


# Ensure the uploads folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Add patient route
@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if 'loggedin' in session:
        if request.method == 'POST':
            # Handle file upload for radiology image
            radiology_image = request.files.get('radiology_images')
            radiology_image_filename = None  # Default to None if no image is uploaded
            
            if radiology_image and radiology_image.filename != '':
                filename = secure_filename(radiology_image.filename)
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                radiology_image.save(upload_path)
                radiology_image_filename = filename  # Store the filename to save in the database
            
            # Patient data processing here
            new_patient = Patient(
                doctor_id=session['doctor_id'],
                name=request.form.get('name'),
                age=request.form.get('age'),
                weight=request.form.get('weight'),
                gender=request.form.get('gender'),
                medical_history=request.form.get('medical_history'),
                medication=request.form.get('medication'),
                allergies=', '.join(request.form.getlist('allergies')),
                immunization_status=request.form.get('immunization_status'),
                lab_results=request.form.get('lab_results'),
                radiology_images=radiology_image_filename,  # Save filename of the uploaded image
                vital_signs=request.form.get('vital_signs'),
                billing_info=request.form.get('billing_info'),
                last_visit_date=request.form.get('last_visit_date')
            )
            db.session.add(new_patient)
            db.session.commit()

            # Render the success confirmation
            return render_template('add_patient.html', success=True)

        return render_template('add_patient.html', success=False)
    else:
        return redirect(url_for('login'))


# view patient
@app.route('/patients')
def view_patients():
    if 'loggedin' in session:
        # Fetch patients for the logged-in doctor
        patients = Patient.query.filter_by(doctor_id=session['doctor_id']).all()
        return render_template('view_patients.html', patients=patients)
    else:
        flash('Please log in to view patients.', 'danger')
        return redirect(url_for('login'))

# edit_patient
@app.route('/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    success = False  # Flag for displaying acknowledgment

    if request.method == 'POST':
        try:
            # Update patient details from the form
            patient.name = request.form['name']
            patient.age = int(request.form['age'])
            patient.weight = float(request.form['weight'])
            patient.gender = request.form['gender']
            patient.medical_history = request.form['medical_history']
            patient.medication = request.form['medication']

            # Convert list of allergies to a comma-separated string
            patient.allergies = ', '.join(request.form.getlist('allergies'))

            # Optional fields with defaults
            patient.immunization_status = request.form.get('immunization_status', 'Not Provided')
            patient.lab_results = request.form.get('lab_results', '')
            patient.billing_info = request.form.get('billing_info', '')

            # Validate and update last visit date
            patient.last_visit_date = request.form['last_visit_date'] if request.form['last_visit_date'] else None

            # Handle radiology image upload
            radiology_image = request.files.get('radiology_images')
            if radiology_image and radiology_image.filename != '':
                filename = secure_filename(radiology_image.filename)
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                radiology_image.save(upload_path)
                patient.radiology_images = filename  # Save filename in the database

            # Commit changes to the database
            db.session.commit()
            success = True
        except Exception as e:
            # Handle any errors gracefully
            db.session.rollback()
            error_message = f"An error occurred while updating the patient's information: {str(e)}"
            return render_template('edit_patient.html', patient=patient, success=False, error=error_message)

    return render_template('edit_patient.html', patient=patient, success=success)


# delete patient
@app.route('/delete_patient/<int:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    db.session.delete(patient)
    db.session.commit()
    flash('Patient record deleted!', 'success')
    return redirect(url_for('dashboard'))

# about
@app.route('/about')
def about():

    return render_template('about.html')

@app.route('/env-info')
def env_info():
    """Debug endpoint to see environment information"""
    import socket
    
    info = {
        "environment": {
            "in_docker": os.path.exists('/.dockerenv'),
            "flask_env": os.environ.get('FLASK_ENV'),
            "app_url": os.environ.get('APP_URL'),
            "port": os.environ.get('PORT'),
            "database_url": os.environ.get('DATABASE_URL'),
        },
        "network": {
            "hostname": socket.gethostname(),
            "internal_port": app.config.get('PORT', 5001),
            "external_access": "http://localhost:5000"
        },
        "url_examples": {
            "confirm_email_example": f"{os.environ.get('APP_URL', 'http://localhost:5000')}/confirm/test-token-123",
            "reset_password_example": f"{os.environ.get('APP_URL', 'http://localhost:5000')}/reset_password/test-token-456",
        }
    }
    return jsonify(info)

    @app.errorhandler(500)
    def internal_error(error):
        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({'success': False, 'message': 'Internal server error'}), 500
        return error

    

if __name__ == '__main__':
    # Wait for database and create tables
    initialize_database()
    
    if wait_for_db():
        logger.info("✓ Database connection established")
    else:
        logger.warning("⚠ Starting app without database connection")
    
    # Get port from environment variable (Railway/Docker will set this)
    port = int(os.environ.get('PORT', 5001))
    
    # Start the Flask app
    app.run(host='0.0.0.0', port=port, debug=False)  # debug=False for production