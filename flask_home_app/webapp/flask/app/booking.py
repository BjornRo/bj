from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
from . import local_addr, control

# from flask_jwt_extended import create_access_token

booking = Blueprint("booking", __name__)


@booking.context_processor
def inject_enumerate():
    return dict(enumerate=enumerate)


@booking.route("")
def home():
    local = request.headers.get("X-Forwarded-For").split(',')[0].split(".")[:2] in local_addr
    if local:
        if control.query_booking_sort():
            printables = control.get_printables_dict()
            return render_template(
                "booking.html",
                title="Booking",
                data=printables,
                keys=sorted(printables),
                local=local,
            )
        else:
            return render_template("booking.html", title="Booking failed", failed=True)
    return render_template("booking.html", title="Booking not local", local=local)


@booking.route("/api", methods=["GET", "POST"])
def api():
    if request.headers.get("X-Forwarded-For").split(',')[0].split(".")[:2] in local_addr:
        try:
            if request.method == "GET":
                if control.query_booking_sort():
                    return jsonify(
                        control.get_bookable(
                            request.args.get("location"),
                            datetime.fromisoformat(request.args.get("timeslot")),
                        )
                    )
            else:
                username, password = request.form.get("user"), request.form.get("pass")
                url = control.get_url(
                    request.form.get("loc_key"),
                    datetime.fromisoformat(request.form.get("time_key")),
                )
                if url and username and password:
                    res = control.post_data(url, username, password)
                    return jsonify({"res": res[0], "msg": res[1]})
        except:
            pass
    return ("", 204)
