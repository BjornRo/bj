from flask import Flask
from flask_sqlalchemy import SQLAlchemy

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
from .models import Measurer, Temperature, Humidity, Airpressure, Timestamp


def create_app():

    app = Flask(__name__)
    app.config["SECRET_KET"] = "secret"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_NAME}"
    db.init_app(app)
    create_db(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/")


    return app


def create_db(app):
    from os import path
    if not path.exists("backend/" + DB_NAME):
        db.create_all(app=app)


