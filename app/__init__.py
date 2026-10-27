from flask import Flask

from config import Config
from app.extensions import db, migrate, login_manager
from app import models


def create_app():

    app = Flask(__name__)

    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    login_manager.login_view = "auth.login"
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.User, int(user_id))

    from app.auth import auth
    app.register_blueprint(auth)

    from app.admin import admin
    app.register_blueprint(admin)

    from app.teacher import teacher
    app.register_blueprint(teacher)

    from app.student import student
    app.register_blueprint(student)

    from flask import redirect, url_for

    @app.route("/")
    def home():
        return redirect(url_for("auth.login"))
    

    return app