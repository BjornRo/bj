from flask import Blueprint, render_template, request, jsonify
from datetime import datetime, timedelta
from modules.sab import MainController, load_json
from . import local_addr

#from flask_jwt_extended import create_access_token

control = MainController(0, **load_json()["site"]["data"])
booking = Blueprint("booking", __name__)

@booking.context_processor
def inject_enumerate():
    return dict(enumerate=enumerate)


@booking.route("")
def home():
    local = request.remote_addr.split(".")[:2] in local_addr
    if local:
        if control.query_booking_sort():
            return render_template(
                "booking.html", title="Booking", data=control.get_printables_dict(), local=local
            )
        else:
            return render_template("booking.html", title="Booking failed", failed=True)
    return render_template("booking.html", title="Booking not local", local=local)


@booking.route("/api", methods=["GET", "POST"])
def api():
    if request.remote_addr.split(".")[:2] in local_addr:
        try:
            if request.method == "GET":
                loc_key = request.args.get("location")
                time_key = datetime.fromisoformat(request.args.get("timeslot"))
                if loc_key and time_key and control.query_booking_sort():
                    return jsonify(control.get_bookable(loc_key, time_key))
            else:
                username = request.form.get("user")
                password = request.form.get("pass")
                loc_key = request.form.get("loc_key")
                time_key = datetime.fromisoformat(request.form.get("time_key"))
                if username and password and loc_key and time_key:
                    url = control.get_url(loc_key, time_key)
                    if url:
                        res = control.post_data(url, username, password)
                        return {"res": res[0], "msg": res[1]}
        except:
            pass
    return ("", 204)
