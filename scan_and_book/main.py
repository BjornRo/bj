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
import json
from datetime import datetime, timedelta

# Search every # seconds.
search_frequency = 20

# Date related
year, week, _ = datetime.today().isocalendar()
day = datetime.today().isocalendar()[2] - 1
days = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}

# Load JSON data
with open("data.json", "r") as f:
    data = json.load(f)

# Links - url
main_url = data["site"]["main_url"]
bookings_url = data["site"]["bookings_url"]

# Week, Week+1
queries = (
    data["site"]["query"].format(year, week),
    data["site"]["query"].format(year, (week % datetime(year, 12, 31).isocalendar()[1]) + 1),
)

# Username and pass
username = data["login"]["username"]
password = data["login"]["password"]

# Functions
def get_user_input(max_value: int):
    user_input = input()
    if user_input.isdigit():
        user_input = int(user_input)
        if 1 <= user_input <= int(max_value):
            return user_input - 1
        elif user_input == 0:
            return None
    print("Enter a valid input!")
    return get_user_input(max_value)


def post_data(main_url, url_str: str):
    try:
        response = requests.get(url_str, timeout=15)
    except:
        print("Failed to get booking link")
        return False

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
        payload["Username"] = username
        payload["Password"] = password

        # Send data
        try:
            sent = requests.post(main_url + soup_response["action"], data=payload)
            if sent:
                booking_status_soup = BeautifulSoup(sent.content, "html.parser").find("p", class_="error")
                # Check if the post returned error. If no error, then the statement evaluates as None.
                if not booking_status_soup:
                    print("Successfully Booked")
                    return True
                else:
                    error_code = re.sub(" |\r|\n", "", booking_status_soup.text)
                    if re.match(".+?maxantalbokningar", error_code):
                        print("Error: Already booked - Task failed successfully")
                        return True
                    else:
                        print("Error: Failed to book")
        except:
            pass
    return False


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
    else:
        return loc_keys[user_input]


def select_day_time(bookingslist: list):
    # Key for time
    time_keys = list(bookingslist)

    print("Select your time:")
    print("  0: Select location")
    for i, elem in enumerate(time_keys):
        slot_elem = bookingslist.get(elem)
        print(f"  {i+1}: {slot_elem[2]}, {time_keys[i]}, slots: {slot_elem[1]}")
    user_input = get_user_input(len(bookingslist))
    if user_input is None:
        return None
    else:
        return time_keys[user_input]


def get_bookings(day, query1, query2):
    # Access booking pages
    prsr = "html.parser"
    try:
        bookings = BeautifulSoup(requests.get(query1, timeout=10).content, prsr).find_all("li", class_="day")
        if day == 6:
            bookings += BeautifulSoup(requests.get(query2, timeout=10).content, prsr).find_all("li", class_="day")
        return bookings
    except:
        print("Failed to connect to URL")
        return None


# Returns {location: {day: {time: (link, slots)}}}
def sort_and_order_bookinglist(main_url, day, unsorted_bookings: list):
    # Time related, to sort out unavailable times.
    tf, tb = "%H:%M", "[0-9]+:[0-9]+"
    time_now = datetime.strptime(datetime.now().strftime(tf), tf)

    # Empty dict. Can be in for loop due to python scope. C-like programmers would be confused though...
    booking_list = {}

    # Add all relevant data for each booking at each location.
    # For loop looks like going i out of array but if sunday, next week is added...
    for i in range(day, day + 2):
        bookday_list = unsorted_bookings[i].find_all("li")

        # Pop uncessecary header
        bookday_list.pop(0)

        # Add day to the dict
        for j in bookday_list:
            # Check status of the booking activity. OR If there is a message then you can't book
            if "inactive" in j["class"] or j.find("span", class_="message"):
                continue

            # Main key
            location = re.sub("\n|\r|\(|\)", "", j.find("div", class_="location").text.strip())
            time_book = re.sub(" |\n|\r", "", j.find("div", class_="time").text)
            booking_url = main_url + j.find("div", class_="button-holder").find("a")["href"]
            slots = re.search(":(>[0-9]+|[0-9]+)", re.sub(" |\n|\r", "", j.find("div", class_="status").text))

            # Check if all slots are taken and there is 2hours or less, then continue. You can't unbook less than 2hours.
            if slots[1] == "0" and datetime.strptime(re.search(tb, time_book)[0], tf) - time_now <= timedelta(hours=2):
                continue

            # If current location doesn't exist, add an empty dict
            if not booking_list.get(location):
                booking_list[location] = {}

            # Add time as key, then bookingurl and slots in a tuple
            booking_list[location][i] = {time_book: (booking_url, slots[1])}
    return booking_list


def main():
    # Set to None, to make the algorithm try to automatically book the later selected time.
    timeslot = None

    # Flag if it hasn't booked.
    booked = False

    while not booked:
        unsorted_bookings = get_bookings(day, bookings_url + queries[0], bookings_url + queries[1])
        # Check if request getting page is successful
        if unsorted_bookings:
            # Get all bookings, today and tomorrow
            all_bookings = sort_and_order_bookinglist(main_url, day, unsorted_bookings)
            xs = all_bookings

            # Check if there are any available times for the day.
            if not all_bookings:
                print("No available times for the day")
                break

            # Select Booking
            while not timeslot:
                location = select_location(all_bookings)
                if location is None:
                    return
                day, time_ = select_day_time(all_bookings.get(location), days)
                if timeslot[1] is None:
                    timeslot = None

            # Save the data for the timeslot. May end up as None if timeslot becomes unavailable: Passed the time etc..
            timeslot_data = all_bookings.get(timeslot[0]).get(timeslot[1])

            if timeslot_data:
                if timeslot_data[1] == "0":
                    print("No slots available...")
                else:
                    booked = post_data(main_url, timeslot_data[0])
            else:
                print("Selected location and time is unavailable, stopping")
                return

        if not booked:
            print(f"Retrying after {search_frequency} seconds...")
            time.sleep(search_frequency)


if __name__ == "__main__":
    main()
