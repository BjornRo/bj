from flask import Blueprint, render_template, request, jsonify, url_for, redirect
from datetime import datetime
from modules.sab import MainController, load_json
import pickle
from . import local_addr

validate_str = load_json()["site"]["validate"]
control = MainController(0, **load_json()['site']['data'])
with open("data.p", "rb") as f:
    control = pickle.load(f)
    # with open("data.p","wb") as f:
    # pickle.dump(control, f, pickle.HIGHEST_PROTOCOL)


booking = Blueprint("booking", __name__)


@booking.route("")
def home():
    control.query_booking_sort()
    with open("data.p","wb") as f:
        pickle.dump(control, f, pickle.HIGHEST_PROTOCOL)
    addr = request.remote_addr.split(".")[:2]
    local = True if addr in local_addr else False
    if local:
        # Query site
        # control.query_booking_sort()
        return render_template(
            "booking.html", title="Booking", data=control.get_payload_dict(), local=local
        )
    return render_template("booking.html", title="Booking", data={}, local=local)


@booking.route("/result", methods=["GET", "POST"])
def result():
    addr = request.remote_addr.split(".")[:2]
    local = True if addr in local_addr else False
    if local and request.method == "POST":
        # Validate form
        location = request.form.get("location")
        time = request.form.get("time")
        username = request.form.get("user")
        password = request.form.get("pass")
        if location and time and username and password:
            time_key = datetime.strptime(time, "%Y-%m-%d %H:%M:%S").replace(second=0)
            timeslot_data = control.get_timeslot_data(location, time_key)
            if not timeslot_data:
                return render_template(
                    "booking_result.html", title="Booking not available.", success=False
                )

            # If there is no url, get number of seconds to sleep.
            if not timeslot_data.get("url"):
                sleep_time = (time_key - datetime.now()).total_seconds() + 20
                return render_template(
                    "booking_result.html",
                    title="Booking not unlocked.",
                    data=request.form,
                    seconds=sleep_time,
                    success=True,
                    booked=False,
                    url=False,
                )
            if timeslot_data.get("slots") == "0":
                return render_template(
                    "booking_result.html",
                    title="Booking, no slots.",
                    data=request.form,
                    seconds=90,
                    success=True,
                    booked=False,
                    url=True,
                )
            booked = control.post_data(
                timeslot_data.get("url"), {"username": username, "password": password}
            )
            if booked[0]:
                return render_template(
                    "booking_result.html",
                    title="Booking successful!",
                    success=True,
                    booked=True,
                )
            return render_template(
                "booking_result.html",
                title="Booking failed!",
                success=False,
            )
    return redirect(url_for("booking.home"))


@booking.route("/post_data", methods=["POST"])
def query_booking():
    if True if request.remote_addr.split(".")[:2] in local_addr else False:
        username = request.form.get("user")
        password = request.form.get("pass")
        url = request.form.get("url")
        if username and password and url:
            res = control.post_data(url, {"username": username, "password": password})
        return {"success": res[0], "msg": res[1]}
    return redirect(url_for("booking.home"))


@booking.route("/get_json")
def get_json():
    if True if request.remote_addr.split(".")[:2] in local_addr else False:
        control.query_booking_sort()
        return control.get_payload_dict()
    return redirect(url_for("booking.home"))
