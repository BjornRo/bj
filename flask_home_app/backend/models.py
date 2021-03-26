from . import db
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config['SQLALCHEMY_ECHO'] = True
db = SQLAlchemy(app)
"""

# Trying to have as little dependencys as possible. After learning 1-BC-4NF, updating data
# is horrible with bad design. Anomalies will get you!
# Not all measurers have same functionality. Some may only have temp, temphumid or all three.

class Measurer(db.Model):
    key = db.Column(db.String(8), primary_key=True)
    temp = db.relationship("Temperature", backref="measure", lazy="dynamic")
    humid = db.relationship("Humidity", backref="measure", lazy="dynamic")
    press = db.relationship("Airpressure", backref="measure", lazy="dynamic")

# Weak entity, we don't know really what this is until we combine it with a measurer.
class Timestamp(db.Model):
    time = db.Column(db.DateTime(timezone=True), primary_key=True)
    temp = db.relationship("Temperature", backref="timestamp", cascade="all, delete", lazy="dynamic")
    humid = db.relationship("Humidity", backref="timestamp", cascade="all, delete", lazy="dynamic")
    press = db.relationship("Airpressure", backref="timestamp", cascade="all, delete", lazy="dynamic")

class Temperature(db.Model):
    measurer = db.Column(db.String(8), db.ForeignKey('measurer.key'), primary_key=True)
    time = db.Column(db.DateTime(timezone=True), db.ForeignKey('timestamp.time'), primary_key=True)
    temperature = db.Column(db.Numeric(2), nullable=False)

class Humidity(db.Model):
    measurer = db.Column(db.String(8), db.ForeignKey('measurer.key'), primary_key=True)
    time = db.Column(db.DateTime(timezone=True), db.ForeignKey('timestamp.time'), primary_key=True)
    humidity = db.Column(db.Numeric(2), nullable=False)

class Airpressure(db.Model):
    measurer = db.Column(db.String(8), db.ForeignKey('measurer.key'), primary_key=True)
    time = db.Column(db.DateTime(timezone=True), db.ForeignKey('timestamp.time'), primary_key=True)
    airpressure = db.Column(db.Numeric(2), nullable=False)

class Notes(db.Model):
    time = db.Column(db.DateTime(timezone=True), primary_key=True)
    text = db.Column(db.String(1000), nullable=False)
    updated = db.relationship("Notes_updated", backref="notes", cascade="all, delete", lazy="joined", order_by="Notes_updated.updatetime.desc()")

class Notes_updated(db.Model):
    notetime = db.Column(db.DateTime(timezone=True), db.ForeignKey('notes.time'), primary_key=True)
    updatetime = db.Column(db.DateTime(timezone=True), primary_key=True)