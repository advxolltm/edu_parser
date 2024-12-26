from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from globals.services import ServiceTypes


def get_service_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="VFS Global", callback_data="cities_choose__" + ServiceTypes.VFS
        ),
        InlineKeyboardButton(
            text="Austrian Consulate",
            callback_data="cities_choose__" + ServiceTypes.CONSULATE,
        ),
    )
    builder.row(InlineKeyboardButton(text="Назад", callback_data="main_menu"))

    return builder.as_markup()
