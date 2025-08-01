from app import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import func

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'shop_staff' or 'technician'
    full_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with batteries
    batteries = db.relationship('Battery', backref='customer', lazy=True)

class Battery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    battery_id = db.Column(db.String(20), unique=True, nullable=False)  # BAT0001, BAT0002, etc.
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    battery_type = db.Column(db.String(100), nullable=False)
    voltage = db.Column(db.String(10), nullable=False)  # e.g., "12V"
    capacity = db.Column(db.String(10), nullable=False)  # e.g., "100Ah"
    status = db.Column(db.String(20), default='Received', nullable=False)
    inward_date = db.Column(db.DateTime, default=datetime.utcnow)
    service_price = db.Column(db.Float, default=0.0)
    
    # Relationship with status history
    status_history = db.relationship('BatteryStatusHistory', backref='battery', lazy=True, cascade='all, delete-orphan')
    
    @staticmethod
    def generate_next_battery_id():
        """Generate the next sequential battery ID"""
        last_battery = Battery.query.order_by(Battery.id.desc()).first()
        if last_battery:
            # Extract number from last battery ID (e.g., BAT0001 -> 1)
            last_num = int(last_battery.battery_id[3:])
            next_num = last_num + 1
        else:
            next_num = 1
        return f"BAT{next_num:04d}"

class BatteryStatusHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    battery_id = db.Column(db.Integer, db.ForeignKey('battery.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    comments = db.Column(db.Text)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='status_updates')
