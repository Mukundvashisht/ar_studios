from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import User, Project, ProjectAssignment, Task, Milestone, ChatMessage, Activity
from app import db, socketio, app
from flask_socketio import join_room, leave_room
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
import os
import json

project_bp = Blueprint('project', __name__)


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def project_access_required(f):
    """Decorator to require project access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        project_id = kwargs.get('project_id')
        if not project_id:
            return f(*args, **kwargs)

        # Admin can access all projects
        if current_user.is_admin():
            return f(*args, **kwargs)

        # Check if user is assigned to the project
        assignment = ProjectAssignment.query.filter_by(
            project_id=project_id,
            user_id=current_user.id
        ).first()

        if not assignment:
            flash('You do not have access to this project.', 'error')
            return redirect(url_for('dashboard'))

        return f(*args, **kwargs)
    return decorated_function


def calculate_project_progress(project):
    """Calculate project progress based on completed milestones; fallback to tasks when none exist."""
    # Prefer milestone completion
    total_milestones = Milestone.query.filter_by(project_id=project.id).count()
    if total_milestones > 0:
        completed_milestones = Milestone.query.filter_by(project_id=project.id, status='completed').count()
        return round((completed_milestones / total_milestones) * 100, 1)

    # Fallback to tasks if no milestones
    total_tasks = Task.query.filter_by(project_id=project.id).count()
    if total_tasks > 0:
        completed_tasks = Task.query.filter_by(project_id=project.id, status='completed').count()
        return round((completed_tasks / total_tasks) * 100, 1)

    return 0


def update_project_status(project):
    """Update project status based on progress"""
    progress = calculate_project_progress(project)
    project.progress = progress

    if progress == 100:
        project.status = 'complete'
    elif progress > 0:
        project.status = 'ongoing'
    else:
        project.status = 'pending'

    project.updated_at = datetime.utcnow()
    db.session.commit()


@project_bp.route('/projects')
@login_required
def projects():
    """Show projects based on user role"""
    if current_user.is_admin():
        # Admin sees all projects
        projects = Project.query.all()
    else:
        # Other users see only assigned projects
        assignments = ProjectAssignment.query.filter_by(
            user_id=current_user.id).all()
        project_ids = [assignment.project_id for assignment in assignments]
        projects = Project.query.filter(Project.id.in_(project_ids)).all()

    # Calculate progress for each project and annotate not_opened flag
    for project in projects:
        project.progress = calculate_project_progress(project)
        opened = Activity.query.filter_by(user_id=current_user.id, project_id=project.id, action="Project Opened").first()
        project.not_opened = False if opened else True

    return render_template('projects/index.html', projects=projects)


@project_bp.route('/projects/<int:project_id>')
@login_required
@project_access_required
def project_detail(project_id):
    """Show project details"""
    project = Project.query.get_or_404(project_id)
    tasks = Task.query.filter_by(project_id=project_id).all()
    milestones = Milestone.query.filter_by(project_id=project_id).all()

    # Calculate project progress automatically
    project.progress = calculate_project_progress(project)

    # Get project members
    assignments = ProjectAssignment.query.filter_by(
        project_id=project_id).all()
    members = [assignment.user for assignment in assignments]

    # Log first-time open activity for this user and project
    opened = Activity.query.filter_by(user_id=current_user.id, project_id=project_id, action="Project Opened").first()
    if not opened:
        activity = Activity()
        activity.user_id = current_user.id
        activity.project_id = project_id
        activity.action = "Project Opened"
        activity.description = f"Viewed project: {project.name}"
        db.session.add(activity)
        db.session.commit()

    return render_template('projects/detail.html',
                           project=project,
                           tasks=tasks,
                           milestones=milestones,
                           members=members)


@project_bp.route('/projects/new', methods=['GET', 'POST'])
@login_required
def create_project():
    """Create new project (any authenticated user). Assign to creator and all admins automatically."""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        department = request.form.get('department')
        priority = request.form.get('priority')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        client_name = request.form.get('client_name')

        if not name:
            flash('Project name is required.', 'error')
            return render_template('projects/create.html')

        project = Project()
        project.name = name
        project.description = description
        project.department = department
        project.priority = priority
        project.status = 'pending'
        project.progress = 0

        if start_date:
            project.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            project.end_date = datetime.strptime(end_date, '%Y-%m-%d')
        if client_name:
            project.client_name = client_name

        db.session.add(project)
        db.session.commit()

        # Automatically assign all admins to the project
        admins = User.query.filter_by(role='admin').all()
        for admin in admins:
            existing = ProjectAssignment.query.filter_by(project_id=project.id, user_id=admin.id).first()
            if not existing:
                admin_assignment = ProjectAssignment()
                admin_assignment.project_id = project.id
                admin_assignment.user_id = admin.id
                admin_assignment.role = "Admin"
                db.session.add(admin_assignment)

        # Automatically assign the creator to the project
        existing_creator = ProjectAssignment.query.filter_by(project_id=project.id, user_id=current_user.id).first()
        if not existing_creator:
            creator_assignment = ProjectAssignment()
            creator_assignment.project_id = project.id
            creator_assignment.user_id = current_user.id
            creator_assignment.role = "Owner"
            db.session.add(creator_assignment)

        db.session.commit()

        # Log activity
        activity = Activity()
        activity.user_id = current_user.id
        activity.project_id = project.id
        activity.action = "Project Created"
        activity.description = f"Created new project: {project.name}"
        db.session.add(activity)
        db.session.commit()

        flash('Project created successfully!', 'success')
        return redirect(url_for('project.project_detail', project_id=project.id))

    return render_template('projects/create.html')


@project_bp.route('/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_project(project_id):
    """Edit project (admin only)"""
    project = Project.query.get_or_404(project_id)

    if request.method == 'POST':
        project.name = request.form.get('name')
        project.description = request.form.get('description')
        project.department = request.form.get('department')
        project.priority = request.form.get('priority')
        project.status = request.form.get('status')
        project.progress = int(request.form.get('progress', 0))

        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        client_name = request.form.get('client_name')

        if start_date:
            project.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            project.end_date = datetime.strptime(end_date, '%Y-%m-%d')
        if client_name:
            project.client_name = client_name

        project.updated_at = datetime.utcnow()
        db.session.commit()

        # Log activity
        activity = Activity()
        activity.user_id = current_user.id
        activity.project_id = project.id
        activity.action = "Project Updated"
        activity.description = f"Updated project: {project.name}"
        db.session.add(activity)
        db.session.commit()

        flash('Project updated successfully!', 'success')
        return redirect(url_for('project.project_detail', project_id=project.id))

    return render_template('projects/edit.html', project=project)


@project_bp.route('/projects/<int:project_id>/assign', methods=['GET', 'POST'])
@login_required
@admin_required
def assign_users(project_id):
    """Assign users to project (admin only)"""
    project = Project.query.get_or_404(project_id)

    if request.method == 'POST':
        user_ids = request.form.getlist('user_ids')

        # Remove existing assignments (except admin)
        existing_assignments = ProjectAssignment.query.filter_by(
            project_id=project_id).all()
        for assignment in existing_assignments:
            if assignment.user.role != 'admin':
                db.session.delete(assignment)

        # Add new assignments
        for user_id in user_ids:
            if user_id:
                assignment = ProjectAssignment()
                assignment.project_id = project_id
                assignment.user_id = int(user_id)
                assignment.role = "Team Member"
                db.session.add(assignment)

        db.session.commit()

        # Log activity
        activity = Activity()
        activity.user_id = current_user.id
        activity.project_id = project.id
        activity.action = "Users Assigned"
        activity.description = f"Assigned users to project: {project.name}"
        db.session.add(activity)
        db.session.commit()

        flash('Users assigned successfully!', 'success')
        return redirect(url_for('project.project_detail', project_id=project.id))

    # Get all users except admin
    users = User.query.filter(User.role != 'admin').all()
    current_assignments = ProjectAssignment.query.filter_by(
        project_id=project_id).all()
    assigned_user_ids = [
        assignment.user_id for assignment in current_assignments]

    return render_template('projects/assign.html',
                           project=project,
                           users=users,
                           assigned_user_ids=assigned_user_ids)


@project_bp.route('/projects/<int:project_id>/milestones', methods=['GET', 'POST'])
@login_required
@project_access_required
def manage_milestones(project_id):
    """Manage project milestones"""
    project = Project.query.get_or_404(project_id)

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        due_date = request.form.get('due_date')

        if not title:
            flash('Milestone title is required.', 'error')
            return redirect(url_for('project.manage_milestones', project_id=project_id))

        milestone = Milestone()
        milestone.title = title
        milestone.description = description
        milestone.project_id = project_id
        milestone.created_by = current_user.id

        if due_date:
            milestone.due_date = datetime.strptime(due_date, '%Y-%m-%d')

        db.session.add(milestone)
        db.session.commit()

        flash('Milestone created successfully!', 'success')
        return redirect(url_for('project.manage_milestones', project_id=project_id))

    milestones = Milestone.query.filter_by(project_id=project_id).all()
    return render_template('projects/milestones.html', project=project, milestones=milestones)


@project_bp.route('/milestones/<int:milestone_id>/update-status', methods=['POST'])
@login_required
def update_milestone_status(milestone_id):
    """Update milestone status (designer and admin only)"""
    milestone = Milestone.query.get_or_404(milestone_id)

    # Check if user has access to the project
    assignment = ProjectAssignment.query.filter_by(
        project_id=milestone.project_id,
        user_id=current_user.id
    ).first()

    if not assignment and not current_user.is_admin():
        return jsonify({'error': 'Access denied'}), 403

    # Only designers and admins can update milestone status
    if not (current_user.is_designer() or current_user.is_admin()):
        return jsonify({'error': 'Only designers and admins can update milestone status'}), 403

    status = request.json.get('status')
    if status not in ['pending', 'in_progress', 'completed']:
        return jsonify({'error': 'Invalid status'}), 400

    milestone.status = status
    milestone.updated_at = datetime.utcnow()

    if status == 'completed':
        milestone.completed_at = datetime.utcnow()

    db.session.commit()

    # Log activity
    activity = Activity()
    activity.user_id = current_user.id
    activity.project_id = milestone.project_id
    activity.action = "Milestone Updated"
    activity.description = f"Updated milestone '{milestone.title}' to {status}"
    db.session.add(activity)
    db.session.commit()

    # Update project progress if milestone is completed
    project = Project.query.get(milestone.project_id)
    if project:
        update_project_status(project)

    return jsonify({'success': True, 'status': status})

# Real-time chat functionality


@socketio.on('join_project')
def on_join_project(data):
    """Join project chat room"""
    project_id = data['project_id']

    # Verify user has access to the project
    if current_user.is_admin():
        join_room(f'project_{project_id}')
        socketio.emit('user_joined', {
            'user': current_user.username,
            'message': f'{current_user.username} joined the chat'
        }, room=f'project_{project_id}')
    else:
        assignment = ProjectAssignment.query.filter_by(
            project_id=project_id,
            user_id=current_user.id
        ).first()

        if assignment:
            join_room(f'project_{project_id}')
            socketio.emit('user_joined', {
                'user': current_user.username,
                'message': f'{current_user.username} joined the chat'
            }, room=f'project_{project_id}')


@socketio.on('leave_project')
def on_leave_project(data):
    """Leave project chat room"""
    project_id = data['project_id']
    leave_room(f'project_{project_id}')
    socketio.emit('user_left', {
        'user': current_user.username,
        'message': f'{current_user.username} left the chat'
    }, room=f'project_{project_id}')


@socketio.on('send_message')
def on_send_message(data):
    """Send chat message"""
    project_id = data['project_id']
    message_content = data['message']

    # Verify user has access to the project
    if current_user.is_admin():
        pass  # Admin can access all projects
    else:
        assignment = ProjectAssignment.query.filter_by(
            project_id=project_id,
            user_id=current_user.id
        ).first()

        if not assignment:
            return

    # Save message to database
    chat_message = ChatMessage()
    chat_message.content = message_content
    chat_message.user_id = current_user.id
    chat_message.project_id = project_id
    db.session.add(chat_message)
    db.session.commit()

    # Broadcast message to all users in the project
    socketio.emit('new_message', {
        'id': chat_message.id,
        'user': current_user.username,
        'avatar': current_user.avatar_url,
        'message': message_content,
        'timestamp': chat_message.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }, room=f'project_{project_id}')


@project_bp.route('/projects/<int:project_id>/chat/upload', methods=['POST'])
@login_required
@project_access_required
def upload_attachment(project_id):
    """Upload an attachment to the project chat and broadcast it in real-time"""
    file = request.files.get('file')
    if not file or file.filename.strip() == '':
        return jsonify({'error': 'No file provided'}), 400

    upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'projects', str(project_id))
    os.makedirs(upload_dir, exist_ok=True)

    base_name = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
    name, ext = os.path.splitext(base_name)
    final_name = f"{name}_{timestamp}{ext}"
    save_path = os.path.join(upload_dir, final_name)
    file.save(save_path)

    file_url = url_for('static', filename=f'uploads/projects/{project_id}/{final_name}')
    file_size = os.path.getsize(save_path)
    mime = file.mimetype or 'application/octet-stream'

    chat_message = ChatMessage()
    attachment_payload = {
        '__attachment__': True,
        'url': file_url,
        'filename': base_name,
        'mimetype': mime,
        'size': file_size
    }
    chat_message.content = json.dumps(attachment_payload)
    chat_message.user_id = current_user.id
    chat_message.project_id = project_id
    db.session.add(chat_message)
    db.session.commit()

    socketio.emit('new_message', {
        'id': chat_message.id,
        'user': current_user.username,
        'avatar': current_user.avatar_url,
        'message': '',
        'timestamp': chat_message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'attachment': {
            'url': file_url,
            'filename': base_name,
            'mimetype': mime,
            'size': file_size
        }
    }, room=f'project_{project_id}')

    return jsonify({
        'success': True,
        'message_id': chat_message.id,
        'attachment': {
            'url': file_url,
            'filename': base_name,
            'mimetype': mime,
            'size': file_size
        }
    }), 201


@project_bp.route('/projects/<int:project_id>/chat')
@login_required
@project_access_required
def project_chat(project_id):
    """Project chat page"""
    project = Project.query.get_or_404(project_id)

    # Get recent chat messages
    messages = ChatMessage.query.filter_by(project_id=project_id)\
        .order_by(ChatMessage.created_at.desc())\
        .limit(50)\
        .all()
    messages.reverse()  # Show oldest first

    # Hydrate attachment metadata for persisted messages
    for m in messages:
        m.is_attachment = False
        m.attachment = None
        try:
            data = json.loads(m.content or '')
            if isinstance(data, dict) and data.get('__attachment__'):
                m.is_attachment = True
                m.attachment = {
                    'url': data.get('url'),
                    'filename': data.get('filename'),
                    'mimetype': data.get('mimetype'),
                    'size': data.get('size')
                }
                m.content = ''
        except Exception:
            pass

    return render_template('projects/chat.html',
                           project=project,
                           messages=messages)

# API endpoints for AJAX requests

# Note: Project progress is now calculated automatically based on completed milestones
# No manual progress update is needed
