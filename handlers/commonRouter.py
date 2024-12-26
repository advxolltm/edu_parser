import asyncio
from parser.SubscriptionClass import ps

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from filters.chat_type import ChatTypeFilter
from filters.check_password import CheckUserPassword
from globals.services import ServiceTypes
from keyboards.back_kb import get_back_kb
from keyboards.main_menu_kb import get_main_menu_kb
from keyboards.service_cities_kb import get_service_cities_kb
from keyboards.service_kb import get_service_kb

PARSER_INFO = """
    Данный бот предназначен для отслеживания доступных записей на сайте консульства Австрии в Вене и в сервисе бронирования слотов VFS Global.
    Порядок действий и доступных функций:
    1. Доступ с помощью пароля
    2. Выбор сервиса для отслеживания (VFS Global или консульство)
    3. Выбор города для отслеживания
    4. Включение/отключение уведомлений
"""


commonRouter = Router()


async def is_subs_init(message: Message):
    if not ps.isInitialized:
        await message.answer(
            "Сервис инициализируется, повторите попытку в течении 5 минут"
        )
        return True
    return False


def cancel_task():
    tasks = asyncio.tasks.all_tasks()
    for task in tasks:
        if task.get_name() == "update_checker_task":
            task.cancel()


class UserState(StatesGroup):
    AwaitOfPassword = State()
    Entered = State()


@commonRouter.message(ChatTypeFilter(chat_type="private"), Command(commands=["start"]))
async def first_handler(message: Message, state: FSMContext):
    if await is_subs_init(message):
        return
    await message.answer(
        "Привет👋🏻\nЯ бот 🤖 для отслеживания доступных записей\nВведите пароль для доступа в систему"
    )
    await state.set_state(UserState.AwaitOfPassword)
    ps.unsubscribe_all(message.chat.id)


@commonRouter.message(UserState.AwaitOfPassword, CheckUserPassword())
async def entered_сorrect_pass_admin_panel(message: Message, state: FSMContext):
    await state.clear()
    data = {
        ServiceTypes.CONSULATE: [],
        ServiceTypes.VFS: [],
    }
    await state.set_state(UserState.Entered)
    await state.set_data(data)
    await message.answer(
        "Добро пожаловать👋🏻\nВыберите действие:", reply_markup=get_main_menu_kb(False)
    )
    ps.unsubscribe_all(message.chat.id)


@commonRouter.message(UserState.AwaitOfPassword)
async def entered_incorrect_pass_admin_panel(message: Message, state: FSMContext):
    await message.answer("Неверный пароль, попробуйте еще раз")


@commonRouter.callback_query(UserState.Entered, F.data.startswith("main_menu"))
async def main_admin_panel(callback_query: CallbackQuery, state: FSMContext):
    ps.unsubscribe_all(callback_query.message.chat.id)
    data = await state.get_data()

    if data == {}:
        data = {
            ServiceTypes.CONSULATE: [],
            ServiceTypes.VFS: [],
        }
    if "__subscribe" in callback_query.data:
        type, city = callback_query.data.split("__")[2:]
        data[type].append(city)

    if "__unsubscribe" in callback_query.data:
        type, city = callback_query.data.split("__")[2:]
        data[type].remove(city)

    await state.set_data(data)
    if (
        data[ServiceTypes.CONSULATE].__len__() == 0
        and data[ServiceTypes.VFS].__len__() == 0
    ):
        await callback_query.message.edit_text(
            "**Главное меню парсера** ⚙️\nВыберите действие:",
            reply_markup=get_main_menu_kb(False),
            parse_mode="Markdown",
        )
    else:
        main_message = (
            "**Главное меню парсера** ⚙️\nВы подписаны на уведомления городов\n"
        )
        if data[ServiceTypes.CONSULATE].__len__() > 0:
            main_message += "\n\n"
            cities = " \n".join(data[ServiceTypes.CONSULATE])
            main_message += "**Консульство Австрии**: \n" + cities
            main_message += "\n\n"
        if data[ServiceTypes.VFS].__len__() > 0:
            main_message += "\n\n"
            cities = " \n".join(data[ServiceTypes.VFS])
            main_message += "**VFS Global**: \n" + cities
            main_message += "\n\n"

        main_message += "\nВыберите действие:"
        await callback_query.message.edit_text(
            main_message,
            reply_markup=get_main_menu_kb(True),
            parse_mode="Markdown",
        )


@commonRouter.callback_query(UserState.Entered, F.data == "parser_monitore")
async def parser_monitore(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    for city in data[ServiceTypes.CONSULATE]:
        ps.subscribe(city, callback_query.message.chat.id, ServiceTypes.CONSULATE)
    for city in data[ServiceTypes.VFS]:
        ps.subscribe(city, callback_query.message.chat.id, ServiceTypes.VFS)
    await callback_query.message.edit_text(
        'Вы прослушиваете эфир📣\n\nДля изменения параметров парсинга нажмите на кнопку "Назад⏪"\n\nДля сброса параметров введите /start',
        reply_markup=get_back_kb(),
    )


@commonRouter.callback_query(UserState.Entered, F.data == "parser_setting")
async def parser_setting(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(
        "Веберите сервис для отслеживания", reply_markup=get_service_kb()
    )


@commonRouter.callback_query(UserState.Entered, F.data.startswith("cities_choose__"))
async def city_choice_handler(callback_query: CallbackQuery, state: FSMContext):
    type = callback_query.data.split("__")[1]
    data = await state.get_data()
    await callback_query.message.edit_text(
        "Выберите город для отслеживания в " + type.capitalize(),
        reply_markup=get_service_cities_kb(type, data[type]),
    )


@commonRouter.callback_query(UserState.Entered, F.data == "parser_info")
async def parser_setting(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(PARSER_INFO, reply_markup=get_back_kb())


@commonRouter.callback_query(F.data != None)
async def callback_handler(callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "Возможно бот был перезагружен ⚙️\nПожалуйста, введите команду /start"
    )


@commonRouter.message(ChatTypeFilter(chat_type=["private"]), F.sticker)
async def message_with_sticker(message: Message):
    await message.answer(
        "Хорошая попытка...\nПопробуйте в следующий раз следовать инструкциям\nВсе подписки отменены"
    )
    ps.unsubscribe_all(message.chat.id)


@commonRouter.message(ChatTypeFilter(chat_type=["private"]), F.animation)
async def message_with_gif(message: Message):
    await message.answer(
        "Хорошая попытка...\nПопробуйте в следующий раз следовать инструкциям\nВсе подписки отменены"
    )
    ps.unsubscribe_all(message.chat.id)


@commonRouter.message(ChatTypeFilter(chat_type=["private"]), F.photo)
async def message_with_photo(message: Message):
    await message.answer(
        "Хорошая попытка...\nПопробуйте в следующий раз следовать инструкциям\nВсе подписки отменены"
    )
    ps.unsubscribe_all(message.chat.id)


@commonRouter.message(ChatTypeFilter(chat_type=["private"]), F.text)
async def message_from_unatharize_user(message: Message):
    if await is_subs_init(message):
        return
    await message.answer("Пожалуйста, введите команду /start")
    ps.unsubscribe_all(message.chat.id)
