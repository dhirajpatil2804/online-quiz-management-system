from datetime import datetime

from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    request
)

from flask_login import login_required, current_user

from app.student import student
from app.extensions import db
from app.models import (
    Quiz,
    QuizAttempt,
    QuizAnswer,
    Question,
    Option
)


@student.route("/dashboard")
@login_required
def dashboard():

    if current_user.role != "student":
        return "Access Denied", 403

    published_quizzes = Quiz.query.filter_by(
        status="published"
    ).order_by(
        Quiz.id.desc()
    ).all()

    return render_template(
        "student/dashboard.html",
        user=current_user,
        quizzes=published_quizzes
    )


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

    existing_attempt = QuizAttempt.query.filter_by(
        student_id=current_user.id,
        quiz_id=quiz.id,
        status="in_progress"
    ).first()

    if existing_attempt:

        return redirect(
            url_for(
                "student.quiz_instructions",
                attempt_id=existing_attempt.id
            )
        )

    attempt = QuizAttempt(
        student_id=current_user.id,
        quiz_id=quiz.id,
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


@student.route("/quiz/<int:attempt_id>/instructions")
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

    if attempt.status != "in_progress":
        flash(
            "This quiz attempt is no longer active.",
            "danger"
        )

        return redirect(
            url_for("student.dashboard")
        )

    quiz = attempt.quiz

    return render_template(
        "student/quiz_instructions.html",
        attempt=attempt,
        quiz=quiz
    )


@student.route(
    "/quiz/<int:attempt_id>/test",
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

    if attempt.status != "in_progress":
        flash(
            "This quiz attempt is no longer active.",
            "danger"
        )

        return redirect(
            url_for("student.dashboard")
        )

    quiz = attempt.quiz

    questions = Question.query.filter_by(
        quiz_id=quiz.id
    ).order_by(
        Question.question_order.asc()
    ).all()

    if not questions:
        flash(
            "This quiz has no questions.",
            "danger"
        )

        return redirect(
            url_for("student.dashboard")
        )

    # -----------------------------
    # SUBMIT QUIZ
    # -----------------------------

    if request.method == "POST":

        now = datetime.utcnow()

        elapsed_seconds = (
            now - attempt.started_at
        ).total_seconds()

        quiz_duration_seconds = (
            quiz.duration * 60
        )

        # Allow a small 5-second server tolerance
        if elapsed_seconds > quiz_duration_seconds + 5:

            flash(
                "The quiz time has expired. Your submitted answers will be evaluated.",
                "danger"
            )

        total_score = 0

        for question in questions:

            field_name = (
                f"question_{question.id}"
            )

            selected_option_id = request.form.get(
                field_name
            )

            selected_option = None

            if selected_option_id:

                try:

                    selected_option_id = int(
                        selected_option_id
                    )

                except ValueError:

                    selected_option_id = None

            if selected_option_id:

                selected_option = Option.query.filter_by(
                    id=selected_option_id,
                    question_id=question.id
                ).first()

            # Default: skipped question
            is_correct = False
            marks_obtained = 0

            # If an option was selected
            if selected_option:

                if selected_option.is_correct:

                    is_correct = True

                    marks_obtained = question.marks

                else:

                    marks_obtained = (
                        -question.negative_marks
                    )

            total_score += marks_obtained

            # Check whether this answer already exists
            existing_answer = QuizAnswer.query.filter_by(
                attempt_id=attempt.id,
                question_id=question.id
            ).first()

            if existing_answer:

                existing_answer.selected_option_id = (
                    selected_option.id
                    if selected_option
                    else None
                )

                existing_answer.is_correct = is_correct

                existing_answer.marks_obtained = (
                    marks_obtained
                )

            else:

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

        attempt.score = total_score

        attempt.submitted_at = now

        attempt.status = "submitted"

        db.session.commit()

        return redirect(
            url_for(
                "student.quiz_result",
                attempt_id=attempt.id
            )
        )

    return render_template(
        "student/take_quiz.html",
        attempt=attempt,
        quiz=quiz,
        questions=questions
    )


@student.route("/quiz/<int:attempt_id>/result")
@login_required
def quiz_result(attempt_id):

    if current_user.role != "student":
        return "Access Denied", 403

    attempt = QuizAttempt.query.filter_by(
        id=attempt_id,
        student_id=current_user.id
    ).first()

    if not attempt:
        return "Quiz attempt not found.", 404

    if attempt.status != "submitted":

        return redirect(
            url_for(
                "student.take_quiz",
                attempt_id=attempt.id
            )
        )

    quiz = attempt.quiz

    answers = QuizAnswer.query.filter_by(
        attempt_id=attempt.id
    ).order_by(
        QuizAnswer.question_id.asc()
    ).all()

    total_questions = len(answers)

    attempted = sum(
        1
        for answer in answers
        if answer.selected_option_id is not None
    )

    skipped = total_questions - attempted

    correct = sum(
        1
        for answer in answers
        if answer.is_correct
    )

    wrong = attempted - correct

    score = attempt.score or 0

    if quiz.total_marks > 0:

        percentage = (
            score / quiz.total_marks
        ) * 100

    else:

        percentage = 0

    return render_template(
        "student/quiz_result.html",
        attempt=attempt,
        quiz=quiz,
        answers=answers,
        score=score,
        total_questions=total_questions,
        attempted=attempted,
        correct=correct,
        wrong=wrong,
        skipped=skipped,
        percentage=percentage
    )

    if current_user.role != "student":
        return "Access Denied", 403

    attempt = QuizAttempt.query.filter_by(
        id=attempt_id,
        student_id=current_user.id
    ).first()

    if not attempt:
        return "Quiz attempt not found.", 404

    if attempt.status != "submitted":

        return redirect(
            url_for(
                "student.take_quiz",
                attempt_id=attempt.id
            )
        )

    quiz = attempt.quiz

    score = attempt.score or 0

    passed = score >= quiz.passing_marks

    answers = QuizAnswer.query.filter_by(
        attempt_id=attempt.id
    ).order_by(
        QuizAnswer.question_id.asc()
    ).all()

    return render_template(
        "student/quiz_result.html",
        attempt=attempt,
        quiz=quiz,
        score=score,
        passed=passed,
        answers=answers
    )