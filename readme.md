# Battery Repair ERP System

## Overview

This is a Battery Repair Enterprise Resource Planning (ERP) system built with Flask that manages battery repair services for a shop. The system handles customer registration, battery intake, technician workflow management, status tracking, and billing. It provides role-based access for shop staff and technicians, with shop staff handling customer interactions and battery intake, while technicians manage the repair workflow and status updates.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask web framework with Python
- **Database**: SQLite for local storage with SQLAlchemy ORM
- **Authentication**: Flask-Login for session management with role-based access control
- **Models**: Four main entities - User, Customer, Battery, and BatteryStatusHistory
- **Blueprint Structure**: Modular routing with separate auth and main blueprints

### Frontend Architecture
- **Template Engine**: Jinja2 templates with base template inheritance
- **CSS Framework**: Bootstrap with dark theme support
- **Icons**: Font Awesome for UI icons
- **Print Support**: Dedicated print stylesheet for receipts and bills
- **Responsive Design**: Mobile-friendly interface with Bootstrap grid system

### Data Models
- **User**: Role-based system (shop_staff, technician) with password hashing
- **Customer**: Basic contact information with relationship to batteries
- **Battery**: Sequential ID generation (BAT0001, BAT0002) with status tracking
- **BatteryStatusHistory**: Audit trail for status changes with timestamps and comments

### Authentication & Authorization
- **Login System**: Username/password authentication with secure password hashing
- **Role-based Access**: Shop staff can register batteries, technicians can update status
- **Session Management**: Flask-Login handles user sessions and login requirements
- **Default Users**: Seeded staff and technician accounts for immediate access

### Business Logic
- **Battery Workflow**: Received → Diagnosing → Repairing → Ready → Delivered
- **Auto ID Generation**: Sequential battery IDs with BAT prefix
- **Status Tracking**: Complete audit trail of status changes with timestamps
- **Billing System**: Service pricing with printable receipts and bills

## External Dependencies

### Python Packages
- **Flask**: Web framework for application structure
- **Flask-SQLAlchemy**: Database ORM for data persistence
- **Flask-Login**: User session and authentication management
- **Werkzeug**: Password hashing and security utilities

### Frontend Libraries
- **Bootstrap**: CSS framework for responsive UI design
- **Font Awesome**: Icon library for enhanced user interface
- **Print CSS**: Custom stylesheet for document printing

### Database
- **SQLite**: Local file-based database for data storage
- **SQLAlchemy**: ORM layer with declarative base for model definitions

### Infrastructure
- **Development Server**: Flask built-in development server
- **Static Files**: CSS and print stylesheets served via Flask static file handling
- **Template Rendering**: Jinja2 template engine for dynamic HTML generation
