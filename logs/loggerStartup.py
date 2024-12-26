import logging
from config.configReader import LOGGER_PATH
async def logger_startup() -> None:
    
    file_log = logging.FileHandler(LOGGER_PATH)
    console_out = logging.StreamHandler()

    logging.basicConfig(handlers=(file_log, console_out), 
                        format='[%(asctime)s | %(levelname)s]: %(message)s', 
                        datefmt='%d.%m.%Y %H:%M:%S',
                        level= logging.INFO
                        )