from flask import Blueprint, render_template, request, jsonify, url_for
import sys
from . import TmpData
import paho.mqtt.publish as publish
#publish.single("paho/test/single", "payload", hostname="mqtt.eclipse.org")
views = Blueprint('views',__name__)

@views.route('/')
def home():
    return render_template("index.html", title="Home", data=list(TmpData().tmp.values()))

@views.route('/home_status')
def home_status():
    return TmpData().tmp

#"{{ url_for('views.home_status') }}"