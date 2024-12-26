import asyncio
import json
import logging
import os
from collections import defaultdict
from typing import Any, Callable, Dict, List, Literal

from globals.services import ServiceTypes
from utils.transform_parser_subs_to_one_dict import transform_parser_subs_to_one_dict

from .ConsulateParserClass import ConsulateParser
from .ProxyManager import proxy_manager
from .VFSparserClass import VFSparser


class ParserSubscription:
    def __init__(self):
        self.send_message = None
        self.vfs_parser = None
        self.consulate_parser = None
        self.isInitialized = False
        self.vfs_subscribers = {}
        self.consulate_subscribers = {}

    async def initilize(self, send_message_func: Callable[[Any], Any]):
        logging.info("Parser subscription: initializing")
        with open("db.json", "r") as file:
            json_values = json.load(file)
            if "vfs_subscribers" in json_values.keys():
                self.vfs_subscribers = json_values["vfs_subscribers"]
            if "consulate_subscribers" in json_values.keys():
                self.consulate_subscribers = json_values["consulate_subscribers"]
        self.set_send_message(send_message_func)
        await proxy_manager.initialize()
        self.vfs_parser = VFSparser()
        self.consulate_parser = ConsulateParser()
        await self.vfs_parser.initialize()
        await self.consulate_parser.initialize()
        logging.info("Parser subscription: initialized")
        logging.info("Start pulling updates")
        self.isInitialized = True
        await self.check_updates()

    def subscribe(
        self, city: dict, chat_id: str, type: Literal["vfs_global", "ausria_consulate"]
    ):
        if type == ServiceTypes.VFS:

            if city not in list(self.vfs_subscribers.keys()):
                self.vfs_subscribers[city] = []
            self.vfs_subscribers[city].append(chat_id)
            self.vfs_parser.add_city_to_updates(city)
        elif type == ServiceTypes.CONSULATE:
            if city not in list(self.consulate_subscribers.keys()):
                self.consulate_subscribers[city] = []
            self.consulate_subscribers[city].append(chat_id)
            self.consulate_parser.add_city_to_updates(city)
        else:
            raise Exception("Invalid type provided")
        self.rewrite_db()

    def unsubscribe_all(self, chat_id: str):
        for city in list(self.vfs_subscribers.keys()):
            if chat_id in self.vfs_subscribers[city]:
                self.vfs_subscribers[city].remove(chat_id)
                if self.vfs_subscribers[city].__len__() == 0:
                    self.vfs_parser.delete_city_from_updates(city)
                    del self.vfs_subscribers[city]
                # if self.vfs_subscribers.keys().__len__() == 0:
                #     self.vfs_parser.deactivate_parser()
        for city in list(self.consulate_subscribers.keys()):
            if chat_id in self.consulate_subscribers[city]:
                self.consulate_subscribers[city].remove(chat_id)
                if self.consulate_subscribers[city].__len__() == 0:
                    self.consulate_parser.delete_city_from_updates(city)

    def unsubscribe(
        self, chat_id: str, type: Literal["vfs_global", "ausria_consulate"], city: str
    ):
        if type == ServiceTypes.VFS:
            self.vfs_subscribers[city].remove(chat_id)
            if self.vfs_subscribers[city].__len__() == 0:
                self.vfs_parser.delete_city_from_updates(city)
                del self.vfs_subscribers[city]
            # if self.vfs_subscribers.keys().__len__() == 0:
            #     self.vfs_parser.deactivate_parser()
        elif type == ServiceTypes.CONSULATE:
            self.consulate_subscribers[city].remove(chat_id)
            if self.consulate_subscribers[city].__len__() == 0:
                self.consulate_parser.delete_city_from_updates(city)
        self.rewrite_db()

    async def send_appointments_message(
        self, chat_id, vfs_appointments=None, consulate_appointments=None
    ):
        answer = "Собрали новые данные для вас :)\n"
        if vfs_appointments != None:
            for city, appointments in vfs_appointments.items():
                if appointments.__len__() > 0:
                    answer += (
                        f"Для записи в VFS Global - {city} доступны следующие даты:\n"
                    )
                    for appointment in appointments:
                        # TODO:
                        answer += f"📅 {appointment}\n"
                else:
                    answer += f"Для записи в VFS Global - {city} нет доступных дат"
                answer += "\n\n"
        if consulate_appointments != None:
            for city, appointments in consulate_appointments.items():
                if appointments.__len__() > 0:
                    answer += (
                        f"Для записи в консульство - {city} доступны следующие даты:\n"
                    )
                    for appointment in appointments:
                        answer += f"📅 {appointment}\n"
                else:
                    answer += f"Для записи в консульство - {city} нет доступных дат"
                answer += "\n\n"

        await self.send_message(chat_id, text=answer, parse_mode="HTML")

    async def check_updates(self):
        while True:
            try:
                vfs_appointments = None
                consulate_appointments = None

                errors = []
                try:
                    vfs_appointments = await self.vfs_parser.check_updates()
                except Exception as e:
                    errors.append(e)
                    logging.error(e)
                try:
                    consulate_appointments = await self.consulate_parser.check_updates()
                except Exception as e:
                    errors.append(e)
                    logging.error(e)

                if errors.__len__() == 2:
                    raise Exception("Both parsers got errors\nNothing to send to users")

                subscribers_dict = transform_parser_subs_to_one_dict(
                    self.consulate_subscribers, self.vfs_subscribers
                )

                for chat_id, item in subscribers_dict.items():
                    vfs_cities = item[ServiceTypes.VFS]
                    consulate_cities = item[ServiceTypes.CONSULATE]

                    is_there_something_to_send = False
                    vfs_to_send = {}
                    consulate_to_send = {}

                    for city in vfs_cities:
                        vfs_to_send[city] = vfs_appointments[city]["appointments"]
                        if (
                            vfs_appointments != None
                            and vfs_appointments[city]["is_updated"]
                        ):
                            is_there_something_to_send = True

                    for city in consulate_cities:
                        consulate_to_send[city] = consulate_appointments[city]["data"]
                        if (
                            consulate_appointments != None
                            and consulate_appointments[city]["is_updated"]
                        ):
                            is_there_something_to_send = True

                    if not is_there_something_to_send:
                        logging.info("No updates to send for users: " + chat_id)
                        return

                    await self.send_appointments_message(
                        chat_id=chat_id,
                        vfs_appointments=vfs_to_send,
                        consulate_appointments=consulate_to_send,
                    )
            except Exception as e:
                logging.error(e)
            finally:
                check_interval = int(os.environ.get("UPDATE_CHECK_INTERVAL"))
                if not check_interval or check_interval == None:
                    check_interval = 5
                await asyncio.sleep(check_interval * 60)

    def get_vfs_cities(self) -> list:
        return self.vfs_parser.get_cities()

    def get_consulate_cities(self) -> list:
        return self.consulate_parser.get_cities()

    def set_send_message(self, send_message):
        self.send_message = send_message

    def rewrite_db(self):
        with open("db.json", "w") as file:
            json.dump(
                {
                    "vfs_subscribers": self.vfs_subscribers,
                    "consulate_subscribers": self.consulate_subscribers,
                },
                file,
            )

    def get_data_by_chat_id(self, chat_id):
        data = transform_parser_subs_to_one_dict(
            self.consulate_subscribers, self.vfs_subscribers
        )
        if chat_id not in data.keys():
            return None
        return transform_parser_subs_to_one_dict(
            self.consulate_subscribers, self.vfs_subscribers
        )[chat_id]


ps = ParserSubscription()
