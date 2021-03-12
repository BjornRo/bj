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
import scan_and_book as sab

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Hardcoded until forms are created.
jsondata = sab.load_json()
logindata = {"username": jsondata["login"]["username"], "password": jsondata["login"]["password"]}

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

@app.context_processor
def inject_enumerate():
    return dict(enumerate=enumerate)

@app.route("/")
def index():
    return render_template("index.html", title="Main index")

# TODO.. Solve how to store data for each session, or just pass on data...Or dynamically update
# to keep the data for the session.

@app.route("/booking", methods=["POST", "GET"])
def booking():
    if request.method == "GET":
        keys = [(i,i) for i in all_bookings.keys()]
        return render_template("booking.html", title="Booking page", select="Facilities:", keys=keys)
    else:
        resdata = list(request.form)
        try:
            # Check if selected time
            if resdata[1] in all_bookings.keys():
                location = resdata[1]
                bookingslist = all_bookings.get(location)

                # Wrangle timeslots
                all_timeslots = []
                for i in bookingslist:
                    for j in bookingslist.get(i):
                        all_timeslots.append((i, j))

                time_print = []
                for i, (d, t) in enumerate(all_timeslots):
                    print(days.get(int(d)), file=sys.stderr)

                    to_print = f"{days.get(int(d))}, {t}, slots: "
                    if bookingslist.get(d).get(t)[0]:
                        to_print += bookingslist.get(d).get(t)[1]
                    else:
                        to_print += "not unlocked"
                    time_print.append((to_print, (location, d, t)))
                return render_template("booking.html", title="Booking page", select=f"Select your time for {location}:", keys=time_print)
            else:
                print(resdata, file=sys.stderr)
                loc_day_time = ast.literal_eval(resdata[1])
                link, slots = all_bookings.get(loc_day_time[0]).get(loc_day_time[1]).get(loc_day_time[2])
                # TODO Check if its possible to book.
                response = sab.post_data(main_url, link)
                return redirect(url_for('index'))
        except:
            return "404"

@app.route("/result", methods=["POST"])
def result():
    request.form
    return render_template("index.html", title="Main index")


if __name__ == "__main__":
    app.run(debug=True, threaded=False)
