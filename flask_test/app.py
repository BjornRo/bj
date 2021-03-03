from flask import Flask, request

app = Flask(__name__)


@app.route("/")
def index():
    return '<a href="/submit">submit data</a><br>'


@app.route("/submit")
def form():
    s = "<body>" '<form action="/submit" method="POST">'
    '<input type="text" name="abc"></input>'
    '<input type="submit"></input>'
    "</form>" "</body>"
    return s


# @app.route("/submit", methods=["POST"])
# def post_form():
#     text = request.form['abc']
#     return text.upper()
