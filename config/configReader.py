import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("config/config.env")

BOT_API_TOKEN = os.environ.get("BOT_API_TOKEN")
USER_KEY = os.environ.get("USER_KEY")

BASE_DIR = Path(__file__).resolve().parent.parent
LOGGER_PATH = os.path.join(BASE_DIR, "logs/workbotLogging.log")
