from app import create_app
from app.extensions import db
from app.models import User


app = create_app()

with app.app_context():

    existing_user = User.query.filter_by(
        email="admin@onlinequiz.com"
    ).first()

    if existing_user:
        print("Admin user already exists.")
    else:
        admin = User(
            name="System Admin",
            email="admin@onlinequiz.com",
            role="admin",
            is_active=True
        )

        admin.set_password("Admin@123")

        db.session.add(admin)
        db.session.commit()

        print("Admin user created successfully.")
        print("Email: admin@onlinequiz.com")
        print("Password: Admin@123")