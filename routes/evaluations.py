from flask import Blueprint, render_template, request, session, redirect
import pandas as pd
from models.evaluation_model import (
    init_evaluation_db,
    get_filtered_students_for_eval,
    get_distinct_semesters,
    get_gender_options,
    get_student_active_evaluation,
    get_student_last_evaluation,
    get_student_evaluation_by_sem,
    promote_student_semester,
    calculate_final_evaluation,
    create_initial_evaluation,
    get_student_all_evaluations_list,
    upsert_evaluation_scores,
    end_seventh_semester,
    bulk_upsert_evaluations
)
from models.student_model import get_filter_options, check_and_update_completion_status, get_student_ticket_id_map

evaluations_bp = Blueprint('evaluations', __name__)
init_evaluation_db()

@evaluations_bp.route('/evaluations')
def list_evaluations():
    if 'username' not in session:
        return redirect('/login')

    role = session.get('role')
    
    if role not in ['Admin', 'SDC Coordinator']:
        return "Access Denied"

    raw_status = request.args.get('status', '')
    
    db_filters = {
        'semester': request.args.get('semester', ''),
        'semester_status': raw_status,
        'student_status': '',
        'year': request.args.get('year', ''),
        'batch_no': request.args.get('batch_no', ''),
        'branch': request.args.get('branch', ''),
        'department': request.args.get('department', ''),
        'gender': request.args.get('gender', ''),
        'ticket_no': request.args.get('ticket_no', ''),
        'function': request.args.get('function', ''),
        'bits_stream': request.args.get('bits_stream', ''),
        'plant_location': request.args.get('location', '')
    }
    
    if 'status' not in request.args:
        db_filters['semester_status'] = 'ongoing'

    user_location = session.get('plant_location')
    if role == 'SDC Coordinator' and user_location:
        db_filters['plant_location'] = user_location

    students_data = get_filtered_students_for_eval(db_filters)

    for student in students_data:
        student['final_eval'] = calculate_final_evaluation(student)

    restriction = user_location if role == 'SDC Coordinator' else None
    filter_options = get_filter_options(plant_location_restriction=restriction) 
    
    sem_numbers = get_distinct_semesters()
    genders = get_gender_options()

    view_filters = {
        'semester': db_filters['semester'],
        'status': db_filters['semester_status'],
        'year': db_filters['year'],
        'batch_no': db_filters['batch_no'],
        'branch': db_filters['branch'],
        'department': db_filters['department'],
        'gender': db_filters['gender'],
        'ticket_no': db_filters['ticket_no'],
        'function': db_filters['function'],
        'bits_stream': db_filters['bits_stream'],
        'plant_location': db_filters['plant_location']
    }

    return render_template(
        'student_evaluation.html',
        students=students_data,
        filters=view_filters,
        filter_options=filter_options,
        sem_numbers=sem_numbers,
        genders=genders
    )


@evaluations_bp.route('/evaluations/<int:student_id>', methods=['GET', 'POST'])
def evaluation_sheet(student_id):
    if 'username' not in session:
        return redirect('/login')
    
    role = session.get('role')
    
    if role not in ['Admin', 'SDC Coordinator']:
        return "Access Denied"

    check_and_update_completion_status()
    
    if request.method == 'POST':
        current_semester = int(request.form.get('semester', 1))
        
        if role == 'SDC Coordinator':
            check_data = get_student_evaluation_by_sem(student_id, current_semester)
            if check_data and check_data.get('plant_location') != session.get('plant_location'):
                return "Access Denied: You cannot edit students outside your plant.", 403

        success, message = upsert_evaluation_scores(student_id, current_semester, request.form)
        if not success:
            return f"Error updating record: {message}", 403
        return redirect(f'/evaluations/{student_id}?semester={current_semester}')

    active_eval = get_student_active_evaluation(student_id)
    
    if not active_eval:
        last_eval = get_student_last_evaluation(student_id)
        if last_eval:
            active_eval = last_eval
        else:
            create_initial_evaluation(student_id)
            active_eval = get_student_active_evaluation(student_id)

    if not active_eval:
         return "Error: Could not initialize evaluation record.", 404

    real_current_semester = active_eval['semester']

    requested_sem = request.args.get('semester')
    viewing_semester = int(requested_sem) if requested_sem else real_current_semester

    student_data = get_student_evaluation_by_sem(student_id, viewing_semester)
    
    if not student_data:
        student_data = get_student_evaluation_by_sem(student_id, real_current_semester)
        viewing_semester = real_current_semester

    if not student_data:
         return "Error loading student data.", 404
    
    if role == 'SDC Coordinator':
        if student_data.get('plant_location') != session.get('plant_location'):
            return "Access Denied: This student does not belong to your plant location.", 403
    
    is_latest_semester = (viewing_semester >= real_current_semester)

    all_semesters = get_student_all_evaluations_list(student_id)
    
    final_eval = calculate_final_evaluation(student_data)
    view_status = student_data['semester_status']
    
    student_status = student_data.get('status', 'active')

    return render_template(
        'trainee_sheet.html',
        student=student_data,
        current_semester=viewing_semester,
        final_eval=final_eval,
        status=view_status,
        all_semesters=all_semesters,
        is_latest_semester=is_latest_semester,
        active_semester=real_current_semester,
        student_status=student_status
    )

@evaluations_bp.route('/evaluations/<int:student_id>/promote', methods=['POST'])
def move_next_semester(student_id):
    if 'username' not in session:
        return redirect('/login')
    
    role = session.get('role')
    if role not in ['Admin', 'SDC Coordinator']:
         return "Access Denied", 403

    if role == 'SDC Coordinator':
        check_eval = get_student_last_evaluation(student_id)
        if check_eval and check_eval.get('plant_location') != session.get('plant_location'):
            return "Access Denied", 403

    success, message = promote_student_semester(student_id)
    
    if success:
        return redirect(f'/evaluations/{student_id}')
    else:
        return f"Error: {message}", 400

@evaluations_bp.route('/evaluations/<int:student_id>/end-semester-seven', methods=['POST'])
def end_semester_seven_route(student_id):
    if 'username' not in session:
        return redirect('/login')
    
    role = session.get('role')
    if role not in ['Admin', 'SDC Coordinator']:
         return "Access Denied", 403

    if role == 'SDC Coordinator':
        check_eval = get_student_last_evaluation(student_id)
        if check_eval and check_eval.get('plant_location') != session.get('plant_location'):
            return "Access Denied", 403

    success, message = end_seventh_semester(student_id)
    
    if success:
        return redirect(f'/evaluations/{student_id}')
    else:
        return f"Error: {message}", 400

# ---------------------------------------
# BULK UPLOAD ROUTE
# ---------------------------------------

@evaluations_bp.route('/evaluations/upload-excel', methods=['GET', 'POST'])
def upload_evaluations_excel():
    if 'username' not in session:
        return redirect('/login')

    role = session.get('role')
    if role not in ['Admin', 'SDC Coordinator']:
        return "Access Denied"

    if request.method == 'GET':
        return render_template('upload_evaluations.html', success_count=None, error_rows=None)

    # POST Logic
    if 'excel_file' not in request.files:
        return render_template('upload_evaluations.html', error="No file selected.", success_count=None, error_rows=None)

    file = request.files['excel_file']
    if file.filename == '':
        return render_template('upload_evaluations.html', error="No file selected.", success_count=None, error_rows=None)

    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        return render_template('upload_evaluations.html', error="Invalid file format. Please upload .xlsx or .xls", success_count=None, error_rows=None)

    try:
        # Read Excel
        df = pd.read_excel(file)

        # ---------------------------------------------------------
        # COLUMN MAPPING: Excel Header -> Internal Variable Name
        # ---------------------------------------------------------
        column_mapping = {
            'Ticket No': 'ticket_no',
            'Employee Name': 'employee_name', # Optional, ignored in logic but allowed in file
            'Semester': 'semester',
            'Semester Status': 'semester_status',
            'Score Attendance': 'score_attendance',
            'Score Suggestions': 'score_suggestions',
            'Score Projects': 'score_projects',
            'Score Recognitions': 'score_recognitions',
            'Score Safety': 'score_safety',
            'Score Discipline': 'score_discipline',
            'Score BITS Attendance': 'score_bits_attendance',
            'Score Equipment': 'score_equipment',
            'Score Shop Task': 'score_shop_task',
            'Score Function Output': 'score_function_output',
            'Training Marks': 'training_marks',
            'BITS CGPA': 'bits_cgpa'
        }

        # 1. Clean column headers (strip whitespace)
        df.columns = [str(col).strip() for col in df.columns]

        # 2. Rename columns using mapping
        # We create a subset of mapping for columns that actually exist in the file
        cols_to_rename = {col: column_mapping[col] for col in df.columns if col in column_mapping}
        df.rename(columns=cols_to_rename, inplace=True)

        # 3. Check Required Columns (using internal names now)
        required_internal = ['ticket_no', 'semester']
        
        # Reverse map to show friendly names in error messages
        reverse_map = {v: k for k, v in column_mapping.items()}

        for col in required_internal:
            if col not in df.columns:
                friendly_name = reverse_map.get(col, col)
                return render_template('upload_evaluations.html', 
                                       error=f"Missing required column: '{friendly_name}'", 
                                       success_count=None, error_rows=None)

        # Fetch Student Map
        ticket_map = get_student_ticket_id_map()

        valid_records = []
        error_rows = []

        # Helper for validation
        def safe_float(val, default=0.0):
            try:
                return float(val) if pd.notna(val) else default
            except:
                return default

        def validate_score(val, min_v, max_v, field_name):
            v = safe_float(val, 0)
            if v < min_v or v > max_v:
                return None, f"{field_name} must be {min_v}-{max_v}"
            return v, None

        # Iterate and Validate
        for index, row in df.iterrows():
            row_num = index + 2  # Excel is 1-based + header
            ticket_no = str(row['ticket_no']).strip()
            
            # Validation 1: Ticket Existence
            if ticket_no not in ticket_map:
                error_rows.append({"row": row_num, "ticket_no": ticket_no, "reason": "Ticket No not found in system"})
                continue

            # Validation 2: Semester
            semester = int(row['semester']) if pd.notna(row['semester']) else None
            if semester is None or semester < 1 or semester > 7:
                error_rows.append({"row": row_num, "ticket_no": ticket_no, "reason": "Semester must be 1-7"})
                continue

            # Validation 3: Semester Status
            sem_status = str(row.get('semester_status', 'ongoing')).strip().lower() if pd.notna(row.get('semester_status')) else 'ongoing'
            if sem_status not in ['ongoing', 'completed']:
                error_rows.append({"row": row_num, "ticket_no": ticket_no, "reason": "Status must be 'ongoing' or 'completed'"})
                continue

            # Validation 4: Score ranges
            ojt_fields = ['score_attendance', 'score_suggestions', 'score_projects', 'score_recognitions', 
                          'score_safety', 'score_discipline', 'score_bits_attendance', 'score_equipment', 
                          'score_shop_task', 'score_function_output']
            
            record_data = {
                'student_id': ticket_map[ticket_no],
                'semester': semester,
                'semester_status': sem_status
            }
            
            has_error = False
            for field in ojt_fields:
                val, err = validate_score(row.get(field), 0, 10, field)
                if err:
                    error_rows.append({"row": row_num, "ticket_no": ticket_no, "reason": err})
                    has_error = True
                    break
                record_data[field] = val
            
            if has_error:
                continue

            # Training (0-100)
            t_mark, err = validate_score(row.get('training_marks'), 0, 100, 'training_marks')
            if err:
                error_rows.append({"row": row_num, "ticket_no": ticket_no, "reason": err})
                continue
            record_data['training_marks'] = t_mark

            # CGPA (0-10)
            cgpa, err = validate_score(row.get('bits_cgpa'), 0, 10, 'bits_cgpa')
            if err:
                error_rows.append({"row": row_num, "ticket_no": ticket_no, "reason": err})
                continue
            record_data['bits_cgpa'] = cgpa

            valid_records.append(record_data)

        # DB Operation
        success_count = 0
        if valid_records:
            success_count = bulk_upsert_evaluations(valid_records)

        return render_template('upload_evaluations.html', 
                               success_count=success_count, 
                               error_rows=error_rows,
                               total_rows=len(df))

    except Exception as e:
        print(f"Upload Error: {e}")
        return render_template('upload_evaluations.html', error=f"Processing Error: {str(e)}", success_count=None, error_rows=None)