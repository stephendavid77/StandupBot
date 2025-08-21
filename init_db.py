from app import app
from src.models import db

with app.app_context():
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
    db.init_app(app)
    db.create_all()
    print("Database tables created.")
