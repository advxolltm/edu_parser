import asyncio
import json
import logging
import os
import time
from datetime import datetime

import certifi
from bs4 import BeautifulSoup as bs
from mechanize import Browser

from .ProxyManager import proxy_manager

URL = "https://appointment.bmeia.gv.at/"

DATEFORMAT = "%m/%d/%Y %I:%M:%S %p"


class ConsulateParser:
    def __init__(self):
        self.data = {
            # "city": {
            #       "data": [],
            #       "is_updated": False
            # }
        }
        self.cities = None

    async def initialize(self):
        logging.info("Initializing consulate parser")
        while True:
            try:
                self.parse_cities()
                base_path = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..")
                )
                db_path = os.path.join(base_path, "db.json")

                with open(db_path, "r") as f:
                    data = json.load(f)
                    if "consulate_subscribers" in data.keys():
                        for city in data["consulate_subscribers"].keys():
                            self.add_city_to_updates(city)
                break
            except Exception as e:
                logging.error(e)
                await asyncio.sleep(10)
        logging.info("Consulate parser initialized")

    def parse_cities(self):
        br = Browser()
        br.set_proxies(
            {
                "http": proxy_manager.get_proxy_string(),
                "https": proxy_manager.get_proxy_string(),
            }
        )

        br.set_handle_robots(False)  # ignore robots
        br.set_ca_data(cafile=certifi.where())
        br.addheaders = [("User-agent", "Firefox")]
        br.open(URL)
        time.sleep(5)
        page = bs(br.response().read(), "html.parser")
        cities = page.find("select", {"name": "Office"}).find_all("option")
        cities = [city.text for city in cities]
        cities.pop(0)
        self.cities = cities

    def parse_appointment(self, city: str):
        br = Browser()
        br.set_proxies(
            {
                "http": proxy_manager.get_proxy_string(),
                "https": proxy_manager.get_proxy_string(),
            }
        )
        br.set_handle_robots(False)  # ignore robots
        br.set_ca_data(cafile=certifi.where())
        br.addheaders = [("User-agent", "Firefox")]
        br.open(URL)
        time.sleep(5)
        br.select_form(nr=0)
        br.form["Office"] = [city]
        response = br.submit()
        time.sleep(5)
        page = bs(response.read(), "html.parser")
        value = page.find("option", string=lambda text: "Aufenthaltstitel" in text).get(
            "value"
        )
        br.select_form(nr=0)
        br.form["CalendarId"] = [value]
        response = br.submit(type="submit", name="Command", nr=0)
        time.sleep(5)
        br.select_form(nr=0)
        br.form["PersonCount"] = ["1"]
        response = br.submit(type="submit", name="Command", nr=2)
        time.sleep(5)
        br.select_form(nr=0)
        response = br.submit(type="submit", name="Command", nr=1)
        time.sleep(5)
        page = bs(response.read(), "html.parser")
        radioInputs = page.find_all("input", {"type": "radio"})
        if not radioInputs:
            raise Exception("No appointments available")

        appointments = []
        for radio in radioInputs:
            parsedTime = datetime.strptime(radio.get("value"), DATEFORMAT)

            appointments.append(
                f'{parsedTime.strftime("%d.%m.%Y")} в {parsedTime.strftime("%H:%M")}'
            )

        return appointments

    def add_city_to_updates(self, city):
        if city not in self.data.keys():
            self.data[city] = {"data": [], "is_updated": True}

    def delete_city_from_updates(self, city):
        if city in self.data.keys():
            del self.data[city]

    async def check_updates(self):
        for city in self.data.keys():
            old_appointments = self.data[city]["data"]
            appointments = self.parse_appointment(city)
            if appointments != old_appointments:
                self.data[city]["is_updated"] = True
                self.data[city]["data"] = appointments
                return self.data
            else:
                self.data[city]["is_updated"] = False

    def get_data(self):
        return self.data

    def get_cities(self):
        return self.cities
