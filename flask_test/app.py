from scan_and_book.main import get_user_input
from flask import Flask, request, render_template
import scan_and_book

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.route("/")
def index():
    return render_template("index.html", title="Main index", user="a")

@app.route("/booking")
def index():
    return render_template("booking.html", title="Booking page", user="a")


if __name__ == "__main__":
    app.run(debug=True)