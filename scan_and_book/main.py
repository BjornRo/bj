import requests
from bs4 import BeautifulSoup
import re
import time
import json
import os
from datetime import datetime, timedelta

# time_slot: "" or "19:45-21:45"...
time_slot = ""
where = "Centrum"  # Sisjön, Partille

# Search every # seconds.
search_frequency = 20

# Load JSON data
with open('data.json', 'r') as f:
    data = json.load(f)

site = data['site'][0]['main']
sub_url = data['site'][0]['sub']

# Username and pass
username = data['login'][0]['username']
password = "pSXNRHx6642r!zT"

def main():
    global time_slot

    # Flag if it hasn't booked.
    booked = False

    while not booked:
        try:
            response = requests.get(site + sub_url, timeout=10)
        except:
            print("Failed to connect to URL")
            time.sleep(10)
            continue

        # Check if request getting page is successful
        if response:
            # Get all bookings
            bookings = clean_bookinglist(BeautifulSoup(response.content, "html.parser"), where)

            # Set response to None to discard the data.
            response = None

            # Check if there are any available times for the day.
            if not bookings:
                print("No available times for the day")
                break

            # If there is no specified time_slot, print and let user choose.
            # Also check if the timeslot is valid
            if not time_slot:
                time_slot = print_times_and_get_user_input(bookings)
            else:
                for i in bookings:
                    if time_slot in i.text.replace(" ", ""):
                        break
                else:
                    print("Invalid time specified")
                    break

            # Check if there is more than two hours to the time chosen.
            if datetime.strptime(re.search("[0-9]+:[0-9]+", time_slot).group(0), "%H:%M") - datetime.strptime(
                datetime.now().strftime("%H:%M"), "%H:%M"
            ) <= timedelta(hours=2):
                print("No available times for the day, less than two hours")
                break

            # Next step get the timeslot link.
            timeslot_url = timeslot_link(bookings)

            if timeslot_url:
                # TODO
                booked = True  # post_data(timeslot_url)

        if not booked:
            print("No slots")
            time.sleep(search_frequency)


def print_times_and_get_user_input(bookingslist: list):
    # If there are no more times, return current time.
    if not bookingslist:
        return datetime.now().strftime("%H:%M")
    print("Select your time:")
    for i, elem in enumerate(bookingslist):
        btime = re.sub(" |\n|\r", "", elem.find("div", class_="time").text)
        bslots = re.search(":([0-9]+|>[0-9]+)", re.sub(" |\n|\r", "", elem.find("div", class_="status").text))
        print(f"  {i}: {btime}, slots: {bslots.group(1)}")
    user_in = input()
    if user_in.isdigit() and (0 <= int(user_in) < len(bookingslist)):
        return re.sub(" |\n|\r", "", bookingslist[int(user_in)].find("div", class_="time").text)
    print("Enter a valid input!")
    print_times_and_get_user_input(bookingslist)


def clean_bookinglist(soup: list, location: str):
    souplist = soup.find("li", class_="day active").find_all("li")
    # Pop the first element since it doesn't contain any valuable info.
    souplist.pop(0)

    # Remove unavailable times and times in locations thats not relevant.
    while souplist:
        if "inactive" in souplist[0]["class"] or location not in souplist[0].text:
            # Remove inactive time
            souplist.pop(0)
        else:
            break
    return souplist


# Gets the link for the timeslot
# Else None if not found/full.
def timeslot_link(all_time_slots: list):
    # Regex to match, gets the slots
    re_match = f"{time_slot}.+?{where}.+?platserkvar:([0-9]|>[0-9])"

    for i in all_time_slots:
        # If slot is None, then it hasn't found the timeslot.
        slot = re.search(re_match, re.sub(" |\n|\r", "", i.text))

        if slot:
            if slot.group(1) == "0":
                return None

            # Returns link and if timeslot is available
            return site + i.find("div", class_="button-holder").find("a")["href"]
    return None


def post_data(url_str: str):
    try:
        response = requests.get(url_str)
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
                if not BeautifulSoup(sent.content, "html.parser").find("form").find("p", class_="error"):
                    print("Successfully Booked")
                    return True
        except:
            pass
    return False


if __name__ == "__main__":
    main()
