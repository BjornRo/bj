from flask import Flask, request, render_template
import json
import sys
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
import time
import pickle
import os

# Import booking script
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), "..")))
import scan_and_book as sab

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Hardcoded until forms are created.
jsondata = sab.load_json()

year, week, _ = datetime.today().isocalendar()
day = datetime.today().isocalendar()[2] - 1
days = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
timeformat, time_re = "%H:%M", "[0-9]+:[0-9]+"
main_url, bookings_url, _ = jsondata.get("site").values()
queries = (
    jsondata["site"]["query"].format(year, week),
    jsondata["site"]["query"].format(year, (week % datetime(year, 12, 31).isocalendar()[1]) + 1),
)
"""
all_bookings = sab.sort_and_order_bookinglist(
    main_url, day, sab.get_bookings(day, bookings_url + queries[0], bookings_url + queries[1]), timeformat, time_re
)
"""

with open("dat.json", "r") as f:
    all_bookings = json.load(f)


@app.route("/")
def index():
    return render_template("index.html", title="Main index")


@app.route("/booking", methods=["POST", "GET"])
def booking():
    if request.method == "GET":
        keys = all_bookings.keys()
        return render_template("booking.html", title="Booking page", select="Facilities:", keys=keys)
    else:
        result = all_bookings.get(list(request.form)[0])
        print(result, file=sys.stderr)
        return render_template("booking.html", title="Booking page", select="Time:", keys=result)


@app.route("/result", methods=["POST"])
def result():
    request.form
    return render_template("index.html", title="Main index")


if __name__ == "__main__":
    app.run(debug=True)