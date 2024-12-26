from aiogram.filters import BaseFilter
from aiogram.types import Message

from config.configReader import USER_KEY


class CheckUserPassword(BaseFilter):  # [1]
    def __init__(self: str) -> None:
        pass

    async def __call__(self, message: Message) -> bool:  # [3]
        return message.text == USER_KEY
