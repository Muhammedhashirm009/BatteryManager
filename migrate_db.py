#!/usr/bin/env python3
"""
Database initialization script
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import generate_password_hash
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Create Flask app for migration
migration_app = Flask(__name__)
migration_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///battery_repair.db"
migration_app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

migration_db = SQLAlchemy(model_class=Base)
migration_db.init_app(migration_app)

# Import models after db is set up
with migration_app.app_context():
    from datetime import datetime
    
    class User(migration_db.Model):
        id = migration_db.Column(migration_db.Integer, primary_key=True)
        username = migration_db.Column(migration_db.String(64), unique=True, nullable=False)
        password_hash = migration_db.Column(migration_db.String(256), nullable=False)
        role = migration_db.Column(migration_db.String(20), nullable=False)
        full_name = migration_db.Column(migration_db.String(100), nullable=False)
        created_at = migration_db.Column(migration_db.DateTime, default=datetime.utcnow)
        is_active = migration_db.Column(migration_db.Boolean, default=True)

    class SystemSettings(migration_db.Model):
        id = migration_db.Column(migration_db.Integer, primary_key=True)
        setting_key = migration_db.Column(migration_db.String(50), unique=True, nullable=False)
        setting_value = migration_db.Column(migration_db.Text, nullable=False)
        updated_at = migration_db.Column(migration_db.DateTime, default=datetime.utcnow)
    
    # Remove old database if exists
    db_path = 'battery_repair.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed old database: {db_path}")
    
    # Create all tables
    migration_db.create_all()
    print("Created all database tables with new schema")
    
    # Create default users
    try:
        admin_user = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            role='admin',
            full_name='Administrator',
            is_active=True
        )
        migration_db.session.add(admin_user)
        
        staff_user = User(
            username='staff',
            password_hash=generate_password_hash('staff123'),
            role='shop_staff',
            full_name='Shop Staff',
            is_active=True
        )
        migration_db.session.add(staff_user)
        
        tech_user = User(
            username='technician',
            password_hash=generate_password_hash('tech123'),
            role='technician',
            full_name='Technician',
            is_active=True
        )
        migration_db.session.add(tech_user)
        
        # Initialize system settings
        default_settings = [
            ('shop_name', 'Battery Repair Service'),
            ('battery_id_prefix', 'BAT'),
            ('battery_id_start', '1'),
            ('battery_id_padding', '4')
        ]
        
        for key, value in default_settings:
            setting = SystemSettings(setting_key=key, setting_value=value)
            migration_db.session.add(setting)
        
        migration_db.session.commit()
        print("Successfully created default users and settings!")
        print("Default logins:")
        print("  Admin: username='admin', password='admin123'")
        print("  Staff: username='staff', password='staff123'")
        print("  Technician: username='technician', password='tech123'")
        
    except Exception as e:
        print(f"Error creating users: {e}")
        migration_db.session.rollback()