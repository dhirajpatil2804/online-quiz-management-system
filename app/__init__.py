from flask import Flask


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = "dev-secret-key"

    @app.route("/")
    def home():
        return """
        <h1>Online Quiz Management System</h1>
        <p>Flask application structure is working!</p>
        """

    return app