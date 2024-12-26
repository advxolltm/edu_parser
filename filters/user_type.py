from typing import Union

from aiogram.filters import BaseFilter
from aiogram.types import Message



class UserSubscribe(BaseFilter): 
    user_type: str
    async def __call__(self, message: Message) -> bool:
            return True