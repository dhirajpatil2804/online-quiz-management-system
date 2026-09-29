from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )

    def __repr__(self):
        return f"<User {self.email}>"

class Quiz(db.Model):
    __tablename__ = "quizzes"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    duration = db.Column(
        db.Integer,
        nullable=False
    )

    number_of_questions = db.Column(
        db.Integer,
        nullable=False,
        default=10
    )

    total_marks = db.Column(
        db.Integer,
        nullable=False
    )

    passing_marks = db.Column(
        db.Integer,
        nullable=False
    )

    status = db.Column(
        db.String(20),
        default="draft",
        nullable=False
    )

    created_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    creator = db.relationship(
        "User",
        backref="quizzes",
        foreign_keys=[created_by]
    )

    def __repr__(self):
        return f"<Quiz {self.title}>"


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    quiz_id = db.Column(
        db.Integer,
        db.ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False
    )

    question_text = db.Column(
        db.Text,
        nullable=False
    )

    marks = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    negative_marks = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    question_order = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    quiz = db.relationship(
        "Quiz",
        backref=db.backref(
            "questions",
            cascade="all, delete-orphan"
        )
    )

    options = db.relationship(
        "Option",
        backref="question",
        cascade="all, delete-orphan",
        order_by="Option.id"
    )

    def __repr__(self):
        return f"<Question {self.id}>"


class Option(db.Model):
    __tablename__ = "options"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False
    )

    option_text = db.Column(
        db.Text,
        nullable=False
    )

    is_correct = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    def __repr__(self):
        return f"<Option {self.id}>"


class QuizAttempt(db.Model):
    __tablename__ = "quiz_attempts"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    quiz_id = db.Column(
        db.Integer,
        db.ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False
    )

    started_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    submitted_at = db.Column(
        db.DateTime,
        nullable=True
    )

    score = db.Column(
        db.Integer,
        nullable=True
    )

    status = db.Column(
        db.String(20),
        default="in_progress",
        nullable=False
    )

    student = db.relationship(
        "User",
        backref="quiz_attempts",
        foreign_keys=[student_id]
    )

    quiz = db.relationship(
        "Quiz",
        backref="attempts",
        foreign_keys=[quiz_id]
    )

    def __repr__(self):
        return f"<QuizAttempt {self.id}>"

class QuizAnswer(db.Model):
    __tablename__ = "quiz_answers"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    attempt_id = db.Column(
        db.Integer,
        db.ForeignKey("quiz_attempts.id", ondelete="CASCADE"),
        nullable=False
    )

    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False
    )

    selected_option_id = db.Column(
        db.Integer,
        db.ForeignKey("options.id", ondelete="SET NULL"),
        nullable=True
    )

    is_correct = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    marks_obtained = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    attempt = db.relationship(
        "QuizAttempt",
        backref="answers",
        foreign_keys=[attempt_id]
    )

    question = db.relationship(
        "Question",
        foreign_keys=[question_id]
    )

    selected_option = db.relationship(
        "Option",
        foreign_keys=[selected_option_id]
    )

    def __repr__(self):
        return f"<QuizAnswer {self.id}>"


class QuizRetakePermission(db.Model):
    __tablename__ = "quiz_retake_permissions"

    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    quiz_id = db.Column(
        db.Integer,
        db.ForeignKey("quizzes.id", ondelete="CASCADE"),
        nullable=False
    )

    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    reason = db.Column(
        db.Text,
        nullable=True
    )

    used = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    student = db.relationship(
        "User",
        foreign_keys=[student_id]
    )

    quiz = db.relationship(
        "Quiz",
        foreign_keys=[quiz_id]
    )

    teacher = db.relationship(
        "User",
        foreign_keys=[teacher_id]
    )

    def __repr__(self):
        return f"<QuizRetakePermission student={self.student_id} quiz={self.quiz_id}>"