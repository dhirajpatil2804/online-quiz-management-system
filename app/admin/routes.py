from datetime import datetime

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    Response,
    send_file
)

from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from app.admin import admin
from app.extensions import db
from app.models import User, Quiz, Question, QuizAttempt
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

def to_ist(dt):
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc).astimezone(IST)

# =========================================================
# ADMIN DASHBOARD
# =========================================================

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


# =========================================================
# ALL USERS
# =========================================================

@admin.route("/users")
@login_required
def users():

    if current_user.role != "admin":
        return "Access Denied", 403

    all_users = User.query.order_by(
        User.id.desc()
    ).all()

    return render_template(
        "admin/users.html",
        users=all_users
    )


# =========================================================
# ADD USER
# =========================================================

@admin.route("/users/add", methods=["GET", "POST"])
@login_required
def add_user():

    if current_user.role != "admin":
        return "Access Denied", 403

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        role = request.form.get(
            "role",
            ""
        ).strip().lower()

        if not name or not email or not password or not role:

            flash(
                "All fields are required.",
                "danger"
            )

            return redirect(
                url_for("admin.add_user")
            )

        if role not in ["teacher", "student"]:

            flash(
                "Invalid role selected.",
                "danger"
            )

            return redirect(
                url_for("admin.add_user")
            )

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            flash(
                "A user with this email already exists.",
                "danger"
            )

            return redirect(
                url_for("admin.add_user")
            )

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

        return redirect(
            url_for("admin.users")
        )

    return render_template(
        "admin/add_user.html"
    )


# =========================================================
# TEACHER MANAGEMENT
# =========================================================

@admin.route("/teachers")
@login_required
def teachers():

    if current_user.role != "admin":
        return "Access Denied", 403

    teachers = User.query.filter_by(
        role="teacher"
    ).order_by(
        User.id.desc()
    ).all()

    return render_template(
        "admin/teachers.html",
        teachers=teachers
    )


# =========================================================
# ADD TEACHER
# =========================================================

@admin.route("/teachers/add", methods=["GET", "POST"])
@login_required
def add_teacher():

    if current_user.role != "admin":
        return "Access Denied", 403

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not name or not email or not password:

            flash(
                "Name, email and password are required.",
                "danger"
            )

            return redirect(
                url_for("admin.add_teacher")
            )

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            flash(
                "A user with this email already exists.",
                "danger"
            )

            return redirect(
                url_for("admin.add_teacher")
            )

        teacher = User(
            name=name,
            email=email,
            role="teacher",
            is_active=True
        )

        teacher.set_password(password)

        db.session.add(teacher)
        db.session.commit()

        flash(
            "Teacher added successfully.",
            "success"
        )

        return redirect(
            url_for("admin.teachers")
        )

    return render_template(
        "admin/add_teacher.html"
    )


# =========================================================
# EDIT TEACHER
# =========================================================

@admin.route("/teachers/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def edit_teacher(user_id):

    if current_user.role != "admin":
        return "Access Denied", 403

    teacher = User.query.filter_by(
        id=user_id,
        role="teacher"
    ).first()

    if not teacher:

        flash(
            "Teacher not found.",
            "danger"
        )

        return redirect(
            url_for("admin.teachers")
        )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not name or not email:

            flash(
                "Name and email are required.",
                "danger"
            )

            return redirect(
                url_for(
                    "admin.edit_teacher",
                    user_id=teacher.id
                )
            )

        existing_user = User.query.filter(
            User.email == email,
            User.id != teacher.id
        ).first()

        if existing_user:

            flash(
                "Another user already uses this email.",
                "danger"
            )

            return redirect(
                url_for(
                    "admin.edit_teacher",
                    user_id=teacher.id
                )
            )

        teacher.name = name
        teacher.email = email

        # Password is optional while editing
        if password:

            teacher.set_password(password)

        db.session.commit()

        flash(
            "Teacher updated successfully.",
            "success"
        )

        return redirect(
            url_for("admin.teachers")
        )

    return render_template(
        "admin/edit_teacher.html",
        teacher=teacher
    )


# =========================================================
# ACTIVATE / DEACTIVATE TEACHER
# =========================================================

@admin.route(
    "/teachers/<int:user_id>/toggle-status",
    methods=["POST"]
)
@login_required
def toggle_teacher_status(user_id):

    if current_user.role != "admin":
        return "Access Denied", 403

    teacher = User.query.filter_by(
        id=user_id,
        role="teacher"
    ).first()

    if not teacher:

        flash(
            "Teacher not found.",
            "danger"
        )

        return redirect(
            url_for("admin.teachers")
        )

    teacher.is_active = not teacher.is_active

    db.session.commit()

    if teacher.is_active:

        flash(
            f"{teacher.name} has been activated.",
            "success"
        )

    else:

        flash(
            f"{teacher.name} has been deactivated.",
            "warning"
        )

    return redirect(
        url_for("admin.teachers")
    )


# =========================================================
# DELETE TEACHER
# =========================================================

@admin.route(
    "/teachers/<int:user_id>/delete",
    methods=["POST"]
)
@login_required
def delete_teacher(user_id):

    if current_user.role != "admin":
        return "Access Denied", 403

    teacher = User.query.filter_by(
        id=user_id,
        role="teacher"
    ).first()

    if not teacher:

        flash(
            "Teacher not found.",
            "danger"
        )

        return redirect(
            url_for("admin.teachers")
        )

    # Prevent deleting a teacher who has created quizzes
    quiz_count = Quiz.query.filter_by(
        created_by=teacher.id
    ).count()

    if quiz_count > 0:

        flash(
            "This teacher cannot be deleted because they have created quizzes. Deactivate the teacher instead.",
            "danger"
        )

        return redirect(
            url_for("admin.teachers")
        )

    teacher_name = teacher.name

    db.session.delete(teacher)
    db.session.commit()

    flash(
        f"Teacher {teacher_name} deleted successfully.",
        "success"
    )

    return redirect(
        url_for("admin.teachers")
    )


# =========================================================
# ADMIN QUIZ OVERVIEW
# =========================================================

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


# =========================================================
# ADMIN EDIT QUIZ
# =========================================================

@admin.route(
    "/quizzes/<int:quiz_id>/edit",
    methods=["GET", "POST"]
)
@login_required
def edit_quiz(quiz_id):

    if current_user.role != "admin":
        return "Access Denied", 403

    quiz = Quiz.query.get(quiz_id)

    if not quiz:
        flash(
            "Quiz not found.",
            "danger"
        )

        return redirect(
            url_for("admin.quizzes")
        )

    # -----------------------------------------------------
    # Check whether any student has attempted this quiz
    # -----------------------------------------------------

    from app.models import QuizAttempt

    attempt_exists = QuizAttempt.query.filter_by(
        quiz_id=quiz.id
    ).first()

    if attempt_exists:

        flash(
            "This quiz cannot be edited because a student has already attempted it.",
            "warning"
        )

        return redirect(
            url_for("admin.quizzes")
        )

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        duration_text = request.form.get(
            "duration",
            ""
        ).strip()

        number_of_questions_text = request.form.get(
            "number_of_questions",
            ""
        ).strip()

        total_marks_text = request.form.get(
            "total_marks",
            ""
        ).strip()

        passing_marks_text = request.form.get(
            "passing_marks",
            ""
        ).strip()

        if not title:

            flash(
                "Quiz title is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "admin.edit_quiz",
                    quiz_id=quiz.id
                )
            )

        try:

            duration = int(duration_text)
            number_of_questions = int(
                number_of_questions_text
            )
            total_marks = int(total_marks_text)
            passing_marks = int(passing_marks_text)

        except ValueError:

            flash(
                "Duration, number of questions and marks must be valid numbers.",
                "danger"
            )

            return redirect(
                url_for(
                    "admin.edit_quiz",
                    quiz_id=quiz.id
                )
            )

        if duration <= 0:

            flash(
                "Duration must be greater than 0.",
                "danger"
            )

            return redirect(
                url_for(
                    "admin.edit_quiz",
                    quiz_id=quiz.id
                )
            )

        if number_of_questions <= 0:

            flash(
                "Number of questions must be greater than 0.",
                "danger"
            )

            return redirect(
                url_for(
                    "admin.edit_quiz",
                    quiz_id=quiz.id
                )
            )

        if total_marks <= 0:

            flash(
                "Total marks must be greater than 0.",
                "danger"
            )

            return redirect(
                url_for(
                    "admin.edit_quiz",
                    quiz_id=quiz.id
                )
            )

        if passing_marks < 0 or passing_marks > total_marks:

            flash(
                "Passing marks must be between 0 and total marks.",
                "danger"
            )

            return redirect(
                url_for(
                    "admin.edit_quiz",
                    quiz_id=quiz.id
                )
            )

        quiz.title = title
        quiz.description = description
        quiz.duration = duration
        quiz.number_of_questions = number_of_questions
        quiz.total_marks = total_marks
        quiz.passing_marks = passing_marks

        db.session.commit()

        flash(
            "Quiz updated successfully.",
            "success"
        )

        return redirect(
            url_for("admin.quizzes")
        )

    return render_template(
        "admin/edit_quiz.html",
        quiz=quiz
    )


# =========================================================
# ADMIN PUBLISH / UNPUBLISH QUIZ
# =========================================================

@admin.route(
    "/quizzes/<int:quiz_id>/toggle-status",
    methods=["POST"]
)
@login_required
def toggle_quiz_status(quiz_id):

    if current_user.role != "admin":
        return "Access Denied", 403

    quiz = Quiz.query.get(quiz_id)

    if not quiz:

        flash(
            "Quiz not found.",
            "danger"
        )

        return redirect(
            url_for("admin.quizzes")
        )

    from app.models import QuizAttempt

    attempt_exists = QuizAttempt.query.filter_by(
        quiz_id=quiz.id
    ).first()

    if attempt_exists:

        flash(
            "Quiz status cannot be changed because a student has already attempted it.",
            "warning"
        )

        return redirect(
            url_for("admin.quizzes")
        )

    if quiz.status == "published":

        quiz.status = "draft"

        flash(
            f"'{quiz.title}' has been moved to draft.",
            "warning"
        )

    else:

        quiz.status = "published"

        flash(
            f"'{quiz.title}' has been published.",
            "success"
        )

    db.session.commit()

    return redirect(
        url_for("admin.quizzes")
    )


# =========================================================
# ADMIN DELETE QUIZ
# =========================================================

@admin.route("/quizzes/<int:quiz_id>/delete", methods=["POST"])
@login_required
def delete_quiz(quiz_id):

    if current_user.role != "admin":
        return "Access Denied", 403

    quiz = Quiz.query.get(quiz_id)

    if not quiz:
        flash("Quiz not found.", "danger")
        return redirect(url_for("admin.quizzes"))

    # Do not delete quizzes with student attempts.
    attempt_exists = QuizAttempt.query.filter_by(
        quiz_id=quiz.id
    ).first()

    if attempt_exists:
        flash(
            "This quiz cannot be deleted because students have attempted it.",
            "danger"
        )
        return redirect(url_for("admin.quizzes"))

    quiz_title = quiz.title

    try:
        # Remove questions and their options first.
        questions = Question.query.filter_by(
            quiz_id=quiz.id
        ).all()

        from app.models import Option

        for question in questions:
            Option.query.filter_by(
                question_id=question.id
            ).delete(synchronize_session=False)

            db.session.delete(question)

        db.session.delete(quiz)
        db.session.commit()

        flash(
            f"Quiz '{quiz_title}' deleted successfully.",
            "success"
        )

    except Exception:
        db.session.rollback()
        flash(
            "Unable to delete this quiz. Please check its related records.",
            "danger"
        )

    return redirect(url_for("admin.quizzes"))



# =========================================================
# STUDENT MANAGEMENT
# =========================================================

@admin.route("/students")
@login_required
def students():

    if current_user.role != "admin":
        return "Access Denied", 403

    students = User.query.filter_by(
        role="student"
    ).order_by(
        User.id.desc()
    ).all()

    return render_template(
        "admin/students.html",
        students=students
    )


# =========================================================
# ADD STUDENT
# =========================================================

@admin.route("/students/add", methods=["GET", "POST"])
@login_required
def add_student():

    if current_user.role != "admin":
        return "Access Denied", 403

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not name or not email or not password:

            flash(
                "Name, email and password are required.",
                "danger"
            )

            return redirect(
                url_for("admin.add_student")
            )

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            flash(
                "A user with this email already exists.",
                "danger"
            )

            return redirect(
                url_for("admin.add_student")
            )

        student = User(
            name=name,
            email=email,
            role="student",
            is_active=True
        )

        student.set_password(password)

        db.session.add(student)
        db.session.commit()

        flash(
            "Student added successfully.",
            "success"
        )

        return redirect(
            url_for("admin.students")
        )

    return render_template(
        "admin/add_student.html"
    )


# =========================================================
# EDIT STUDENT
# =========================================================

@admin.route(
    "/students/<int:user_id>/edit",
    methods=["GET", "POST"]
)
@login_required
def edit_student(user_id):

    if current_user.role != "admin":
        return "Access Denied", 403

    student = User.query.filter_by(
        id=user_id,
        role="student"
    ).first()

    if not student:

        flash(
            "Student not found.",
            "danger"
        )

        return redirect(
            url_for("admin.students")
        )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not name or not email:

            flash(
                "Name and email are required.",
                "danger"
            )

            return redirect(
                url_for(
                    "admin.edit_student",
                    user_id=student.id
                )
            )

        existing_user = User.query.filter(
            User.email == email,
            User.id != student.id
        ).first()

        if existing_user:

            flash(
                "Another user already uses this email.",
                "danger"
            )

            return redirect(
                url_for(
                    "admin.edit_student",
                    user_id=student.id
                )
            )

        student.name = name
        student.email = email

        if password:

            student.set_password(password)

        db.session.commit()

        flash(
            "Student updated successfully.",
            "success"
        )

        return redirect(
            url_for("admin.students")
        )

    return render_template(
        "admin/edit_student.html",
        student=student
    )


# =========================================================
# ACTIVATE / DEACTIVATE STUDENT
# =========================================================

@admin.route(
    "/students/<int:user_id>/toggle-status",
    methods=["POST"]
)
@login_required
def toggle_student_status(user_id):

    if current_user.role != "admin":
        return "Access Denied", 403

    student = User.query.filter_by(
        id=user_id,
        role="student"
    ).first()

    if not student:

        flash(
            "Student not found.",
            "danger"
        )

        return redirect(
            url_for("admin.students")
        )

    student.is_active = not student.is_active

    db.session.commit()

    if student.is_active:

        flash(
            f"{student.name} has been activated.",
            "success"
        )

    else:

        flash(
            f"{student.name} has been deactivated.",
            "warning"
        )

    return redirect(
        url_for("admin.students")
    )


# =========================================================
# DELETE STUDENT
# =========================================================

@admin.route(
    "/students/<int:user_id>/delete",
    methods=["POST"]
)
@login_required
def delete_student(user_id):

    if current_user.role != "admin":
        return "Access Denied", 403

    student = User.query.filter_by(
        id=user_id,
        role="student"
    ).first()

    if not student:

        flash(
            "Student not found.",
            "danger"
        )

        return redirect(
            url_for("admin.students")
        )

    # Check whether student has quiz attempts
    attempt_count = len(student.quiz_attempts)

    if attempt_count > 0:

        flash(
            "This student cannot be deleted because they have quiz attempts. Deactivate the student instead.",
            "danger"
        )

        return redirect(
            url_for("admin.students")
        )

    student_name = student.name

    db.session.delete(student)
    db.session.commit()

    flash(
        f"Student {student_name} deleted successfully.",
        "success"
    )

    return redirect(
        url_for("admin.students")
    )


# =========================================================
# ADMIN VIEW QUIZ QUESTIONS
# =========================================================

@admin.route("/quizzes/<int:quiz_id>/questions")
@login_required
def quiz_questions(quiz_id):

    if current_user.role != "admin":
        return "Access Denied", 403

    quiz = Quiz.query.get(quiz_id)

    if not quiz:
        flash(
            "Quiz not found.",
            "danger"
        )

        return redirect(
            url_for("admin.quizzes")
        )

    questions = Question.query.filter_by(
        quiz_id=quiz.id
    ).order_by(
        Question.question_order.asc()
    ).all()

    return render_template(
        "admin/quiz_questions.html",
        quiz=quiz,
        questions=questions
    )



def get_filtered_report_attempts():
    attempts = QuizAttempt.query.filter_by(
        status="submitted"
    ).order_by(
        QuizAttempt.submitted_at.asc()
    ).all()

    # Calculate attempt number before filtering so numbering stays correct.
    attempt_counts = {}

    for attempt in attempts:
        key = (attempt.student_id, attempt.quiz_id)
        attempt_counts[key] = attempt_counts.get(key, 0) + 1
        attempt.display_attempt_number = attempt_counts[key]

    student_id = request.args.get("student_id", "").strip()
    teacher_id = request.args.get("teacher_id", "").strip()
    quiz_id = request.args.get("quiz_id", "").strip()
    result_filter = request.args.get("result", "").strip().upper()
    date_from_text = request.args.get("date_from", "").strip()
    date_to_text = request.args.get("date_to", "").strip()

    if student_id:
        try:
            student_id = int(student_id)
            attempts = [a for a in attempts if a.student_id == student_id]
        except ValueError:
            pass

    if teacher_id:
        try:
            teacher_id = int(teacher_id)
            attempts = [a for a in attempts if a.quiz.created_by == teacher_id]
        except ValueError:
            pass

    if quiz_id:
        try:
            quiz_id = int(quiz_id)
            attempts = [a for a in attempts if a.quiz_id == quiz_id]
        except ValueError:
            pass

    if result_filter == "PASS":
        attempts = [
            a for a in attempts
            if a.score is not None and a.score >= a.quiz.passing_marks
        ]
    elif result_filter == "FAIL":
        attempts = [
            a for a in attempts
            if a.score is not None and a.score < a.quiz.passing_marks
        ]

    if date_from_text:
        try:
            date_from = datetime.strptime(date_from_text, "%Y-%m-%d").date()
            attempts = [
                a for a in attempts
                if a.submitted_at and a.submitted_at.date() >= date_from
            ]
        except ValueError:
            pass

    if date_to_text:
        try:
            date_to = datetime.strptime(date_to_text, "%Y-%m-%d").date()
            attempts = [
                a for a in attempts
                if a.submitted_at and a.submitted_at.date() <= date_to
            ]
        except ValueError:
            pass

    attempts.reverse()
    return attempts


# =========================================================
# ADMIN REPORTS
# =========================================================

@admin.route("/reports")
@login_required
def reports():
    if current_user.role != "admin":
        return "Access Denied", 403

    attempts = get_filtered_report_attempts()
    for attempt in attempts:
        attempt.submitted_at_ist = to_ist(attempt.submitted_at)

    total_attempts = len(attempts)
    passed_attempts = 0
    failed_attempts = 0
    total_percentage = 0

    for attempt in attempts:
        if attempt.quiz.total_marks > 0 and attempt.score is not None:
            percentage = (attempt.score / attempt.quiz.total_marks) * 100
        else:
            percentage = 0

        if attempt.score is not None and attempt.score >= attempt.quiz.passing_marks:
            passed_attempts += 1
        else:
            failed_attempts += 1

        total_percentage += percentage

    average_percentage = (
        total_percentage / total_attempts
        if total_attempts > 0 else 0
    )

    students = User.query.filter_by(role="student").order_by(User.name.asc()).all()
    teachers = User.query.filter_by(role="teacher").order_by(User.name.asc()).all()
    quizzes = Quiz.query.order_by(Quiz.title.asc()).all()

    return render_template(
        "admin/reports.html",
        attempts=attempts,
        total_attempts=total_attempts,
        passed_attempts=passed_attempts,
        failed_attempts=failed_attempts,
        average_percentage=average_percentage,
        students=students,
        teachers=teachers,
        quizzes=quizzes
    )


# =========================================================
# EXPORT REPORT - CSV
# =========================================================

@admin.route("/reports/export/csv")
@login_required
def export_reports_csv():
    if current_user.role != "admin":
        return "Access Denied", 403

    attempts = get_filtered_report_attempts()
    for attempt in attempts:
        attempt.submitted_at_ist = to_ist(attempt.submitted_at)

    csv_data = (
        "Student,Email,Quiz,Teacher,Attempt,Score,Total Marks,"
        "Percentage,Result,Submitted\n"
    )

    for attempt in attempts:
        percentage = (
            (attempt.score / attempt.quiz.total_marks) * 100
            if attempt.quiz.total_marks > 0 and attempt.score is not None
            else 0
        )

        result = (
            "PASS"
            if attempt.score is not None
            and attempt.score >= attempt.quiz.passing_marks
            else "FAIL"
        )

        submitted = (
            attempt.submitted_at_ist.strftime("%d-%m-%Y %I:%M %p") if attempt.submitted_at_ist else ""
        )

        row = [
            attempt.student.name,
            attempt.student.email,
            attempt.quiz.title,
            attempt.quiz.creator.name,
            attempt.display_attempt_number,
            attempt.score,
            attempt.quiz.total_marks,
            f"{percentage:.2f}%",
            result,
            submitted
        ]

        csv_data += ",".join(
            '"' + str(value).replace('"', '""') + '"'
            for value in row
        ) + "\n"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=quiz_reports.csv"
        }
    )


# =========================================================
# EXPORT REPORT - EXCEL
# =========================================================

@admin.route("/reports/export/excel")
@login_required
def export_reports_excel():
    if current_user.role != "admin":
        return "Access Denied", 403

    import pandas as pd
    from io import BytesIO

    attempts = get_filtered_report_attempts()
    for attempt in attempts:
        attempt.submitted_at_ist = to_ist(attempt.submitted_at)
    data = []

    for attempt in attempts:
        percentage = (
            (attempt.score / attempt.quiz.total_marks) * 100
            if attempt.quiz.total_marks > 0 and attempt.score is not None
            else 0
        )

        result = (
            "PASS"
            if attempt.score is not None
            and attempt.score >= attempt.quiz.passing_marks
            else "FAIL"
        )

        submitted = (
            attempt.submitted_at_ist.strftime("%d-%m-%Y %I:%M %p")
            if attempt.submitted_at_ist else ""
        )

        data.append({
            "Student": attempt.student.name,
            "Email": attempt.student.email,
            "Quiz": attempt.quiz.title,
            "Teacher": attempt.quiz.creator.name,
            "Attempt": attempt.display_attempt_number,
            "Score": attempt.score,
            "Total Marks": attempt.quiz.total_marks,
            "Percentage": round(percentage, 2),
            "Result": result,
            "Submitted": submitted
        })

    df = pd.DataFrame(data)
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Quiz Reports")

        worksheet = writer.sheets["Quiz Reports"]
        for column_cells in worksheet.columns:
            max_length = 0
            column_letter = column_cells[0].column_letter

            for cell in column_cells:
                value = "" if cell.value is None else str(cell.value)
                max_length = max(max_length, len(value))

            worksheet.column_dimensions[column_letter].width = min(
                max(max_length + 2, 12), 35
            )

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="quiz_reports.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )


# =========================================================
# EXPORT REPORT - PDF
# =========================================================

@admin.route("/reports/export/pdf")
@login_required
def export_reports_pdf():
    if current_user.role != "admin":
        return "Access Denied", 403

    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer
    )
    from reportlab.lib.styles import getSampleStyleSheet

    attempts = get_filtered_report_attempts()
    for attempt in attempts:
        attempt.submitted_at_ist = to_ist(attempt.submitted_at)

    table_data = [[
        "Student",
        "Quiz",
        "Teacher",
        "Attempt",
        "Score",
        "Total",
        "%",
        "Result",
        "Submitted"
    ]]

    for attempt in attempts:
        percentage = (
            (attempt.score / attempt.quiz.total_marks) * 100
            if attempt.quiz.total_marks > 0 and attempt.score is not None
            else 0
        )

        result = (
            "PASS"
            if attempt.score is not None
            and attempt.score >= attempt.quiz.passing_marks
            else "FAIL"
        )

        submitted = (
            attempt.submitted_at_ist.strftime("%d-%m-%Y %I:%M %p") if attempt.submitted_at_ist else ""
        )

        table_data.append([
            attempt.student.name,
            attempt.quiz.title,
            attempt.quiz.creator.name,
            attempt.display_attempt_number,
            attempt.score,
            attempt.quiz.total_marks,
            f"{percentage:.1f}%",
            result,
            submitted
        ])

    output = BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=25,
        leftMargin=25,
        topMargin=25,
        bottomMargin=25
    )

    styles = getSampleStyleSheet()
    elements = [
        Paragraph("<b>Online Quiz Management System</b>", styles["Title"]),
        Paragraph("Quiz Attempt Report", styles["Heading2"]),
        Spacer(1, 15)
    ]

    table = Table(table_data, repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (3, 1), (7, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        (
            "ROWBACKGROUNDS",
            (0, 1),
            (-1, -1),
            [colors.white, colors.HexColor("#f3f4f6")]
        ),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
    ]))

    elements.append(table)
    doc.build(elements)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="quiz_reports.pdf",
        mimetype="application/pdf"
    )

# =========================================================
# ADMIN ANALYTICS DASHBOARD
# =========================================================

@admin.route("/analytics")
@login_required
def analytics():

    if current_user.role != "admin":
        return "Access Denied", 403

    # -----------------------------------------------------
    # Basic counts
    # -----------------------------------------------------

    total_students = User.query.filter_by(
        role="student"
    ).count()

    active_students = User.query.filter_by(
        role="student",
        is_active=True
    ).count()

    inactive_students = User.query.filter_by(
        role="student",
        is_active=False
    ).count()

    total_teachers = User.query.filter_by(
        role="teacher"
    ).count()

    active_teachers = User.query.filter_by(
        role="teacher",
        is_active=True
    ).count()

    inactive_teachers = User.query.filter_by(
        role="teacher",
        is_active=False
    ).count()

    total_quizzes = Quiz.query.count()

    published_quizzes = Quiz.query.filter_by(
        status="published"
    ).count()

    draft_quizzes = Quiz.query.filter_by(
        status="draft"
    ).count()

    # -----------------------------------------------------
    # Submitted attempts
    # -----------------------------------------------------

    attempts = QuizAttempt.query.filter_by(
        status="submitted"
    ).order_by(
        QuizAttempt.submitted_at.desc()
    ).all()

    total_attempts = len(attempts)

    passed_attempts = 0
    failed_attempts = 0

    total_percentage = 0

    for attempt in attempts:

        if (
            attempt.score is not None
            and attempt.quiz.total_marks > 0
        ):
            percentage = (
                attempt.score /
                attempt.quiz.total_marks
            ) * 100
        else:
            percentage = 0

        total_percentage += percentage

        if (
            attempt.score is not None
            and attempt.score >= attempt.quiz.passing_marks
        ):
            passed_attempts += 1
        else:
            failed_attempts += 1

    average_percentage = (
        total_percentage / total_attempts
        if total_attempts > 0
        else 0
    )

    # -----------------------------------------------------
    # Quiz-wise analytics
    # -----------------------------------------------------

    quiz_data = []

    quizzes = Quiz.query.order_by(
        Quiz.title.asc()
    ).all()

    for quiz in quizzes:

        quiz_attempts = [
            attempt
            for attempt in attempts
            if attempt.quiz_id == quiz.id
        ]

        attempt_count = len(quiz_attempts)

        quiz_total_percentage = 0

        for attempt in quiz_attempts:

            if (
                attempt.score is not None
                and quiz.total_marks > 0
            ):
                percentage = (
                    attempt.score /
                    quiz.total_marks
                ) * 100
            else:
                percentage = 0

            quiz_total_percentage += percentage

        quiz_average = (
            quiz_total_percentage / attempt_count
            if attempt_count > 0
            else 0
        )

        quiz_data.append({
            "title": quiz.title,
            "attempts": attempt_count,
            "average": round(quiz_average, 2)
        })

    # -----------------------------------------------------
    # Recent activity
    # -----------------------------------------------------

    recent_attempts = attempts[:10]
    for attempt in recent_attempts:
        attempt.submitted_at_ist = to_ist(attempt.submitted_at)

    return render_template(
        "admin/analytics.html",

        total_students=total_students,
        active_students=active_students,
        inactive_students=inactive_students,

        total_teachers=total_teachers,
        active_teachers=active_teachers,
        inactive_teachers=inactive_teachers,

        total_quizzes=total_quizzes,
        published_quizzes=published_quizzes,
        draft_quizzes=draft_quizzes,

        total_attempts=total_attempts,
        passed_attempts=passed_attempts,
        failed_attempts=failed_attempts,
        average_percentage=average_percentage,

        quiz_data=quiz_data,
        recent_attempts=recent_attempts
    )


