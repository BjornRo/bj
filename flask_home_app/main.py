from datetime import datetime
import time
from threading import Thread
from backend import db, TmpData, create_app
from backend.models import *
import schedule
import sys


def main():
    try:
        app = create_app()

        app.config["TEMPLATES_AUTO_RELOAD"] = True

        Thread(target=mqtt_agent, daemon=True).start()
        Thread(target=schedule_setup, args=(app,), daemon=True).start()

        app.run(debug=True, use_reloader=False)
    except KeyboardInterrupt:
        sys.exit(1)



def schedule_setup(app):
    def querydb():
        time_now = datetime.now().replace(microsecond=0, second=0)
        with app.app_context():
            db.session.add(Timestamp(time=time_now))
            for i, (key, value) in enumerate(tuple(TmpData.tmp.items())[1:]):
                keydict = {"measurer": key.split("/")[0], "time": time_now}
                temp, humid, press = None, None, None
                if i == 0:
                    continue
                    # temp, humid = value
                elif i == 1:
                    temp, humid, press = value
                elif i == 2:
                    temp = value
                db.session.add(Temperature(**keydict, temperature=temp))
                if humid:
                    db.session.add(Humidity(**keydict, humidity=humid))
                if press:
                    db.session.add(Airpressure(**keydict, airpressure=press))
            db.session.commit()
        return

    schedule.every().hour.at(":30").do(querydb)
    schedule.every().hour.at(":00").do(querydb)

    while True:
        schedule.run_pending()
        time.sleep(5)


# This agent only needs threading. Multiprocessing is nicer but I don't expect too much concurrency
# on this webapp. Small microseconds delay are no problem at home.
def mqtt_agent():
    from ast import literal_eval
    import paho.mqtt.client as mqtt

    def on_connect(client, *_):
        for s in TmpData().subs:
            client.subscribe("home/" + s)

    def on_message(client, userdata, msg):
        val = literal_eval(msg.payload.decode("utf-8"))
        m = msg.topic.replace("home/", "")
        # Would be perfect for pattern matching! 4 different structures.
        for i, sub in enumerate(TmpData().subs):
            if m == sub:
                if i == 0:
                    break
                elif i == 1:
                    val = [x / 100 for x in val]
                    break
                elif i == 2:
                    val = [x / 100 for x in val]
                    break
                elif i == 3:
                    val /= 100
                    break
                else:
                    return
        TmpData().tmp[sub] = val

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("www.home", 1883, 60)
    client.loop_forever(timeout=1)


if __name__ == "__main__":
    main()
