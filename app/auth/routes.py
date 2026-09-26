from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required

from app.auth import auth
from app.models import User


@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):

            if not user.is_active:
                flash("Your account is inactive.", "danger")
                return redirect(url_for("auth.login"))

            login_user(user)

            if user.role == "admin":
                return redirect(url_for("admin.dashboard"))

            elif user.role == "teacher":
                return redirect(url_for("teacher.dashboard"))

            elif user.role == "student":
                return redirect(url_for("student.dashboard"))

            else:
                flash("Invalid user role.", "danger")
                return redirect(url_for("auth.login"))

        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html")


@auth.route("/logout")
@login_required
def logout():

    logout_user()

    flash("You have been logged out.", "success")

    return redirect(url_for("auth.login"))