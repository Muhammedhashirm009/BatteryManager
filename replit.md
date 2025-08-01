# Battery Repair ERP System

## Project Overview
A Flask-based ERP system for battery repair shops with features for:
- Customer and battery management
- Status tracking and history
- User authentication (admin, staff, technician roles)
- Receipt and bill generation
- Search functionality

## Project Architecture
- **Backend**: Flask with SQLAlchemy ORM
- **Database**: PostgreSQL (migrated from SQLite for Replit compatibility)
- **Authentication**: Flask-Login with role-based access
- **Deployment**: Gunicorn WSGI server

## User Preferences
- Prefer web-based interfaces over API endpoints
- Focus on clean, functional UI
- Robust security practices required

## Recent Changes
- **2025-08-01**: Successfully migrated from Replit Agent to Replit environment
- Database migrated from SQLite to PostgreSQL for production readiness
- Added ProxyFix middleware for proper HTTPS URL generation
- Updated configuration for environment variables
- Fixed backup and restore functionality - now fully operational
- Updated technician panel to show minimal view unless searched
- Fixed bill page display issues
- Updated backup permissions to allow staff users
- Added secondary mobile number field to customer records
- Implemented monthly and yearly reporting functionality  
- Made battery IDs clickable: Ready status → Bill page, Others → Technician page
- Fixed billing summary display and shop name integration
- Updated receipt to use shop name from system settings
- Made all pending battery IDs clickable across search and finished battery pages
- Fixed technician panel battery IDs to be clickable in both minimal and detailed views
- Added Docker support with PostgreSQL for easy deployment and installation
- Created .env.example file with all required environment variables
- Added pickup service charge functionality for batteries collected from customer sites
- Updated billing and receipt templates to show pickup charges separately
- Enhanced revenue calculations to include pickup service charges

## Environment Variables Required
- `SESSION_SECRET`: Flask session secret key
- `DATABASE_URL`: PostgreSQL connection string (auto-provided by Replit)

## Database Models
- User: Authentication and role management
- Customer: Customer information
- Battery: Battery tracking with auto-generated IDs
- BatteryStatusHistory: Status change tracking
- SystemSettings: Configurable system parameters