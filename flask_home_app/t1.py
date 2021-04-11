
from os import read
import time

import glob


# Defined read only global variables
# Find the device file to read from.
device_file = glob.glob("/sys/bus/w1/devices/28*")[0] + "/w1_slave"

def main():
    # Datastructure is in the form of:
    #  devicename/measurements: for each measurement type: value.
    # New value is a flag to know if value has been updated since last SQL-query. -> Each :00, :30
    tmpdata = {
        "pizw/temp": {
            "Temperature": -99,
        }
    }
    new_values = {key: False for key in tmpdata}

    # Slowly poll away -99.
    while 1:
        time.sleep(2)
        read_temp(tmpdata, new_values, "pizw/temp")
        print(tmpdata)
        print(new_values)


def read_temp(tmpdata: dict, new_values: dict, measurer: str):
    with open(device_file, "rb") as f:
        lines = f.readlines()
    if lines[0].strip()[-3:] == "YES":
        equals_pos = lines[1].find("t=")
        tmp_val = lines[1][equals_pos + 2 :]
        if equals_pos != -1 and tmp_val.isdigit():
            conv_val = round(int(tmp_val) / 1000, 1)
            if _test_value("Temperature", int(conv_val * 100)):
                tmpdata[measurer]["Temperature"] = conv_val
                new_values[measurer] = True



def _test_value(key, value) -> bool:
    if isinstance(value, int):
        if key == "Temperature":
            return -5000 <= value <= 6000
        elif key == "Humidity":
            return 0 <= value <= 10000
        elif key == "Airpressure":
            return 90000 <= value <= 115000
    return False


if __name__ == "__main__":
    main()
