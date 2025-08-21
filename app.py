from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import logging

from src.services.jira_service import JiraClient
from src.services.email_service import email_report

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = 'super secret key'

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Flask-Login Configuration
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

# User Loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/')
app.register_blueprint(main_bp, url_prefix='/')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0')