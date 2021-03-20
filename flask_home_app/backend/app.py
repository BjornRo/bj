from flask import Flask, request, render_template, redirect, jsonify
import sys
import os

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.context_processor
def inject_enumerate():
    return dict(enumerate=enumerate)

@app.route("/")
def index():
    return render_template("index.html", title="Home")


if __name__ == '__main__':
    app.run(debug=True, threaded=False)