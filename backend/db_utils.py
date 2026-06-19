import json
import logging
import os
import secrets
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from database import chats_collection, db, pdf_results_collection, users_collection
    from models import Chat, PDFResult, QueryLog, User
except ImportError:
    from backend.database import chats_collection, db, pdf_results_collection, users_collection
    from backend.models import Chat, PDFResult, QueryLog, User


logger = logging.getLogger("genifi.db_utils")
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("LOCAL_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _model_dump(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _read_list(name: str) -> list[dict[str, Any]]:
    path = DATA_DIR / f"{name}.json"
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except Exception as exc:
        logger.warning("Could not read local store %s: %s", path, exc)
        return []


def _write_list(name: str, rows: list[dict[str, Any]]) -> None:
    path = DATA_DIR / f"{name}.json"
    tmp_path = path.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as file:
        json.dump(rows, file, indent=2, default=_json_default)
    tmp_path.replace(path)


def _append_local(name: str, row: dict[str, Any]) -> None:
    rows = _read_list(name)
    rows.append(row)
    _write_list(name, rows)


async def _mongo_available() -> bool:
    if db is None:
        return False
    try:
        await db.client.admin.command("ping")
        return True
    except Exception as exc:
        logger.info("MongoDB unavailable; using local JSON storage: %s", exc)
        return False


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 120_000
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def verify_password(password: str, stored_password: str | None) -> bool:
    if not stored_password:
        return False

    if not stored_password.startswith("pbkdf2_sha256$"):
        return secrets.compare_digest(password, stored_password)

    try:
        _algorithm, iterations, salt, expected = stored_password.split("$", 3)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return secrets.compare_digest(digest, expected)
    except Exception:
        return False


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def insert_user(user: User) -> bool:
    email = _normalize_email(user.email)
    document = {
        "email": email,
        "password_hash": hash_password(user.password),
        "created_at": datetime.utcnow(),
    }

    if await _mongo_available() and users_collection is not None:
        try:
            existing = await users_collection.find_one({"email": email})
            if existing:
                return False
            await users_collection.insert_one(document)
            return True
        except Exception as exc:
            logger.warning("Mongo insert_user failed; falling back locally: %s", exc)

    users = _read_list("users")
    if any(row.get("email") == email for row in users):
        return False
    users.append(document)
    _write_list("users", users)
    return True


async def get_user(email: str) -> dict[str, Any] | None:
    normalized_email = _normalize_email(email)

    if await _mongo_available() and users_collection is not None:
        try:
            user = await users_collection.find_one({"email": normalized_email})
            if user:
                user.pop("_id", None)
            return user
        except Exception as exc:
            logger.warning("Mongo get_user failed; falling back locally: %s", exc)

    for row in _read_list("users"):
        if row.get("email") == normalized_email:
            return row
    return None


async def save_chat(chat: Chat) -> None:
    document = _model_dump(chat)
    if await _mongo_available() and chats_collection is not None:
        try:
            await chats_collection.insert_one(document)
            return
        except Exception as exc:
            logger.warning("Mongo save_chat failed; saving locally: %s", exc)
    _append_local("chats", document)


async def get_chats(user_id: str) -> list[dict[str, Any]]:
    if await _mongo_available() and chats_collection is not None:
        try:
            cursor = chats_collection.find({"user_id": user_id})
            rows = await cursor.to_list(length=100)
            for row in rows:
                row.pop("_id", None)
            return rows
        except Exception as exc:
            logger.warning("Mongo get_chats failed; reading locally: %s", exc)

    return [row for row in _read_list("chats") if row.get("user_id") == user_id]


async def save_pdf_result(pdf_result: PDFResult) -> None:
    document = _model_dump(pdf_result)
    if await _mongo_available() and pdf_results_collection is not None:
        try:
            await pdf_results_collection.insert_one(document)
            return
        except Exception as exc:
            logger.warning("Mongo save_pdf_result failed; saving locally: %s", exc)
    _append_local("pdf_results", document)


async def save_query_log(log: QueryLog) -> None:
    document = _model_dump(log)
    if await _mongo_available() and db is not None:
        try:
            await db["query_logs"].insert_one(document)
            return
        except Exception as exc:
            logger.warning("Mongo save_query_log failed; saving locally: %s", exc)
    _append_local("query_logs", document)
