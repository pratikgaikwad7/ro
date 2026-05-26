from flask import Blueprint, render_template, request, redirect, session
from models.user_model import get_all_users, add_user, delete_user

users_bp = Blueprint('users', __name__)


@users_bp.route('/users')
def users_page():
    if 'username' not in session:
        return redirect('/login')

    if session.get('role') != 'Admin':
        return "Access Denied"

    users = get_all_users()
    return render_template('users.html', users=users)


@users_bp.route('/users/add', methods=['POST'])
def users_add():
    if 'username' not in session:
        return redirect('/login')

    if session.get('role') != 'Admin':
        return "Access Denied"

    username = request.form['username']
    password = request.form['password']
    role = request.form['role']
    plant_location = request.form.get('plant_location') or None

    location_roles = ['HR Head', 'Skill Head', 'SDC Coordinator']

    if role not in location_roles:
        plant_location = None

    add_user(username, password, role, plant_location)

    return redirect('/users')


@users_bp.route('/users/delete/<int:id>', methods=['POST'])
def users_delete(id):
    if 'username' not in session:
        return redirect('/login')

    if session.get('role') != 'Admin':
        return "Access Denied"

    delete_user(id)

    return redirect('/users')