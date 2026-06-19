import logging
import re
from functools import lru_cache
from pathlib import Path


logger = logging.getLogger("genifi.summarize")
MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "summarization_model"

FINANCE_KEYWORDS = {
    "revenue",
    "profit",
    "loss",
    "income",
    "expense",
    "cash",
    "asset",
    "liability",
    "equity",
    "debt",
    "loan",
    "investment",
    "margin",
    "growth",
    "risk",
    "audit",
    "tax",
    "shareholder",
}


@lru_cache(maxsize=1)
def _load_model():
    try:
        import torch
        from transformers import BartForConditionalGeneration, BartTokenizer
    except ImportError as exc:
        raise RuntimeError("torch and transformers are not installed") from exc

    if not MODEL_PATH.exists():
        raise RuntimeError(f"Summarization model folder not found: {MODEL_PATH}")

    tokenizer = BartTokenizer.from_pretrained(str(MODEL_PATH), local_files_only=True)
    model = BartForConditionalGeneration.from_pretrained(
        str(MODEL_PATH),
        local_files_only=True,
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    return torch, tokenizer, model, device


def mask_sensitive_info(text: str) -> str:
    patterns = [
        r"(?<!\w)[\$\u20AC\u00A3\u00A5]?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?:\s?(?:million|billion|m|b))?",
        r"(?<!\w)[\$\u20AC\u00A3\u00A5]\d+(?:\.\d+)?(?:\s?(?:million|billion|m|b))?",
        r"\d+(?:\.\d+)?%",
        r"\b(19|20)\d{2}\b",
        r"\b[A-Z]{2,5}-\d{2,5}\b",
        r"\b\d{8,}\b",
    ]

    for pattern in patterns:
        text = re.sub(pattern, "[REDACTED]", text, flags=re.IGNORECASE)

    return text


def _split_sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    return [sentence.strip() for sentence in sentences if len(sentence.strip()) > 20]


def _fallback_summary(text: str, max_sentences: int = 5) -> str:
    sentences = _split_sentences(text)
    if not sentences:
        return mask_sensitive_info(text[:1200].strip())

    scored = []
    for index, sentence in enumerate(sentences):
        lower = sentence.lower()
        keyword_score = sum(1 for keyword in FINANCE_KEYWORDS if keyword in lower)
        number_score = min(len(re.findall(r"\d", sentence)), 8) / 8
        score = keyword_score + number_score
        scored.append((score, index, sentence))

    selected = sorted(
        sorted(scored, key=lambda item: item[0], reverse=True)[:max_sentences],
        key=lambda item: item[1],
    )
    summary = " ".join(sentence for _score, _index, sentence in selected)
    return mask_sensitive_info(summary[:1800].strip())


def generate_masked_summary(text: str) -> str:
    if not text or not text.strip():
        return ""

    try:
        torch, tokenizer, model, device = _load_model()
        inputs = tokenizer(
            text[:10000],
            return_tensors="pt",
            truncation=True,
            max_length=512,
        ).to(device)

        with torch.no_grad():
            summary_ids = model.generate(
                inputs["input_ids"],
                max_length=150,
                min_length=40,
                length_penalty=1.0,
                num_beams=4,
                no_repeat_ngram_size=3,
                early_stopping=True,
            )

        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        if summary.strip():
            return mask_sensitive_info(summary.strip())
    except Exception as exc:
        logger.info("Using extractive summarization fallback: %s", exc)

    return _fallback_summary(text)
