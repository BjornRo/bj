from flask import Flask
from flask.json import JSONEncoder
from flask_sqlalchemy import SQLAlchemy
from flask_scss import Scss
from datetime import date

# Pseudo memory-db. Use a static class.
# Data that is not critical to store in db.
# Locks are not necessary since race conditions are ok in this specific case.
class TmpData:
    subs = (
        "balcony/relaystatus",
        "balcony/temphumid",
        "kitchen/temphumidpress",
        "bikeroom/temp",
    )
    # Init values doesn't matter.
    tmp = {k: v for k, v in zip(subs, ([-1, -1, -1, -1], [-99, -99], [-99, -99, -99], -99))}

db = SQLAlchemy()
DB_NAME = "database.db"
local_addr = (["192", "168"], ["127", "0"])

def create_app():

    app = Flask(__name__)
    Scss(app)
    app.json_encoder = CustomJSONEncoder
    app.config["SECRET_KET"] = "secret"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_NAME}"
    db.init_app(app)
    create_db(app)

    from .views import views
    #from .auth import auth
    from .datavisualizer import datavisualizer
    from .booking import booking

    app.register_blueprint(views, url_prefix="/")
    #app.register_blueprint(auth, url_prefix="/")
    app.register_blueprint(booking, url_prefix="/booking")
    app.register_blueprint(datavisualizer, url_prefix="/dataviz")

    return app


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, date):
                return obj.isoformat("T", "minutes")
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)

def create_db(app):
    from os import path
    if not path.exists("backend/" + DB_NAME):
        from .models import Measurer, Temperature, Humidity, Airpressure, Timestamp#, Note
        db.create_all(app=app)


