from flask import Blueprint, render_template, request, redirect, session, flash
from models.user_model import check_user_login

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
@auth_bp.route('/login')
def login_page():
    return render_template('login.html')

@auth_bp.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    # 1. HARDCODED ADMIN LOGIN (No role selection needed)
    if username == 'admin' and password == 'admin123':
        session['user_id'] = 0
        session['username'] = 'admin'
        session['role'] = 'Admin'
        session['plant_location'] = None
        session['is_admin'] = True
        return redirect('/admin-dashboard')

    # 2. DATABASE USER LOGIN
    # We pass only username and password. The model returns the user object with their role.
    user = check_user_login(username, password)

    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        session['plant_location'] = user.get('plant_location')
        session['is_admin'] = user['role'] == 'Admin'

        # Redirect based on the role found in database
        if user['role'] in ['Admin', 'PMO', 'SDC Coordinator']:
            return redirect('/admin-dashboard')
        else:
            return redirect('/user_dashboard')

    # If login fails
    flash('Invalid Username or Password', 'error')
    return redirect('/login')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/login')