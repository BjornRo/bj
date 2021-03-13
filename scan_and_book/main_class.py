"""
This was more of a fun project since I really disliked the company booking-site(I'm just a casual user, not an employee).
Messy old code with hidden elements which wasn't really hidden since data was just under layers of 'design'...

Maybe someone can find inspiration or something. May not be usable for anything other than just for this company.

Tried to implement what I've learnt from Computer Science courses so far.

* Functional decomposition
* Finite automata (Regular expressions)
* Very light "database"... few rows of JSON.
* Some algorithms
* Recursion on the user input! :D Wish Python had more haskell-like style though...
* Programming IS Math: f(g(h(x)))
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import sys
import os
import json
from datetime import datetime as dt, timedelta


class QueryPost:
    def __init__(self, first_wkday_num: int, protocol: str, hostname: str, path: str):
        # Attempts for retrying.
        self.attempts = 0
        # timeslot = (location, day, selected_time)
        self.timeslot = None
        # Flag if object has successfully booked.
        self.booked = False
        # Timeout, default 10.
        self.timeout = 10

        # Time related
        self.year, self.week, self.day = dt.now().isocalendar()
        # If Monday starts with 0 or 1. Adjust it.
        self.day += first_wkday_num - 1

        # URL
        self.main_url = protocol + hostname
        self.query_url = self.main_url + path

        # Data-related
        self._rawdata_buffer = []
        # Usable data in dict form.
        self.data = {}

    def query_site(self, query_arg: str, find_tag: str, tag_class: str):
        self._rawdata_buffer += BeautifulSoup(
            requests.get(self.query_url + query_arg, self.timeout).content, "html.parser"
        ).find_all(find_tag, class_=tag_class)

    def set_timeout(self, timeout):
        self.timeout = timeout

    def sort_data():
        pass

    def post_data():
        pass


class QueryPostSiteF(QueryPost):
    # To be a little more verbose, *args works as well
    def __init__(self, first_wkday_num: int, protocol: str, hostname: str, path: str, query: str):
        super().__init__(first_wkday_num, protocol, hostname, path)
        self.timeform = "%H:%M"
        self.time_regex = "[0-9]+:[0-9]+"
        day_succ = dt.now() + timedelta(days=1)
        self.queries = (query.format(self.year, self.week), query.format(day_succ.year, day_succ.isocalendar()[1]))

    # Query site
    def query_booking_site(self) -> bool:
        try:
            super().query_site(self.queries[0], "li", "day")
            if self.day == 6:
                super().query_site(self.queries[1], "li", "day")
            return True
        except:
            return False

    def clear_data(self):
        self.data = {}

    def sort_data(self) -> bool:
        # Don't sort if buffer is empty or there exist data.
        if not self._rawdata_buffer or self.data:
            return False
        for i in range(self.day, self.day + 2):
            bookday_list = self._rawdata_buffer[i].find_all("li")

            # Pop uncessecary header
            bookday_list.pop(0)

            # Add day to the dict
            for j in bookday_list:
                # Get booking url. IF time hasn't opened, then the url is none
                booking_url = None
                # If there is no message, then there exist a link. Add the link.
                if not j.find("span", class_="message"):
                    booking_url = self.main_url + j.find("div", class_="button-holder").find("a")["href"]
                # Check status of the booking activity. OR If there is a message then you can't book
                elif "inactive" in j["class"] or "drop" in j.find("span", class_="message").text.lower():
                    continue

                # Get "number" of slots, location and time
                location = re.sub("\n|\r|\(|\)", "", j.find("div", class_="location").text.strip())
                slots = re.sub(" |:|\n|\r|[a-zåäö]+", "", j.find("div", class_="status").text.lower())
                start_end = [x.split(":") for x in re.sub(" |\n|\r", "", j.find("div", class_="time").text).split("-")]
                txs = [int(t) for subxs in start_end for t in subxs]
                stime = dt(self.year, dt.now().month, dt.now().day, txs[0], txs[1]) + timedelta(days=(i - self.day))
                end_time = stime.replace(hour=txs[2], minute=txs[3])

                # Check if all slots are taken and there is 2hours or less, then continue. You can't unbook less than 2hours.
                if slots == "0" and (stime - dt.now()) <= timedelta(hours=2):
                    continue

                # If current location doesn't exist, and day, add an empty dict
                if not self.data.get(location):
                    self.data[location] = {}

                # Add booking_url and number of slots to the list.
                # Keys: Location, WeekDay, start DateTime
                self.data[location][stime] = (end_time, booking_url, slots)
        # Clear the buffer
        self._rawdata_buffer = []
        return True

    def post_data(self, booking_url, logindata):
        try:
            response = requests.get(booking_url, self.timeout)
        except:
            return (False, "Failed to get booking link")

        # Check if response is correct. Http evaluates: 200-400 is true, else is false.
        if response:
            # Soupify it, to extract data to post from 'form', then find all inputs.
            soup_response = BeautifulSoup(response.content, "html.parser").find("form")

            # Data to post
            payload = {}
            for i in soup_response.find_all("input"):
                try:
                    payload[i["id"]] = i["value"]
                except:
                    try:
                        payload[i["name"]] = i["value"]
                    except:
                        pass
            payload["Username"] = logindata.get("username")
            payload["Password"] = logindata.get("password")

            # Send data
            try:
                sent = requests.post(self.main_url + soup_response["action"], data=payload)
                if sent:
                    booking_status_soup = BeautifulSoup(sent.content, "html.parser").find("p", class_="error")
                    # Check if the post returned error. If no error, then the statement evaluates as None.
                    if not booking_status_soup:
                        return (True, "Successfully booked {} at {}")
                    else:
                        print(booking_status_soup, file=sys.stderr)
                        error_code = re.sub(" |\r|\n", "", booking_status_soup.text).lower()
                        if re.match(".+?maxantalbokningar", error_code):
                            return (True, "Error: Already booked {} at {}")
                        elif re.search("felaktigt", error_code):
                            return (False, "Error: Wrong username or password.")
                        else:
                            return (False, "Error: Failed to book.")
            except:
                pass
        return (False, "Error: Failed to send data.")

    def get_data(self):
        return self.data

    def get_timeform(self):
        return self.timeform


# Thought of a facade pattern to make it easier to handle.
# Might need some refactoring... Whatever... Strong dependency to QPSF. MC is a weak entity though.
class MainController:
    def __init__(self, first_wkday_num: int, protocol: str, hostname: str, path: str, query: str, search_freq=90):
        self.control = QueryPostSiteF(first_wkday_num, protocol, hostname, path, query)
        self.attempts = 0
        self.booked = False
        self.timeform = self.control.get_timeform()
        self.search_freq = search_freq

        # Data
        self.location = None
        self.timeslot = None
        self.timeslot_data = None

    def get_allbookings(self):
        return self.control.data

    def get_location_list(self) -> list:
        loc_keys = list(self.control.data)
        list.sort(loc_keys)
        return loc_keys

    def query_booking_sort(self):
        b = self.control.query_booking_site()
        if b:
            self.control.sort_data()
        return b

    def post_data(self, link, logindata):
        res = self.control.post_data(link, logindata)
        if res[0]:
            self.booked = True
        return res

    def set_timeslot(self, timeslot):
        self.timeslot = timeslot

    def get_timeform(self):
        return self.timeform

    def set_location(self, location):
        self.location = location

    def get_location(self):
        return self.location

    def get_timeslot(self):
        return self.timeslot

    # Returns list for that particular location -> [("String", datetime, url_string)]
    def get_slotlist_string(self, location=None):
        loc = location if location else self.location
        if not loc:
            return []

        slot_strings = []
        slot_list = self.control.data.get(loc)
        slot_keys = tuple(slot_list)

        for t in slot_keys:
            item = slot_list.get(t)
            to_print = f"{day_int_to_str(t.weekday())}, {time_interval_str(t, item[0], self.timeform)}, slots:"
            if item[1]:
                to_print += " " + item[2]
            else:
                to_print += " not unlocked"
            slot_strings.append((to_print, t, item[1]))
        return slot_strings

    def slot_time_interval(self, ts1=None, ts2=None) -> str:
        t1 = ts1 if ts1 else self.timeslot
        t2 = ts2 if ts2 else (self.get_timeslot_data()[0] if self.location and self.timeslot else None)
        if not (t1 and t2):
            return ""
        return f"{dt.strftime(t1, self.timeform)}-{dt.strftime(t2, self.timeform)}"

    def get_all_timeslots(self, location=None):
        loc = location if location else self.location
        if not loc:
            return ()
        return tuple(self.control.data.get(loc))

    def get_payload_dict(self):
        return {loc: self.get_slotlist_string(loc) for loc in self.get_location_list()}

    def get_booked(self):
        return self.booked

    def get_timeslot_data(self, location=None, timeslot=None):
        loc = location if location else self.location
        ts = timeslot if timeslot else self.timeslot
        if not (loc and ts):
            return None
        return self.control.data.get(loc).get(ts)

    def get_attempts(self):
        return self.attempts

    def succ_attempts(self):
        self.attempts += 1

    def get_search_freq(self):
        return self.search_freq

    def set_search_freq(self, search_freq):
        self.search_freq = search_freq


def p():
    print("Hello there")


def disable_win32_quickedit():
    import ctypes

    # Disable quickedit since it freezes the code.
    if sys.platform == "win32":
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), (0x4 | 0x80 | 0x20 | 0x2 | 0x10 | 0x1 | 0x00 | 0x100))


def get_user_input(max_value: int):
    user_input = input()
    if user_input.isdigit():
        user_input = int(user_input)
        if 1 <= user_input <= int(max_value):
            return user_input - 1
        elif user_input == 0:
            return None
    elif user_input and user_input[0] in ["e", "q"]:
        sys.exit()
    print("Enter a valid input!")
    return get_user_input(max_value)


def day_int_to_str(value):
    return {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}.get(value)


def time_interval_str(time_from: dt, time_to: dt, timeform) -> str:
    return dt.strftime(time_from, timeform) + "-" + dt.strftime(time_to, timeform)


def select_day_time(object: MainController):
    # Manipulate data to get day_key into a list of elements.
    # ie {day: {datetime: (slot_data)}}: [datetime,...]
    print(f"Select your time for {object.get_location()}:")
    print("  0: Return to select location")
    for i, t in enumerate(object.get_slotlist_string()):
        print(f"  {i+1}: {t}")

    all_timeslots = object.get_all_timeslots()
    user_input = get_user_input(len(all_timeslots))
    if user_input is None:
        return None
    return all_timeslots[user_input]


def select_location(loc_list):
    # Print all locations
    print("Select location:")
    print("  0: Exit")
    for i, elem in enumerate(loc_list):
        print(f"  {i+1}: {elem}")
    user_input = get_user_input(len(loc_list))
    if user_input is None:
        return None
    return loc_list[user_input]


# Example terminal. Follow same pattern for webapp.
def main(object: MainController, logindata):
    while not object.get_booked():
        # Check if request getting page is successful
        if object.query_booking_sort():
            # Select Booking slot
            while not object.get_timeslot():
                object.set_location(select_location(object.get_location_list()))
                if object.get_location() is None:
                    return
                object.set_timeslot(select_day_time(object))

            # Save the data for the timeslot. May end up as None if timeslot becomes unavailable: Passed the time etc..
            # timeslot = selected_time
            # timeslot_data = (endtime, link = (None | Str), slots)
            if not object.get_timeslot_data():
                return print("Selected location and time is unavailable, stopping")

            # If Link is None, then wait until there are less or equal to 24h to that slot.
            # Then continue to query the booking again also to get a link.
            time_interval_string = object.slot_time_interval()
            if not object.get_timeslot_data()[1]:
                sleep_time = (object.get_timeslot() - dt.now()).total_seconds() + 20
                print(
                    f"Sleeping for {sleep_time} seconds to try to book {time_interval_string} at {object.get_location()}:"
                )
                countdown_blocking(sleep_time)
                print("Trying to book.")
                continue

            if object.get_timeslot_data()[2] == "0":
                print("No slots available...")
            else:
                booked = object.post_data(object.get_timeslot_data()[1], logindata)

        if not booked[0]:
            object.succ_attempts()
            print(f"Retry to book in {obj.get_search_freq()} seconds, total booking attempts: {object.get_attempts()}")
            countdown_blocking(object.get_search_freq())
        else:
            print(booked[1].format(time_interval_string, object.get_location()))


def countdown_blocking(value):
    for i in range(value, -1, -1):
        sys.stdout.write("\r")
        sys.stdout.write(f" {i} seconds remaining.")
        sys.stdout.flush()
        time.sleep(-time.time() % 1)
    sys.stdout.write("\r\n")
    sys.stdout.flush()


def load_json():
    # Load JSON data
    filepath = os.path.dirname(os.path.realpath(__file__)) + "\\data.json"
    with open(filepath, "r") as f:
        return json.load(f)


if __name__ == "__main__":
    # Search every # seconds. Default value.
    dat = load_json()

    # Username and pass
    logindata = {"username": dat["login"]["username"], "password": dat["login"]["password"]}

    # Create object
    obj = MainController(0, dat["site"]["protocol"], dat["site"]["hostname"], dat["site"]["path"], dat["site"]["query"])

    try:
        if sys.argv[1].isdigit() and 0 < int(sys.argv[1]):
            obj.set_search_freq(int(sys.argv[1]))
        else:
            print(f"Invalid search delay time. Resorts to default {obj.get_search_freq()} seconds")
    except:
        pass

    disable_win32_quickedit()
    main(obj, logindata)
