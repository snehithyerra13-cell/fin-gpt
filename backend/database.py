import logging
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return None


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("genifi.database")

MONGO_URI = os.getenv("MONGO_URI", "").strip()
DB_NAME = os.getenv("DB_NAME", "finance_gpt").strip() or "finance_gpt"
MONGO_TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", "2000"))

client = None
db = None
users_collection = None
chats_collection = None
pdf_results_collection = None

if MONGO_URI:
    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        client = AsyncIOMotorClient(
            MONGO_URI,
            serverSelectionTimeoutMS=MONGO_TIMEOUT_MS,
            connectTimeoutMS=MONGO_TIMEOUT_MS,
        )
        db = client[DB_NAME]
        users_collection = db["users"]
        chats_collection = db["chats"]
        pdf_results_collection = db["pdf_results"]
    except Exception as exc:
        logger.warning("MongoDB client could not be initialized: %s", exc)
        client = None
        db = None
        users_collection = None
        chats_collection = None
        pdf_results_collection = None
else:
    logger.info("MONGO_URI is not set; using local JSON storage.")
