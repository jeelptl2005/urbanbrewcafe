from flask import Flask, render_template, request, url_for, redirect, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from urllib.parse import quote_plus
import random
import string
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cafe-website-secret-key-2026")

# Database configuration with SQLAlchemy - PostgreSQL
# Encode password to handle special characters
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False

db = SQLAlchemy(app)

# Email configuration
EMAIL_CONFIG = {
    'smtp_server': os.environ.get("EMAIL_HOST"),
    'smtp_port': int(os.environ.get("EMAIL_PORT", 587)),
    'sender_email': os.environ.get("EMAIL_USER"),
    'sender_password': os.environ.get("EMAIL_PASS")  # Use App Password for Gmail
}


# Database Models
class Signup(db.Model):
    __tablename__ = 'signup'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    orders = db.relationship('Order', backref='user', cascade='all, delete-orphan')


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
    order_items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def init_database():
    """Initialize database tables if they don't exist"""
    with app.app_context():
        try:
            db.create_all()
            print("Database tables initialized successfully!")
        except Exception as e:
            print(f"Database initialization error: {e}")


def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))


def send_otp_email(email, otp):
    """Send OTP to user's email"""
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
                <p>© 2026 Urban Brew Cafe. All rights reserved.</p>
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

        return True
    except Exception as e:
        print(f"OTP Email sending error: {e}")
        return False


def send_order_confirmation_email(customer_email, customer_name, order_details, total_amount, address):
    """Send order confirmation email"""
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Order Confirmation - Urban Brew Cafe'
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = customer_email

        # Create HTML email body
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
                📧 jeelptl2005@gmail.com</p>
              </div>
              <div class="footer">
                <p>© 2026 Urban Brew Cafe. All rights reserved.</p>
                <p>Anand, Gujarat</p>
              </div>
            </div>
          </body>
        </html>
        """

        # Attach HTML content
        msg.attach(MIMEText(html, 'html'))

        # Send email
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"Email sending error: {e}")
        return False


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        try:
            user = Signup.query.filter_by(username=username, password=password).first()

            if user:
                session['logged_in'] = True
                session['username'] = user.username
                session['email'] = user.email
                session['user_id'] = user.id
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
        email = request.form.get("email")

        try:
            # Check if email exists in database
            user = Signup.query.filter_by(email=email).first()

            if user:
                # Generate OTP
                otp = generate_otp()

                # Store OTP and email in session (expires in 10 minutes)
                session['reset_otp'] = otp
                session['reset_email'] = email
                session['otp_timestamp'] = datetime.now().timestamp()

                # Send OTP via email
                if send_otp_email(email, otp):
                    flash('OTP sent to your email successfully!', 'success')
                    return redirect(url_for('verify_otp'))
                else:
                    flash('Failed to send OTP. Please try again.', 'error')
            else:
                flash('Email not found in our records!', 'error')

        except Exception as e:
            flash(f'Error: {e}', 'error')

    return render_template("forgot_password.html")


@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    if 'reset_otp' not in session or 'reset_email' not in session:
        flash('Please request a password reset first.', 'error')
        return redirect(url_for('forgot_password'))

    if request.method == "POST":
        entered_otp = request.form.get("otp")

        # Check if OTP is expired (10 minutes)
        otp_timestamp = session.get('otp_timestamp', 0)
        current_timestamp = datetime.now().timestamp()

        if current_timestamp - otp_timestamp > 600:  # 10 minutes = 600 seconds
            session.pop('reset_otp', None)
            session.pop('reset_email', None)
            session.pop('otp_timestamp', None)
            flash('OTP expired. Please request a new one.', 'error')
            return redirect(url_for('forgot_password'))

        # Verify OTP
        if entered_otp == session.get('reset_otp'):
            # OTP verified, redirect to reset password page
            session.pop('reset_otp', None)  # Clear OTP after verification
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
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        # Validation
        if new_password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template("reset_password.html")

        if len(new_password) < 6:
            flash('Password must be at least 6 characters long!', 'error')
            return render_template("reset_password.html")

        try:
            # Update password in database
            user = Signup.query.filter_by(email=session['reset_email']).first()

            if user:
                user.password = new_password
                db.session.commit()

                # Clear session
                session.pop('reset_email', None)

                flash('Password reset successfully! Please login with your new password.', 'success')
                return redirect(url_for('login'))
            else:
                flash('User not found!', 'error')

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating password: {e}', 'error')

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

            # Insert new user
            new_user = Signup(username=username, password=password, email=email)
            db.session.add(new_user)
            db.session.commit()

            flash('Signup successful! Please login.', 'success')
            return render_template("signup.html")

        except Exception as e:
            db.session.rollback()
            print(f'Database error: {e}')
            flash(f'Database error occurred. Please try again later.', 'error')
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
        cart_items = data.get('cart_items', [])
        total_amount = data.get('total_amount', 0)
        address = data.get('address', '')

        if not cart_items or not address:
            return jsonify({'success': False, 'message': 'Invalid order data'}), 400

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
            db.session.flush()  # Get the order ID without committing

            # Insert order items
            for item in cart_items:
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
                order_details_html += f"""
                <div class="order-item">
                  <strong>{item['name']}</strong><br>
                  Quantity: {item['quantity']} × ₹{item['price']} = ₹{item['quantity'] * item['price']}
                </div>
                """

            # Send confirmation email
            email_sent = send_order_confirmation_email(
                session['email'],
                session['username'],
                order_details_html,
                total_amount,
                address
            )

            return jsonify({
                'success': True,
                'message': 'Order placed successfully!' + (
                    ' Email confirmation sent.' if email_sent else ' (Email notification failed)'),
                'order_id': new_order.id
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Database error: {str(e)}'}), 500

    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        subject = request.form.get("subject")
        message = request.form.get("message")

        # Validation
        if not name or not email or not subject or not message:
            flash('All required fields must be filled!', 'error')
            return render_template("contact.html")

        # You can save to database or send email here
        try:
            # Send email notification (optional)
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'Contact Form: {subject}'
            msg['From'] = EMAIL_CONFIG['sender_email']
            msg['To'] = EMAIL_CONFIG['sender_email']  # Send to yourself

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

            flash('Thank you for contacting us! We will get back to you soon.', 'success')
            return render_template("contact.html")

        except Exception as e:
            print(f'Email error: {e}')
            flash('Message received! We will respond shortly.', 'success')
            return render_template("contact.html")

    return render_template("contact.html")


app=app
