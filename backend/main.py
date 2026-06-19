import base64
import logging
import os
import traceback
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from services import chatbot_general, chatbot_pdf, classify, summarize
    from services.pdf_utils import extract_text_from_pdf
    from db_utils import (
        get_user,
        insert_user,
        save_pdf_result,
        save_query_log,
        verify_password,
    )
    from models import PDFResult, QueryLog
except ImportError:
    from backend.services import chatbot_general, chatbot_pdf, classify, summarize
    from backend.services.pdf_utils import extract_text_from_pdf
    from backend.db_utils import (
        get_user,
        insert_user,
        save_pdf_result,
        save_query_log,
        verify_password,
    )
    from backend.models import PDFResult, QueryLog


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("genifi.api")

app = FastAPI(
    title="GeniFi Finance GPT API",
    version="1.0.0",
    description="Finance document summarization, classification, PDF Q&A, and chat API.",
)


def _parse_cors_origins() -> tuple[list[str], bool]:
    raw = os.getenv(
        "CORS_ORIGINS",
        "*",
    )
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if not origins or "*" in origins:
        return ["*"], False
    return origins, True


cors_origins, cors_credentials = _parse_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProcessRequest(BaseModel):
    filename: str
    filedata: str
    summarize_checked: bool = False
    classify_checked: bool = False
    qa_checked: bool = False
    qa_query: str | None = None
    user_id: str | None = None


class ChatRequest(BaseModel):
    query: str
    user_id: str | None = None


class User(BaseModel):
    email: str
    password: str


@app.get("/")
def root():
    return {
        "message": "GeniFi Finance GPT backend is running.",
        "docs": "/docs",
    }


@app.get("/health/")
def health():
    return {
        "status": "ok",
        "service": "genifi-finance-gpt",
    }


def _decode_base64_pdf(filedata: str) -> bytes:
    if "," in filedata and filedata.lower().startswith("data:"):
        filedata = filedata.split(",", 1)[1]

    try:
        return base64.b64decode(filedata, validate=True)
    except Exception as exc:
        logger.warning("Base64 decode failed: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid base64 file data.") from exc


def _public_process_result(filename: str, result: dict[str, Any], extracted_text: str) -> dict[str, Any]:
    return {
        "filename": filename,
        "text_length": len(extracted_text),
        "result": result,
    }


@app.post("/process/")
async def process_pdf(request: ProcessRequest = Body(...)):
    summarize_flag = request.summarize_checked
    classify_flag = request.classify_checked
    qa_flag = request.qa_checked

    content = _decode_base64_pdf(request.filedata)
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        text = extract_text_from_pdf(content)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("PDF extraction failed")
        raise HTTPException(
            status_code=400,
            detail=f"Could not read text from PDF: {exc}",
        ) from exc

    if not text.strip():
        raise HTTPException(status_code=400, detail="No text extracted from PDF.")

    if not (summarize_flag or classify_flag or qa_flag):
        raise HTTPException(status_code=400, detail="No processing option selected.")

    result: dict[str, Any] = {}

    if summarize_flag:
        try:
            result["summary"] = summarize.generate_masked_summary(text)
        except Exception as exc:
            logger.exception("Summarization error")
            raise HTTPException(
                status_code=500,
                detail=f"Summarization failed: {exc}",
            ) from exc

    if classify_flag:
        try:
            result["classification"] = classify.classify_text(text)
        except Exception as exc:
            logger.exception("Classification error")
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Classification failed: {exc}",
            ) from exc

    if qa_flag:
        if not request.qa_query or not request.qa_query.strip():
            raise HTTPException(status_code=400, detail="QA query must be provided.")

        try:
            answer = chatbot_pdf.answer_pdf_query(request.qa_query.strip(), text)
            result["pdf_answer"] = answer

            try:
                log = QueryLog(
                    user_id=request.user_id,
                    query=request.qa_query.strip(),
                    answer=answer,
                    source="pdf_qa",
                    created_at=datetime.utcnow(),
                )
                await save_query_log(log)
            except Exception:
                logger.exception("Query log save error")

        except Exception as exc:
            logger.exception("PDF Q&A error")
            raise HTTPException(
                status_code=500,
                detail=f"Q&A failed: {exc}",
            ) from exc

    try:
        pdf_data = PDFResult(
            user_id=request.user_id,
            filename=request.filename,
            result=result,
            created_at=datetime.utcnow(),
        )
        await save_pdf_result(pdf_data)
    except Exception:
        logger.exception("PDF result save error")

    return _public_process_result(request.filename, result, text)


@app.post("/general-chat/")
async def general_chat(request: ChatRequest):
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        answer = chatbot_general.answer_general_query(query)

        try:
            log = QueryLog(
                user_id=request.user_id,
                query=query,
                answer=answer,
                source="general_chat",
                created_at=datetime.utcnow(),
            )
            await save_query_log(log)
        except Exception:
            logger.exception("Query log save error")

        return {"answer": answer}

    except Exception as exc:
        logger.exception("General chat error")
        raise HTTPException(
            status_code=500,
            detail=f"Chat failed: {exc}",
        ) from exc


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_user_input(user: User) -> tuple[str, str]:
    email = _normalize_email(user.email)
    password = user.password

    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="A valid email address is required.")

    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    return email, password


@app.post("/register/")
async def register_user(user: User):
    email, password = _validate_user_input(user)

    try:
        created = await insert_user(User(email=email, password=password))
        if not created:
            raise HTTPException(status_code=400, detail="Email already registered.")

        return {"message": "Registration successful!"}

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Registration error")
        raise HTTPException(
            status_code=500,
            detail=f"Could not register user: {exc}",
        ) from exc


@app.post("/login/")
async def login_user(user: User):
    email, password = _validate_user_input(user)

    try:
        existing_user = await get_user(email)
        stored_password = None
        if existing_user:
            stored_password = existing_user.get("password_hash") or existing_user.get("password")

        if not existing_user or not verify_password(password, stored_password):
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        return {"message": "Login successful!"}

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Login error")
        raise HTTPException(
            status_code=500,
            detail=f"Could not log in user: {exc}",
        ) from exc
