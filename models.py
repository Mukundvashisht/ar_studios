from app import db
from datetime import datetime, timedelta
from flask_login import UserMixin
import random


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    avatar_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)

    # User role - admin, designer, client
    role = db.Column(db.String(20), default='client', nullable=False)

    # User preferences
    theme_preference = db.Column(db.String(20), default='light')
    notifications_enabled = db.Column(db.Boolean, default=True)

    # User restrictions and bans
    is_restricted = db.Column(db.Boolean, default=False)
    restriction_until = db.Column(db.DateTime, nullable=True)
    restriction_reason = db.Column(db.Text, nullable=True)
    is_banned = db.Column(db.Boolean, default=False)
    ban_reason = db.Column(db.Text, nullable=True)
    banned_at = db.Column(db.DateTime, nullable=True)

    def get_id(self):
        return str(self.id)

    def is_admin(self):
        return self.role == 'admin'

    def is_designer(self):
        return self.role == 'designer'

    def is_client(self):
        return self.role == 'client'

    def is_currently_restricted(self):
        """Check if user is currently under restriction"""
        if not self.is_restricted:
            return False
        if self.restriction_until and self.restriction_until < datetime.utcnow():
            # Restriction has expired, auto-unrestrict
            self.is_restricted = False
            self.restriction_until = None
            self.restriction_reason = None
            db.session.commit()
            return False
        return True

    def is_currently_banned(self):
        """Check if user is currently banned"""
        return self.is_banned

    def can_access_dashboard(self):
        """Check if user can access dashboard (not banned and not restricted)"""
        return not self.is_currently_banned() and not self.is_currently_restricted()


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    # total, pending, ongoing, complete
    status = db.Column(db.String(20), nullable=False)
    department = db.Column(db.String(50))
    priority = db.Column(db.String(10))  # High, Medium, Low
    progress = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Project details
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    client_name = db.Column(db.String(100))

    # Relationships
    assignments = db.relationship(
        'ProjectAssignment', backref='project', lazy=True, cascade='all, delete-orphan')
    activities = db.relationship('Activity', backref='project', lazy=True)
    milestones = db.relationship(
        'Milestone', backref='project', lazy=True, cascade='all, delete-orphan')
    chat_messages = db.relationship(
        'ChatMessage', backref='project', lazy=True, cascade='all, delete-orphan')


class ProjectAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey(
        'project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(50))
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to user
    user = db.relationship('User', backref='project_assignments')


class Milestone(db.Model):
    """Milestones within projects"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    # pending, in_progress, completed
    status = db.Column(db.String(20), default='pending')
    due_date = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    # Foreign keys
    project_id = db.Column(db.Integer, db.ForeignKey(
        'project.id'), nullable=False)
    created_by = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    creator = db.relationship('User', backref='created_milestones')


class ChatMessage(db.Model):
    """Real-time chat messages for projects"""
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)

    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey(
        'project.id'), nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='chat_messages')


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    action = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='activities')


class Task(db.Model):
    """Individual tasks within projects"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    # todo, in_progress, completed
    status = db.Column(db.String(20), default='todo')
    priority = db.Column(db.String(10), default='medium')

    # Foreign keys
    project_id = db.Column(db.Integer, db.ForeignKey(
        'project.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    # Relationships
    assignee = db.relationship('User', foreign_keys=[
                               assigned_to], backref='assigned_tasks')
    creator = db.relationship('User', foreign_keys=[
                              created_by], backref='created_tasks')
    project = db.relationship('Project', backref='tasks')


class Comment(db.Model):
    """Comments on projects and tasks"""
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)

    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'))

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='comments')
    project = db.relationship('Project', backref='comments')
    task = db.relationship('Task', backref='comments')


class Notification(db.Model):
    """User notifications"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    # info, success, warning, error
    type = db.Column(db.String(50), default='info')

    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Status
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='notifications')


class FeaturedWork(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100))
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    project_url = db.Column(db.String(500))
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    logo_url = db.Column(db.String(500))
    # Optional: e.g., 'fa-brands fa-apple'
    icon_class = db.Column(db.String(120))
    website_url = db.Column(db.String(500))
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_sample_data():
    """Initialize the database with sample data"""

    # Create sample users with roles
    users_data = [
        {"username": "randy_riley", "email": "randy.riley@gmail.com",
            "avatar_url": "https://ui-avatars.com/api/?name=Randy+Riley&background=6366f1&color=fff", "role": "designer"},
        {"username": "lucinda_massey", "email": "lucinda.massey@company.com",
            "avatar_url": "https://ui-avatars.com/api/?name=Lucinda+Massey&background=ec4899&color=fff", "role": "client"},
        {"username": "john_doe", "email": "john.doe@company.com",
            "avatar_url": "https://ui-avatars.com/api/?name=John+Doe&background=10b981&color=fff", "role": "designer"},
        {"username": "jane_smith", "email": "jane.smith@company.com",
            "avatar_url": "https://ui-avatars.com/api/?name=Jane+Smith&background=f59e0b&color=fff", "role": "client"},
        {"username": "admin", "email": "admin@protend.com",
            "avatar_url": "https://ui-avatars.com/api/?name=Admin&background=ef4444&color=fff", "role": "admin"},
    ]

    users = []
    for user_data in users_data:
        user = User()
        user.username = user_data["username"]
        user.email = user_data["email"]
        user.avatar_url = user_data["avatar_url"]
        user.role = user_data["role"]
        # Set default password for demo (in production, users would set their own)
        from werkzeug.security import generate_password_hash
        user.password_hash = generate_password_hash("password123")
        db.session.add(user)
        users.append(user)

    db.session.commit()

    # Create sample projects
    projects_data = [
        {"name": "Adobe XD", "description": "Designing Department", "status": "ongoing",
            "department": "Design", "priority": "High", "progress": 75},
        {"name": "HTML", "description": "HTML Coding Department", "status": "ongoing",
            "department": "Development", "priority": "Low", "progress": 45},
        {"name": "Digital Marketing", "description": "Marketing Department",
            "status": "ongoing", "department": "Marketing", "priority": "Medium", "progress": 60},
        {"name": "Angular", "description": "Angular Department", "status": "ongoing",
            "department": "Development", "priority": "High", "progress": 85},
        {"name": "Software Architecture Design", "description": "System design and architecture",
            "status": "ongoing", "department": "Development", "priority": "High", "progress": 92},
        {"name": "React Dashboard", "description": "Building a modern dashboard with React",
            "status": "pending", "department": "Development", "priority": "Medium", "progress": 0},
        {"name": "Brand Identity", "description": "Creating brand guidelines and assets",
            "status": "complete", "department": "Design", "priority": "High", "progress": 100},
        {"name": "Mobile App UI", "description": "Designing mobile app interface",
            "status": "pending", "department": "Design", "priority": "Medium", "progress": 15},
    ]

    projects = []
    for project_data in projects_data:
        project = Project()
        project.name = project_data["name"]
        project.description = project_data["description"]
        project.status = project_data["status"]
        project.department = project_data["department"]
        project.priority = project_data["priority"]
        project.progress = project_data["progress"]
        project.start_date = datetime.utcnow() - timedelta(days=random.randint(1, 90))
        if project.status == "complete":
            project.end_date = datetime.utcnow() - timedelta(days=random.randint(1, 30))
        elif project.status == "ongoing":
            project.end_date = datetime.utcnow() + timedelta(days=random.randint(30, 120))
        db.session.add(project)
        projects.append(project)

    db.session.commit()

    # Create project assignments
    admin_user = next((user for user in users if user.role == 'admin'), None)

    for project in projects:
        # Always assign admin to all projects
        if admin_user:
            admin_assignment = ProjectAssignment()
            admin_assignment.project_id = project.id
            admin_assignment.user_id = admin_user.id
            admin_assignment.role = "Admin"
            db.session.add(admin_assignment)

        # Assign other random users to projects (excluding admin)
        other_users = [user for user in users if user.role != 'admin']
        if other_users:
            assigned_users = random.sample(other_users, random.randint(1, 3))
            for user in assigned_users:
                assignment = ProjectAssignment()
                assignment.project_id = project.id
                assignment.user_id = user.id
                assignment.role = "Developer" if project.department == "Development" else "Team Member"
                db.session.add(assignment)

    # Create sample tasks
    for project in projects[:5]:  # Add tasks to first 5 projects
        for i in range(random.randint(3, 7)):
            task = Task()
            task.title = f"Task {i+1} for {project.name}"
            task.description = f"Description for task {i+1} in {project.name}"
            task.status = random.choice(['todo', 'in_progress', 'completed'])
            task.priority = random.choice(['low', 'medium', 'high'])
            task.project_id = project.id
            task.assigned_to = random.choice(
                [a.user_id for a in project.assignments])
            task.created_by = users[0].id  # Admin creates tasks
            task.due_date = datetime.utcnow() + timedelta(days=random.randint(1, 30))
            if task.status == 'completed':
                task.completed_at = datetime.utcnow() - timedelta(days=random.randint(1, 10))
            db.session.add(task)

    # Create sample milestones
    for project in projects[:5]:  # Add milestones to first 5 projects
        for i in range(random.randint(2, 4)):
            milestone = Milestone()
            milestone.title = f"Milestone {i+1} for {project.name}"
            milestone.description = f"Description for milestone {i+1} in {project.name}"
            milestone.status = random.choice(
                ['pending', 'in_progress', 'completed'])
            milestone.project_id = project.id
            milestone.created_by = admin_user.id if admin_user else users[0].id
            milestone.due_date = datetime.utcnow() + timedelta(days=random.randint(7, 60))
            if milestone.status == 'completed':
                milestone.completed_at = datetime.utcnow() - timedelta(days=random.randint(1, 20))
            db.session.add(milestone)

    # Create sample activities
    activities_data = [
        {"user_id": 2, "action": "Add New Task", "description": "Added new task to Digital Marketing project",
            "created_at": datetime.utcnow() - timedelta(hours=2)},
        {"user_id": 1, "action": "Project Update", "description": "Updated Adobe XD project progress",
            "created_at": datetime.utcnow() - timedelta(hours=5)},
        {"user_id": 3, "action": "Code Review", "description": "Completed code review for Angular project",
            "created_at": datetime.utcnow() - timedelta(days=1)},
        {"user_id": 4, "action": "Task Completed", "description": "Completed design mockups task",
            "created_at": datetime.utcnow() - timedelta(hours=8)},
        {"user_id": 5, "action": "Comment Added", "description": "Added comment on React Dashboard project",
            "created_at": datetime.utcnow() - timedelta(hours=12)},
    ]

    for activity_data in activities_data:
        activity = Activity()
        activity.user_id = activity_data["user_id"]
        activity.action = activity_data["action"]
        activity.description = activity_data["description"]
        activity.created_at = activity_data["created_at"]
        db.session.add(activity)

    # Create sample notifications
    for user in users[:3]:  # Add notifications for first 3 users
        for i in range(random.randint(1, 3)):
            notification = Notification()
            notification.title = f"Project Update {i+1}"
            notification.message = f"Your project has been updated with new information."
            notification.type = random.choice(['info', 'success', 'warning'])
            notification.user_id = user.id
            notification.read = random.choice([True, False])
            db.session.add(notification)

    db.session.commit()
