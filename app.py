from flask import Flask, render_template, request, url_for, redirect, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import random
import string
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ===== CONFIGURATION =====
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Fix for Supabase - Replace postgres:// with postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = os.getenv('SQLALCHEMY_ECHO', 'false').lower() == 'true'
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'pool_size': 10,
    'max_overflow': 20,
    'connect_args': {
        'connect_timeout': 10
    }
}

db = SQLAlchemy(app)

# Email configuration from environment variables
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': os.getenv('EMAIL_USER'),
    'sender_password': os.getenv('EMAIL_PASSWORD')
}

# Validate email configuration
if not EMAIL_CONFIG['sender_email'] or not EMAIL_CONFIG['sender_password']:
    logger.warning("Email credentials not configured. Email functionality will be disabled.")


# ===== DATABASE MODELS =====
class Signup(db.Model):
    __tablename__ = 'signup'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationship
    orders = db.relationship('Order', backref='user', cascade='all, delete-orphan', lazy='dynamic')

    # Password property
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('signup.id', ondelete='CASCADE'), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    delivery_address = db.Column(db.Text, nullable=False)
    order_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    order_items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan', lazy='dynamic')


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ===== HELPER FUNCTIONS =====
def init_database():
    """Initialize database tables if they don't exist"""
    with app.app_context():
        try:
            # Drop all existing tables to recreate with new schema
            db.drop_all()
            # Create all tables with updated schema
            db.create_all()
            print("✅ Database tables initialized successfully!")

            # Optional: Create a test admin user
            try:
                admin_user = Signup(
                    username="admin",
                    email="admin@urbanbrew.com"
                )
                admin_user.password = "Admin@123"  # Uses the setter to hash password
                db.session.add(admin_user)
                db.session.commit()
                print("✅ Admin test user created!")
            except:
                db.session.rollback()
                print("ℹ️  Admin user already exists or not needed")

        except Exception as e:
            print(f"❌ Database initialization error: {e}")


def generate_otp(length=6):
    """Generate a numeric OTP"""
    return ''.join(random.choices(string.digits, k=length))


def is_otp_valid(timestamp):
    """Check if OTP is still valid (10 minutes)"""
    if not timestamp:
        return False
    return datetime.now().timestamp() - timestamp < 600  # 10 minutes


def send_otp_email(email, otp):
    """Send OTP to user's email"""
    if not EMAIL_CONFIG['sender_email'] or not EMAIL_CONFIG['sender_password']:
        logger.error("Email credentials not configured")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Password Reset OTP - Urban Brew Cafe'
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = email

        html = f"""
        <html>
          <head>
            <style>
              body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
              .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
              .header {{ background: #B98C00; color: white; padding: 20px; text-align: center; }}
              .content {{ background: #f9f9f9; padding: 30px; }}
              .otp-box {{ background: white; padding: 20px; margin: 20px 0; border-radius: 10px; text-align: center; }}
              .otp {{ font-size: 32px; font-weight: bold; color: #B98C00; letter-spacing: 5px; }}
              .footer {{ text-align: center; padding: 20px; color: #666; }}
            </style>
          </head>
          <body>
            <div class="container">
              <div class="header">
                <h1>☕ Urban Brew Cafe</h1>
                <p>Password Reset Request</p>
              </div>
              <div class="content">
                <h2>Reset Your Password</h2>
                <p>We received a request to reset your password. Use the OTP below to continue:</p>

                <div class="otp-box">
                  <p style="margin: 0; color: #666;">Your OTP Code:</p>
                  <p class="otp">{otp}</p>
                  <p style="margin: 0; color: #666; font-size: 14px;">This OTP is valid for 10 minutes</p>
                </div>

                <p><strong>If you didn't request this,</strong> please ignore this email and your password will remain unchanged.</p>

                <p>For security reasons, never share this OTP with anyone.</p>
              </div>
              <div class="footer">
                <p>© {datetime.now().year} Urban Brew Cafe. All rights reserved.</p>
                <p>Anand, Gujarat</p>
              </div>
            </div>
          </body>
        </html>
        """

        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)

        logger.info(f"OTP sent to {email}")
        return True
    except Exception as e:
        logger.error(f"OTP Email sending error: {e}")
        return False


def send_order_confirmation_email(customer_email, customer_name, order_details, total_amount, address):
    """Send order confirmation email"""
    if not EMAIL_CONFIG['sender_email'] or not EMAIL_CONFIG['sender_password']:
        logger.error("Email credentials not configured")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Order Confirmation - Urban Brew Cafe'
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = customer_email

        html = f"""
        <html>
          <head>
            <style>
              body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
              .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
              .header {{ background: #B98C00; color: white; padding: 20px; text-align: center; }}
              .content {{ background: #f9f9f9; padding: 20px; }}
              .order-item {{ background: white; padding: 15px; margin: 10px 0; border-radius: 5px; }}
              .total {{ font-size: 20px; font-weight: bold; color: #B98C00; margin-top: 20px; }}
              .footer {{ text-align: center; padding: 20px; color: #666; }}
            </style>
          </head>
          <body>
            <div class="container">
              <div class="header">
                <h1>☕ Urban Brew Cafe</h1>
                <p>Order Confirmation</p>
              </div>
              <div class="content">
                <h2>Hello {customer_name}!</h2>
                <p>Thank you for your order. We're preparing it with love! ❤️</p>

                <h3>Order Details:</h3>
                <p><strong>Order Date:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>

                <h3>Delivery Address:</h3>
                <p>{address}</p>

                <h3>Items Ordered:</h3>
                {order_details}

                <div class="total">
                  Total Amount: ₹{total_amount}
                </div>

                <p style="margin-top: 20px;">
                  <strong>Estimated Delivery Time:</strong> 30-40 minutes
                </p>

                <p>If you have any questions, please contact us at:</p>
                <p>📞 +91 9313464150<br>
                📧 {EMAIL_CONFIG['sender_email']}</p>
              </div>
              <div class="footer">
                <p>© {datetime.now().year} Urban Brew Cafe. All rights reserved.</p>
                <p>Anand, Gujarat</p>
              </div>
            </div>
          </body>
        </html>
        """

        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)

        logger.info(f"Order confirmation sent to {customer_email}")
        return True
    except Exception as e:
        logger.error(f"Order confirmation email error: {e}")
        return False


# ===== ROUTES =====
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        try:
            # Find user by username
            user = Signup.query.filter_by(username=username).first()

            if user and user.verify_password(password):  # Use verify_password method
                session['logged_in'] = True
                session['username'] = user.username
                session['email'] = user.email
                session['user_id'] = user.id

                # Update last login time
                user.last_login = datetime.utcnow()
                db.session.commit()

                flash('Login successful!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid username or password!', 'error')
                return render_template("login.html", error=True)
        except Exception as e:
            flash(f'Database error: {e}', 'error')
            return render_template("login.html", error=True)

    return render_template("login.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email:
            flash('Email is required!', 'error')
            return render_template("forgot_password.html")

        try:
            user = Signup.query.filter_by(email=email).first()

            if user:
                otp = generate_otp()

                # Store OTP and email in session
                session['reset_otp'] = otp
                session['reset_email'] = email
                session['otp_timestamp'] = datetime.now().timestamp()

                if send_otp_email(email, otp):
                    flash('OTP sent to your email successfully!', 'success')
                    return redirect(url_for('verify_otp'))
                else:
                    flash('Failed to send OTP. Please try again.', 'error')
            else:
                # Don't reveal if email exists (security best practice)
                flash('If an account exists with this email, an OTP will be sent.', 'info')
                # Still redirect to verify OTP to prevent email enumeration
                return redirect(url_for('verify_otp'))

        except SQLAlchemyError as e:
            logger.error(f"Database error in forgot password: {e}")
            flash('An error occurred. Please try again.', 'error')
        except Exception as e:
            logger.error(f"Unexpected error in forgot password: {e}")
            flash('An unexpected error occurred.', 'error')

    return render_template("forgot_password.html")


@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    # Always show the OTP verification page
    # Don't redirect even if no OTP in session (security)

    if request.method == "POST":
        entered_otp = request.form.get("otp", "").strip()

        if not entered_otp:
            flash('OTP is required!', 'error')
            return render_template("verify_otp.html")

        # Check if OTP exists and is valid
        if 'reset_otp' not in session or 'reset_email' not in session:
            flash('Invalid or expired OTP. Please request a new one.', 'error')
            return redirect(url_for('forgot_password'))

        # Check OTP expiration
        otp_timestamp = session.get('otp_timestamp')
        if not is_otp_valid(otp_timestamp):
            session.pop('reset_otp', None)
            session.pop('reset_email', None)
            session.pop('otp_timestamp', None)
            flash('OTP expired. Please request a new one.', 'error')
            return redirect(url_for('forgot_password'))

        # Verify OTP
        if entered_otp == session.get('reset_otp'):
            session.pop('reset_otp', None)
            session.pop('otp_timestamp', None)
            return redirect(url_for('reset_password'))
        else:
            flash('Invalid OTP. Please try again.', 'error')

    return render_template("verify_otp.html")


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if 'reset_email' not in session:
        flash('Session expired. Please start the password reset process again.', 'error')
        return redirect(url_for('forgot_password'))

    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validation
        if not new_password or not confirm_password:
            flash('Both password fields are required!', 'error')
            return render_template("reset_password.html")

        if new_password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template("reset_password.html")

        if len(new_password) < 6:
            flash('Password must be at least 6 characters long!', 'error')
            return render_template("reset_password.html")

        try:
            user = Signup.query.filter_by(email=session['reset_email']).first()

            if user:
                user.password = new_password  # Uses the setter to hash password
                db.session.commit()

                # Clear session
                session.pop('reset_email', None)

                flash('Password reset successfully! Please login with your new password.', 'success')
                return redirect(url_for('login'))
            else:
                flash('User not found!', 'error')
                return redirect(url_for('forgot_password'))

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error resetting password: {e}")
            flash('An error occurred. Please try again.', 'error')
        except Exception as e:
            logger.error(f"Unexpected error resetting password: {e}")
            flash('An unexpected error occurred.', 'error')

    return render_template("reset_password.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        email = request.form.get("email")

        # Validation
        if not username or not password or not email:
            flash('All fields are required!', 'error')
            return render_template("signup.html")

        if len(password) < 6:
            flash('Password must be at least 6 characters long!', 'error')
            return render_template("signup.html")

        try:
            # Check if username already exists
            if Signup.query.filter_by(username=username).first():
                flash('Username already exists! Please choose another.', 'error')
                return render_template("signup.html")

            # Check if email already exists
            if Signup.query.filter_by(email=email).first():
                flash('Email already registered! Please use another email.', 'error')
                return render_template("signup.html")

            # Create new user with password hashing
            new_user = Signup(username=username, email=email)
            new_user.password = password  # This uses the setter to hash the password
            db.session.add(new_user)
            db.session.commit()

            flash('Signup successful! Please login.', 'success')
            return redirect(url_for('login'))  # Redirect to login page

        except Exception as e:
            db.session.rollback()
            print(f'Database error: {e}')
            flash(f'Error occurred. Please try again.', 'error')
            return render_template("signup.html")

    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))


@app.route("/order")
def order():
    return render_template("orders.html")


@app.route("/place_order", methods=["POST"])
def place_order():
    if 'logged_in' not in session:
        return jsonify({'success': False, 'message': 'Please login to place an order'}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Invalid request data'}), 400

        cart_items = data.get('cart_items', [])
        total_amount = data.get('total_amount', 0)
        address = data.get('address', '').strip()

        if not cart_items:
            return jsonify({'success': False, 'message': 'Cart is empty'}), 400

        if not address:
            return jsonify({'success': False, 'message': 'Delivery address is required'}), 400

        if total_amount <= 0:
            return jsonify({'success': False, 'message': 'Invalid total amount'}), 400

        try:
            # Create new order
            new_order = Order(
                user_id=session['user_id'],
                username=session['username'],
                email=session['email'],
                total_amount=total_amount,
                delivery_address=address,
                order_date=datetime.now(),
                status='Pending'
            )
            db.session.add(new_order)
            db.session.flush()

            # Insert order items
            for item in cart_items:
                if 'name' not in item or 'quantity' not in item or 'price' not in item:
                    continue

                new_item = OrderItem(
                    order_id=new_order.id,
                    item_name=item['name'],
                    quantity=item['quantity'],
                    price=item['price']
                )
                db.session.add(new_item)

            db.session.commit()

            # Prepare order details for email
            order_details_html = ""
            for item in cart_items:
                if 'name' in item and 'quantity' in item and 'price' in item:
                    subtotal = item['quantity'] * item['price']
                    order_details_html += f"""
                    <div class="order-item">
                      <strong>{item['name']}</strong><br>
                      Quantity: {item['quantity']} × ₹{item['price']} = ₹{subtotal}
                    </div>
                    """

            # Send confirmation email
            email_sent = False
            if EMAIL_CONFIG['sender_email'] and EMAIL_CONFIG['sender_password']:
                email_sent = send_order_confirmation_email(
                    session['email'],
                    session['username'],
                    order_details_html,
                    total_amount,
                    address
                )

            return jsonify({
                'success': True,
                'message': 'Order placed successfully!' +
                           (' Email confirmation sent.' if email_sent else ' (Email notification failed)'),
                'order_id': new_order.id
            })

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error placing order: {e}")
            return jsonify({'success': False, 'message': 'Failed to save order. Please try again.'}), 500
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error placing order: {e}")
            return jsonify({'success': False, 'message': 'An unexpected error occurred.'}), 500

    except Exception as e:
        logger.error(f"Error processing order request: {e}")
        return jsonify({'success': False, 'message': 'Invalid request format'}), 400


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        # Validation
        if not name or not email or not subject or not message:
            flash('All required fields must be filled!', 'error')
            return render_template("contact.html")

        if len(message) < 10:
            flash('Message must be at least 10 characters long!', 'error')
            return render_template("contact.html")

        try:
            # Only send email if credentials are configured
            if EMAIL_CONFIG['sender_email'] and EMAIL_CONFIG['sender_password']:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = f'Contact Form: {subject}'
                msg['From'] = EMAIL_CONFIG['sender_email']
                msg['To'] = EMAIL_CONFIG['sender_email']

                html = f"""
                <html>
                  <body style="font-family: Arial, sans-serif;">
                    <h2 style="color: #B98C00;">New Contact Form Submission</h2>
                    <p><strong>Name:</strong> {name}</p>
                    <p><strong>Email:</strong> {email}</p>
                    <p><strong>Phone:</strong> {phone if phone else 'Not provided'}</p>
                    <p><strong>Subject:</strong> {subject}</p>
                    <p><strong>Message:</strong></p>
                    <p>{message}</p>
                  </body>
                </html>
                """

                msg.attach(MIMEText(html, 'html'))

                with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
                    server.starttls()
                    server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
                    server.send_message(msg)

                logger.info(f"Contact form submission from {email}")
                flash('Thank you for contacting us! We will get back to you soon.', 'success')
            else:
                flash('Message received! We will respond shortly.', 'success')

        except Exception as e:
            logger.error(f"Contact form email error: {e}")
            flash('Message received! We will respond shortly.', 'success')

        return render_template("contact.html")

    return render_template("contact.html")


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f"Internal server error: {e}")
    return render_template('500.html'), 500


app= app
