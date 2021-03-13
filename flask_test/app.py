from flask import Flask, request, render_template, redirect, jsonify
import json
import sys
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
import time
import pickle
import ast
import os

from flask.helpers import url_for

# Import booking script
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "..")))
from scan_and_book import MainController
import scan_and_book as sab

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Hardcoded until forms are created.
dat = sab.load_json()
logindata = {"username": dat["login"]["username"], "password": dat["login"]["password"]}

obj = MainController(0, dat["site"]["protocol"], dat["site"]["hostname"], dat["site"]["path"], dat["site"]["query"])
validation_str = dat["site"]["validate"]
# obj.query_booking_sort()

# with open('data.p','wb') as o:
#    pickle.dump(obj, o, pickle.HIGHEST_PROTOCOL)

# with open("data.p", "rb") as o:
#    obj = pickle.load(o)


@app.context_processor
def inject_enumerate():
    return dict(enumerate=enumerate)


@app.route("/")
def index():
    return render_template("index.html", title="Main index")


# obj.query_booking_sort()
@app.route("/booking", methods=["POST", "GET"])
def booking():
    if request.method == "GET":
        obj.query_booking_sort()
        payload = obj.get_payload_dict()
        return render_template(
            "booking.html", title="Booking page", dir="/booking", select="Facilities:", payload=payload
        )
    elif request.method == "POST":
        formdata = dict(request.form)
        book_url = formdata.pop("select_time", None)
        if book_url and validation_str in book_url:
            try:
                location_key = list(formdata)[0]
                location_time = formdata.get(location_key)
                print(dict(request.form), file=sys.stderr)
                return render_template(
                    "booking.html",
                    title="Booking page",
                    dir="/result",
                    select="Login credentials:",
                    login=True,
                    time=location_time,
                    location=location_key,
                    book_url=book_url,
                    payload={0: []},
                )
            except:
                pass
        elif book_url is None:
            return "Invalid time selected"
    return "404"


@app.route("/result", methods=["POST"])
def result():
    formdata = dict(request.form)
    print(dict(request.form), file=sys.stderr)
    book_url = formdata.pop("book_url", None)
    if book_url and validation_str in book_url:
        try:
            payload = {"username": formdata.get("username"), "password": formdata.get("password")}
            print(payload, file=sys.stderr)

            result, message = obj.post_data(book_url, payload)
            if not result:
                return render_template(
                    "booking.html",
                    title="Booking page",
                    dir="/result",
                    select="Login credentials:",
                    login=True,
                    time=formdata.get("location_time"),
                    location=formdata.get("location"),
                    book_url=book_url,
                    message=message,
                    payload={0: []},
                )
            else:
                return render_template(
                    "index.html",
                    title="Main index",
                    message=message.format(formdata.get("location_time"), formdata.get("location")),
                )
        except:
            pass
    return "404"


if __name__ == "__main__":
    app.run(debug=True, threaded=False)
