from blog.models import Photo
from database import db
from main_app import app

with app.app_context():
    db.create_all()
    print("Photo table created (if it did not already exist).")
