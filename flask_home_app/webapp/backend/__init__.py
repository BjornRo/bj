from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os
from flask.json import JSONEncoder
from datetime import date

# # Pseudo memory-db. Use a static class.
# # Data that is not critical to store in db.
# # Locks are not necessary since race conditions are ok in this specific case.
# class TmpData:
#     subs = (
#         "balcony/relay/status",
#         "balcony/temphumid",
#         "kitchen/temphumidpress",
#         "bikeroom/temp",
#     )
#     # Init values doesn't matter.
#     tmp = {k: v for k, v in zip(subs, ([-1, -1, -1, -1], [-99, -99], [-99, -99, -99], -99))}


db = SQLAlchemy()
DB_NAME = "database.db"
local_addr = (["192", "168"], ["127", "0"])


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KET"] = "secret"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_NAME}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.json_encoder = CustomJSONEncoder
    db.init_app(app)
    create_db(app)
    with app.app_context():
        db.session.execute("PRAGMA foreign_keys=on")

    from .views import views

    # from .auth import auth
    from .datavisualizer import datavisualizer
    from .booking import booking

    app.register_blueprint(views, url_prefix="/")
    # app.register_blueprint(auth, url_prefix="/")
    app.register_blueprint(booking, url_prefix="/booking")
    app.register_blueprint(datavisualizer, url_prefix="/dataviz")

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(
            os.path.join(app.root_path, "static"),
            "favicon.ico",
            mimetype="image/vnd.microsoft.icon",
        )

    return app


def create_db(app):
    if not os.path.isfile(DB_NAME):
        from .models import Measurer, Temperature, Humidity, Airpressure, Timestamp, Notes

        db.create_all(app=app)


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, date):
                return obj.isoformat("T")
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)
