from aiogram.types import InlineKeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu_kb(subscribe_btn: bool) -> ReplyKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="Добавить город🔧", callback_data="parser_setting"),
        InlineKeyboardButton(text="Справкаℹ️", callback_data="parser_info"),
    )
    if subscribe_btn:
        builder.row(
            InlineKeyboardButton(
                text="Включить отслеживание📢", callback_data="parser_monitore"
            )
        )

    return builder.as_markup()
