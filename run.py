from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return """
    <h1>Online Quiz Management System</h1>
    <p>Flask is working successfully!</p>
    """


if __name__ == "__main__":
    app.run(debug=True)