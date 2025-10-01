from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import User, Project, ProjectAssignment, Activity
from app import db
from datetime import datetime
from sqlalchemy import func

api_bp = Blueprint('api', __name__)

@api_bp.route('/projects', methods=['GET', 'POST'])
@login_required
def projects():
    if request.method == 'POST':
        data = request.get_json()
        
        # Validation
        required_fields = ['name', 'description', 'department', 'priority']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Create new project
        project = Project()
        project.name = data['name']
        project.description = data['description']
        project.department = data['department']
        project.priority = data['priority']
        project.status = data.get('status', 'pending')
        project.progress = data.get('progress', 0)
        
        db.session.add(project)
        db.session.commit()
        
        # Log activity
        activity = Activity()
        activity.user_id = current_user.id
        activity.project_id = project.id
        activity.action = "Project Created"
        activity.description = f"Created new project: {project.name}"
        db.session.add(activity)
        db.session.commit()
        
        return jsonify({
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'status': project.status,
            'department': project.department,
            'priority': project.priority,
            'progress': project.progress,
            'created_at': project.created_at.isoformat()
        }), 201
    
    # GET request
    projects = Project.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'status': p.status,
        'department': p.department,
        'priority': p.priority,
        'progress': p.progress,
        'created_at': p.created_at.isoformat(),
        'updated_at': p.updated_at.isoformat()
    } for p in projects])

@api_bp.route('/projects/<int:project_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'GET':
        return jsonify({
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'status': project.status,
            'department': project.department,
            'priority': project.priority,
            'progress': project.progress,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat(),
            'team_members': [{
                'id': assignment.user.id,
                'username': assignment.user.username,
                'email': assignment.user.email,
                'role': assignment.role,
                'avatar_url': assignment.user.avatar_url
            } for assignment in project.assignments]
        })
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        # Update project fields
        if 'name' in data:
            project.name = data['name']
        if 'description' in data:
            project.description = data['description']
        if 'status' in data:
            project.status = data['status']
        if 'department' in data:
            project.department = data['department']
        if 'priority' in data:
            project.priority = data['priority']
        if 'progress' in data:
            project.progress = data['progress']
        
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
        
        return jsonify({'message': 'Project updated successfully'})
    
    elif request.method == 'DELETE':
        # Remove project assignments first
        ProjectAssignment.query.filter_by(project_id=project.id).delete()
        
        # Log activity before deletion
        activity = Activity()
        activity.user_id = current_user.id
        activity.action = "Project Deleted"
        activity.description = f"Deleted project: {project.name}"
        db.session.add(activity)
        
        db.session.delete(project)
        db.session.commit()
        
        return jsonify({'message': 'Project deleted successfully'})

@api_bp.route('/projects/<int:project_id>/assign', methods=['POST'])
@login_required
def assign_user_to_project(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.get_json()
    
    user_id = data.get('user_id')
    role = data.get('role', 'Team Member')
    
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    user = User.query.get_or_404(user_id)
    
    # Check if user is already assigned
    existing_assignment = ProjectAssignment.query.filter_by(
        project_id=project_id, user_id=user_id
    ).first()
    
    if existing_assignment:
        return jsonify({'error': 'User is already assigned to this project'}), 400
    
    # Create assignment
    assignment = ProjectAssignment()
    assignment.project_id = project_id
    assignment.user_id = user_id
    assignment.role = role
    db.session.add(assignment)
    db.session.commit()
    
    # Log activity
    activity = Activity()
    activity.user_id = current_user.id
    activity.project_id = project_id
    activity.action = "User Assigned"
    activity.description = f"Assigned {user.username} to {project.name}"
    db.session.add(activity)
    db.session.commit()
    
    return jsonify({'message': 'User assigned successfully'})

@api_bp.route('/projects/<int:project_id>/unassign/<int:user_id>', methods=['DELETE'])
@login_required
def unassign_user_from_project(project_id, user_id):
    assignment = ProjectAssignment.query.filter_by(
        project_id=project_id, user_id=user_id
    ).first_or_404()
    
    project = Project.query.get(project_id)
    user = User.query.get(user_id)
    
    db.session.delete(assignment)
    db.session.commit()
    
    # Log activity
    activity = Activity()
    activity.user_id = current_user.id
    activity.project_id = project_id
    activity.action = "User Unassigned"
    activity.description = f"Unassigned {user.username} from {project.name}"
    db.session.add(activity)
    db.session.commit()
    
    return jsonify({'message': 'User unassigned successfully'})

@api_bp.route('/users', methods=['GET'])
@login_required
def users():
    users = User.query.all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'avatar_url': u.avatar_url,
        'created_at': u.created_at.isoformat()
    } for u in users])

@api_bp.route('/activities', methods=['GET'])
@login_required
def activities():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    activities = db.session.query(Activity, User).join(User).order_by(
        Activity.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'activities': [{
            'id': activity.id,
            'action': activity.action,
            'description': activity.description,
            'created_at': activity.created_at.isoformat(),
            'user': {
                'id': user.id,
                'username': user.username,
                'avatar_url': user.avatar_url
            },
            'project': {
                'id': activity.project.id,
                'name': activity.project.name
            } if activity.project else None
        } for activity, user in activities.items],
        'total': activities.total,
        'pages': activities.pages,
        'current_page': activities.page
    })

@api_bp.route('/dashboard/stats', methods=['GET'])
@login_required
def dashboard_stats():
    total_projects = Project.query.count()
    pending_projects = Project.query.filter_by(status='pending').count()
    ongoing_projects = Project.query.filter_by(status='ongoing').count()
    complete_projects = Project.query.filter_by(status='complete').count()
    
    return jsonify({
        'total_projects': total_projects,
        'pending_projects': pending_projects,
        'ongoing_projects': ongoing_projects,
        'complete_projects': complete_projects
    })

@api_bp.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    # Search projects
    projects = Project.query.filter(
        Project.name.contains(query) | 
        Project.description.contains(query)
    ).limit(10).all()
    
    # Search users
    users = User.query.filter(
        User.username.contains(query) |
        User.email.contains(query)
    ).limit(5).all()
    
    return jsonify({
        'projects': [{
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'status': p.status,
            'type': 'project'
        } for p in projects],
        'users': [{
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'avatar_url': u.avatar_url,
            'type': 'user'
        } for u in users]
    })