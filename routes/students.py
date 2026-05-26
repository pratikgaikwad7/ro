from flask import Blueprint, render_template, request, jsonify, session
import pandas as pd
from models.student_model import get_all_students, add_student, update_student, delete_student, get_filter_options

students_bp = Blueprint('students', __name__)

@students_bp.route('/students')
def index():
    if 'username' not in session:
        return render_template('login.html')
    return render_template('students.html')

@students_bp.route('/api/students/filters', methods=['GET'])
def api_get_filters():
    """API endpoint to get dropdown options for filters"""
    try:
        restriction = None
        if session.get('role') == 'SDC Coordinator':
            restriction = session.get('plant_location')
            
        options = get_filter_options(plant_location_restriction=restriction)
        return jsonify(options)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@students_bp.route('/api/students', methods=['GET'])
def api_get_students():
    filters = {
        'plant_location': request.args.get('location'),
        'year': request.args.get('year'),
        'department': request.args.get('department'),
        'batch_no': request.args.get('batch_no'),
        'function': request.args.get('function'),
        'bits_stream': request.args.get('bits_stream'), # NEW
        'status': request.args.get('status')
    }
    
    if session.get('role') == 'SDC Coordinator':
        user_loc = session.get('plant_location')
        if user_loc:
            filters['plant_location'] = user_loc
    
    filters = {k: v for k, v in filters.items() if v}
    data = get_all_students(filters)
    return jsonify(data)

@students_bp.route('/api/students', methods=['POST'])
def api_add_student():
    try:
        data = request.json
        
        if session.get('role') == 'SDC Coordinator':
            data['plant_location'] = session.get('plant_location')

        required = ['first_name', 'surname', 'ticket_no', 'gender', 'mobile_no']
        for field in required:
            if not data.get(field) or str(data.get(field)).strip() == "":
                return jsonify({'error': f'{field.replace("_", " ").title()} is required'}), 400
        
        new_id = add_student(data)
        return jsonify({'success': True, 'id': new_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@students_bp.route('/api/students/<int:id>', methods=['PUT'])
def api_update_student(id):
    try:
        data = request.json
        
        required = ['first_name', 'surname', 'ticket_no', 'gender', 'mobile_no']
        for field in required:
            if not data.get(field) or str(data.get(field)).strip() == "":
                return jsonify({'error': f'{field.replace("_", " ").title()} is required'}), 400
        
        if session.get('role') == 'SDC Coordinator':
            user_loc = session.get('plant_location')
            if user_loc:
                data['plant_location'] = user_loc

        update_student(id, data)
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@students_bp.route('/api/students/<int:id>', methods=['DELETE'])
def api_delete_student(id):
    try:
        delete_student(id)
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- NEW EXCEL UPLOAD ROUTE ---
@students_bp.route('/api/students/upload-excel', methods=['POST'])
def upload_excel():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if not file.filename.endswith(('.xlsx', '.xls')):
         return jsonify({'error': 'Invalid file type. Only .xlsx or .xls allowed'}), 400

    try:
        df = pd.read_excel(file)
        df.columns = df.columns.str.strip()
        
        required_columns = ['Full Name', 'Ticket No', 'Gender', 'Mobile No']
        for col in required_columns:
            if col not in df.columns:
                return jsonify({'error': f'Missing required column in Excel: {col}'}), 400
        
        total_rows = len(df)
        inserted_count = 0
        skipped_count = 0
        failed_rows = []
        
        from models.db import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ticket_no FROM students")
        existing_tickets = set(row[0] for row in cursor.fetchall())
        conn.close()

        for index, row in df.iterrows():
            row_num = index + 2 
            
            missing_fields = []
            for field in required_columns:
                val = row.get(field)
                if pd.isna(val) or str(val).strip() == '':
                    missing_fields.append(field)
            
            if missing_fields:
                failed_rows.append(f"Row {row_num}: Missing fields - {', '.join(missing_fields)}")
                continue

            ticket_no = str(row['Ticket No']).strip()
            if ticket_no in existing_tickets:
                skipped_count += 1
                continue

            full_name = str(row['Full Name']).strip()
            name_parts = full_name.split()
            
            if len(name_parts) < 2:
                 failed_rows.append(f"Row {row_num}: Full Name must contain at least First Name and Surname.")
                 continue

            first_name = name_parts[0]
            surname = name_parts[-1]
            middle_name = ' '.join(name_parts[1:-1]) if len(name_parts) > 2 else ''

            doj_raw = row.get('Date of Joining')
            doj_formatted = None
            if pd.notna(doj_raw):
                try:
                    doj_formatted = pd.to_datetime(doj_raw).strftime('%Y-%m-%d')
                except:
                    pass

            status_raw = row.get('Status')
            status_val = str(status_raw).strip().lower() if pd.notna(status_raw) else 'active'

            # Handle NEW 'BITS Stream' from Excel
            bits_stream_raw = row.get('BITS Stream')

            student_payload = {
                'first_name': first_name,
                'middle_name': middle_name,
                'surname': surname,
                'ticket_no': ticket_no,
                'gender': str(row['Gender']).strip(),
                'mobile_no': str(row['Mobile No']).strip(),
                'email': str(row['Email']).strip() if pd.notna(row.get('Email')) else None,
                'diploma_branch': str(row['Diploma Branch']).strip() if pd.notna(row.get('Diploma Branch')) else None,
                'department': str(row['Department']).strip() if pd.notna(row.get('Department')) else None,
                'bc_no': str(row['BC No']).strip() if pd.notna(row.get('BC No')) else None,
                'reporting_manager': str(row['Reporting Manager']).strip() if pd.notna(row.get('Reporting Manager')) else None,
                'function': str(row['Function']).strip() if pd.notna(row.get('Function')) else None,
                'date_of_joining': doj_formatted,
                'plant_location': str(row['Plant Location']).strip() if pd.notna(row.get('Plant Location')) else None,
                'batch_year': int(row['Batch Year']) if pd.notna(row.get('Batch Year')) else None,
                'batch_no': int(row['Batch No']) if pd.notna(row.get('Batch No')) else None,
                'status': status_val,
                'bits_stream': str(bits_stream_raw).strip() if pd.notna(bits_stream_raw) else None # NEW
            }

            if session.get('role') == 'SDC Coordinator':
                user_loc = session.get('plant_location')
                if student_payload['plant_location'] and student_payload['plant_location'] != user_loc:
                    failed_rows.append(f"Row {row_num}: Location mismatch. You cannot add students for other locations.")
                    continue
                else:
                    student_payload['plant_location'] = user_loc

            try:
                add_student(student_payload)
                inserted_count += 1
                existing_tickets.add(ticket_no)
            except Exception as e:
                failed_rows.append(f"Row {row_num}: {str(e)}")

        return jsonify({
            'message': 'Upload processed',
            'total_rows': total_rows,
            'inserted': inserted_count,
            'skipped': skipped_count,
            'failed': len(failed_rows),
            'errors': failed_rows
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500