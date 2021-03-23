from flask import Blueprint, render_template, request, jsonify, url_for, redirect
from datetime import datetime
from modules.sab import MainController, load_json
from . import local_addr

control = MainController(0, **load_json()["site"]["data"])
booking = Blueprint("booking", __name__)


@booking.context_processor
def inject_enumerate():
    return dict(enumerate=enumerate)


@booking.route("")
def home():
    addr = request.remote_addr.split(".")[:2]
    local = True if addr in local_addr else False
    if local:
        # Query site
        if control.query_booking_sort():
            return render_template(
                "booking.html", title="Booking", data=control.get_payload_dict(), local=local
            )
        else:
            return render_template("booking.html", title="Booking failed", failed=True)
    return render_template("booking.html", title="Booking not local", local=local)


@booking.route("/post_data", methods=["POST"])
def post_data():
    if True if request.remote_addr.split(".")[:2] in local_addr else False:
        username = request.form.get("user")
        password = request.form.get("pass")
        url = request.form.get("url")
        if username and password and url:
            res = control.post_data(url, {"username": username, "password": password})
        return {"success": res[0], "msg": res[1]}
    return redirect(url_for("booking.home"))


@booking.route("/get_timeslot_data", methods=["POST"])
def get_timeslot_data():
    if True if request.remote_addr.split(".")[:2] in local_addr else False:
        try:
            location = request.form.get("location")
            timeslot = datetime.fromisoformat(request.form.get("timeslot"))
            if location and timeslot and control.query_booking_sort():
                return control.get_timeslot_data(location, timeslot)
        except:
            pass
    return ("", 204)