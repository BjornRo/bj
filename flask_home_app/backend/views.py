from flask import Blueprint, render_template, request, jsonify
from . import TmpData, local_addr, db
import paho.mqtt.publish as publish
from .models import Notes, Timestamp


views = Blueprint("views", __name__)

@views.route("/")
def home():
    local = request.remote_addr.split(".")[:2] in local_addr
    return render_template(
        "index.html",
        title="Home",
        data=list(TmpData().tmp.values()),
        local=local,
        rel_status=TmpData().tmp["balcony/relaystatus"],
    )

@views.route("/notes", methods=["GET","POST"])
def notes():
    local = request.remote_addr.split(".")[:2] in local_addr
    return render_template('notes.html', local=local)

@views.route("/api", methods=['GET','POST'])
def api():
    if request.remote_addr.split(".")[:2] in local_addr:
        if request.args and request.args.get('c').isdigit():
            count = int(request.args.get('c'))
            print(count)
            n_posts = db.session.query(Notes).count()
            print("Nposts")
            print(n_posts)
            if count == n_posts:
                return jsonify([(i,[str(i)]*10) for i in range(20)])
            return jsonify(db.session.query(Notes).order_by(Notes.time).limit(10).offset(count))
    return ("",204)


# Everyone can get this data
@views.route("/home_status")
def home_status():
    return TmpData().tmp


# Pinsetup for arduino. Send 0-3
# By pin index 0-3(2-5): 2: Full light, 3: Low Light, 4: HEATER_PIN, 5: Unused
entities = {"alloff": "ALLOFF", "full_light": 0, "low_light": 1, "heater": 2}
commands = {"off": 0, "on": 1}


@views.route("/post_command", methods=["POST"])
def post_command():
    if request.remote_addr.split(".")[:2] in local_addr:
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
