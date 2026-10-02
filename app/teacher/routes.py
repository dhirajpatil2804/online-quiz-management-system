from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, Response, send_file

from flask_login import login_required, current_user

from app.teacher import teacher
from app.extensions import db
from app.models import (
    Quiz,
    Question,
    Option,
    QuizAttempt,
    QuizRetakePermission,
    User
)

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models import User

@teacher.route("/students/add", methods=["GET", "POST"])
@login_required
def add_student():
    if current_user.role != "teacher":
        flash("Access denied.", "danger")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill in all fields.", "danger")
            return render_template("teacher/add_student.html")

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")
            return render_template("teacher/add_student.html")

        student = User(
            name=name,
            email=email,
            role="student",
            is_active=True
        )
        student.set_password(password)

        try:
            db.session.add(student)
            db.session.commit()
            flash("Student added successfully.", "success")
            return redirect(url_for("teacher.add_student"))
        except Exception:
            db.session.rollback()
            flash("Unable to add student. Please try again.", "danger")

    return render_template("teacher/add_student.html")

# =========================================================
# TEACHER DASHBOARD
# =========================================================

@teacher.route("/dashboard")
@login_required
def dashboard():

    if current_user.role != "teacher":
        return "Access Denied", 403

    # ---------------------------------------------------------
    # QUIZ STATISTICS
    # ---------------------------------------------------------

    teacher_quizzes = Quiz.query.filter_by(
        created_by=current_user.id
    ).all()

    total_quizzes = len(teacher_quizzes)

    published_quizzes = sum(
        1 for quiz in teacher_quizzes
        if quiz.status == "published"
    )

    draft_quizzes = sum(
        1 for quiz in teacher_quizzes
        if quiz.status == "draft"
    )

    # ---------------------------------------------------------
    # QUESTION STATISTICS
    # ---------------------------------------------------------

    total_questions = Question.query.join(
        Quiz,
        Question.quiz_id == Quiz.id
    ).filter(
        Quiz.created_by == current_user.id
    ).count()

    # ---------------------------------------------------------
    # GET TEACHER'S SUBMITTED RESULTS
    # ---------------------------------------------------------

    teacher_attempts = QuizAttempt.query.join(
        Quiz,
        QuizAttempt.quiz_id == Quiz.id
    ).filter(
        Quiz.created_by == current_user.id,
        QuizAttempt.status == "submitted"
    ).order_by(
        QuizAttempt.submitted_at.desc()
    ).all()

    total_attempts = len(teacher_attempts)

    # ---------------------------------------------------------
    # UNIQUE STUDENTS
    # ---------------------------------------------------------

    student_ids = {
        attempt.student_id
        for attempt in teacher_attempts
    }

    total_students = len(student_ids)

    # ---------------------------------------------------------
    # PASS / FAIL / PERCENTAGE
    # ---------------------------------------------------------

    passed_results = 0
    failed_results = 0
    total_percentage = 0
    highest_percentage = 0

    for attempt in teacher_attempts:

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

        # Store percentage for template
        attempt.display_percentage = percentage

        # PASS / FAIL
        if (
            attempt.score is not None
            and attempt.score >= attempt.quiz.passing_marks
        ):

            passed_results += 1

        else:

            failed_results += 1

        total_percentage += percentage

        if percentage > highest_percentage:
            highest_percentage = percentage

    # ---------------------------------------------------------
    # AVERAGE PERCENTAGE
    # ---------------------------------------------------------

    average_percentage = (
        total_percentage / total_attempts
        if total_attempts > 0
        else 0
    )

    # ---------------------------------------------------------
    # RECENT RESULTS
    # ---------------------------------------------------------

    recent_results = teacher_attempts[:5]

    # ---------------------------------------------------------
    # RENDER DASHBOARD
    # ---------------------------------------------------------

    return render_template(
        "teacher/dashboard.html",

        user=current_user,

        total_quizzes=total_quizzes,

        published_quizzes=published_quizzes,

        draft_quizzes=draft_quizzes,

        total_questions=total_questions,

        total_students=total_students,

        total_attempts=total_attempts,

        passed_results=passed_results,

        failed_results=failed_results,

        average_percentage=average_percentage,

        highest_percentage=highest_percentage,

        recent_results=recent_results
    )

# =========================================================
# MANAGE QUIZZES
# =========================================================

@teacher.route("/quizzes")
@login_required
def quizzes():

    if current_user.role != "teacher":
        return "Access Denied", 403

    # ---------------------------------------------------------
    # GET TEACHER'S QUIZZES
    # ---------------------------------------------------------

    all_quizzes = Quiz.query.filter_by(
        created_by=current_user.id
    ).order_by(
        Quiz.id.desc()
    ).all()

    # ---------------------------------------------------------
    # CALCULATE PERFORMANCE FOR EACH QUIZ
    # ---------------------------------------------------------

    for quiz in all_quizzes:

        attempts = QuizAttempt.query.filter_by(
            quiz_id=quiz.id,
            status="submitted"
        ).all()

        # Total attempts
        quiz.total_attempts = len(attempts)

        # Unique students
        quiz.unique_students = len({
            attempt.student_id
            for attempt in attempts
        })

        # Performance values
        percentages = []

        passed = 0
        failed = 0

        for attempt in attempts:

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

            percentages.append(percentage)

            # Pass / Fail
            if (
                attempt.score is not None
                and attempt.score >= quiz.passing_marks
            ):

                passed += 1

            else:

                failed += 1

        # -----------------------------------------------------
        # AVERAGE
        # -----------------------------------------------------

        if percentages:

            quiz.average_percentage = (
                sum(percentages) /
                len(percentages)
            )

        else:

            quiz.average_percentage = 0

        # -----------------------------------------------------
        # HIGHEST
        # -----------------------------------------------------

        if percentages:

            quiz.highest_percentage = max(
                percentages
            )

        else:

            quiz.highest_percentage = 0

        # -----------------------------------------------------
        # PASS / FAIL
        # -----------------------------------------------------

        quiz.passed_attempts = passed

        quiz.failed_attempts = failed

        # -----------------------------------------------------
        # LAST ATTEMPT
        # -----------------------------------------------------

        last_attempt = QuizAttempt.query.filter_by(
            quiz_id=quiz.id,
            status="submitted"
        ).order_by(
            QuizAttempt.submitted_at.desc()
        ).first()

        quiz.last_attempt = last_attempt

    # ---------------------------------------------------------
    # RENDER
    # ---------------------------------------------------------

    return render_template(
        "teacher/quizzes.html",
        quizzes=all_quizzes
    )


# =========================================================
# TEACHER RESULTS
# =========================================================

def get_teacher_filtered_results():
    """
    Get submitted attempts for the logged-in teacher and apply report filters.
    Attempt numbers are calculated before filtering.
    """

    results = QuizAttempt.query.join(
        Quiz,
        QuizAttempt.quiz_id == Quiz.id
    ).filter(
        Quiz.created_by == current_user.id,
        QuizAttempt.status == "submitted"
    ).order_by(
        QuizAttempt.submitted_at.asc()
    ).all()

    # Calculate attempt number per student + quiz.
    attempt_counts = {}

    for attempt in results:
        key = (attempt.student_id, attempt.quiz_id)
        attempt_counts[key] = attempt_counts.get(key, 0) + 1
        attempt.display_attempt_number = attempt_counts[key]

    student_id = request.args.get("student_id", "").strip()
    quiz_id = request.args.get("quiz_id", "").strip()
    result_filter = request.args.get("result", "").strip().upper()
    date_from_text = request.args.get("date_from", "").strip()
    date_to_text = request.args.get("date_to", "").strip()

    if student_id:
        try:
            student_id = int(student_id)
            results = [
                attempt for attempt in results
                if attempt.student_id == student_id
            ]
        except ValueError:
            pass

    if quiz_id:
        try:
            quiz_id = int(quiz_id)
            results = [
                attempt for attempt in results
                if attempt.quiz_id == quiz_id
            ]
        except ValueError:
            pass

    if result_filter == "PASS":
        results = [
            attempt for attempt in results
            if attempt.score is not None
            and attempt.score >= attempt.quiz.passing_marks
        ]

    elif result_filter == "FAIL":
        results = [
            attempt for attempt in results
            if attempt.score is not None
            and attempt.score < attempt.quiz.passing_marks
        ]

    if date_from_text:
        try:
            date_from = datetime.strptime(
                date_from_text,
                "%Y-%m-%d"
            ).date()

            results = [
                attempt for attempt in results
                if attempt.submitted_at
                and attempt.submitted_at.date() >= date_from
            ]
        except ValueError:
            pass

    if date_to_text:
        try:
            date_to = datetime.strptime(
                date_to_text,
                "%Y-%m-%d"
            ).date()

            results = [
                attempt for attempt in results
                if attempt.submitted_at
                and attempt.submitted_at.date() <= date_to
            ]
        except ValueError:
            pass

    results.reverse()

    return results


# =========================================================
# TEACHER RESULTS
# =========================================================

@teacher.route("/results")
@login_required
def results():

    if current_user.role != "teacher":
        return "Access Denied", 403

    results = get_teacher_filtered_results()

    total_results = len(results)
    passed_results = 0
    failed_results = 0
    total_percentage = 0

    for attempt in results:

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
            passed_results += 1
        else:
            failed_results += 1

    average_percentage = (
        total_percentage / total_results
        if total_results > 0
        else 0
    )

    # Only students who have attempted this teacher's quizzes.
    teacher_student_ids = {
        attempt.student_id
        for attempt in QuizAttempt.query.join(
            Quiz,
            QuizAttempt.quiz_id == Quiz.id
        ).filter(
            Quiz.created_by == current_user.id,
            QuizAttempt.status == "submitted"
        ).all()
    }

    students = User.query.filter(
        User.id.in_(teacher_student_ids)
    ).order_by(
        User.name.asc()
    ).all() if teacher_student_ids else []

    quizzes = Quiz.query.filter_by(
        created_by=current_user.id
    ).order_by(
        Quiz.title.asc()
    ).all()

    return render_template(
        "teacher/results.html",
        results=results,
        total_results=total_results,
        passed_results=passed_results,
        failed_results=failed_results,
        average_percentage=average_percentage,
        students=students,
        quizzes=quizzes
    )


# =========================================================
# TEACHER RESULTS - CSV
# =========================================================

@teacher.route("/results/export/csv")
@login_required
def export_results_csv():

    if current_user.role != "teacher":
        return "Access Denied", 403

    results = get_teacher_filtered_results()

    csv_data = (
        "Student,Email,Quiz,Attempt,Score,Total Marks,"
        "Percentage,Result,Submitted\n"
    )

    for attempt in results:

        percentage = (
            (attempt.score / attempt.quiz.total_marks) * 100
            if (
                attempt.score is not None
                and attempt.quiz.total_marks > 0
            )
            else 0
        )

        result = (
            "PASS"
            if (
                attempt.score is not None
                and attempt.score >= attempt.quiz.passing_marks
            )
            else "FAIL"
        )

        submitted = (
            attempt.submitted_at.strftime(
                "%d-%m-%Y %I:%M %p"
            )
            if attempt.submitted_at
            else ""
        )

        row = [
            attempt.student.name,
            attempt.student.email,
            attempt.quiz.title,
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
            "Content-Disposition":
                "attachment; filename=teacher_results.csv"
        }
    )


# =========================================================
# TEACHER RESULTS - EXCEL
# =========================================================

@teacher.route("/results/export/excel")
@login_required
def export_results_excel():

    if current_user.role != "teacher":
        return "Access Denied", 403

    import pandas as pd
    from io import BytesIO

    results = get_teacher_filtered_results()

    data = []

    for attempt in results:

        percentage = (
            (attempt.score / attempt.quiz.total_marks) * 100
            if (
                attempt.score is not None
                and attempt.quiz.total_marks > 0
            )
            else 0
        )

        result = (
            "PASS"
            if (
                attempt.score is not None
                and attempt.score >= attempt.quiz.passing_marks
            )
            else "FAIL"
        )

        submitted = (
            attempt.submitted_at.strftime(
                "%d-%m-%Y %I:%M %p"
            )
            if attempt.submitted_at
            else ""
        )

        data.append({
            "Student": attempt.student.name,
            "Email": attempt.student.email,
            "Quiz": attempt.quiz.title,
            "Attempt": attempt.display_attempt_number,
            "Score": attempt.score,
            "Total Marks": attempt.quiz.total_marks,
            "Percentage": round(percentage, 2),
            "Result": result,
            "Submitted": submitted
        })

    df = pd.DataFrame(data)
    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="Teacher Results"
        )

        worksheet = writer.sheets["Teacher Results"]

        for column_cells in worksheet.columns:

            max_length = 0
            column_letter = column_cells[0].column_letter

            for cell in column_cells:
                value = (
                    ""
                    if cell.value is None
                    else str(cell.value)
                )

                max_length = max(
                    max_length,
                    len(value)
                )

            worksheet.column_dimensions[
                column_letter
            ].width = min(
                max(max_length + 2, 12),
                35
            )

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="teacher_results.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )


# =========================================================
# TEACHER RESULTS - PDF
# =========================================================

@teacher.route("/results/export/pdf")
@login_required
def export_results_pdf():

    if current_user.role != "teacher":
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

    results = get_teacher_filtered_results()

    table_data = [[
        "Student",
        "Quiz",
        "Attempt",
        "Score",
        "Total",
        "%",
        "Result",
        "Submitted"
    ]]

    for attempt in results:

        percentage = (
            (attempt.score / attempt.quiz.total_marks) * 100
            if (
                attempt.score is not None
                and attempt.quiz.total_marks > 0
            )
            else 0
        )

        result = (
            "PASS"
            if (
                attempt.score is not None
                and attempt.score >= attempt.quiz.passing_marks
            )
            else "FAIL"
        )

        submitted = (
            attempt.submitted_at.strftime("%d-%m-%Y")
            if attempt.submitted_at
            else ""
        )

        table_data.append([
            attempt.student.name,
            attempt.quiz.title,
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
        Paragraph(
            "<b>Online Quiz Management System</b>",
            styles["Title"]
        ),
        Paragraph(
            "Teacher Quiz Results",
            styles["Heading2"]
        ),
        Spacer(1, 15)
    ]

    table = Table(
        table_data,
        repeatRows=1
    )

    table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#2563eb")
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "ALIGN",
                (2, 1),
                (6, -1),
                "CENTER"
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),
            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8
            ),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#f3f4f6")
                ]
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            )
        ])
    )

    elements.append(table)

    doc.build(elements)

    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="teacher_results.pdf",
        mimetype="application/pdf"
    )




# =========================================================
# ALLOW RETAKE
# =========================================================

@teacher.route(
    "/results/<int:attempt_id>/allow-retake",
    methods=["POST"]
)
@login_required
def allow_retake(attempt_id):

    if current_user.role != "teacher":
        return "Access Denied", 403

    # Find submitted attempt
    attempt = QuizAttempt.query.get(attempt_id)

    if not attempt:

        flash(
            "Quiz attempt not found.",
            "danger"
        )

        return redirect(
            url_for("teacher.results")
        )

    # Make sure quiz belongs to logged-in teacher
    quiz = Quiz.query.filter_by(
        id=attempt.quiz_id,
        created_by=current_user.id
    ).first()

    if not quiz:

        flash(
            "You do not have permission to manage this quiz.",
            "danger"
        )

        return redirect(
            url_for("teacher.results")
        )

    # Only completed attempts can receive retake permission
    if attempt.status != "submitted":

        flash(
            "Retake can only be allowed for a completed quiz.",
            "danger"
        )

        return redirect(
            url_for("teacher.results")
        )

    # Check for an unused permission
    existing_permission = QuizRetakePermission.query.filter_by(
        student_id=attempt.student_id,
        quiz_id=attempt.quiz_id,
        used=False
    ).first()

    if existing_permission:

        flash(
            "A retake permission is already available for this student.",
            "info"
        )

        return redirect(
            url_for("teacher.results")
        )

    # Get reason from teacher
    reason = request.form.get(
        "reason",
        ""
    ).strip()

    if not reason:
        reason = "Teacher-approved retake"

    # Create permission
    permission = QuizRetakePermission(
        student_id=attempt.student_id,
        quiz_id=attempt.quiz_id,
        teacher_id=current_user.id,
        reason=reason,
        used=False
    )

    db.session.add(permission)
    db.session.commit()

    flash(
        f"Retake permission granted to {attempt.student.name}.",
        "success"
    )

    return redirect(
        url_for("teacher.results")
    )


# =========================================================
# QUESTIONS
# =========================================================

@teacher.route("/quizzes/<int:quiz_id>/questions")
@login_required
def questions(quiz_id):

    if current_user.role != "teacher":
        return "Access Denied", 403

    quiz = Quiz.query.filter_by(
        id=quiz_id,
        created_by=current_user.id
    ).first()

    if not quiz:
        return "Quiz not found or access denied.", 404

    all_questions = Question.query.filter_by(
        quiz_id=quiz.id
    ).order_by(
        Question.question_order.asc()
    ).all()

    return render_template(
        "teacher/questions.html",
        quiz=quiz,
        questions=all_questions
    )


# =========================================================
# ADD QUESTION
# =========================================================

@teacher.route(
    "/quizzes/<int:quiz_id>/questions/add",
    methods=["GET", "POST"]
)
@login_required
def add_question(quiz_id):

    if current_user.role != "teacher":
        return "Access Denied", 403

    quiz = Quiz.query.filter_by(
        id=quiz_id,
        created_by=current_user.id
    ).first()

    if not quiz:
        return "Quiz not found or access denied.", 404

    if request.method == "POST":

        question_text = request.form.get(
            "question_text",
            ""
        ).strip()

        marks = request.form.get(
            "marks",
            ""
        ).strip()

        negative_marks = request.form.get(
            "negative_marks",
            "0"
        ).strip()

        option1 = request.form.get(
            "option1",
            ""
        ).strip()

        option2 = request.form.get(
            "option2",
            ""
        ).strip()

        option3 = request.form.get(
            "option3",
            ""
        ).strip()

        option4 = request.form.get(
            "option4",
            ""
        ).strip()

        correct_option = request.form.get(
            "correct_option",
            ""
        ).strip()

        if not question_text:

            flash(
                "Question text is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.add_question",
                    quiz_id=quiz.id
                )
            )

        if not marks:

            flash(
                "Marks are required.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.add_question",
                    quiz_id=quiz.id
                )
            )

        if not option1 or not option2 or not option3 or not option4:

            flash(
                "All four options are required.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.add_question",
                    quiz_id=quiz.id
                )
            )

        if correct_option not in ["1", "2", "3", "4"]:

            flash(
                "Please select the correct answer.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.add_question",
                    quiz_id=quiz.id
                )
            )

        try:

            marks = int(marks)
            negative_marks = int(
                negative_marks or 0
            )

        except ValueError:

            flash(
                "Marks must be valid numbers.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.add_question",
                    quiz_id=quiz.id
                )
            )

        if marks <= 0:

            flash(
                "Marks must be greater than 0.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.add_question",
                    quiz_id=quiz.id
                )
            )

        if negative_marks < 0:

            flash(
                "Negative marks cannot be negative.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.add_question",
                    quiz_id=quiz.id
                )
            )

        existing_questions = Question.query.filter_by(
            quiz_id=quiz.id
        ).count()

        question = Question(
            quiz_id=quiz.id,
            question_text=question_text,
            marks=marks,
            negative_marks=negative_marks,
            question_order=existing_questions + 1
        )

        db.session.add(question)
        db.session.flush()

        options = [
            (option1, correct_option == "1"),
            (option2, correct_option == "2"),
            (option3, correct_option == "3"),
            (option4, correct_option == "4")
        ]

        for option_text, is_correct in options:

            option = Option(
                question_id=question.id,
                option_text=option_text,
                is_correct=is_correct
            )

            db.session.add(option)

        db.session.commit()

        flash(
            "Question added successfully.",
            "success"
        )

        return redirect(
            url_for(
                "teacher.questions",
                quiz_id=quiz.id
            )
        )

    return render_template(
        "teacher/add_question.html",
        quiz=quiz
    )


# =========================================================
# EDIT QUESTION
# =========================================================

@teacher.route(
    "/quizzes/<int:quiz_id>/questions/<int:question_id>/edit",
    methods=["GET", "POST"]
)
@login_required
def edit_question(quiz_id, question_id):

    if current_user.role != "teacher":
        return "Access Denied", 403
            # Prevent editing questions after students have attempted the quiz
    attempt_exists = QuizAttempt.query.filter_by(
        quiz_id=quiz_id
    ).first()

    if attempt_exists:
        flash(
            "This question cannot be edited because a student has already attempted this quiz.",
            "danger"
        )

        return redirect(
            url_for(
                "teacher.questions",
                quiz_id=quiz_id
            )
        )

    quiz = Quiz.query.filter_by(
        id=quiz_id,
        created_by=current_user.id
    ).first()

    if not quiz:
        return "Quiz not found or access denied.", 404

    question = Question.query.filter_by(
        id=question_id,
        quiz_id=quiz.id
    ).first()

    if not question:
        return "Question not found.", 404

    if request.method == "POST":

        question_text = request.form.get(
            "question_text",
            ""
        ).strip()

        marks = request.form.get(
            "marks",
            ""
        ).strip()

        negative_marks = request.form.get(
            "negative_marks",
            "0"
        ).strip()

        option1 = request.form.get(
            "option1",
            ""
        ).strip()

        option2 = request.form.get(
            "option2",
            ""
        ).strip()

        option3 = request.form.get(
            "option3",
            ""
        ).strip()

        option4 = request.form.get(
            "option4",
            ""
        ).strip()

        correct_option = request.form.get(
            "correct_option",
            ""
        ).strip()

        if not question_text:

            flash(
                "Question text is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.edit_question",
                    quiz_id=quiz.id,
                    question_id=question.id
                )
            )

        if not marks:

            flash(
                "Marks are required.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.edit_question",
                    quiz_id=quiz.id,
                    question_id=question.id
                )
            )

        if not option1 or not option2 or not option3 or not option4:

            flash(
                "All four options are required.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.edit_question",
                    quiz_id=quiz.id,
                    question_id=question.id
                )
            )

        if correct_option not in ["1", "2", "3", "4"]:

            flash(
                "Please select the correct answer.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.edit_question",
                    quiz_id=quiz.id,
                    question_id=question.id
                )
            )

        try:

            marks = int(marks)
            negative_marks = int(
                negative_marks or 0
            )

        except ValueError:

            flash(
                "Marks must be valid numbers.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.edit_question",
                    quiz_id=quiz.id,
                    question_id=question.id
                )
            )

        if marks <= 0:

            flash(
                "Marks must be greater than 0.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.edit_question",
                    quiz_id=quiz.id,
                    question_id=question.id
                )
            )

        if negative_marks < 0:

            flash(
                "Negative marks cannot be negative.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.edit_question",
                    quiz_id=quiz.id,
                    question_id=question.id
                )
            )

        question.question_text = question_text
        question.marks = marks
        question.negative_marks = negative_marks

        options = [
            option1,
            option2,
            option3,
            option4
        ]

        existing_options = Option.query.filter_by(
            question_id=question.id
        ).order_by(
            Option.id.asc()
        ).all()

        for index, option in enumerate(existing_options):

            option.option_text = options[index]

            option.is_correct = (
                correct_option == str(index + 1)
            )

        db.session.commit()

        flash(
            "Question updated successfully.",
            "success"
        )

        return redirect(
            url_for(
                "teacher.questions",
                quiz_id=quiz.id
            )
        )

    existing_options = Option.query.filter_by(
        question_id=question.id
    ).order_by(
        Option.id.asc()
    ).all()

    return render_template(
        "teacher/edit_question.html",
        quiz=quiz,
        question=question,
        options=existing_options
    )


# =========================================================
# DELETE QUESTION
# =========================================================

@teacher.route(
    "/quizzes/<int:quiz_id>/questions/<int:question_id>/delete",
    methods=["POST"]
)
@login_required
def delete_question(quiz_id, question_id):

    if current_user.role != "teacher":
        return "Access Denied", 403
            # Prevent deleting questions after students have attempted the quiz
    attempt_exists = QuizAttempt.query.filter_by(
        quiz_id=quiz_id
    ).first()

    if attempt_exists:
        flash(
            "This question cannot be deleted because a student has already attempted this quiz.",
            "danger"
        )

        return redirect(
            url_for(
                "teacher.questions",
                quiz_id=quiz_id
            )
        )

    quiz = Quiz.query.filter_by(
        id=quiz_id,
        created_by=current_user.id
    ).first()

    if not quiz:
        return "Quiz not found or access denied.", 404

    question = Question.query.filter_by(
        id=question_id,
        quiz_id=quiz.id
    ).first()

    if not question:

        flash(
            "Question not found.",
            "danger"
        )

        return redirect(
            url_for(
                "teacher.questions",
                quiz_id=quiz.id
            )
        )

    db.session.delete(question)
    db.session.commit()

    flash(
        "Question deleted successfully.",
        "success"
    )

    return redirect(
        url_for(
            "teacher.questions",
            quiz_id=quiz.id
        )
    )

# =========================================================
# DUPLICATE QUIZ
# =========================================================

@teacher.route(
    "/quizzes/<int:quiz_id>/duplicate",
    methods=["POST"]
)
@login_required
def duplicate_quiz(quiz_id):

    if current_user.role != "teacher":
        return "Access Denied", 403

    # Find the original quiz
    original_quiz = Quiz.query.filter_by(
        id=quiz_id,
        created_by=current_user.id
    ).first()

    if not original_quiz:
        flash(
            "Quiz not found or access denied.",
            "danger"
        )

        return redirect(
            url_for("teacher.quizzes")
        )

    # Create copied quiz
    copied_quiz = Quiz(
        title=f"{original_quiz.title} (Copy)",
        description=original_quiz.description,
        duration=original_quiz.duration,
        number_of_questions=original_quiz.number_of_questions,
        total_marks=original_quiz.total_marks,
        passing_marks=original_quiz.passing_marks,
        status="draft",
        created_by=current_user.id
    )

    db.session.add(copied_quiz)
    db.session.flush()

    # Copy all questions
    original_questions = Question.query.filter_by(
        quiz_id=original_quiz.id
    ).order_by(
        Question.question_order.asc()
    ).all()

    for original_question in original_questions:

        copied_question = Question(
            quiz_id=copied_quiz.id,
            question_text=original_question.question_text,
            marks=original_question.marks,
            negative_marks=original_question.negative_marks,
            question_order=original_question.question_order
        )

        db.session.add(copied_question)
        db.session.flush()

        # Copy all options
        original_options = Option.query.filter_by(
            question_id=original_question.id
        ).order_by(
            Option.id.asc()
        ).all()

        for original_option in original_options:

            copied_option = Option(
                question_id=copied_question.id,
                option_text=original_option.option_text,
                is_correct=original_option.is_correct
            )

            db.session.add(copied_option)

    db.session.commit()

    flash(
        "Quiz duplicated successfully. The copied quiz is saved as a draft.",
        "success"
    )

    return redirect(
        url_for("teacher.quizzes")
    )

# =========================================================
# DELETE QUIZ
# =========================================================

@teacher.route(
    "/quizzes/<int:quiz_id>/delete",
    methods=["POST"]
)
@login_required
def delete_quiz(quiz_id):

    if current_user.role != "teacher":
        return "Access Denied", 403

    # Find quiz belonging to this teacher
    quiz = Quiz.query.filter_by(
        id=quiz_id,
        created_by=current_user.id
    ).first()

    if not quiz:
        return "Quiz not found or access denied.", 404

    # Do not allow deletion if students have attempted it
    attempt_exists = QuizAttempt.query.filter_by(
        quiz_id=quiz.id
    ).first()

    if attempt_exists:
        flash(
            "This quiz cannot be deleted because a student has already attempted it.",
            "danger"
        )

        return redirect(
            url_for("teacher.quizzes")
        )

    # Delete quiz
    db.session.delete(quiz)
    db.session.commit()

    flash(
        "Quiz deleted successfully.",
        "success"
    )

    return redirect(
        url_for("teacher.quizzes")
    )

# =========================================================
# CREATE QUIZ
# =========================================================

@teacher.route(
    "/quizzes/create",
    methods=["GET", "POST"]
)
@login_required
def create_quiz():

    if current_user.role != "teacher":
        return "Access Denied", 403

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        duration = request.form.get(
            "duration",
            ""
        ).strip()

        number_of_questions = request.form.get(
            "number_of_questions",
            ""
        ).strip()

        total_marks = request.form.get(
            "total_marks",
            ""
        ).strip()

        passing_marks = request.form.get(
            "passing_marks",
            ""
        ).strip()

        # Required field validation
        if (
            not title
            or not duration
            or not number_of_questions
            or not total_marks
            or not passing_marks
        ):

            flash(
                "Please fill in all required fields.",
                "danger"
            )

            return redirect(
                url_for("teacher.create_quiz")
            )

        # Convert numeric values
        try:

            duration = int(duration)
            number_of_questions = int(
                number_of_questions
            )
            total_marks = int(total_marks)
            passing_marks = int(passing_marks)

        except ValueError:

            flash(
                "Duration, number of questions and marks must be valid numbers.",
                "danger"
            )

            return redirect(
                url_for("teacher.create_quiz")
            )

        # Duration validation
        if duration <= 0:

            flash(
                "Duration must be greater than 0.",
                "danger"
            )

            return redirect(
                url_for("teacher.create_quiz")
            )

        # Number of questions validation
        if number_of_questions <= 0:

            flash(
                "Number of questions must be greater than 0.",
                "danger"
            )

            return redirect(
                url_for("teacher.create_quiz")
            )

        if number_of_questions > 200:

            flash(
                "Number of questions cannot be greater than 200.",
                "danger"
            )

            return redirect(
                url_for("teacher.create_quiz")
            )

        # Total marks validation
        if total_marks <= 0:

            flash(
                "Total marks must be greater than 0.",
                "danger"
            )

            return redirect(
                url_for("teacher.create_quiz")
            )

        # Passing marks validation
        if passing_marks < 0 or passing_marks > total_marks:

            flash(
                "Passing marks must be between 0 and total marks.",
                "danger"
            )

            return redirect(
                url_for("teacher.create_quiz")
            )

        # Create quiz
        quiz = Quiz(
            title=title,
            description=description,
            duration=duration,
            number_of_questions=number_of_questions,
            total_marks=total_marks,
            passing_marks=passing_marks,
            status="draft",
            created_by=current_user.id
        )

        db.session.add(quiz)
        db.session.commit()

        flash(
            "Quiz created successfully.",
            "success"
        )

        return redirect(
            url_for("teacher.quizzes")
        )

    return render_template(
        "teacher/create_quiz.html"
    )


# =========================================================
# EDIT QUIZ
# =========================================================

@teacher.route(
    "/quizzes/<int:quiz_id>/edit",
    methods=["GET", "POST"]
)
@login_required
def edit_quiz(quiz_id):

    if current_user.role != "teacher":
        return "Access Denied", 403

    quiz = Quiz.query.filter_by(
        id=quiz_id,
        created_by=current_user.id
    ).first()

    if not quiz:
        return "Quiz not found or access denied.", 404

    attempt_exists = QuizAttempt.query.filter_by(
        quiz_id=quiz.id
    ).first()

    if attempt_exists:

        flash(
            "This quiz cannot be edited because a student has already attempted it.",
            "danger"
        )

        return redirect(
            url_for("teacher.quizzes")
        )

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        duration = request.form.get(
            "duration",
            ""
        ).strip()

        total_marks = request.form.get(
            "total_marks",
            ""
        ).strip()

        passing_marks = request.form.get(
            "passing_marks",
            ""
        ).strip()

        if (
            not title
            or not duration
            or not total_marks
            or not passing_marks
        ):

            flash(
                "All required fields must be filled.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.edit_quiz",
                    quiz_id=quiz.id
                )
            )

        try:

            duration = int(duration)
            total_marks = int(total_marks)
            passing_marks = int(passing_marks)

        except ValueError:

            flash(
                "Duration and marks must be valid numbers.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.edit_quiz",
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
                    "teacher.edit_quiz",
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
                    "teacher.edit_quiz",
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
                    "teacher.edit_quiz",
                    quiz_id=quiz.id
                )
            )

        quiz.title = title
        quiz.description = description
        quiz.duration = duration
        quiz.total_marks = total_marks
        quiz.passing_marks = passing_marks

        db.session.commit()

        flash(
            "Quiz updated successfully.",
            "success"
        )

        return redirect(
            url_for("teacher.quizzes")
        )

    return render_template(
        "teacher/edit_quiz.html",
        quiz=quiz
    )


# =========================================================
# PUBLISH QUIZ
# =========================================================


@teacher.route(
    "/quizzes/<int:quiz_id>/publish",
    methods=["POST"]
)
@login_required
def publish_quiz(quiz_id):

    if current_user.role != "teacher":
        return "Access Denied", 403

    quiz = Quiz.query.filter_by(
        id=quiz_id,
        created_by=current_user.id
    ).first()

    if not quiz:
        return "Quiz not found or access denied.", 404

    if quiz.status == "published":
        flash(
            "This quiz is already published.",
            "info"
        )
        return redirect(
            url_for(
                "teacher.questions",
                quiz_id=quiz.id
            )
        )

    # Publish the quiz
    quiz.status = "published"
    db.session.commit()

    flash("Quiz published successfully!", "success")

    return redirect(
        url_for("teacher.questions", quiz_id=quiz.id)
    )



    if current_user.role != "teacher":
        return "Access Denied", 403

    quiz = Quiz.query.filter_by(
        id=quiz_id,
        created_by=current_user.id
    ).first()

    if not quiz:
        return "Quiz not found or access denied.", 404

    if quiz.status == "published":

        flash(
            "This quiz is already published.",
            "info"
        )

        return redirect(
            url_for(
                "teacher.questions",
                quiz_id=quiz.id
            )
        )
        # =========================================================
# UNPUBLISH QUIZ
# =========================================================

@teacher.route(
    "/quizzes/<int:quiz_id>/unpublish",
    methods=["POST"]
)
@login_required
def unpublish_quiz(quiz_id):

    if current_user.role != "teacher":
        return "Access Denied", 403

    quiz = Quiz.query.filter_by(
        id=quiz_id,
        created_by=current_user.id
    ).first()

    if not quiz:
        return "Quiz not found or access denied.", 404

    # ---------------------------------------------------------
    # CHECK IF STUDENTS HAVE ATTEMPTED THE QUIZ
    # ---------------------------------------------------------

    attempt_exists = QuizAttempt.query.filter_by(
        quiz_id=quiz.id
    ).first()

    if attempt_exists:

        flash(
            "This quiz cannot be unpublished because students have already attempted it.",
            "danger"
        )

        return redirect(
            url_for("teacher.quizzes")
        )

    # ---------------------------------------------------------
    # UNPUBLISH
    # ---------------------------------------------------------

    quiz.status = "draft"

    db.session.commit()

    flash(
        "Quiz unpublished successfully.",
        "success"
    )

    return redirect(
        url_for("teacher.quizzes")
    )

    # Get all questions
    questions = Question.query.filter_by(
        quiz_id=quiz.id
    ).order_by(
        Question.question_order.asc()
    ).all()

    question_count = len(questions)

    # =====================================================
    # CHECK NUMBER OF QUESTIONS
    # =====================================================

    if question_count < quiz.number_of_questions:

        remaining = (
            quiz.number_of_questions
            - question_count
        )

        flash(
            f"You selected {quiz.number_of_questions} questions, "
            f"but only {question_count} questions have been added. "
            f"Please add {remaining} more question"
            f"{'s' if remaining != 1 else ''} before publishing.",
            "danger"
        )

        return redirect(
            url_for(
                "teacher.questions",
                quiz_id=quiz.id
            )
        )

    if question_count > quiz.number_of_questions:

        extra = (
            question_count
            - quiz.number_of_questions
        )

        flash(
            f"You selected {quiz.number_of_questions} questions, "
            f"but {question_count} questions have been added. "
            f"Please remove {extra} question"
            f"{'s' if extra != 1 else ''} before publishing.",
            "danger"
        )

        return redirect(
            url_for(
                "teacher.questions",
                quiz_id=quiz.id
            )
        )

    # =====================================================
    # CHECK QUESTIONS EXIST
    # =====================================================

    if not questions:

        flash(
            "You must add at least one question before publishing.",
            "danger"
        )

        return redirect(
            url_for(
                "teacher.questions",
                quiz_id=quiz.id
            )
        )

    # =====================================================
    # CHECK QUESTION COMPLETENESS
    # =====================================================

    for index, question in enumerate(
        questions,
        start=1
    ):

        if not question.question_text.strip():

            flash(
                f"Question {index} is incomplete. "
                f"Question text is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.questions",
                    quiz_id=quiz.id
                )
            )

        if question.marks is None or question.marks <= 0:

            flash(
                f"Question {index} has invalid marks.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.questions",
                    quiz_id=quiz.id
                )
            )

        # Get options
        options = Option.query.filter_by(
            question_id=question.id
        ).all()

        # Exactly 4 options
        if len(options) != 4:

            flash(
                f"Question {index} must have exactly 4 options. "
                f"Currently it has {len(options)}.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.questions",
                    quiz_id=quiz.id
                )
            )

        # Every option must have text
        for option in options:

            if not option.option_text.strip():

                flash(
                    f"Question {index} has an empty option. "
                    f"Please complete all four options.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "teacher.questions",
                        quiz_id=quiz.id
                    )
                )

        # Exactly one correct answer
        correct_options = [
            option
            for option in options
            if option.is_correct
        ]

        if len(correct_options) != 1:

            flash(
                f"Question {index} must have exactly one correct answer.",
                "danger"
            )

            return redirect(
                url_for(
                    "teacher.questions",
                    quiz_id=quiz.id
                )
            )

    # =====================================================
    # CHECK TOTAL MARKS
    # =====================================================

    question_marks = sum(
        question.marks
        for question in questions
    )

    if question_marks != quiz.total_marks:

        flash(
            f"Question marks total {question_marks}, "
            f"but quiz total marks are {quiz.total_marks}. "
            f"Please add or edit questions before publishing.",
            "danger"
        )

        return redirect(
            url_for(
                "teacher.questions",
                quiz_id=quiz.id
            )
        )

    # =====================================================
    # CHECK PASSING MARKS
    # =====================================================

    if quiz.passing_marks > quiz.total_marks:

        flash(
            "Passing marks cannot be greater than total marks.",
            "danger"
        )

        return redirect(
            url_for(
                "teacher.questions",
                quiz_id=quiz.id
            )
        )

    # =====================================================
    # PUBLISH QUIZ
    # =====================================================

    quiz.status = "published"

    db.session.commit()

    flash(
        "Quiz published successfully.",
        "success"
    )

    return redirect(
        url_for(
            "teacher.questions",
            quiz_id=quiz.id
        )
    )