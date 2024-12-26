import asyncio
import logging
import os
from parser.SubscriptionClass import ps
from parser.VFSparserClass import VFSparser

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config.configReader import BOT_API_TOKEN
from handlers import commonRouter
from logs.loggerStartup import logger_startup


async def on_startup():
    await logger_startup()


async def await_start_of_bot(bot: Bot):
    await asyncio.sleep(10)
    await ps.initilize(bot.send_message)


async def main():

    await on_startup()
    bot = Bot(token=BOT_API_TOKEN)
    memoStorage = MemoryStorage()
    dp = Dispatcher(storage=memoStorage)
    dp.include_router(commonRouter.commonRouter)
    await bot.delete_webhook(drop_pending_updates=True)
    # start pooling
    try:
        logging.info(f"Bot started!")
        clientTask = asyncio.ensure_future(dp.start_polling(bot))
        initialize_task = asyncio.create_task(await_start_of_bot(bot))
        await clientTask
        await initialize_task
    except Exception as e:
        print(e)
        logging.error(e)

    finally:
        await bot.session.close()


if __name__ == "__main__":
    print("eeee")
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info(f"Bot stopped!")
    except Exception:
        logging.error(Exception)
