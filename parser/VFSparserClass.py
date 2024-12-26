import asyncio
import json
import logging
import os
import time

import requests

# import seleniumwire.undetected_chromedriver.v2 as uc
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium_stealth import stealth

from .ProxyManager import proxy_manager

VFS_LOGIN_URL = "https://visa.vfsglobal.com/rus/en/aut/login"
CITIES_API_URL = "https://lift-api.vfsglobal.com/master/center/aut/rus/en-US"
SLOTS_API_URL = "https://lift-api.vfsglobal.com/appointment/CheckIsSlotAvailable"


class VFSparser:
    def __init__(self, *args, **kwargs):
        self.driver = uc.Chrome(options=self.get_chrome_options())
        stealth(
            self.driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        self.driver.execute_cdp_cmd("Network.enable", {})
        self.driver.delete_all_cookies()
        self.username = os.environ.get("VFS_USERNAME")
        self.password = os.environ.get("VFS_PASSWORD")
        self.api_key = os.environ.get("API_KEY_CAPSOLVER")

        self.is_actived = False
        self.cities = {
            # "city" : {
            #     "city": "city",
            #     "centerName": "centerName",
            #     "isoCode": "isoCode",
            #      ...
            #     "appointments": []
            #     "is_updated": False
            #     "is_need_to_be_updated": None
            #
            # }
        }

    def get_chrome_options(self):
        chrome_options = uc.ChromeOptions()
        chrome_options.add_argument("--auto-open-devtools-for-tabs")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("start-maximized")
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        chrome_options.add_argument(f"--user-agent={ua}")
        # chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        # chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument("--ignore-ssl-errors")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--ignore-certificate-errors-spki-list")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--no-zygote")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-breakpad")
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        extension_path = os.path.join(
            os.path.dirname(__file__), "capmonster_chrome_extension"
        )

        chrome_options.add_argument(f"--proxy-server={proxy_manager.get_new_proxy()}")
        chrome_options.add_argument(f"--load-extension={extension_path}")
        return chrome_options

    def change_proxy(self):
        self.driver.quit()
        self.driver = uc.Chrome(options=self.get_chrome_options())
        self.driver.delete_all_cookies()
        self.driver.execute_cdp_cmd("Network.enable", {})

    def get_element(self, by, value, timeout=10):
        iteration = 0
        while True:
            if iteration > timeout:
                self.get_screenshoot(f"{by}_{value}.png")
                logging.error(f"Failed to find element by {by} and value {value}")
                raise Exception(f"Failed to find element by {by} and value {value}")
            try:
                return self.driver.find_element(by, value)
            except Exception as e:
                # CHECK TO MANY REQUESTS
                self.check_blocked_by_captcha()
                continue
            finally:
                iteration += 1
                time.sleep(1)

    def get_screenshoot(self, name):
        self.driver.save_screenshot(f"/errors_screens/{name}.png")

    def get_check_status_code(self, code, log, url, *args):
        log = json.loads(log["message"])["message"]
        if (
            "Network.responseReceived" in log["method"]
            and "params" in log.keys()
            and "response" in log["params"].keys()
            and log["params"]["response"]["url"].startswith(url)
            and log["params"]["response"]["status"] == code
        ):
            return True
        return False

    async def set_up_driver_extension(self):
        # Открытие страницы
        self.driver.get("chrome://extensions/")
        By.TAG_NAME
        # Извлечение идентификатора расширения
        script = """
            const extension = document.getElementsByTagName('extensions-manager')[0].shadowRoot.getElementById('items-list').shadowRoot.querySelectorAll('extensions-item')
            const extension_ids = Array.from(extension).map((item) => item.getAttribute('id'))
            console.log(extension_ids)
            return extension_ids
        """

        extension_ids = self.driver.execute_script(script)
        if not extension_ids or extension_ids == []:
            raise Exception("Extension not found in chrome://extensions/")

        self.driver.get(f"chrome-extension://{extension_ids[0]}/popup.html")
        try:
            api_key_input = self.get_element(By.ID, "client-key-input")
            api_key_save_btn = self.get_element(By.ID, "client-key-save-btn")
        except Exception as e:
            raise Exception("Failed to find api key input and save button in extension")

        api_key_input.send_keys(self.api_key)
        api_key_save_btn.click()
        await asyncio.sleep(2)

    def check_blocked_by_captcha(self):
        logs = self.driver.get_log("performance")
        for log in logs:
            if (
                self.get_check_status_code(403, log, "https://visa.vfsglobal.com/")
                or self.get_check_status_code(
                    429, log, "https://lift-api.vfsglobal.com"
                )
                or self.get_check_status_code(
                    403, log, "https://lift-api.vfsglobal.com"
                )
                or self.get_check_status_code(429, log, "https://visa.vfsglobal.com/")
            ):
                self.get_screenshoot(f"{proxy_manager.get_proxy_string}_{429}.png")
                raise Exception("Blocked by captcha")

    async def open_page(self):
        self.driver.get(VFS_LOGIN_URL)
        while True:
            try:
                self.driver.find_element(By.NAME, "cf-turnstile-response")
                break
            except:
                self.check_blocked_by_captcha()
                await asyncio.sleep(1)

    def fill_form(self):
        try:
            usernameInput = self.get_element(By.ID, "email")
            passwordInput = self.get_element(By.ID, "password")
        except Exception as e:
            raise Exception("Failed to find form elements email and password")

        usernameInput.send_keys(self.username)
        passwordInput.send_keys(self.password)

    def press_login_button(self):
        try:
            loginButton = self.get_element(By.CLASS_NAME, "btn-block")
            if loginButton.text != "Sign In":
                raise Exception("Login button not found")
        except Exception as e:
            raise Exception("Failed to find login button")

        loginButton.click()

    def accept_cookies(self):
        onetrust_accept_btn_handler = self.get_element(
            By.ID, "onetrust-accept-btn-handler"
        )
        onetrust_accept_btn_handler.click()

    def press_book_appointment(self):
        try:
            button = self.get_element(By.CLASS_NAME, "custom-height-button", 30)
            button.click()
        except Exception as e:
            self.get_screenshoot("/errors/book_appointment.png")
            raise Exception("Failed to find book appointment button")

    def get_cities_from_logs(self, log, url, *args):
        log = json.loads(log["message"])["message"]
        if (
            "Network.responseReceived" in log["method"]
            and "params" in log.keys()
            and "response" in log["params"].keys()
            and log["params"]["response"]["url"] == url
        ):
            body = self.driver.execute_cdp_cmd(
                "Network.getResponseBody", {"requestId": log["params"]["requestId"]}
            )
            body = json.loads(body["body"])
            if type(body) != list:
                return None
            return body

    def process_logs(self, url, func, *args):
        logs = self.driver.get_log("performance")
        # Обработка логов
        for log in logs:
            body = func(log, url, *args)
            # TODO: test this
            if body != None:
                return body
        return None

    async def ensure_logged_in(self):
        div = self.get_element(By.ID, "mat-tab-label-0-0", timeout=30)
        if div:
            return True

    async def authorize(self):
        await self.open_page()
        await asyncio.sleep(5)
        self.accept_cookies()
        self.fill_form()
        await asyncio.sleep(5)
        self.press_login_button()
        logged_in = await self.ensure_logged_in()
        if logged_in == True:
            logging.info("VFS Global parser had logged in")
            await asyncio.sleep(5)
        else:
            raise Exception(f"Failed to login: {logged_in}")

    async def parse_cities(self):
        await asyncio.sleep(5)
        self.press_book_appointment()
        await asyncio.sleep(5)
        body_from_logs = self.process_logs(CITIES_API_URL, self.get_cities_from_logs)
        if body_from_logs == None:
            raise Exception("Failed to get cities from logs")
        self.cities = {item["city"]: item for item in body_from_logs}
        return True

    def press_city_choose_form_field(self):
        try:
            self.driver.find_elements(By.TAG_NAME, "mat-form-field")[0].click()
        except Exception as e:
            raise Exception("Failed to find city form input")

    async def press_city_in_choice_form_field(self, city):
        try:
            span = self.driver.find_element(
                By.XPATH, f"//span[text()=' {city['centerName']} ']"
            )
            # Прокрутка к элементу
            self.driver.execute_script("arguments[0].scrollIntoView(true);", span)

            # Ожидание, чтобы элемент стал видимым и кликабельным
            await asyncio.sleep(1)
            span.click()
        except Exception as e:
            raise Exception("Failed to mat-option of city form input")

    def get_appointment_response(self, log, url, city):
        log = json.loads(log["message"])["message"]
        if (
            "Network.requestWillBeSent" in log["method"]
            and "params" in log.keys()
            and "request" in log["params"].keys()
            and log["params"]["request"]["url"] == url
        ):
            if "postData" in log["params"]["request"]:
                requestData = json.loads(log["params"]["request"]["postData"])
                if requestData["vacCode"] == city["isoCode"]:
                    body = self.driver.execute_cdp_cmd(
                        "Network.getResponseBody",
                        {"requestId": log["params"]["requestId"]},
                    )
                    body = json.loads(body["body"])
                    if type(body) != dict:
                        return None
                    return body
        return None

    def check_all_fields_filled(self):
        fields = self.driver.find_elements(By.CLASS_NAME, "mat-mdc-select-min-line")
        for field in fields:
            if field.text.startswith("Select"):
                field.click()
                try:
                    span = self.driver.find_element(
                        By.XPATH, f"//span[text()=' Long stay Visa D/Visa C ']"
                    )
                except Exception as e:
                    spans = self.driver.find_elements(
                        By.CLASS_NAME, "mdc-list-item__primary-text"
                    )
                    if spans.__len__() > 1:
                        span = spans[1]
                    else:
                        span = spans[0]

                # Прокрутка к элементу
                self.driver.execute_script("arguments[0].scrollIntoView(true);", span)

                # Ожидание, чтобы элемент стал видимым и кликабельным
                time.sleep(1)
                span.click()
                time.sleep(5)

    async def parse_city_appointments(self, city):
        self.press_city_choose_form_field()
        await self.press_city_in_choice_form_field(city)
        await asyncio.sleep(10)
        self.check_all_fields_filled()

        appointments = self.process_logs(
            SLOTS_API_URL, self.get_appointment_response, city
        )

        if appointments == None:
            raise Exception(f"Failed to get appointments for city {city['city']}")

        prev_state_appointments = (
            self.cities[city["city"]]
            if "appointments" in self.cities[city["city"]]
            else []
        )

        if (
            "error" in appointments.keys()
            and appointments["error"] != None
            and "description" in appointments["error"].keys()
            and appointments["error"]["description"] == "No slots available"
        ):
            self.cities[city["city"]]["appointments"] = []
        else:
            self.cities[city["city"]]["appointments"] = appointments[
                "earliestSlotLists"
            ]

        self.cities[city["city"]]["is_updated"] = True
        # if prev_state_appointments != self.cities[city["city"]]["appointments"]:
        #     self.cities[city["city"]]["is_updated"] = True
        # else:
        #     self.cities[city["city"]]["is_updated"] = False

    async def parse_all_appointments(self):
        for city in self.cities.keys():
            try:
                await self.parse_city_appointments(self.cities[city])
            except Exception as e:
                logging.error(
                    f"Appointments for {city['city']} failed due to exception:\n{e}"
                )
                continue

    def get_cities(self):
        return self.cities

    def check_page_loaded(self):
        while True:
            try:
                self.driver.find_element(By.ID, "mat-tab-label-0-0")
                return True
            except Exception as e:
                continue

    async def check_appointments(self, cities_to_update):
        for city in cities_to_update:
            await self.parse_city_appointments(self.cities[city])

    async def check_updates(self) -> dict[str, dict]:
        city_to_update = self.get_cities_to_update()
        if city_to_update == []:
            return None
        retries = 0  # retries counter
        try:
            self.change_proxy()
            await self.set_up_driver_extension()
            await self.authorize()
            await asyncio.sleep(10)
            self.press_book_appointment()
            await asyncio.sleep(10)
            await self.check_appointments(city_to_update)
            self.driver.quit()
            return self.cities
        except Exception as e:
            if e.__str__() == "Blocked by captcha":
                if retries > 15:
                    logging.error(
                        f"Failed to check updates after {retries} retries due to: Block by captcha"
                    )
                    return None
                logging.warning(
                    f"Failed to check updates with proxy {proxy_manager.get_proxy_string()} due to:\n{e}"
                )
                logging.info("Retrying to check updates")
                retries += 1
                await self.check_updates()
                return
            logging.error(f"Failed to check updates due to:\n{e}")
            return None

    def add_city_to_updates(self, city):
        try:
            self.cities[city]["is_need_to_be_updated"] = True
        except Exception as e:
            logging.error(f"Failed to add city {city} to updates due to:\n{e}")

    def delete_city_from_updates(self, city):
        try:
            self.cities[city]["is_need_to_be_updated"] = False
        except Exception as e:
            logging.error(f"Failed to delete city {city} from updates due to:\n{e}")

    def get_cities_to_update(self):
        return [
            city
            for city in self.cities.keys()
            if self.cities[city].get("is_need_to_be_updated", False)
        ]

    def init_subs(self):
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        db_path = os.path.join(base_path, "db.json")
        with open(db_path, "r") as file:
            data = json.load(file)
            if "vfs_subscribers" in data.keys():
                for city in data["vfs_subscribers"].keys():
                    self.add_city_to_updates(city)

    async def initialize(self, reinit=False):
        try:
            if reinit:
                self.change_proxy()
            logging.info("Initializing VFS Global parser")
            await self.set_up_driver_extension()
            await self.authorize()
            await self.parse_cities()
            self.init_subs()
            self.driver.quit()
            logging.info("VFS Global parser initialized")
        except Exception as e:
            if e.__str__() == "Blocked by captcha":
                logging.warning(f"Failed to initialize VFS Global parser due to:\n{e}")
                logging.info("Trying to reinitialize")
                await self.initialize(reinit=True)
                return
            logging.error(f"Failed to initialize VFS Global parser due to:\n{e}")

    def activate_parser(self):
        self.is_actived = True

    def deactivate_parser(self):
        self.is_actived = False
