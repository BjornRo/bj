from flask import Blueprint, render_template, request, jsonify, url_for
import sys
from . import TmpData
import paho.mqtt.publish as publish

# publish.single("paho/test/single", "payload", hostname="mqtt.eclipse.org")
views = Blueprint("views", __name__)


@views.route("/")
def home():
    return render_template("index.html", title="Home", data=list(TmpData().tmp.values()))


@views.route("/home_status")
def home_status():
    return TmpData().tmp


# Pinsetup for arduino
# 0+2 2 all off
# 1+2 3 hi light
# 2+2 4 low light
# 3+2 5 heater
entities = {"alloff": "ALLOFF", "full_light": 0, "low_light": 1, "heater": 2}
commands = {"off": 0, "on": 1}


@views.route("/post_command", methods=["POST"])
def post_command():
    ent = request.form.get("entity")
    com = request.form.get("command")
    if ent in entities and com in commands:
        if ent == "alloff":
            pub = entities[ent]
        elif com == "on":
            pub = f"({entities[ent]},{commands[com]},{5 if ent == 'full_light' else 420})"
        elif com == "off":
            pub = f"({entities[ent]},{commands[com]},0)"
        else:
            return ""
        publish.single("home/balcony/relay", pub, hostname="www.home")
    return ""
