from flask import render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app import app, db
from models import User, Project, ProjectAssignment, Activity, Milestone, Task, FeaturedWork, Client
from sqlalchemy import func
from datetime import datetime, timedelta


def calculate_project_progress(project):
    """Calculate project progress from completed milestones; fallback to tasks when no milestones exist."""
    # Use milestone completion if available
    total_milestones = Milestone.query.filter_by(project_id=project.id).count()
    if total_milestones > 0:
        completed_milestones = Milestone.query.filter_by(
            project_id=project.id, status='completed').count()
        return round((completed_milestones / total_milestones) * 100, 1)

    # Fallback to tasks when no milestones exist
    total_tasks = Task.query.filter_by(project_id=project.id).count()
    if total_tasks > 0:
        completed_tasks = Task.query.filter_by(
            project_id=project.id, status='completed').count()
        return round((completed_tasks / total_tasks) * 100, 1)

    return 0


def get_user_projects():
    """Get projects based on user role"""
    if current_user.is_admin():
        # Admin sees all projects
        return Project.query.all()
    else:
        # Other users see only assigned projects
        assignments = ProjectAssignment.query.filter_by(
            user_id=current_user.id).all()
        project_ids = [assignment.project_id for assignment in assignments]
        return Project.query.filter(Project.id.in_(project_ids)).all() if project_ids else []


@app.route('/')
def home():
    featured_works = FeaturedWork.query.filter_by(is_active=True) \
        .order_by(FeaturedWork.display_order.asc(), FeaturedWork.created_at.desc()) \
        .limit(6).all()
    clients = Client.query.filter_by(is_active=True) \
        .order_by(Client.display_order.asc(), Client.created_at.desc()).all()
    return render_template('home.html', featured_works=featured_works, clients=clients)

# Public pages with dedicated endpoints used by the public header


@app.route('/service')
def service():
    return render_template('service.html')


@app.route('/portfolio')
def portfolio():
    # Fetch featured works (portfolio projects)
    featured_works = FeaturedWork.query.filter_by(is_active=True) \
        .order_by(FeaturedWork.display_order.asc(), FeaturedWork.created_at.desc()).all()

    # Fetch clients
    clients = Client.query.filter_by(is_active=True) \
        .order_by(Client.display_order.asc(), Client.created_at.desc()).all()

    return render_template('portfolio.html', featured_works=featured_works, clients=clients)


@app.route('/pricing')
def pricing():
    return render_template('pricing.html')


@app.route('/contact-us')
def contact_us():
    return render_template('contact.html')


@app.route('/about-us')
def about_us():
    return render_template('about.html')


@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard route"""
    # Check if user is banned or restricted
    if not current_user.can_access_dashboard():
        if current_user.is_currently_banned():
            flash('Your account has been banned. Please contact support.', 'error')
            return redirect(url_for('auth.logout'))
        elif current_user.is_currently_restricted():
            flash(
                'Your account is currently restricted. Please contact support.', 'error')
            return redirect(url_for('auth.logout'))

    # Get projects based on user role
    user_projects = get_user_projects()

    # If client (non-admin) has no projects, show a simple dashboard page that still includes header/sidebar
    if not current_user.is_admin() and not user_projects:
        return render_template('dashboard_empty.html', current_user=current_user)

    # Calculate project statistics
    total_projects = len(user_projects)
    pending_projects = len([p for p in user_projects if p.status == 'pending'])
    ongoing_projects = len([p for p in user_projects if p.status == 'ongoing'])
    complete_projects = len(
        [p for p in user_projects if p.status == 'complete'])

    # Calculate progress and flag 'not_opened' only for projects created within the last 24 hours
    now = datetime.utcnow()
    for project in user_projects:
        project.progress = calculate_project_progress(project)
        project.not_opened = bool(project.created_at and (
            now - project.created_at) <= timedelta(hours=24))

    # Get recent projects (limit to user's projects)
    recent_projects = sorted(
        user_projects, key=lambda x: x.updated_at, reverse=True)[:4]

    # Get project data for chart (filtered by user's projects)
    chart_data = get_project_chart_data(user_projects)

    # Get employee category data (filtered by user's projects)
    employee_categories = get_employee_category_data(user_projects)

    # Get recent activities (limit to user's projects)
    project_ids = [p.id for p in user_projects]
    if current_user.is_admin():
        recent_activities = db.session.query(Activity, User).join(
            User).order_by(Activity.created_at.desc()).limit(5).all()
    else:
        recent_activities = db.session.query(Activity, User).join(User)\
            .filter(Activity.project_id.in_(project_ids) if project_ids else False)\
            .order_by(Activity.created_at.desc()).limit(5).all()

    # Get in-progress projects (limit to user's projects)
    in_progress_projects = [
        p for p in user_projects if p.status == 'ongoing'][:3]

    return render_template('dashboard.html',
                           total_projects=total_projects,
                           pending_projects=pending_projects,
                           ongoing_projects=ongoing_projects,
                           complete_projects=complete_projects,
                           recent_projects=recent_projects,
                           chart_data=chart_data,
                           employee_categories=employee_categories,
                           recent_activities=recent_activities,
                           in_progress_projects=in_progress_projects,
                           current_user=current_user)


@app.route('/search')
def search():
    """Search functionality"""
    query = request.args.get('q', '')
    if query:
        # Filter search results based on user's projects
        user_projects = get_user_projects()
        project_ids = [p.id for p in user_projects]

        if current_user.is_admin():
            projects = Project.query.filter(
                Project.name.contains(query) |
                Project.description.contains(query)
            ).limit(10).all()
        else:
            projects = Project.query.filter(
                Project.id.in_(project_ids),
                (Project.name.contains(query) | Project.description.contains(query))
            ).limit(10).all()

        return jsonify([{
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'status': p.status
        } for p in projects])
    return jsonify([])


def get_project_chart_data(user_projects):
    """Generate chart data for project statistics based on user's projects"""
    if not user_projects:
        return {
            'labels': [],
            'datasets': [
                {
                    'label': 'Complete',
                    'data': [],
                    'borderColor': '#6366f1',
                    'backgroundColor': 'rgba(99, 102, 241, 0.1)',
                    'tension': 0.4
                },
                {
                    'label': 'Ongoing',
                    'data': [],
                    'borderColor': '#f59e0b',
                    'backgroundColor': 'rgba(245, 158, 11, 0.1)',
                    'tension': 0.4
                }
            ]
        }

    # Get last 6 months
    months = []
    complete_data = []
    ongoing_data = []

    for i in range(6):
        date = datetime.now() - timedelta(days=30*i)
        month_name = date.strftime('%b')
        months.insert(0, month_name)

        # Count projects by status for this month
        month_start = date.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0)
        month_end = (month_start + timedelta(days=32)
                     ).replace(day=1) - timedelta(seconds=1)

        complete_count = len([p for p in user_projects
                              if p.status == 'complete' and
                              p.updated_at and
                              month_start <= p.updated_at <= month_end])
        ongoing_count = len([p for p in user_projects
                             if p.status == 'ongoing' and
                             p.updated_at and
                             month_start <= p.updated_at <= month_end])

        complete_data.insert(0, complete_count)
        ongoing_data.insert(0, ongoing_count)

    return {
        'labels': months,
        'datasets': [
            {
                'label': 'Complete',
                'data': complete_data,
                'borderColor': '#6366f1',
                'backgroundColor': 'rgba(99, 102, 241, 0.1)',
                'tension': 0.4
            },
            {
                'label': 'Ongoing',
                'data': ongoing_data,
                'borderColor': '#f59e0b',
                'backgroundColor': 'rgba(245, 158, 11, 0.1)',
                'tension': 0.4
            }
        ]
    }


def get_employee_category_data(user_projects):
    """Generate donut chart data per project weighted by completion percentage.
    Ensures each project has at least a 1% visible slice (including 0%% progress)."""
    if not user_projects:
        return {
            'labels': [],
            'datasets': [{
                'data': [],
                'backgroundColor': [],
                'borderWidth': 0
            }]
        }

    labels = [p.name for p in user_projects]

    # Build values from project progress with a minimum floor of 1 for visibility
    values = []
    for p in user_projects:
        prog = getattr(p, 'progress', None)
        if prog is None:
            # Fallback if progress wasn't precomputed
            prog = calculate_project_progress(p)
        # Enforce minimum visibility of 1% for 0% and sub-1% progress
        if prog < 1:
            prog = 1
        values.append(prog)

    total = sum(values)

    # Normalize to percentages summing to ~100 with 1% min per project
    if total == 0:
        data = [1 for _ in values]
    else:
        data = [round((v / total) * 100, 1) for v in values]
        # Enforce min 1% after rounding
        data = [1 if d < 1 else d for d in data]

    # Adjust for rounding so total is exactly 100
    total_after = round(sum(data), 1)
    diff = round(100 - total_after, 1)
    if diff != 0 and len(data) > 0:
        # Adjust the largest slice to absorb the rounding difference
        max_idx = max(range(len(data)), key=lambda i: data[i])
        adjusted = round(data[max_idx] + diff, 1)
        # Keep at least 1%
        if adjusted < 1:
            adjusted = 1
        data[max_idx] = adjusted

    base_colors = ['#6366f1', '#10b981', '#f59e0b', '#ef4444',
                   '#8b5cf6', '#06b6d4', '#22c55e', '#0ea5e9', '#eab308', '#f97316']
    # Repeat colors if projects exceed base palette
    background_colors = [base_colors[i %
                                     len(base_colors)] for i in range(len(labels))]

    return {
        'labels': labels,
        'datasets': [{
            'data': data,
            'backgroundColor': background_colors,
            'borderWidth': 0
        }]
    }


@app.context_processor
def utility_processor():
    """Add utility functions to template context"""
    def get_project_icon(project_name):
        icons = {
            'Adobe XD': 'fab fa-adobe',
            'HTML': 'fab fa-html5',
            'Digital Marketing': 'fas fa-bullhorn',
            'Angular': 'fab fa-angular',
            'Software Architecture Design': 'fas fa-code'
        }
        return icons.get(project_name, 'fas fa-project-diagram')

    def get_priority_color(priority):
        colors = {
            'High': 'danger',
            'Medium': 'warning',
            'Low': 'success'
        }
        return colors.get(priority, 'secondary')

    def time_ago(date):
        if not date:
            return 'Unknown'

        now = datetime.utcnow()
        diff = now - date

        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"

    return dict(
        get_project_icon=get_project_icon,
        get_priority_color=get_priority_color,
        time_ago=time_ago
    )
