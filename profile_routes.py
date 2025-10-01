from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import User, Activity, Project, ProjectAssignment, Notification
from app import db
import os

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/')
@login_required
def profile():
    """User profile page"""
    # Get user's projects
    user_projects = db.session.query(Project).join(ProjectAssignment).filter(
        ProjectAssignment.user_id == current_user.id
    ).all()
    
    # Get user's recent activities
    recent_activities = Activity.query.filter_by(user_id=current_user.id).order_by(
        Activity.created_at.desc()
    ).limit(10).all()
    
    return render_template('profile/profile.html', 
                         user_projects=user_projects,
                         recent_activities=recent_activities)

@profile_bp.route('/notifications')
@login_required
def notifications():
    """User notifications page"""
    # Get user's notifications
    user_notifications = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()
    ).all()
    
    return render_template('profile/notifications.html', 
                         notifications=user_notifications)

@profile_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        avatar_url = request.form.get('avatar_url')
        
        # Validation
        if not username or not email:
            flash('Username and email are required.', 'error')
            return render_template('profile/edit_profile.html')
        
        # Check if username/email is already taken by another user
        existing_user = User.query.filter(
            User.username == username, 
            User.id != current_user.id
        ).first()
        if existing_user:
            flash('Username is already taken.', 'error')
            return render_template('profile/edit_profile.html')
        
        existing_email = User.query.filter(
            User.email == email, 
            User.id != current_user.id
        ).first()
        if existing_email:
            flash('Email is already registered.', 'error')
            return render_template('profile/edit_profile.html')
        
        # Update user profile
        current_user.username = username
        current_user.email = email
        if avatar_url:
            current_user.avatar_url = avatar_url
        
        db.session.commit()
        
        # Log activity
        activity = Activity()
        activity.user_id = current_user.id
        activity.action = "Profile Updated"
        activity.description = f"Updated profile information"
        db.session.add(activity)
        db.session.commit()
        
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('profile.profile'))
    
    return render_template('profile/edit_profile.html')

@profile_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not all([current_password, new_password, confirm_password]):
            flash('All fields are required.', 'error')
            return render_template('profile/change_password.html')
        
        # Check current password (only if user has a password)
        if current_user.password_hash:
            if not check_password_hash(current_user.password_hash, current_password):
                flash('Current password is incorrect.', 'error')
                return render_template('profile/change_password.html')
        
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return render_template('profile/change_password.html')
        
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('profile/change_password.html')
        
        # Update password
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        # Log activity
        activity = Activity()
        activity.user_id = current_user.id
        activity.action = "Password Changed"
        activity.description = "Changed account password"
        db.session.add(activity)
        db.session.commit()
        
        flash('Password changed successfully.', 'success')
        return redirect(url_for('profile.profile'))
    
    return render_template('profile/change_password.html')

@profile_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """User settings page"""
    if request.method == 'POST':
        # Handle settings update
        theme = request.form.get('theme', 'light')
        notifications = request.form.get('notifications') == 'on'
        
        # In a real app, you might store these in a UserSettings model
        # For now, we'll just show a success message
        flash('Settings updated successfully.', 'success')
        return redirect(url_for('profile.settings'))
    
    return render_template('profile/settings.html')

@profile_bp.route('/activities')
@login_required
def activities():
    """User's activity history"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    activities = Activity.query.filter_by(user_id=current_user.id).order_by(
        Activity.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('profile/activities.html', activities=activities)

@profile_bp.route('/projects')
@login_required
def projects():
    """User's assigned projects"""
    user_projects = db.session.query(Project, ProjectAssignment).join(
        ProjectAssignment
    ).filter(ProjectAssignment.user_id == current_user.id).all()
    
    return render_template('profile/projects.html', user_projects=user_projects)

@profile_bp.route('/delete-account', methods=['GET', 'POST'])
@login_required
def delete_account():
    """Delete user account"""
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_delete = request.form.get('confirm_delete')
        
        if confirm_delete != 'DELETE':
            flash('Please type "DELETE" to confirm account deletion.', 'error')
            return render_template('profile/delete_account.html')
        
        # Check password if user has one
        if current_user.password_hash:
            if not password or not check_password_hash(current_user.password_hash, password):
                flash('Incorrect password.', 'error')
                return render_template('profile/delete_account.html')
        
        # Log deletion activity before deleting
        activity = Activity()
        activity.user_id = current_user.id
        activity.action = "Account Deleted"
        activity.description = f"User {current_user.username} deleted their account"
        db.session.add(activity)
        db.session.commit()
        
        # Remove user assignments
        ProjectAssignment.query.filter_by(user_id=current_user.id).delete()
        
        # Delete user
        user_id = current_user.id
        db.session.delete(current_user)
        db.session.commit()
        
        flash('Your account has been deleted.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('profile/delete_account.html')

# API endpoints for profile management
@profile_bp.route('/api/avatar', methods=['POST'])
@login_required
def update_avatar():
    """Update user avatar via API"""
    data = request.get_json()
    avatar_url = data.get('avatar_url')
    
    if not avatar_url:
        return jsonify({'error': 'Avatar URL is required'}), 400
    
    current_user.avatar_url = avatar_url
    db.session.commit()
    
    return jsonify({'message': 'Avatar updated successfully', 'avatar_url': avatar_url})

@profile_bp.route('/api/stats')
@login_required
def user_stats():
    """Get user statistics"""
    # Count user's projects by status
    projects_count = db.session.query(Project.status, db.func.count(Project.id)).join(
        ProjectAssignment
    ).filter(ProjectAssignment.user_id == current_user.id).group_by(Project.status).all()
    
    project_stats = {status: count for status, count in projects_count}
    
    # Total activities
    total_activities = Activity.query.filter_by(user_id=current_user.id).count()
    
    return jsonify({
        'total_projects': sum(project_stats.values()),
        'project_stats': project_stats,
        'total_activities': total_activities,
        'member_since': current_user.created_at.isoformat()
    })