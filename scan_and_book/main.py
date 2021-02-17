import requests
from bs4 import BeautifulSoup
import re
import time
import json
from datetime import datetime, timedelta

# Search every # seconds.
search_frequency = 20

# Load JSON data
with open("data.json", "r") as f:
    data = json.load(f)

site = data["site"]["main"]
sub_url = data["site"]["sub"]

# Username and pass
username = data["login"]["username"]
password = data["login"]["password"]


#https://fysiken.nu/sv/boka?units=1133&units=1742&units=1766&locale=sv-SE

# Functions
def sort_and_order_bookinglist(soup: list):
    # Find the bookings
    souplist = soup.find("li", class_="day active").find_all("li")
    # Pop the first element since it doesn't contain any valuable info.
    souplist.pop(0)

    # Empty dict
    booking_list = {}

    # Time related, to sort out unavailable times.
    tf = "%H:%M"
    tb = "[0-9]+:[0-9]+"
    time_now = datetime.strptime(datetime.now().strftime(tf), tf)

    # Add all relevant data for each booking at each location
    for i in souplist:
        # Main key
        location = re.sub("\n|\r|\(|\)", "", i.find("div", class_="location").text.strip())
        time_book = re.sub(" |\n|\r", "", i.find("div", class_="time").text)
        booking_url = site + i.find("div", class_="button-holder").find("a")["href"]
        slots = re.search(":(>[0-9]+|[0-9]+)", re.sub(" |\n|\r", "", i.find("div", class_="status").text))

        # If slots is empty(drop in etc), then just ignore(continue the loop)
        if not slots:
            continue

        # Check if all slots are taken and there is 2hours or less, then continue. You can't unbook less than 2hours.
        if slots[1] == "0" and datetime.strptime(re.search(tb, time_book)[0], tf) - time_now <= timedelta(hours=2):
            continue

        # If current location doesn't exist, add an empty dict
        if not booking_list.get(location):
            booking_list[location] = {}

        # Add time as key, then bookingurl and slots in a tuple
        booking_list[location][time_book] = (booking_url, slots[1])
    return booking_list


def select_location(bookingslist: list):
    # Key for location
    loc_keys = list(bookingslist)

    # Print all locations
    print("Select location:")
    for i, elem in enumerate(loc_keys):
        print(f"  {i}: {elem}")

    # Get user input and check if it's valid
    user_in = input()
    if user_in.isdigit() and (0 <= int(user_in) < len(bookingslist)):
        return bookingslist[loc_keys[int(user_in)]]
    print("Enter a valid input!")
    select_location(bookingslist)


def select_time(bookingslist: list):
    # Key for time
    time_keys = list(bookingslist)

    print("Select your time:")
    for i, elem in enumerate(time_keys):
        print(f"  {i}: {time_keys[i]}, slots: {bookingslist[elem][1]}")
    user_in = input()
    if user_in.isdigit() and (0 <= int(user_in) < len(bookingslist)):
        return bookingslist[time_keys[int(user_in)]][0]
    print("Enter a valid input!")
    select_time(bookingslist)


def main():
    # Set to None, to make the algorithm try to automatically book the later selected time.
    timeslot_link = None

    # Flag if it hasn't booked.
    booked = False

    while not booked:
        # Access main booking page
        try:
            response = requests.get(site + sub_url, timeout=10)
        except:
            print("Failed to connect to URL")
            time.sleep(10)
            continue

        # Check if request getting page is successful
        if response:
            # Get all bookings
            all_bookings = sort_and_order_bookinglist(BeautifulSoup(response.content, "html.parser"))

            # Check if there are any available times for the day.
            if not all_bookings:
                print("No available times for the day")
                break

            # Select Booking
            if not timeslot_link:
                timeslot_link = select_time(select_location(all_bookings))

            booked = True  # post_data(timeslot_link)

        if not booked:
            print("No slots")
            time.sleep(search_frequency)


def post_data(url_str: str):
    try:
        response = requests.get(url_str, timeout=10)
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
            sent = requests.post(site + soup_response["action"], data=payload)
            if sent:
                # Check if the post returned error. If no error, then the statement evaluates as None.
                if not BeautifulSoup(sent.content, "html.parser").find("form").find("p", class_="error"):
                    print("Successfully Booked")
                    return True
        except:
            pass
    return False


if __name__ == "__main__":
    main()
