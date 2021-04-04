from flask import Blueprint, render_template, request, jsonify, url_for
from . import db

datavisualizer = Blueprint("datavisualizer", __name__)


@datavisualizer.route("/")
def home():
    return render_template("dataviz.html", title="Data visualization")


@datavisualizer.route("/api")
def api():
    data = db.session.execute(
        """
        WITH kitchendata AS (
                SELECT time, temperature AS ktemp, humidity AS khumid, airpressure AS kpressure
                FROM Temperature
                NATURAL JOIN Humidity
                NATURAL JOIN Airpressure
                WHERE measurer = 'kitchen'),
            balconydata AS (
                SELECT time, temperature AS btemp, humidity AS bhumid
                FROM Temperature
                NATURAL JOIN Humidity
                WHERE measurer = 'balcony'),
            bikeroomdata AS (
                SELECT time, temperature AS brtemp
                FROM Temperature
                WHERE measurer = 'bikeroom')
        SELECT kd.time, ktemp, khumid, kpressure, btemp, bhumid, brtemp
            FROM kitchendata kd
            LEFT OUTER JOIN
                balconydata bd
                ON kd.time = bd.time
            LEFT OUTER JOIN
                bikeroomdata brd
                ON kd.time = brd.time"""
    ).fetchall()
    db.session.commit()
    return jsonify(
        (
            (
                "date",
                "kitchen temp",
                "kitchen humid",
                "kitchen pressure",
                "balcony temp",
                "balcony humid",
                "bikeroom temp",
            ),
            data,
        )
    )


# outdoor (temp)
# kitchen (temp humid pressure)

# Grid temp  temp
# ---- humid pressure
