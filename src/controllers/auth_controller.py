from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from src.models import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')

        if not username or not password or not first_name or not last_name:
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return render_template('register.html')

        new_user = User(username=username, first_name=first_name, last_name=last_name)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('main.index')) # Redirect to main index
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
