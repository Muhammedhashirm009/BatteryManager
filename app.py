import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase

# Set up logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "battery-repair-erp-secret-key")

# Configure the database - use SQLite for local storage
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///battery_repair.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

def initialize_database():
    """Initialize database with default users and settings"""
    from models import User, SystemSettings
    from werkzeug.security import generate_password_hash
    
    # Create default users if they don't exist
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            role='admin',
            full_name='Administrator'
        )
        db.session.add(admin_user)
    
    if not User.query.filter_by(username='staff').first():
        staff_user = User(
            username='staff',
            password_hash=generate_password_hash('staff123'),
            role='shop_staff',
            full_name='Shop Staff'
        )
        db.session.add(staff_user)
    
    if not User.query.filter_by(username='technician').first():
        tech_user = User(
            username='technician',
            password_hash=generate_password_hash('tech123'),
            role='technician',
            full_name='Technician'
        )
        db.session.add(tech_user)
    
    # Initialize system settings
    default_settings = [
        ('shop_name', 'Battery Repair Service'),
        ('battery_id_prefix', 'BAT'),
        ('battery_id_start', '1'),
        ('battery_id_padding', '4')
    ]
    
    for key, value in default_settings:
        if not SystemSettings.query.filter_by(setting_key=key).first():
            setting = SystemSettings(setting_key=key, setting_value=value)
            db.session.add(setting)
    
    try:
        db.session.commit()
    except Exception as e:
        logging.error(f"Error creating default users and settings: {e}")
        db.session.rollback()

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()
    initialize_database()

# Register blueprints
from auth import auth_bp
from routes import main_bp

app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
