from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from models import User, FeaturedWork, Client
from functools import wraps
import os
from flask import current_app
from werkzeug.utils import secure_filename
import uuid

admin_bp = Blueprint('admin', __name__)

# File upload configuration
UPLOAD_SUBFOLDER = 'featured_works'


def ensure_upload_dir():
    upload_dir = os.path.join(current_app.root_path,
                              'static', 'uploads', UPLOAD_SUBFOLDER)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def save_upload(file_storage):
    if not file_storage or file_storage.filename == '':
        return None
    ensure_upload_dir()
    orig = secure_filename(file_storage.filename)
    # ensure unique filename
    ext = os.path.splitext(orig)[1]
    unique_name = f"{uuid.uuid4().hex}{ext.lower()}"
    rel_url = f"/static/uploads/{UPLOAD_SUBFOLDER}/{unique_name}"
    abs_path = os.path.join(current_app.root_path, rel_url.lstrip('/'))
    file_storage.save(abs_path)
    return rel_url


def is_local_upload(url: str) -> bool:
    return bool(url) and url.startswith(f"/static/uploads/{UPLOAD_SUBFOLDER}/")


def delete_local_upload(url: str):
    try:
        if is_local_upload(url):
            abs_path = os.path.join(current_app.root_path, url.lstrip('/'))
            if os.path.exists(abs_path):
                os.remove(abs_path)
    except Exception:
        # ignore deletion errors
        pass


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


# Featured Work Management
@admin_bp.route('/featured-works')
@login_required
@admin_required
def featured_works():
    items = FeaturedWork.query.order_by(
        FeaturedWork.display_order.asc(), FeaturedWork.created_at.desc()).all()
    return render_template('admin/featured_works.html', items=items)


@admin_bp.route('/featured-works/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_featured_work():
    if request.method == 'POST':
        title = request.form.get('title')
        category = request.form.get('category')
        description = request.form.get('description')

        # Accept either URL or uploaded file
        image_url_input = request.form.get('image_url') or None
        project_url_input = request.form.get('project_url') or None
        image_file = request.files.get('image_file')
        project_file = request.files.get('project_file')

        display_order = request.form.get('display_order') or 0
        is_active = bool(request.form.get('is_active'))

        if not title:
            flash('Title is required', 'error')
            return redirect(url_for('admin.create_featured_work'))

        # Uploaded files take precedence if provided
        saved_image_url = save_upload(
            image_file) if image_file and image_file.filename else image_url_input
        saved_project_url = save_upload(
            project_file) if project_file and project_file.filename else project_url_input

        item = FeaturedWork(
            title=title,
            category=category,
            description=description,
            image_url=saved_image_url,
            project_url=saved_project_url,
            display_order=int(display_order),
            is_active=is_active
        )
        db.session.add(item)
        db.session.commit()
        flash('Featured work created', 'success')
        return redirect(url_for('admin.featured_works'))

    return render_template('admin/featured_work_form.html', item=None)


@admin_bp.route('/featured-works/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_featured_work(item_id):
    item = FeaturedWork.query.get_or_404(item_id)
    if request.method == 'POST':
        item.title = request.form.get('title')
        item.category = request.form.get('category')
        item.description = request.form.get('description')

        # Handle deletion checkboxes
        delete_image = bool(request.form.get('delete_image'))
        delete_project = bool(request.form.get('delete_project'))

        # Inputs for URL and files
        image_url_input = request.form.get('image_url') or None
        project_url_input = request.form.get('project_url') or None
        image_file = request.files.get('image_file')
        project_file = request.files.get('project_file')

        # Image field logic
        if delete_image:
            delete_local_upload(item.image_url)
            item.image_url = None
        elif image_file and image_file.filename:
            # replace existing if local
            delete_local_upload(item.image_url)
            item.image_url = save_upload(image_file)
        elif image_url_input is not None:
            # If switching from a local upload to a URL, remove local file
            if image_url_input != item.image_url:
                delete_local_upload(item.image_url)
                item.image_url = image_url_input

        # Project field logic
        if delete_project:
            delete_local_upload(item.project_url)
            item.project_url = None
        elif project_file and project_file.filename:
            delete_local_upload(item.project_url)
            item.project_url = save_upload(project_file)
        elif project_url_input is not None:
            if project_url_input != item.project_url:
                delete_local_upload(item.project_url)
                item.project_url = project_url_input

        item.display_order = int(request.form.get('display_order') or 0)
        item.is_active = bool(request.form.get('is_active'))
        db.session.commit()
        flash('Featured work updated', 'success')
        return redirect(url_for('admin.featured_works'))

    return render_template('admin/featured_work_form.html', item=item)


@admin_bp.route('/featured-works/<int:item_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_featured_work(item_id):
    item = FeaturedWork.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Featured work deleted', 'success')
    return redirect(url_for('admin.featured_works'))


# Clients Management
@admin_bp.route('/clients')
@login_required
@admin_required
def clients_page():
    items = Client.query.order_by(
        Client.display_order.asc(), Client.created_at.desc()).all()
    return render_template('admin/clients.html', items=items)


@admin_bp.route('/clients/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_client():
    if request.method == 'POST':
        name = request.form.get('name')
        logo_url = request.form.get('logo_url')
        icon_class = request.form.get('icon_class')
        website_url = request.form.get('website_url')
        display_order = request.form.get('display_order') or 0
        is_active = bool(request.form.get('is_active'))

        if not name:
            flash('Client name is required', 'error')
            return redirect(url_for('admin.create_client'))

        item = Client(
            name=name,
            logo_url=logo_url,
            icon_class=icon_class,
            website_url=website_url,
            display_order=int(display_order),
            is_active=is_active
        )
        db.session.add(item)
        db.session.commit()
        flash('Client created', 'success')
        return redirect(url_for('admin.clients_page'))

    return render_template('admin/client_form.html', item=None)


@admin_bp.route('/clients/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_client(item_id):
    item = Client.query.get_or_404(item_id)
    if request.method == 'POST':
        item.name = request.form.get('name')
        item.logo_url = request.form.get('logo_url')
        item.icon_class = request.form.get('icon_class')
        item.website_url = request.form.get('website_url')
        item.display_order = int(request.form.get('display_order') or 0)
        item.is_active = bool(request.form.get('is_active'))
        db.session.commit()
        flash('Client updated', 'success')
        return redirect(url_for('admin.clients_page'))

    return render_template('admin/client_form.html', item=item)


@admin_bp.route('/clients/<int:item_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_client_item(item_id):
    item = Client.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Client deleted', 'success')
    return redirect(url_for('admin.clients_page'))


@admin_bp.route('/users/<int:user_id>/role', methods=['POST'])
@login_required
@admin_required
def update_user_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    if new_role not in ['admin', 'designer', 'client']:
        flash('Invalid role.', 'error')
        return redirect(url_for('admin.manage_users'))

    # Prevent demoting the last admin
    if user.role == 'admin' and new_role != 'admin':
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count <= 1:
            flash('Cannot demote the last admin.', 'error')
            return redirect(url_for('admin.manage_users'))

    user.role = new_role
    db.session.commit()
    flash(f"Updated role for {user.username} to {new_role}.", 'success')
    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    # Prevent deleting self or the last admin
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin.manage_users'))

    if user.role == 'admin':
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count <= 1:
            flash('Cannot delete the last admin.', 'error')
            return redirect(url_for('admin.manage_users'))

    db.session.delete(user)
    db.session.commit()
    flash(f"Deleted user {user.username}.", 'success')
    return redirect(url_for('admin.manage_users'))


# Client Management Routes
@admin_bp.route('/clients-management')
@login_required
@admin_required
def manage_clients():
    """Display all users with role 'client' for management"""
    clients = User.query.filter_by(role='client').order_by(
        User.created_at.desc()).all()
    return render_template('admin/clients_management.html', clients=clients)


@admin_bp.route('/clients-management/<int:user_id>/restrict', methods=['POST'])
@login_required
@admin_required
def restrict_client_user(user_id):
    """Restrict a client user for a specified number of days"""
    user = User.query.get_or_404(user_id)

    if user.role != 'client':
        flash('Can only restrict client users.', 'error')
        return redirect(url_for('admin.manage_clients'))

    days = int(request.form.get('days', 7))
    reason = request.form.get('reason', 'No reason provided')

    from datetime import datetime, timedelta
    user.is_restricted = True
    user.restriction_until = datetime.utcnow() + timedelta(days=days)
    user.restriction_reason = reason

    db.session.commit()
    flash(f"Restricted {user.username} for {days} days.", 'success')
    return redirect(url_for('admin.manage_clients'))


@admin_bp.route('/clients-management/<int:user_id>/unrestrict', methods=['POST'])
@login_required
@admin_required
def unrestrict_client_user(user_id):
    """Remove restriction from a client user"""
    user = User.query.get_or_404(user_id)

    if user.role != 'client':
        flash('Can only unrestrict client users.', 'error')
        return redirect(url_for('admin.manage_clients'))

    user.is_restricted = False
    user.restriction_until = None
    user.restriction_reason = None

    db.session.commit()
    flash(f"Removed restriction from {user.username}.", 'success')
    return redirect(url_for('admin.manage_clients'))


@admin_bp.route('/clients-management/<int:user_id>/ban', methods=['POST'])
@login_required
@admin_required
def ban_client_user(user_id):
    """Ban a client user permanently"""
    user = User.query.get_or_404(user_id)

    if user.role != 'client':
        flash('Can only ban client users.', 'error')
        return redirect(url_for('admin.manage_clients'))

    reason = request.form.get('reason', 'No reason provided')

    from datetime import datetime
    user.is_banned = True
    user.ban_reason = reason
    user.banned_at = datetime.utcnow()
    # Also remove any active restrictions
    user.is_restricted = False
    user.restriction_until = None
    user.restriction_reason = None

    db.session.commit()
    flash(f"Banned {user.username}.", 'success')
    return redirect(url_for('admin.manage_clients'))


@admin_bp.route('/clients-management/<int:user_id>/unban', methods=['POST'])
@login_required
@admin_required
def unban_client_user(user_id):
    """Remove ban from a client user"""
    user = User.query.get_or_404(user_id)

    if user.role != 'client':
        flash('Can only unban client users.', 'error')
        return redirect(url_for('admin.manage_clients'))

    user.is_banned = False
    user.ban_reason = None
    user.banned_at = None

    db.session.commit()
    flash(f"Removed ban from {user.username}.", 'success')
    return redirect(url_for('admin.manage_clients'))


@admin_bp.route('/clients-management/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_client_user(user_id):
    """Permanently delete a client user"""
    user = User.query.get_or_404(user_id)

    if user.role != 'client':
        flash('Can only delete client users.', 'error')
        return redirect(url_for('admin.manage_clients'))

    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f"Permanently deleted client {username}.", 'success')
    return redirect(url_for('admin.manage_clients'))
