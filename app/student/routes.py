from datetime import datetime

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import login_required, current_user

from app.student import student
from app.extensions import db
from app.models import (
    Quiz,
    Question,
    Option,
    QuizAttempt,
    QuizAnswer,
    QuizRetakePermission
)


# =========================================================
# STUDENT DASHBOARD
# =========================================================

@student.route("/dashboard")
@login_required
def dashboard():

    if current_user.role != "student":
        return "Access Denied", 403

    # All published quizzes
    quizzes = Quiz.query.filter_by(
        status="published"
    ).order_by(
        Quiz.id.desc()
    ).all()

    
    # All submitted attempts of this student
    attempts = QuizAttempt.query.filter_by(
        student_id=current_user.id,
        status="submitted"
    ).order_by(
        QuizAttempt.submitted_at.desc()
    ).all()

    # -----------------------------------------------------
    # STUDENT ANALYTICS
    # -----------------------------------------------------

    total_attempts = len(attempts)

    passed_attempts = sum(
        1 for attempt in attempts
        if attempt.quiz
        and attempt.score is not None
        and attempt.score >= attempt.quiz.passing_marks
    )

    failed_attempts = total_attempts - passed_attempts

    percentages = [
        (attempt.score / attempt.quiz.total_marks) * 100
        for attempt in attempts
        if attempt.quiz
        and attempt.score is not None
        and attempt.quiz.total_marks > 0
    ]

    average_percentage = (
        sum(percentages) / len(percentages)
        if percentages else 0
    )

    pass_rate = (
        (passed_attempts / total_attempts) * 100
        if total_attempts else 0
    )

    recent_attempts = sorted(
        attempts,
        key=lambda attempt: attempt.submitted_at or attempt.started_at
    )[-10:]

    performance_labels = [
        attempt.quiz.title if attempt.quiz else "Quiz"
        for attempt in recent_attempts
    ]

    performance_percentages = [
        round(
            (attempt.score / attempt.quiz.total_marks) * 100,
            2
        )
        if attempt.quiz
        and attempt.score is not None
        and attempt.quiz.total_marks > 0
        else 0
        for attempt in recent_attempts
    ]

    # -----------------------------------------------------
    # Create attempt number for each quiz
    # -----------------------------------------------------

    attempt_numbers = {}

    # -----------------------------------------------------
    # Create attempt number for each quiz
    # -----------------------------------------------------

    attempt_numbers = {}

    for attempt in sorted(
        attempts,
        key=lambda x: (
            x.quiz_id,
            x.started_at
        )
    ):

        if attempt.quiz_id not in attempt_numbers:
            attempt_numbers[attempt.quiz_id] = 0

        attempt_numbers[attempt.quiz_id] += 1

        attempt.display_attempt_number = (
            attempt_numbers[attempt.quiz_id]
        )

    # -----------------------------------------------------
    # Check in-progress attempts
    # -----------------------------------------------------

    in_progress_attempts = QuizAttempt.query.filter_by(
        student_id=current_user.id,
        status="in_progress"
    ).all()

    in_progress_map = {
        attempt.quiz_id: attempt
        for attempt in in_progress_attempts
    }

    # -----------------------------------------------------
    # Check unused retake permissions
    # -----------------------------------------------------

    permissions = QuizRetakePermission.query.filter_by(
        student_id=current_user.id,
        used=False
    ).all()

    permission_map = {
        permission.quiz_id: permission
        for permission in permissions
    }

    # -----------------------------------------------------
    # Latest submitted attempt for each quiz
    # -----------------------------------------------------

    latest_attempt_map = {}

    for attempt in attempts:

        if attempt.quiz_id not in latest_attempt_map:

            latest_attempt_map[attempt.quiz_id] = attempt

    return render_template(
        "student/dashboard.html",
        quizzes=quizzes,
        attempts=attempts,
        in_progress_map=in_progress_map,
        permission_map=permission_map,
        latest_attempt_map=latest_attempt_map,
        total_attempts=total_attempts,
        passed_attempts=passed_attempts,
        failed_attempts=failed_attempts,
        average_percentage=average_percentage,
        pass_rate=pass_rate,
        performance_labels=performance_labels,
        performance_percentages=performance_percentages
    )


# =========================================================
# START QUIZ
# =========================================================

@student.route("/quiz/<int:quiz_id>/start")
@login_required
def start_quiz(quiz_id):

    if current_user.role != "student":
        return "Access Denied", 403

    quiz = Quiz.query.filter_by(
        id=quiz_id,
        status="published"
    ).first()

    if not quiz:

        flash(
            "Quiz not found or is not published.",
            "danger"
        )

        return redirect(
            url_for("student.dashboard")
        )

    # -----------------------------------------------------
    # Check if student already has an active attempt
    # -----------------------------------------------------

    active_attempt = QuizAttempt.query.filter_by(
        student_id=current_user.id,
        quiz_id=quiz.id,
        status="in_progress"
    ).first()

    if active_attempt:

        return redirect(
            url_for(
                "student.quiz_instructions",
                attempt_id=active_attempt.id
            )
        )

    # -----------------------------------------------------
    # Check previous submitted attempt
    # -----------------------------------------------------

    previous_attempt = QuizAttempt.query.filter_by(
        student_id=current_user.id,
        quiz_id=quiz.id,
        status="submitted"
    ).order_by(
        QuizAttempt.submitted_at.desc()
    ).first()

    # -----------------------------------------------------
    # If already attempted, check retake permission
    # -----------------------------------------------------

    if previous_attempt:

        permission = QuizRetakePermission.query.filter_by(
            student_id=current_user.id,
            quiz_id=quiz.id,
            used=False
        ).order_by(
            QuizRetakePermission.created_at.desc()
        ).first()

        if not permission:

            flash(
                "You have already completed this quiz. "
                "A teacher must grant a retake permission.",
                "info"
            )

            return redirect(
                url_for(
                    "student.quiz_result",
                    attempt_id=previous_attempt.id
                )
            )

        # -------------------------------------------------
        # Create retake attempt
        # -------------------------------------------------

        new_attempt = QuizAttempt(
            student_id=current_user.id,
            quiz_id=quiz.id,
            started_at=datetime.utcnow(),
            status="in_progress"
        )

        db.session.add(new_attempt)

        # Mark permission as used
        permission.used = True

        db.session.commit()

        return redirect(
            url_for(
                "student.quiz_instructions",
                attempt_id=new_attempt.id
            )
        )

    # -----------------------------------------------------
    # First attempt
    # -----------------------------------------------------

    attempt = QuizAttempt(
        student_id=current_user.id,
        quiz_id=quiz.id,
        started_at=datetime.utcnow(),
        status="in_progress"
    )

    db.session.add(attempt)
    db.session.commit()

    return redirect(
        url_for(
            "student.quiz_instructions",
            attempt_id=attempt.id
        )
    )


# =========================================================
# QUIZ INSTRUCTIONS
# =========================================================

@student.route(
    "/quiz/<int:attempt_id>/instructions"
)
@login_required
def quiz_instructions(attempt_id):

    if current_user.role != "student":
        return "Access Denied", 403

    attempt = QuizAttempt.query.filter_by(
        id=attempt_id,
        student_id=current_user.id
    ).first()

    if not attempt:
        return "Quiz attempt not found.", 404

    quiz = Quiz.query.get(attempt.quiz_id)

    if not quiz:
        return "Quiz not found.", 404

    return render_template(
        "student/quiz_instructions.html",
        quiz=quiz,
        attempt=attempt
    )


# =========================================================
# TAKE QUIZ
# =========================================================

@student.route(
    "/quiz/<int:attempt_id>/take",
    methods=["GET", "POST"]
)
@login_required
def take_quiz(attempt_id):

    if current_user.role != "student":
        return "Access Denied", 403

    attempt = QuizAttempt.query.filter_by(
        id=attempt_id,
        student_id=current_user.id
    ).first()

    if not attempt:
        return "Quiz attempt not found.", 404

    quiz = Quiz.query.get(attempt.quiz_id)

    if not quiz:
        return "Quiz not found.", 404

    # -----------------------------------------------------
    # Already submitted
    # -----------------------------------------------------

    if attempt.status == "submitted":

        return redirect(
            url_for(
                "student.quiz_result",
                attempt_id=attempt.id
            )
        )

    # -----------------------------------------------------
    # Questions
    # -----------------------------------------------------

    questions = Question.query.filter_by(
        quiz_id=quiz.id
    ).order_by(
        Question.question_order.asc()
    ).all()

    # -----------------------------------------------------
    # Server-side timer
    # -----------------------------------------------------

    elapsed_seconds = (
        datetime.utcnow() - attempt.started_at
    ).total_seconds()

    total_seconds = quiz.duration * 60

    remaining_seconds = max(
        0,
        int(total_seconds - elapsed_seconds)
    )

    # -----------------------------------------------------
    # Submit quiz
    # -----------------------------------------------------

    if request.method == "POST":

        # Prevent duplicate submission
        if attempt.status == "submitted":

            return redirect(
                url_for(
                    "student.quiz_result",
                    attempt_id=attempt.id
                )
            )

        # Check time
        elapsed_seconds = (
            datetime.utcnow() - attempt.started_at
        ).total_seconds()

        # -------------------------------------------------
        # Evaluate answers
        # -------------------------------------------------

        total_score = 0

        for question in questions:

            selected_option_id = request.form.get(
                f"question_{question.id}"
            )

            selected_option = None

            if selected_option_id:

                selected_option = Option.query.filter_by(
                    id=int(selected_option_id),
                    question_id=question.id
                ).first()

            is_correct = False
            marks_obtained = 0

            if selected_option:

                if selected_option.is_correct:

                    is_correct = True
                    marks_obtained = question.marks

                else:

                    marks_obtained = -question.negative_marks

            # Save answer
            answer = QuizAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                selected_option_id=(
                    selected_option.id
                    if selected_option
                    else None
                ),
                is_correct=is_correct,
                marks_obtained=marks_obtained
            )

            db.session.add(answer)

            total_score += marks_obtained

        # -------------------------------------------------
        # Prevent negative final score
        # -------------------------------------------------

        if total_score < 0:
            total_score = 0

        # -------------------------------------------------
        # Submit attempt
        # -------------------------------------------------

        attempt.score = total_score
        attempt.submitted_at = datetime.utcnow()
        attempt.status = "submitted"

        db.session.commit()

        flash(
            "Quiz submitted successfully.",
            "success"
        )

        return redirect(
            url_for(
                "student.quiz_result",
                attempt_id=attempt.id
            )
        )

    return render_template(
        "student/take_quiz.html",
        quiz=quiz,
        questions=questions,
        attempt=attempt,
        remaining_seconds=remaining_seconds
    )


# =========================================================
# QUIZ RESULT
# =========================================================

@student.route(
    "/quiz/result/<int:attempt_id>"
)
@login_required
def quiz_result(attempt_id):

    if current_user.role != "student":
        return "Access Denied", 403

    # -----------------------------------------------------
    # Find exact attempt
    # -----------------------------------------------------

    attempt = QuizAttempt.query.filter_by(
        id=attempt_id,
        student_id=current_user.id,
        status="submitted"
    ).first()

    if not attempt:
        return "Result not found.", 404

    quiz = Quiz.query.get(attempt.quiz_id)

    if not quiz:
        return "Quiz not found.", 404

    # -----------------------------------------------------
    # Answers for this exact attempt
    # -----------------------------------------------------

    answers = QuizAnswer.query.filter_by(
        attempt_id=attempt.id
    ).all()

    total_questions = len(
        Question.query.filter_by(
            quiz_id=quiz.id
        ).all()
    )

    correct_answers = sum(
        1
        for answer in answers
        if answer.is_correct
    )

    wrong_answers = sum(
        1
        for answer in answers
        if answer.selected_option_id
        and not answer.is_correct
    )

    unanswered = (
        total_questions
        - len(answers)
    )

    if quiz.total_marks > 0:

        percentage = (
            attempt.score
            / quiz.total_marks
        ) * 100

    else:

        percentage = 0

    passed = (
        attempt.score >= quiz.passing_marks
    )

    # -----------------------------------------------------
    # Attempt number
    # -----------------------------------------------------

    previous_attempts = QuizAttempt.query.filter(
        QuizAttempt.student_id == current_user.id,
        QuizAttempt.quiz_id == quiz.id,
        QuizAttempt.status == "submitted",
        QuizAttempt.id <= attempt.id
    ).count()

    attempt_number = previous_attempts

    # -----------------------------------------------------
    # All attempts for this quiz
    # -----------------------------------------------------

    all_attempts = QuizAttempt.query.filter_by(
        student_id=current_user.id,
        quiz_id=quiz.id,
        status="submitted"
    ).order_by(
        QuizAttempt.submitted_at.asc()
    ).all()

    return render_template(
        "student/quiz_result.html",
        quiz=quiz,
        attempt=attempt,
        answers=answers,
        total_questions=total_questions,
        correct_answers=correct_answers,
        wrong_answers=wrong_answers,
        unanswered=unanswered,
        percentage=percentage,
        passed=passed,
        attempt_number=attempt_number,
        all_attempts=all_attempts
    )