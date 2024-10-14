from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
import smtplib
from email.mime.text import MIMEText
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///health.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'yoursecretkey'
db = SQLAlchemy(app)

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "anoushazaidi432@gmail.com"
EMAIL_PASSWORD = "nhdn nauu qfue lnhn"  # Replace with actual app password

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Email sending function
def send_email(recipient, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = recipient

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, recipient, msg.as_string())
            print(f"Email sent to: {recipient}")
    except Exception as e:
        print(f"Failed to send email to {recipient}: {e}")

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    dateOfBirth = db.Column(db.String(200), nullable=False)
    gender = db.Column(db.String(200), nullable=False)


class HealthLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    blood_sugar = db.Column(db.Float, nullable=False)
    blood_pressure = db.Column(db.String(50), nullable=False)
    medication = db.Column(db.String(100), nullable=True)
    date = db.Column(db.String(10), nullable=False, default=datetime.now(timezone.utc).strftime('%Y-%m-%d'))

class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.String(200), nullable=False)
    time = db.Column(db.String(5), nullable=False)  # Format: HH:MM

# Initialize the database tables
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
def check_reminders():
    with app.app_context():  # Create an application context
        now = datetime.now().strftime('%H:%M')
        print(f"Checking reminders at: {now}")
        
        # Query for reminders that match the current time
        reminders = Reminder.query.filter_by(time=now).all()
        
        if reminders:
            print(f"Found {len(reminders)} reminders due.")
        else:
            print("No reminders due at this time.")
        
        for reminder in reminders:
            user = User.query.get(reminder.user_id)  # Fetch the user associated with the reminder
            if user and user.email:
                subject = "Reminder Notification"
                body = f"Hello {user.username},\n\nThis is a reminder for: {reminder.text}"
                print(f"Preparing to send email for reminder: {reminder.text}")
                send_email(user.email, subject, body)

# Set up a background scheduler to run check_reminders every minute
scheduler = BackgroundScheduler()
scheduler.add_job(check_reminders, 'interval', minutes=1)
scheduler.start()

# Ensure scheduler shuts down when the app exits
atexit.register(lambda: scheduler.shutdown())

# Routes
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        dateOfBirth = request.form['dateOfBirth']
        gender = request.form['gender']
        new_user = User(username=username, password=password, email=email, dateOfBirth= dateOfBirth, gender= gender)
        
        db.session.add(new_user)
        db.session.commit()
        flash("Signup successful. Please login.", "success")
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for('index'))
        flash("Invalid username or password", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    health_logs = HealthLog.query.filter_by(user_id=current_user.id).order_by(HealthLog.date.desc()).all()
    reminders = Reminder.query.filter_by(user_id=current_user.id).all()

    def calculate_averages(logs):
        if not logs:
            return {"avg_blood_sugar": None, "avg_blood_pressure": None, "medications_count": 0,
                    "high_blood_sugar_count": 0, "high_blood_pressure_count": 0}

        avg_blood_sugar = sum(log.blood_sugar for log in logs) / len(logs)
        avg_blood_pressure = sum([int(bp.split('/')[0]) for bp in (log.blood_pressure for log in logs)]) / len(logs)
        medications_count = sum(1 for log in logs if log.medication)
        
        high_blood_sugar_count = sum(1 for log in logs if log.blood_sugar > 140)
        high_blood_pressure_count = sum(1 for log in logs if int(log.blood_pressure.split('/')[0]) > 120)
        
        return {
            "avg_blood_sugar": round(avg_blood_sugar, 2),
            "avg_blood_pressure": round(avg_blood_pressure, 2),
            "medications_count": medications_count,
            "high_blood_sugar_count": high_blood_sugar_count,
            "high_blood_pressure_count": high_blood_pressure_count
        }

    one_week_ago = datetime.now(timezone.utc) - timedelta(weeks=1)
    one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)

    weekly_logs = [log for log in health_logs if datetime.strptime(log.date, '%Y-%m-%d').replace(tzinfo=timezone.utc) >= one_week_ago]
    monthly_logs = [log for log in health_logs if datetime.strptime(log.date, '%Y-%m-%d').replace(tzinfo=timezone.utc) >= one_month_ago]

    weekly_averages = calculate_averages(weekly_logs)
    monthly_averages = calculate_averages(monthly_logs)

    return render_template('index.html', username=current_user.username, health_logs=health_logs, reminders=reminders, 
                           weekly_averages=weekly_averages, monthly_averages=monthly_averages)

@app.route('/log', methods=['POST'])
@login_required
def log_health():
    blood_sugar = float(request.form['bloodSugar'])
    blood_pressure = request.form['bloodPressure']
    medication = request.form['medication']
    new_log = HealthLog(user_id=current_user.id, blood_sugar=blood_sugar, blood_pressure=blood_pressure, medication=medication)
    db.session.add(new_log)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_reminder', methods=['POST'])
@login_required
def add_reminder():
    text = request.form['reminderText']
    time = request.form['reminderTime']
    new_reminder = Reminder(user_id=current_user.id, text=text, time=time)
    db.session.add(new_reminder)
    db.session.commit()
    
    # Print confirmation message
    print(f"Reminder added for user: {current_user.username} at {time} with text: {text}")
    
    flash("Reminder added successfully!", "success")
    return redirect(url_for('index'))

@app.route('/history')
@login_required
def history():
    health_logs = HealthLog.query.filter_by(user_id=current_user.id).order_by(HealthLog.date.desc()).all()
    return render_template('history.html', health_logs=health_logs)

if __name__ == '__main__':
    app.run(debug=True)
