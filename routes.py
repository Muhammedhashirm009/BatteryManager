from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response, jsonify
from flask_login import login_required, current_user
from app import db
from models import User, Customer, Battery, BatteryStatusHistory
from datetime import datetime
import csv
import io

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
    if current_user.role != 'shop_staff':
        flash('Access denied. This feature is only available to shop staff.', 'error')
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
                customer = Customer(name=customer_name, mobile=mobile)
                db.session.add(customer)
                db.session.flush()  # Get customer ID
            
            # Generate battery ID
            battery_id = Battery.generate_next_battery_id()
            
            # Create battery record
            battery = Battery(
                battery_id=battery_id,
                customer_id=customer.id,
                battery_type=battery_type,
                voltage=voltage,
                capacity=capacity,
                status='Received'
            )
            db.session.add(battery)
            db.session.flush()  # Get battery record ID
            
            # Add initial status history
            status_history = BatteryStatusHistory(
                battery_id=battery.id,
                status='Received',
                comments='Battery received from customer',
                updated_by=current_user.id
            )
            db.session.add(status_history)
            
            db.session.commit()
            flash(f'Battery {battery_id} has been successfully registered.', 'success')
            return redirect(url_for('main.receipt', battery_id=battery.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error registering battery: {str(e)}', 'error')
    
    return render_template('battery_entry.html')

@main_bp.route('/technician/panel')
@login_required
def technician_panel():
    if current_user.role != 'technician':
        flash('Access denied. This feature is only available to technicians.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get batteries that need technician attention
    pending_batteries = Battery.query.filter(
        Battery.status.in_(['Received', 'Diagnosing', 'Repairing'])
    ).order_by(Battery.inward_date.asc()).all()
    
    return render_template('technician_panel.html', batteries=pending_batteries)

@main_bp.route('/battery/update', methods=['POST'])
@login_required
def update_battery_status():
    if current_user.role != 'technician':
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
        status_history = BatteryStatusHistory(
            battery_id=battery.id,
            status=new_status,
            comments=comments,
            updated_by=current_user.id
        )
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
