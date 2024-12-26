from parser.SubscriptionClass import ps

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from globals.services import ServiceTypes


def get_service_cities_kb(type: str, choosen_cities: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    cities = []
    if type == ServiceTypes.VFS:
        cities = ps.get_vfs_cities()
    elif type == ServiceTypes.CONSULATE:
        cities = ps.get_consulate_cities()
    else:
        return None
    row = []
    for i, city in enumerate(cities):
        if city in choosen_cities:
            row.append(
                InlineKeyboardButton(
                    text=f"✅ {city}",
                    callback_data=f"main_menu__unsubscribe__{type}__{city}",
                )
            )
        else:
            row.append(
                InlineKeyboardButton(
                    text=city, callback_data=f"main_menu__subscribe__{type}__{city}"
                )
            )
        if len(row) == 2 or i == len(cities) - 1:
            builder.row(*row)
            row.clear()

    return builder.as_markup()
