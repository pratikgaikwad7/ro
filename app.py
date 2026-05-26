from flask import Flask
from dotenv import load_dotenv
import os

# Import Blueprints
from routes.students import students_bp
from routes.auth import auth_bp
from routes.users import users_bp
from routes.admin import admin_bp
from routes.evaluations import evaluations_bp
from routes.user_dashboard import user_dashboard_bp

from models.student_model import init_db

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY')

    # Register Blueprints
    app.register_blueprint(students_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(evaluations_bp)
    app.register_blueprint(user_dashboard_bp)

    _db_initialized = False

    @app.before_request
    def initialize_db_once():
        nonlocal _db_initialized
        if not _db_initialized:
            init_db()
            _db_initialized = True

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host='0.0.0.0', debug=True, port=5001)