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

"""
all_bookings = sab.sort_and_order_bookinglist(
    main_url, day, sab.get_bookings(day, bookings_url + queries[0], bookings_url + queries[1]), timeformat, time_re
)
"""

data = pickle.load(open("data.p", "rb"))


@app.context_processor
def inject_enumerate():
    return dict(enumerate=enumerate)


@app.route("/")
def index():
    return render_template("index.html", title="Main index")


# TODO.. Solve how to store data for each session, or just pass on data...Or dynamically update
# to keep the data for the session.

# obj.query_booking_sort()
@app.route("/booking", methods=["POST", "GET"])
def booking():
    if request.method == "GET":
        return render_template(
            "booking.html", title="Booking page", dir="/booking", select="Facilities:", keys=sorted(list(data)), loc=0
        )
    elif request.method == "POST":
        resdata = dict(request.form)["0"]
        print(resdata, file=sys.stderr)
        try:
            if resdata in list(data):
                print(resdata, file=sys.stderr)
                return render_template(
                    "booking.html",
                    title="Booking page",
                    dir="/result",
                    select="Time slot:",
                    keys=list(data.get(resdata)),
                    data=[dict(request.form)["0"]],
                )
        except:
            pass
    return "404"


@app.route("/result", methods=["POST"])
def result():
    resdata = list(dict(request.form))
    val = None
    print(resdata, file=sys.stderr)
    for i,_ in enumerate(resdata):
        if resdata[i].isdigit():
            val = int(resdata.pop(i))
            break
    loc = resdata[0]
    timeslot = tuple(data.get(loc))[val]
    timeslot_data = data.get(loc).get(timeslot)
    obj.get_control().post_data(timeslot_data[1],logindata)
    return render_template("index.html", title="Main index - success")


if __name__ == "__main__":
    app.run(debug=True, threaded=False)
