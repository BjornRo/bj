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

    def query_site(self, query_arg: str, find_tag: str, tag_class: str) -> list:
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

    def clear_data(self) -> bool:
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
                        error_code = re.sub(" |\r|\n", "", booking_status_soup.text)
                        if re.match(".+?maxantalbokningar", error_code):
                            return (True, "Error: Already booked {} at {}")
                        else:
                            return (False, "Error: Failed to book")
            except:
                pass
        return (False, "Error: Failed to send data")

    def get_data(self):
        return self.data

    def get_timeform(self):
        return self.timeform


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


def select_location(bookingslist: list):
    # Key for location
    loc_keys = list(bookingslist)
    list.sort(loc_keys)

    # Print all locations
    print("Select location:")
    print("  0: Exit")
    for i, elem in enumerate(loc_keys):
        print(f"  {i+1}: {elem}")
    user_input = get_user_input(len(bookingslist))
    if user_input is None:
        return None
    return loc_keys[user_input]


def select_day_time(all_bookings: list, location, tf):
    slotlist = all_bookings.get(location)
    # Manipulate data to get day_key into a list of elements.
    # ie {day: {datetime: (slot_data)}}: [datetime,...]
    all_timeslots = tuple(slotlist)

    print(f"Select your time for {location}:")
    print("  0: Return to select location")
    for i, t in enumerate(all_timeslots):
        to_print = f"  {i+1}: {day_int_to_str(t.weekday())}, {time_interval_str(t, slotlist.get(t)[0], tf)}, slots:"
        if slotlist.get(t)[1]:
            to_print += " " + slotlist.get(t)[2]
        else:
            to_print += " not unlocked"
        print(to_print)

    user_input = get_user_input(len(all_timeslots))
    if user_input is None:
        return None
    return all_timeslots[user_input]


def day_int_to_str(value):
    return {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}.get(value)


def time_interval_str(time_from: dt, time_to: dt, timeform) -> str:
    return dt.strftime(time_from, timeform) + "-" + dt.strftime(time_to, timeform)


def main(object, logindata, search_frequency):
    attempts = 0
    booked = False
    timeslot = None
    while not booked:
        # Check if request getting page is successful
        if object.query_booking_site():
            object.sort_data()
            timeform = object.get_timeform()
            all_bookings = object.get_data()
            # Select Booking slot
            while not timeslot:
                location = select_location(all_bookings)
                if location is None:
                    return
                timeslot = select_day_time(all_bookings, location, timeform)

            # Save the data for the timeslot. May end up as None if timeslot becomes unavailable: Passed the time etc..
            # timeslot = selected_time
            # timeslot_data = (endtime, link = (None | Str), slots)
            try:
                timeslot_data = all_bookings.get(location).get(timeslot)
            except:
                return print("Selected location and time is unavailable, stopping")

            # If Link is None, then wait until there are less or equal to 24h to that slot.
            # Then continue to query the booking again also to get a link.
            time_interval_string = time_interval_str(timeslot, timeslot_data[0], timeform)
            if not timeslot_data[1]:
                sleep_time = (timeslot - dt.now()).total_seconds() + 20
                print(f"Sleeping for {sleep_time} seconds to try to book {time_interval_string} at {location}:")
                countdown_blocking(sleep_time)
                print("Trying to book.")
                continue

            if timeslot_data[2] == "0":
                print("No slots available...")
            else:
                booked = object.post_data(timeslot_data[1], logindata)

        if not booked[0]:
            print(f"Retry to book in {search_frequency} seconds, total booking attempts: {attempts}")
            countdown_blocking(search_frequency)
        else:
            print(booked[1].format(time_interval_string, location))


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
    search_frequency = 90

    try:
        if sys.argv[1].isdigit() and 0 < int(sys.argv[1]):
            search_frequency = int(sys.argv[1])
        else:
            print(f"Invalid search delay time. Resorts to default {search_frequency} seconds")
    except:
        pass

    dat = load_json()

    # Username and pass
    logindata = {"username": dat["login"]["username"], "password": dat["login"]["password"]}

    # Create object
    obj = QueryPostSiteF(0, dat["site"]["protocol"], dat["site"]["hostname"], dat["site"]["path"], dat["site"]["query"])

    disable_win32_quickedit()
    main(obj, logindata, search_frequency)
