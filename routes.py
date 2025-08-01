from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response, jsonify, send_file
from flask_login import login_required, current_user
from app import db
from models import User, Customer, Battery, BatteryStatusHistory, SystemSettings
from werkzeug.security import generate_password_hash
from datetime import datetime
import csv
import io
import json
import tempfile
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return redirect(url_for('main.dashboard'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Get statistics for dashboard
    total_batteries = Battery.query.count()
    pending_batteries = Battery.query.filter(Battery.status.in_(['Received', 'Diagnosing', 'Repairing'])).count()
    completed_batteries = Battery.query.filter_by(status='Ready').count()
    
    # Recent batteries
    recent_batteries = Battery.query.order_by(Battery.inward_date.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                         total_batteries=total_batteries,
                         pending_batteries=pending_batteries,
                         completed_batteries=completed_batteries,
                         recent_batteries=recent_batteries)

@main_bp.route('/battery/entry', methods=['GET', 'POST'])
@login_required
def battery_entry():
    if current_user.role not in ['shop_staff', 'admin']:
        flash('Access denied. This feature is only available to shop staff and admin.', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        customer_name = request.form.get('customer_name')
        mobile = request.form.get('mobile')
        battery_type = request.form.get('battery_type')
        voltage = request.form.get('voltage')
        capacity = request.form.get('capacity')
        
        if not all([customer_name, mobile, battery_type, voltage, capacity]):
            flash('All fields are required.', 'error')
            return render_template('battery_entry.html')
        
        try:
            # Check if customer exists or create new one
            customer = Customer.query.filter_by(mobile=mobile).first()
            if not customer:
                customer = Customer()
                customer.name = customer_name
                customer.mobile = mobile
                db.session.add(customer)
                db.session.flush()  # Get customer ID
            
            # Generate battery ID
            battery_id = Battery.generate_next_battery_id()
            
            # Create battery record
            battery = Battery()
            battery.battery_id = battery_id
            battery.customer_id = customer.id
            battery.battery_type = battery_type
            battery.voltage = voltage
            battery.capacity = capacity
            battery.status = 'Received'
            db.session.add(battery)
            db.session.flush()  # Get battery record ID
            
            # Add initial status history
            status_history = BatteryStatusHistory()
            status_history.battery_id = battery.id
            status_history.status = 'Received'
            status_history.comments = 'Battery received from customer'
            status_history.updated_by = current_user.id
            db.session.add(status_history)
            
            db.session.commit()
            flash(f'Battery {battery_id} has been successfully registered.', 'success')
            return redirect(url_for('main.receipt', battery_id=battery.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error registering battery: {str(e)}', 'error')
    
    return render_template('battery_entry.html')

@main_bp.route('/technician/panel', methods=['GET', 'POST'])
@login_required
def technician_panel():
    if current_user.role not in ['technician', 'shop_staff', 'admin']:
        flash('Access denied.', 'error')
        return redirect(url_for('main.dashboard'))
    
    batteries = []
    search_query = ''
    
    if request.method == 'POST':
        search_query = request.form.get('search_query', '').strip()
        
        if search_query:
            # Search by battery ID, customer mobile, or customer name
            batteries = Battery.query.join(Customer).filter(
                db.and_(
                    Battery.status.in_(['Received', 'Diagnosing', 'Repairing']),
                    db.or_(
                        Battery.battery_id.ilike(f'%{search_query}%'),
                        Customer.mobile.ilike(f'%{search_query}%'),
                        Customer.name.ilike(f'%{search_query}%')
                    )
                )
            ).order_by(Battery.inward_date.asc()).all()
        else:
            # If no search query, show all pending batteries
            batteries = Battery.query.filter(
                Battery.status.in_(['Received', 'Diagnosing', 'Repairing'])
            ).order_by(Battery.inward_date.asc()).all()
    else:
        # GET request - show only battery IDs (minimal view)
        batteries = Battery.query.filter(
            Battery.status.in_(['Received', 'Diagnosing', 'Repairing'])
        ).order_by(Battery.inward_date.asc()).all()
    
    return render_template('technician_panel.html', batteries=batteries, search_query=search_query, show_full_details=(request.method == 'POST' and search_query))

@main_bp.route('/battery/update', methods=['POST'])
@login_required
def update_battery_status():
    if current_user.role not in ['technician', 'shop_staff', 'admin']:
        flash('Access denied.', 'error')
        return redirect(url_for('main.dashboard'))
    
    battery_id = request.form.get('battery_id')
    new_status = request.form.get('status')
    comments = request.form.get('comments', '')
    service_price = request.form.get('service_price', 0)
    
    try:
        battery = Battery.query.get_or_404(battery_id)
        battery.status = new_status
        
        if service_price:
            battery.service_price = float(service_price)
        
        # Add status history
        status_history = BatteryStatusHistory()
        status_history.battery_id = battery.id
        status_history.status = new_status
        status_history.comments = comments
        status_history.updated_by = current_user.id
        db.session.add(status_history)
        db.session.commit()
        
        flash(f'Battery {battery.battery_id} status updated to {new_status}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating battery status: {str(e)}', 'error')
    
    return redirect(url_for('main.technician_panel'))

@main_bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    results = []
    search_query = ''
    
    if request.method == 'POST':
        search_query = request.form.get('search_query', '').strip()
        
        if search_query:
            # Search by battery ID or customer mobile
            batteries = Battery.query.join(Customer).filter(
                db.or_(
                    Battery.battery_id.ilike(f'%{search_query}%'),
                    Customer.mobile.ilike(f'%{search_query}%'),
                    Customer.name.ilike(f'%{search_query}%')
                )
            ).all()
            results = batteries
    
    return render_template('search.html', results=results, search_query=search_query)

@main_bp.route('/receipt/<int:battery_id>')
@login_required
def receipt(battery_id):
    battery = Battery.query.get_or_404(battery_id)
    return render_template('receipt.html', battery=battery)

@main_bp.route('/bill/<int:battery_id>')
@login_required
def bill(battery_id):
    battery = Battery.query.get_or_404(battery_id)
    if battery.status != 'Ready':
        flash('Bill can only be generated for completed repairs.', 'error')
        return redirect(url_for('main.search'))
    
    return render_template('bill.html', battery=battery)

@main_bp.route('/export/csv')
@login_required
def export_csv():
    try:
        batteries = Battery.query.join(Customer).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Battery ID', 'Customer Name', 'Mobile', 'Battery Type', 
            'Voltage', 'Capacity', 'Status', 'Inward Date', 
            'Service Price', 'Last Updated'
        ])
        
        # Write data
        for battery in batteries:
            last_update = battery.status_history[-1].updated_at if battery.status_history else battery.inward_date
            writer.writerow([
                battery.battery_id,
                battery.customer.name,
                battery.customer.mobile,
                battery.battery_type,
                battery.voltage,
                battery.capacity,
                battery.status,
                battery.inward_date.strftime('%Y-%m-%d %H:%M'),
                battery.service_price,
                last_update.strftime('%Y-%m-%d %H:%M')
            ])
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename=battery_records_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response.headers['Content-type'] = 'text/csv'
        
        return response
        
    except Exception as e:
        flash(f'Error exporting data: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/battery/<int:battery_id>/details')
@login_required
def battery_details(battery_id):
    battery = Battery.query.get_or_404(battery_id)
    return render_template('battery_details.html', battery=battery)

# Admin routes
@main_bp.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Access denied. Admin access required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@main_bp.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
def admin_add_user():
    if current_user.role != 'admin':
        flash('Access denied. Admin access required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        full_name = request.form.get('full_name')
        role = request.form.get('role')
        password = request.form.get('password')
        
        if not all([username, full_name, role, password]):
            flash('All fields are required.', 'error')
            return render_template('admin/add_user.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return render_template('admin/add_user.html')
        
        try:
            user = User()
            user.username = username
            user.full_name = full_name
            user.role = role
            if password:
                user.password_hash = generate_password_hash(password)
            db.session.add(user)
            db.session.commit()
            flash(f'User {username} created successfully.', 'success')
            return redirect(url_for('main.admin_users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'error')
    
    return render_template('admin/add_user.html')

@main_bp.route('/admin/users/<int:user_id>/toggle', methods=['POST'])
@login_required
def admin_toggle_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Cannot deactivate your own account.', 'error')
        return redirect(url_for('main.admin_users'))
    
    user.active = not user.active
    try:
        db.session.commit()
        status = 'activated' if user.active else 'deactivated'
        flash(f'User {user.username} has been {status}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating user: {str(e)}', 'error')
    
    return redirect(url_for('main.admin_users'))

@main_bp.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    if current_user.role != 'admin':
        flash('Access denied. Admin access required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        shop_name = request.form.get('shop_name')
        battery_prefix = request.form.get('battery_id_prefix')
        battery_start = request.form.get('battery_id_start')
        battery_padding = request.form.get('battery_id_padding')
        
        try:
            SystemSettings.set_setting('shop_name', shop_name)
            SystemSettings.set_setting('battery_id_prefix', battery_prefix)
            SystemSettings.set_setting('battery_id_start', battery_start)
            SystemSettings.set_setting('battery_id_padding', battery_padding)
            db.session.commit()
            flash('Settings updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating settings: {str(e)}', 'error')
    
    settings = {
        'shop_name': SystemSettings.get_setting('shop_name', 'Battery Repair Service'),
        'battery_id_prefix': SystemSettings.get_setting('battery_id_prefix', 'BAT'),
        'battery_id_start': SystemSettings.get_setting('battery_id_start', '1'),
        'battery_id_padding': SystemSettings.get_setting('battery_id_padding', '4')
    }
    
    return render_template('admin/settings.html', settings=settings)

@main_bp.route('/admin/backup')
@login_required
def admin_backup():
    if current_user.role != 'admin':
        flash('Access denied. Admin access required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Create comprehensive backup data
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'users': [],
            'customers': [],
            'batteries': [],
            'status_history': [],
            'settings': []
        }
        
        # Export users (without passwords for security)
        for user in User.query.all():
            backup_data['users'].append({
                'username': user.username,
                'full_name': user.full_name,
                'role': user.role,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'is_active': user.is_active
            })
        
        # Export customers
        for customer in Customer.query.all():
            backup_data['customers'].append({
                'id': customer.id,
                'name': customer.name,
                'mobile': customer.mobile,
                'created_at': customer.created_at.isoformat() if customer.created_at else None
            })
        
        # Export batteries
        for battery in Battery.query.all():
            backup_data['batteries'].append({
                'id': battery.id,
                'battery_id': battery.battery_id,
                'customer_id': battery.customer_id,
                'battery_type': battery.battery_type,
                'voltage': battery.voltage,
                'capacity': battery.capacity,
                'status': battery.status,
                'inward_date': battery.inward_date.isoformat() if battery.inward_date else None,
                'service_price': battery.service_price
            })
        
        # Export status history
        for history in BatteryStatusHistory.query.all():
            backup_data['status_history'].append({
                'id': history.id,
                'battery_id': history.battery_id,
                'status': history.status,
                'comments': history.comments,
                'updated_by': history.updated_by,
                'updated_at': history.updated_at.isoformat() if history.updated_at else None
            })
        
        # Export settings
        for setting in SystemSettings.query.all():
            backup_data['settings'].append({
                'setting_key': setting.setting_key,
                'setting_value': setting.setting_value,
                'updated_at': setting.updated_at.isoformat() if setting.updated_at else None
            })
        
        # Create JSON response
        backup_json = json.dumps(backup_data, indent=2)
        
        response = make_response(backup_json)
        response.headers['Content-Disposition'] = f'attachment; filename=battery_erp_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        response.headers['Content-Type'] = 'application/json'
        
        return response
        
    except Exception as e:
        flash(f'Error creating backup: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/admin/restore', methods=['GET', 'POST'])
@login_required
def admin_restore():
    if current_user.role != 'admin':
        flash('Access denied. Admin access required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        if 'backup_file' not in request.files:
            flash('No file selected.', 'error')
            return render_template('admin/restore.html')
        
        file = request.files['backup_file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return render_template('admin/restore.html')
        
        if file and file.filename and file.filename.endswith('.json'):
            try:
                backup_data = json.loads(file.read().decode('utf-8'))
                
                # Clear existing data (be careful!)
                confirm = request.form.get('confirm_restore')
                if confirm != 'CONFIRM':
                    flash('Please type "CONFIRM" to proceed with restore.', 'error')
                    return render_template('admin/restore.html')
                
                # Implement actual restore functionality
                try:
                    # Backup current admin user before clearing data
                    admin_user_backup = {
                        'username': current_user.username,
                        'password_hash': current_user.password_hash,
                        'role': current_user.role,
                        'full_name': current_user.full_name
                    }
                    
                    # Clear existing data (preserve current admin)
                    BatteryStatusHistory.query.delete()
                    Battery.query.delete()
                    Customer.query.delete()
                    SystemSettings.query.delete()
                    # Don't delete current admin user
                    User.query.filter(User.id != current_user.id).delete()
                    
                    db.session.commit()
                    
                    # Restore customers
                    customer_id_mapping = {}
                    for customer_data in backup_data.get('customers', []):
                        customer = Customer()
                        customer.name = customer_data['name']
                        customer.mobile = customer_data['mobile']
                        if customer_data.get('created_at'):
                            customer.created_at = datetime.fromisoformat(customer_data['created_at'])
                        db.session.add(customer)
                        db.session.flush()
                        customer_id_mapping[customer_data['id']] = customer.id
                    
                    # Restore batteries
                    battery_id_mapping = {}
                    for battery_data in backup_data.get('batteries', []):
                        battery = Battery()
                        battery.battery_id = battery_data['battery_id']
                        battery.customer_id = customer_id_mapping.get(battery_data['customer_id'])
                        battery.battery_type = battery_data['battery_type']
                        battery.voltage = battery_data['voltage']
                        battery.capacity = battery_data['capacity']
                        battery.status = battery_data['status']
                        battery.service_price = battery_data.get('service_price', 0.0)
                        if battery_data.get('inward_date'):
                            battery.inward_date = datetime.fromisoformat(battery_data['inward_date'])
                        db.session.add(battery)
                        db.session.flush()
                        battery_id_mapping[battery_data['id']] = battery.id
                    
                    # Restore users (except passwords)
                    for user_data in backup_data.get('users', []):
                        if user_data['username'] != current_user.username:  # Don't overwrite current admin
                            user = User()
                            user.username = user_data['username']
                            user.full_name = user_data['full_name']
                            user.role = user_data['role']
                            user.password_hash = generate_password_hash('password123')
                            user.active = user_data.get('is_active', True)
                            if user_data.get('created_at'):
                                user.created_at = datetime.fromisoformat(user_data['created_at'])
                            db.session.add(user)
                    
                    # Restore status history
                    for history_data in backup_data.get('status_history', []):
                        if battery_id_mapping.get(history_data['battery_id']):
                            history = BatteryStatusHistory()
                            history.battery_id = battery_id_mapping[history_data['battery_id']]
                            history.status = history_data['status']
                            history.comments = history_data.get('comments', '')
                            history.updated_by = current_user.id  # Assign to current admin
                            if history_data.get('updated_at'):
                                history.updated_at = datetime.fromisoformat(history_data['updated_at'])
                            db.session.add(history)
                    
                    # Restore system settings
                    for setting_data in backup_data.get('settings', []):
                        setting = SystemSettings()
                        setting.setting_key = setting_data['setting_key']
                        setting.setting_value = setting_data['setting_value']
                        if setting_data.get('updated_at'):
                            setting.updated_at = datetime.fromisoformat(setting_data['updated_at'])
                        db.session.add(setting)
                    
                    db.session.commit()
                    flash('Data restored successfully! Note: Restored user passwords have been reset to "password123".', 'success')
                    return redirect(url_for('main.dashboard'))
                    
                except Exception as restore_error:
                    db.session.rollback()
                    flash(f'Error during restore: {str(restore_error)}', 'error')
                
            except Exception as e:
                flash(f'Error reading backup file: {str(e)}', 'error')
        else:
            flash('Please upload a valid JSON backup file.', 'error')
    
    return render_template('admin/restore.html')

@main_bp.route('/staff/backup')
@login_required
def staff_backup():
    if current_user.role not in ['shop_staff', 'admin']:
        flash('Access denied.', 'error')
        return redirect(url_for('main.dashboard'))
    
    return redirect(url_for('main.admin_backup'))

@main_bp.route('/finished_batteries')
@login_required
def finished_batteries():
    finished = Battery.query.filter_by(status='Ready').order_by(Battery.inward_date.desc()).all()
    return render_template('finished_batteries.html', batteries=finished)
