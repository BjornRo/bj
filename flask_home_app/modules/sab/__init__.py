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
* OOP

"""

from typing import Union
import requests
from bs4 import BeautifulSoup
import re
import os
import json
from datetime import datetime, timedelta


class QueryPost:
    def __init__(
        self,
        first_wkday_num: int,
        protocol: str,
        hostname: str,
        path: str,
        query: str,
        timeform=None,
        timeout=10,
    ):
        # Timeout for requests, default 10.
        self.timeout = timeout
        # Time related
        self.time_now = datetime.now()
        self.year, self.week, _ = self.time_now.isocalendar()
        self.wkday = self.time_now.weekday() + first_wkday_num
        # Timeform datetime: Example %H:%M | %H-%M
        self.timeform = timeform
        self.first_wkday_num = first_wkday_num

        # URL
        self.main_url = protocol + hostname
        self.query_url = self.main_url + path
        self.query = query

        # Data-related
        self._buffer_full = False
        self._rawdata_buffer = []
        # Usable data in dict form.
        self.data = {}

    def update_time(self) -> None:
        self.time_now = datetime.now()
        self.year, self.week, _ = self.time_now.isocalendar()
        self.wkday = self.time_now.weekday() + self.first_wkday_num

    def query_site(self, query_arg: str, find_tag: str, tag_class: str) -> bool:
        if not self._buffer_full:
            try:
                self._rawdata_buffer += BeautifulSoup(
                    requests.get(self.query_url + query_arg, self.timeout).content, "html.parser"
                ).find_all(find_tag, class_=tag_class)
                self._buffer_full = True
            except:
                pass
        return self._buffer_full

    def sort_data() -> bool:
        raise NotImplementedError

    def post_data() -> tuple:
        raise NotImplementedError

    def flush_buffer(self) -> None:
        self._rawdata_buffer.clear()
        self._buffer_full = False


class QueryPostSiteF(QueryPost):
    # To be a little more verbose, *args works as well
    def __init__(
        self,
        first_wkday_num: int,
        protocol: str,
        hostname: str,
        path: str,
        query: str,
        timeform: str,
    ):
        super().__init__(first_wkday_num, protocol, hostname, path, query, timeform)
        self.queries = None

    def update_time(self) -> None:
        super().update_time()

    # Query site
    def query_site_with_args(self) -> bool:
        # Always keep up to wkday.
        self.update_time()
        self.queries = (
            self.query.format(self.year, self.week),
            self.query.format(*(self.time_now + timedelta(days=1)).isocalendar()[:2]),
        )
        b = self.query_site(self.queries[0], "li", "day")
        if b and self.wkday == (6 + self.first_wkday_num):
            self._buffer_full = False
            b = self.query_site(self.queries[1], "li", "day")
        return b

    def sort_data(self) -> bool:
        # Don't sort if buffer is empty or there exist data.
        if not self._rawdata_buffer:
            return False

        for i in range(self.wkday, self.wkday + 2):
            # Add all slots for the day and next day to the dict
            for j in self._rawdata_buffer[i].find_all("li")[1:]:
                # Get booking url. IF time hasn't opened, then the url is none
                url = None
                # If there is no message, then there exist a link. Add the link.
                if not j.find("span", class_="message"):
                    url = self.main_url + j.find("div", class_="button-holder").find("a")["href"]
                # Check status, if neither are true: then booking slot hasn't unlocked yet.
                elif "inactive" in j["class"] or re.search(
                    "drop", j.find("span", class_="message").text, re.I
                ):
                    continue
                # Get "number" of slots, location and time
                location = re.sub(
                    ".*\(|\).*", "", j.find("div", class_="location").text, flags=re.S
                )
                slots = re.sub("[^>0-9]", "", j.find("div", class_="status").text)
                t_start_end_elem = [
                    dict(zip(("hour", "minute"), map(int, t)))
                    for t in re.findall("(\d+):(\d+)", j.find("div", class_="time").text)
                ]
                start_time = datetime(
                    *self.time_now.timetuple()[:3], **t_start_end_elem[0]
                ) + timedelta(days=(i - self.wkday))
                end_time = start_time.replace(**t_start_end_elem[1])

                # Check if all slots are taken and there is 2hours or less, then continue. You can't unbook less than 2hours.
                if slots == "0" and (start_time - self.time_now) <= timedelta(hours=2):
                    continue

                # If current location doesn't exist, and wkday, add an empty dict
                if not self.data.get(location):
                    self.data[location] = {}

                self.data[location][start_time] = {"end_time": end_time, "url": url, "slots": slots}
        return True

    def post_data(self, booking_url: str, user: str, passw: str) -> tuple:
        if not (isinstance(booking_url, str) and isinstance(user, str) and isinstance(passw, str)):
            return (False, "Error: Invalid booking url, and/or invalid logindata")
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
                    payload[i["name"]] = i["value"]
                except:
                    pass
            payload["Username"] = user
            payload["Password"] = passw

            # Send data
            try:
                sent = requests.post(self.main_url + soup_response["action"], data=payload)
                if sent:
                    error_msg = BeautifulSoup(sent.content, "html.parser").find("p", class_="error")
                    # Check if the post returned error. If no error, then the statement evaluates as None.
                    if not error_msg:
                        return (True, "Successfully booked {} at {}")
                    else:
                        error_code = re.sub(" ", "", error_msg.text.strip()).lower()
                        if "maxantalbokningar" in error_code:
                            return (True, "Error: Already booked {} at {}")
                        elif "felaktigt" in error_code:
                            return (False, "Error: Wrong username or password.")
                        else:
                            return (False, "Error: Failed to book.")
            except:
                pass
        return (False, "Error: Failed to send data.")


# Thought of a facade pattern to make it easier to handle.
# Might need some refactoring... Whatever... Strong dependency to QPSF. MC is a weak entity though.
class MainController:
    def __init__(
        self,
        first_wkday_num: int,
        protocol: str,
        hostname: str,
        path: str,
        query: str,
    ):
        self.control = QueryPostSiteF(first_wkday_num, protocol, hostname, path, query, "%H:%M")
        self.days = {
            i + first_wkday_num: v
            for i, v in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
        }

        # Data
        self.attempts = 0

    def query_booking_sort(self) -> bool:
        if self.control.query_site_with_args() and self.control.sort_data():
            self.control.flush_buffer()
            return True
        return False

    def post_data(self, link: str, logindata: dict) -> tuple:
        return self.control.post_data(link, logindata)

    def get_location_list(self) -> list:
        loc_keys = list(self.control.data)
        list.sort(loc_keys)
        return loc_keys

    # Returns list for that particular location -> [("String", datetime, url_string)]
    def get_slotlist_string(self, location=None) -> Union[list, None]:
        loc = location if location else self.location
        if not isinstance(loc, str):
            return None

        slot_strings = []
        for k_dt, v_dict in self.control.data.get(loc).items():
            end_dt, url, slots = v_dict.values()
            dayname = self.days.get(k_dt.weekday() + self.control.first_wkday_num)
            p_str = f"{dayname}, {self.slot_time_interval(k_dt, end_dt)}, slots: {slots if url else 'not unlocked'}"
            slot_strings.append((p_str, k_dt, url, True if url and slots != "0" else False))
        return slot_strings

    def slot_time_interval(self, t1, t2) -> Union[str, None]:
        if isinstance(t1, datetime) and isinstance(t2, datetime):
            return f"{datetime.strftime(t1, self.control.timeform)}-{datetime.strftime(t2, self.control.timeform)}"
        return None

    def get_payload_dict(self) -> dict:
        return {loc: self.get_slotlist_string(loc) for loc in self.get_location_list()}

    def get_attempts(self) -> int:
        return self.attempts

    def succ_attempts(self) -> None:
        self.attempts += 1


def load_json() -> dict:
    with open(os.path.dirname(os.path.realpath(__file__)) + "\\data.json", "r") as f:
        return json.load(f)
