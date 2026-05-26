from flask import Blueprint, render_template, request, session, redirect, jsonify
from models.evaluation_model import (
    get_evaluation_dashboard_stats, 
    get_distinct_semesters, 
    get_gender_options,
    get_filtered_students_for_eval,
    calculate_final_evaluation,
    get_location_breakdown,
    get_batch_breakdown,
    get_distinct_branches,
    get_distinct_functions,
    get_distinct_locations,
    get_distinct_batch_nos,
    get_distinct_bits_streams,
    get_performance_distribution,
    get_attrition_by_location
)
from models.student_model import get_filter_options

user_dashboard_bp = Blueprint('user_dashboard', __name__)


@user_dashboard_bp.route('/user_dashboard', methods=['GET'])
def dashboard():
    if 'username' not in session:
        return redirect('/login')
    
    role = session.get('role')
    user_loc = session.get('plant_location')
    username = session.get('username') # GET USERNAME
    
    # ✅ FILTERS
    filters = {
        'semester': request.args.get('semester', ''),
        'status': request.args.get('status', ''),  
        'year': request.args.get('year', ''),
        'batch_no': request.args.get('batch_no', ''),
        'branch': request.args.get('branch', ''),
        'department': request.args.get('department', ''),
        'gender': request.args.get('gender', ''),
        'function': request.args.get('function', ''),
        'bits_stream': request.args.get('bits_stream', ''),
        'plant_location': request.args.get('plant_location', ''),
        'ticket_no': request.args.get('ticket_no', '')
    }

    if 'status' not in request.args:
        filters['status'] = 'active'

    filters['student_status'] = filters.get('status')

    if role == 'SDC Coordinator' and user_loc:
        filters['plant_location'] = user_loc

    # Data Fetch Logic
    all_locations = get_distinct_locations()
    if role == 'SDC Coordinator' and user_loc:
        locations = [loc for loc in all_locations if loc == user_loc]
    else:
        locations = all_locations

    filter_options = get_filter_options()
    sem_numbers = get_distinct_semesters()
    genders = get_gender_options()
    branches = get_distinct_branches()
    functions = get_distinct_functions()
    batch_numbers = get_distinct_batch_nos()
    bits_streams = get_distinct_bits_streams()

    stats_data = get_evaluation_dashboard_stats(filters)
    students_data = get_filtered_students_for_eval(filters)

    for student in students_data:
        student['final_eval'] = calculate_final_evaluation(student)

    location_raw = get_location_breakdown(filters)
    location_stats = []
    for loc in location_raw:
        total = loc['total']
        male = loc['male']
        female = loc['female']
        male_pct = round((male / total) * 100, 1) if total > 0 else 0
        female_pct = round((female / total) * 100, 1) if total > 0 else 0
        location_stats.append({
            'location': loc['location'],
            'total': total,
            'male_pct': male_pct,
            'female_pct': female_pct
        })

    attrition_filters = filters.copy()
    attrition_filters.pop('status', None)
    attrition_filters.pop('student_status', None)
    attrition_raw = get_attrition_by_location(attrition_filters)
    attrition_data = []
    for row in attrition_raw:
        total = row['total_students']
        dropped = row['dropped_students']
        attrition_pct = round((dropped / total) * 100, 1) if total > 0 else 0
        attrition_data.append({
            'location': row['location'],
            'attrition_pct': attrition_pct
        })

    batch_stats_pivot = get_batch_breakdown(filters)
    performance_data = get_performance_distribution(filters)

    return render_template(
        'user_dashboard.html',
        stats=stats_data['summary'],
        students=students_data,
        filters=filters,
        filter_options=filter_options,
        sem_numbers=sem_numbers,
        genders=genders,
        performance_data=performance_data,
        location_stats=location_stats,
        attrition_data=attrition_data,
        batch_stats=batch_stats_pivot,
        branches=branches,
        functions=functions,
        locations=locations,
        batch_numbers=batch_numbers,
        bits_streams=bits_streams,
        role=role,
        username=username # PASSED USERNAME
    )

@user_dashboard_bp.route('/get-performance-data', methods=['POST'])
def get_performance_data_api():
    data = request.get_json()
    
    filters = {
        'year': data.get('year', []),
        'plant_location': data.get('plant_location', []),
        'semester': data.get('semester', []),
        'status': data.get('status'),
        'bits_stream': data.get('bits_stream', [])
    }

    filters['student_status'] = filters.get('status')

    role = session.get('role')
    user_loc = session.get('plant_location')
    
    if role == 'SDC Coordinator' and user_loc:
        requested_plants = filters.get('plant_location', [])
        if requested_plants:
            allowed = [p for p in requested_plants if p == user_loc]
            filters['plant_location'] = allowed
        else:
            filters['plant_location'] = [user_loc]
            
    chart_data = get_performance_distribution(filters)
    return jsonify(chart_data)
@user_dashboard_bp.route('/get-students-in-range', methods=['POST'])
def get_students_in_range_api():
    data = request.get_json()
    
    # Parse range string (e.g., "8-9")
    range_label = data.get('range', '')
    try:
        parts = range_label.split('-')
        min_val = float(parts[0])
        max_val = float(parts[1])
    except:
        return jsonify([])

    # Prepare filters (reuse logic from existing dashboard route)
    filters = {
        'year': data.get('year', []),
        'plant_location': data.get('plant_location', []),
        'semester': data.get('semester', []),
        'status': data.get('status'),
        'bits_stream': data.get('bits_stream', [])
    }
    filters['student_status'] = filters.get('status')

    # RBAC Check
    role = session.get('role')
    user_loc = session.get('plant_location')
    
    if role == 'SDC Coordinator' and user_loc:
        requested_plants = filters.get('plant_location', [])
        if requested_plants:
            allowed = [p for p in requested_plants if p == user_loc]
            filters['plant_location'] = allowed
        else:
            filters['plant_location'] = [user_loc]
            
    # Fetch data
    from models.evaluation_model import get_students_by_cgpa_range
    students = get_students_by_cgpa_range(filters, min_val, max_val)
    
    return jsonify(students)