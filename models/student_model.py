from models.db import get_db_connection
from models import evaluation_model
from flask import jsonify
import datetime

def init_db():
    """Creates table if not exists and handles migrations."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    create_table = """
    CREATE TABLE IF NOT EXISTS students (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(255),
        employee_name VARCHAR(255) NOT NULL,
        ticket_no VARCHAR(100) NOT NULL,
        diploma_branch VARCHAR(255),
        gender VARCHAR(50) NOT NULL,
        mobile_no VARCHAR(20) NOT NULL,
        department VARCHAR(255),
        bc_no VARCHAR(100),
        reporting_manager VARCHAR(255),
        erc_operation VARCHAR(255),
        date_of_joining DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    cursor.execute(create_table)
    conn.commit()

    # MIGRATION LOGIC
    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.columns 
        WHERE table_schema = DATABASE() AND table_name = 'students' AND column_name = 'function'
    """)
    function_exists = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM information_schema.columns 
        WHERE table_schema = DATABASE() AND table_name = 'students' AND column_name = 'erc_operation'
    """)
    erc_exists = cursor.fetchone()[0]

    if erc_exists and not function_exists:
        print("Migrating database: Renaming 'erc_operation' to 'function'")
        cursor.execute("ALTER TABLE students CHANGE COLUMN erc_operation `function` VARCHAR(255)")
        conn.commit()
    
    def column_exists(column_name):
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_schema = DATABASE() AND table_name = 'students' AND column_name = %s
        """, (column_name,))
        return cursor.fetchone()[0] > 0

    if not column_exists('plant_location'):
        cursor.execute("ALTER TABLE students ADD COLUMN plant_location VARCHAR(100)")

    if not column_exists('batch_year'):
        cursor.execute("ALTER TABLE students ADD COLUMN batch_year INT")

    if not column_exists('batch_no'):
        cursor.execute("ALTER TABLE students ADD COLUMN batch_no INT")

    if not column_exists('status'):
        print("Migrating database: Adding 'status' column")
        cursor.execute("ALTER TABLE students ADD COLUMN status VARCHAR(50) DEFAULT 'active'")
        conn.commit()

    if not column_exists('end_date'):
        print("Migrating database: Adding 'end_date' column")
        cursor.execute("ALTER TABLE students ADD COLUMN end_date DATE")
        conn.commit()
        
    if not column_exists('bits_stream'):  # NEW MIGRATION
        print("Migrating database: Adding 'bits_stream' column")
        cursor.execute("ALTER TABLE students ADD COLUMN bits_stream VARCHAR(255)")
        conn.commit()

    conn.commit()
    conn.close()

def calculate_end_date(doj_str):
    """Calculates end date as DOJ + 5 years."""
    if not doj_str:
        return None
    try:
        doj_str = str(doj_str).strip()
        
        if isinstance(doj_str, datetime.date):
            doj = doj_str
        else:
            doj = datetime.datetime.strptime(doj_str, '%Y-%m-%d').date()
            
        try:
            end_date = doj.replace(year=doj.year + 5)
        except ValueError:
            end_date = doj.replace(year=doj.year + 5, day=28)
        return end_date
    except ValueError:
        return None

def check_and_update_completion_status():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = """
            UPDATE students 
            SET status = 'completed' 
            WHERE status = 'active' 
            AND end_date IS NOT NULL 
            AND end_date <= CURDATE()
        """
        cursor.execute(query)
        conn.commit()
    except Exception as e:
        print(f"Error updating completion status: {e}")
    finally:
        conn.close()

def get_filter_options(plant_location_restriction=None):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    select_distinct = "SELECT DISTINCT {col} FROM students WHERE {col} IS NOT NULL"
    order_by = " ORDER BY {col} ASC"
    
    if plant_location_restriction:
        locations = [plant_location_restriction]
    else:
        cursor.execute(select_distinct.format(col="plant_location") + order_by.format(col="plant_location"))
        locations = [row['plant_location'] for row in cursor.fetchall()]

    dept_query = select_distinct.format(col="department")
    params = []
    if plant_location_restriction:
        dept_query += " AND plant_location = %s"
        params.append(plant_location_restriction)
    
    cursor.execute(dept_query + order_by.format(col="department"), tuple(params))
    departments = [row['department'] for row in cursor.fetchall()]

    func_query = select_distinct.format(col="`function`")
    if plant_location_restriction:
        func_query += " AND plant_location = %s"
    
    cursor.execute(func_query + order_by.format(col="`function`"), tuple(params))
    functions = [row['function'] for row in cursor.fetchall()]

    # NEW: Get BITS Streams
    stream_query = select_distinct.format(col="bits_stream")
    if plant_location_restriction:
        stream_query += " AND plant_location = %s"
    
    cursor.execute(stream_query + order_by.format(col="bits_stream"), tuple(params))
    bits_streams = [row['bits_stream'] for row in cursor.fetchall()]

    year_query = select_distinct.format(col="batch_year")
    if plant_location_restriction:
        year_query += " AND plant_location = %s"
        
    cursor.execute(year_query + " ORDER BY batch_year DESC", tuple(params))
    years = [row['batch_year'] for row in cursor.fetchall()]

    batch_query = select_distinct.format(col="batch_no")
    if plant_location_restriction:
        batch_query += " AND plant_location = %s"
        
    cursor.execute(batch_query + order_by.format(col="batch_no"), tuple(params))
    batch_nos = [row['batch_no'] for row in cursor.fetchall()]

    conn.close()
    
    return {
        'locations': locations,
        'departments': departments,
        'functions': functions,
        'bits_streams': bits_streams, # NEW
        'years': years,
        'batch_nos': batch_nos
    }

def get_all_students(filters=None):
    check_and_update_completion_status()
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT 
            id, email, employee_name, ticket_no, diploma_branch, gender, mobile_no, 
            department, bc_no, reporting_manager, `function`, plant_location, 
            batch_year, batch_no, status, bits_stream,
            DATE_FORMAT(date_of_joining, '%Y-%m-%d') as date_of_joining,
            DATE_FORMAT(end_date, '%Y-%m-%d') as end_date
        FROM students 
        WHERE 1=1
    """
    params = []

    if filters:
        if filters.get('plant_location'):
            query += " AND plant_location = %s"
            params.append(filters['plant_location'])
        
        if filters.get('year'):
            query += " AND batch_year = %s"
            params.append(filters['year'])
            
        if filters.get('department'):
            query += " AND department = %s"
            params.append(filters['department'])
            
        if filters.get('batch_no'):
            query += " AND batch_no = %s"
            params.append(filters['batch_no'])
            
        if filters.get('function'):
            query += " AND `function` = %s"
            params.append(filters['function'])
            
        if filters.get('bits_stream'): # NEW
            query += " AND bits_stream = %s"
            params.append(filters['bits_stream'])
        
        if filters.get('status'):
            query += " AND status = %s"
            params.append(filters['status'])

    query += " ORDER BY id DESC"
    
    cursor.execute(query, tuple(params))
    students = cursor.fetchall()
    conn.close()
    return students

def add_student(data):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # --- NAME CONCATENATION LOGIC START ---
    first_name = data.get('first_name', '').strip()
    middle_name = data.get('middle_name', '').strip()
    surname = data.get('surname', '').strip()
    
    employee_name = " ".join(filter(None, [first_name, middle_name, surname]))
    
    if not employee_name:
        conn.close()
        raise ValueError("Employee name cannot be empty")
    # --- NAME CONCATENATION LOGIC END ---

    doj = data.get('date_of_joining')
    if doj: 
        doj = str(doj).strip()
        
    end_date_val = calculate_end_date(doj)
    
    status_val = data.get('status', 'active')
    if status_val != 'dropped':
        if end_date_val and end_date_val <= datetime.date.today():
            status_val = 'completed'
        else:
            status_val = 'active'

    query = """
        INSERT INTO students 
        (email, employee_name, ticket_no, diploma_branch, gender, mobile_no, department, bc_no, reporting_manager, `function`, date_of_joining, plant_location, batch_year, batch_no, status, end_date, bits_stream) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        data.get('email') or None, 
        employee_name, 
        data.get('ticket_no', '').strip(),
        data.get('diploma_branch') or None, 
        data.get('gender', '').strip(), 
        data.get('mobile_no', '').strip(),
        data.get('department') or None, 
        data.get('bc_no') or None, 
        data.get('reporting_manager') or None,
        data.get('function') or None, 
        doj or None, 
        data.get('plant_location') or None,
        data.get('batch_year') or None, 
        data.get('batch_no') or None, 
        status_val, 
        end_date_val,
        data.get('bits_stream') or None # NEW
    )
    cursor.execute(query, values)
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()

    if last_id and status_val == 'active':
        evaluation_model.create_initial_evaluation(last_id)
        
    return last_id

def update_student(student_id, data):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # --- NAME CONCATENATION LOGIC START ---
    first_name = data.get('first_name', '').strip()
    middle_name = data.get('middle_name', '').strip()
    surname = data.get('surname', '').strip()
    
    employee_name = " ".join(filter(None, [first_name, middle_name, surname]))
    
    if not employee_name:
        conn.close()
        raise ValueError("Employee name cannot be empty")
    # --- NAME CONCATENATION LOGIC END ---

    doj = data.get('date_of_joining')
    
    if doj:
        doj = str(doj).strip()
    else:
        doj = None
        
    end_date_val = calculate_end_date(doj)
    
    current_status = data.get('status', 'active')
    new_status = current_status
    
    if current_status != 'dropped':
        if end_date_val and end_date_val <= datetime.date.today():
            new_status = 'completed'
        else:
            new_status = 'active'
    
    query = """
        UPDATE students SET
        email = %s, employee_name = %s, ticket_no = %s, diploma_branch = %s,
        gender = %s, mobile_no = %s, department = %s, bc_no = %s,
        reporting_manager = %s, `function` = %s, date_of_joining = %s,
        plant_location = %s, batch_year = %s, batch_no = %s, status = %s, end_date = %s, bits_stream = %s
        WHERE id = %s
    """
    values = (
        data.get('email') or None, 
        employee_name, 
        data.get('ticket_no', '').strip(),
        data.get('diploma_branch') or None, 
        data.get('gender', '').strip(), 
        data.get('mobile_no', '').strip(),
        data.get('department') or None, 
        data.get('bc_no') or None, 
        data.get('reporting_manager') or None,
        data.get('function') or None, 
        doj, 
        data.get('plant_location') or None,
        data.get('batch_year') or None, 
        data.get('batch_no') or None, 
        new_status, end_date_val, 
        data.get('bits_stream') or None, # NEW
        student_id
    )
    cursor.execute(query, values)
    conn.commit()
    conn.close()
    return True

def delete_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
    conn.commit()
    conn.close()
    return True    

def get_dashboard_stats():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) as total FROM students")
    total_students = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(DISTINCT department) as total FROM students WHERE department IS NOT NULL")
    total_departments = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(DISTINCT diploma_branch) as total FROM students WHERE diploma_branch IS NOT NULL")
    total_branches = cursor.fetchone()['total']
    cursor.execute("SELECT * FROM students ORDER BY id DESC LIMIT 5")
    recent_students = cursor.fetchall()
    conn.close()
    return total_students, total_departments, total_branches, recent_students

# Add this function at the end of models/student_model.py

def get_student_ticket_id_map():
    """
    Returns a dictionary mapping ticket_no to student id.
    Used for bulk operations.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # We select only active students or specific statuses if needed, 
    # but usually bulk upload implies existing records.
    cursor.execute("SELECT id, ticket_no FROM students WHERE ticket_no IS NOT NULL")
    rows = cursor.fetchall()
    
    ticket_map = {row['ticket_no']: row['id'] for row in rows}
    
    conn.close()
    return ticket_map