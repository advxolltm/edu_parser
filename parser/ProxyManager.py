import logging
import os
import time

import requests


class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.active_proxy = None

    async def initialize(self):
        logging.info("Proxy manager: initializing")
        try:
            response = requests.get(
                os.environ.get("API_URL_PROXY"),
                headers={"Authorization": f"Token {os.environ.get('API_KEY_PROXY')}"},
                timeout=10,
            )
            if response.status_code != 200:
                logging.error(
                    "Failed request to get proxies with status code: "
                    + str(response.status_code)
                )
                return
            self.proxies = response.json()["results"]
            logging.info("Proxy manager: initialized")
        except Exception as e:
            logging.error("Failed to get proxies due to error: " + str(e))
            return

    def change_proxy(self):
        if self.active_proxy == None:
            self.active_proxy = self.proxies.pop()
        else:
            self.proxies.insert(0, self.active_proxy)
            self.active_proxy = self.proxies.pop()

    def get_new_proxy(self):
        self.change_proxy()
        is_proxy_works = self.check_proxy()
        if not is_proxy_works:
            return self.get_new_proxy()

        return self.get_proxy_string()

    def check_proxy(self):

        try:
            proxy_string = self.get_proxy_string()
            time.sleep(2)
            response = requests.get(
                "https://google.com",
                proxies={
                    "https": f"{proxy_string}",
                },
                timeout=10,
            )
            if response.status_code == 200:
                logging.info(f"Proxy {proxy_string} is working")
                return True
            logging.warning(f"Proxy {proxy_string} is NOT working")
            return False

        except Exception as e:
            logging.warning(f"Proxy {self.get_proxy_string()} is NOT working")
            return False

    def get_proxy_string(self):
        return f'{self.active_proxy["proxy_address"]}:{self.active_proxy["port"]}'


proxy_manager = ProxyManager()
