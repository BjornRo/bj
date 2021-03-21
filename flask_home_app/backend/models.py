from . import db

# Trying to have as little dependencys as possible. After learning 1-BC-4NF, updating data
# is horrible with bad design. Anomalies will get you!
# Not all measurers have same functionality. Some may only have temp, temphumid or all three.

class Measurer(db.Model):
    key = db.Column(db.String(8), primary_key=True)

# Weak entity, we don't know really what this is until we combine it with a measurer.
class Timestamp(db.Model):
    time = db.Column(db.DateTime(timezone=True), primary_key=True)

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