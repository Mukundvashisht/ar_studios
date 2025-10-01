import os
import logging
from flask import Flask, request, redirect, url_for, flash, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
from urllib.parse import quote_plus
from flask_login import LoginManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)

load_dotenv()


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get(
    "SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize SocketIO for real-time chat
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'  # Set the login route

# Custom unauthorized handler: redirect to login with a floating notification
@login_manager.unauthorized_handler
def unauthorized():
    # Flash a warning message; the login page will display it as a floating notification
    flash('User not logged in', 'warning')
    # Preserve the originally requested URL
    return redirect(url_for('auth.login', next=request.url))

# Global 404 error handler
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# User loader function for Flask-Login


@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))


# configure the database
db_user = os.environ.get("DB_USER", "")
db_password = quote_plus(os.environ.get("DB_PASSWORD", ""))
db_host = os.environ.get("DB_HOST", "")
db_port = os.environ.get("DB_PORT", "")
db_name = os.environ.get("DB_NAME", "")

# app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///protend.db")
app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    # f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode=require"
)

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Import models and routes
    import models
    import routes

    # Register blueprints
    from auth_routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Import and register other blueprints if they exist
    try:
        from api_routes import api_bp
        app.register_blueprint(api_bp, url_prefix='/api')
    except ImportError:
        pass

    try:
        from profile_routes import profile_bp
        app.register_blueprint(profile_bp, url_prefix='/profile')
    except ImportError:
        pass

    try:
        from project_routes import project_bp
        app.register_blueprint(project_bp, url_prefix='')
    except ImportError:
        pass

    from admin_routes import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Create all tables
    db.create_all()

    # Initialize sample data if tables are empty
    # Remove the problematic line that queries the database during import
    # if models.User.query.count() == 0:
    #     models.init_sample_data()


def reset_database():
    """Drop all tables and recreate them with new schema"""
    print("Dropping all existing tables...")
    db.drop_all()
    print("Creating new tables with updated schema...")
    db.create_all()
    print("Database reset complete!")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # Check if we need to reset the database due to schema changes
        try:
            # Try to query the role column to see if it exists
            test_user = models.User.query.first()
            if test_user and not hasattr(test_user, 'role'):
                print("Database schema is outdated. Resetting database...")
                reset_database()
                models.init_sample_data()
        except Exception as e:
            if "column user.role does not exist" in str(e):
                print("Database schema is outdated. Resetting database...")
                reset_database()
                models.init_sample_data()
            else:
                raise e

        # Initialize sample data if no users exist
        if models.User.query.count() == 0:
            models.init_sample_data()

    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
