from flask import Blueprint, render_template, session, redirect, url_for
# Import the stats function from evaluation_model
from models.evaluation_model import get_evaluation_dashboard_stats

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin-dashboard')
def admin_dashboard():
    # Login required
    if 'username' not in session:
        return redirect('/login')

    role = session.get('role')
    
    # Allowed roles
    if role not in ['Admin', 'PMO', 'SDC Coordinator']:
        return "Access Denied"

    # --- FETCH STATS ---
    filters = {} 
    
    # SDC Coordinator: Filter by their assigned plant location
    if role == 'SDC Coordinator':
        plant_location = session.get('plant_location')
        if plant_location:
            filters['plant_location'] = plant_location
    
    # Get comprehensive stats
    stats_data = get_evaluation_dashboard_stats(filters)
    summary = stats_data['summary']

    return render_template(
        'admin_dashboard.html',
        user_name=session.get('username', 'Admin'),
        stats=summary,
        role=role  # Pass role to template for UI logic
    )