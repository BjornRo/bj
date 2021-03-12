from flask import Flask, request, render_template, redirect
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

with open("dat.json", "w") as f:
    #all_bookings = json.load(f)
    json.dump(data, f)


@app.context_processor
def inject_enumerate():
    return dict(enumerate=enumerate)


@app.route("/")
def index():
    return render_template("index.html", title="Main index")


# TODO.. Solve how to store data for each session, or just pass on data...Or dynamically update
# to keep the data for the session.

#obj.query_booking_sort()
@app.route("/booking", methods=["POST", "GET"])
def booking():
    if request.method == "GET":
        if True:
            return render_template(
                "booking.html", title="Booking page", select="Facilities:", keys=all_bookings
            )
    elif request.method == "POST":
        resdata = list(request.form)
        #print(resdata[0] in list(all_bookings), file=sys.stderr)
        try:
            if resdata[0] in obj.get_location_list():
                # Test if there is another item in the list. Otherwise get 2nd item.
                try:
                    if 0 <= resdata[3] < len(object.get_all_timeslots(resdata[0])):
                        pass
                except:
                    return
        except:
            pass
    return "404"


@app.route("/result", methods=["POST"])
def result():
    request.form
    return render_template("index.html", title="Main index")


if __name__ == "__main__":
    app.run(debug=True, threaded=False)
