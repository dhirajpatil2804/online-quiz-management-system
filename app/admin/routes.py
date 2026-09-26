from flask import render_template, request, redirect, url_for, flash

from flask_login import login_required, current_user

from app.admin import admin
from app.extensions import db
from app.models import User, Quiz, Question



@admin.route("/dashboard")
@login_required
def dashboard():

    if current_user.role != "admin":
        return "Access Denied", 403

    total_students = User.query.filter_by(
        role="student"
    ).count()

    total_teachers = User.query.filter_by(
        role="teacher"
    ).count()

    total_quizzes = Quiz.query.count()

    total_questions = Question.query.count()

    return render_template(
        "admin/dashboard.html",
        user=current_user,
        total_students=total_students,
        total_teachers=total_teachers,
        total_quizzes=total_quizzes,
        total_questions=total_questions
    )

@admin.route("/users")
@login_required
def users():

    if current_user.role != "admin":
        return "Access Denied", 403

    all_users = User.query.order_by(User.id.desc()).all()

    return render_template(
        "admin/users.html",
        users=all_users
    )


@admin.route("/users/add", methods=["GET", "POST"])
@login_required
def add_user():

    if current_user.role != "admin":
        return "Access Denied", 403

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "").strip().lower()

        if not name or not email or not password or not role:
            flash("All fields are required.", "danger")
            return redirect(url_for("admin.add_user"))

        if role not in ["teacher", "student"]:
            flash("Invalid role selected.", "danger")
            return redirect(url_for("admin.add_user"))

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("A user with this email already exists.", "danger")
            return redirect(url_for("admin.add_user"))

        new_user = User(
            name=name,
            email=email,
            role=role,
            is_active=True
        )

        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash(
            f"{role.capitalize()} created successfully.",
            "success"
        )

        return redirect(url_for("admin.users"))

    return render_template("admin/add_user.html")

@admin.route("/quizzes")
@login_required
def quizzes():

    if current_user.role != "admin":
        return "Access Denied", 403

    all_quizzes = Quiz.query.order_by(
        Quiz.id.desc()
    ).all()

    return render_template(
        "admin/quizzes.html",
        quizzes=all_quizzes
    )