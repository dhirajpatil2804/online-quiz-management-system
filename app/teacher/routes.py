from flask import render_template, request, redirect, url_for, flash

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


# =========================================================
# TEACHER DASHBOARD
# =========================================================

@teacher.route("/dashboard")
@login_required
def dashboard():

    if current_user.role != "teacher":
        return "Access Denied", 403

    total_quizzes = Quiz.query.filter_by(
        created_by=current_user.id
    ).count()

    total_questions = Question.query.join(
        Quiz,
        Question.quiz_id == Quiz.id
    ).filter(
        Quiz.created_by == current_user.id
    ).count()

    total_students = User.query.filter_by(
        role="student"
    ).count()

    total_results = QuizAttempt.query.join(
        Quiz,
        QuizAttempt.quiz_id == Quiz.id
    ).filter(
        Quiz.created_by == current_user.id,
        QuizAttempt.status == "submitted"
    ).count()

    return render_template(
        "teacher/dashboard.html",
        user=current_user,
        total_quizzes=total_quizzes,
        total_questions=total_questions,
        total_students=total_students,
        total_results=total_results
    )


# =========================================================
# MANAGE QUIZZES
# =========================================================

@teacher.route("/quizzes")
@login_required
def quizzes():

    if current_user.role != "teacher":
        return "Access Denied", 403

    all_quizzes = Quiz.query.filter_by(
        created_by=current_user.id
    ).order_by(
        Quiz.id.desc()
    ).all()

    return render_template(
        "teacher/quizzes.html",
        quizzes=all_quizzes
    )


# =========================================================
# TEACHER RESULTS
# =========================================================

@teacher.route("/results")
@login_required
def results():

    if current_user.role != "teacher":
        return "Access Denied", 403

    results = QuizAttempt.query.join(
        Quiz,
        QuizAttempt.quiz_id == Quiz.id
    ).filter(
        Quiz.created_by == current_user.id,
        QuizAttempt.status == "submitted"
    ).order_by(
        QuizAttempt.submitted_at.desc()
    ).all()

    return render_template(
        "teacher/results.html",
        results=results
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