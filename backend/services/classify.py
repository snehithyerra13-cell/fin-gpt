import logging
import re
from functools import lru_cache
from pathlib import Path


logger = logging.getLogger("genifi.classify")
CLASSIFICATION_MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "classification_model"

LABEL_LIST = [
    "balance_sheet",
    "income_statement",
    "cash_flow_statement",
    "10k_filing",
    "financial_news_article",
    "contract_agreement",
    "audit_report",
    "prospectus",
    "invoice",
]

RULES = {
    "balance_sheet": ["balance sheet", "total assets", "liabilities", "shareholders' equity", "stockholders' equity"],
    "income_statement": ["income statement", "revenue", "net income", "gross profit", "operating income", "earnings"],
    "cash_flow_statement": ["cash flow", "operating activities", "investing activities", "financing activities"],
    "10k_filing": ["form 10-k", "10-k", "annual report", "securities and exchange commission"],
    "contract_agreement": ["agreement", "contract", "covenant", "party agrees", "termination clause"],
    "audit_report": ["audit", "auditor", "independent registered", "internal control", "material weakness"],
    "prospectus": ["prospectus", "offering", "underwriter", "securities offered"],
    "invoice": ["invoice", "bill to", "invoice number", "amount due", "payment terms"],
}


@lru_cache(maxsize=1)
def _load_model():
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError("torch and transformers are not installed") from exc

    if not CLASSIFICATION_MODEL_DIR.exists():
        raise RuntimeError(f"Classification model folder not found: {CLASSIFICATION_MODEL_DIR}")

    tokenizer = AutoTokenizer.from_pretrained(
        str(CLASSIFICATION_MODEL_DIR),
        local_files_only=True,
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        str(CLASSIFICATION_MODEL_DIR),
        local_files_only=True,
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    return torch, tokenizer, model, device


def _rule_based_classification(text: str) -> dict:
    lower = text.lower()
    scores = {}
    for label, phrases in RULES.items():
        scores[label] = sum(1 for phrase in phrases if phrase in lower)

    if not any(scores.values()):
        number_count = len(re.findall(r"\$?\d[\d,]*(\.\d+)?%?", text))
        label = "financial_news_article" if number_count else "unknown"
        confidence = 0.45 if number_count else 0.0
    else:
        label = max(scores, key=scores.get)
        confidence = min(0.95, 0.55 + scores[label] * 0.1)

    return {
        "label": label,
        "confidence": round(confidence, 3),
        "method": "rules",
    }


def classify_text(text: str):
    if not text or not isinstance(text, str):
        return {"label": "unknown", "confidence": 0.0, "method": "empty"}

    try:
        torch, tokenizer, model, device = _load_model()
        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding="max_length",
            max_length=128,
        )
        inputs = {key: value.to(device) for key, value in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)
            pred_idx = torch.argmax(probs, dim=1).item()
            confidence = probs[0][pred_idx].item()

        label = LABEL_LIST[pred_idx] if pred_idx < len(LABEL_LIST) else "unknown"
        return {
            "label": label,
            "confidence": round(confidence, 3),
            "method": "local_transformer",
        }
    except Exception as exc:
        logger.info("Using rule-based classification fallback: %s", exc)
        return _rule_based_classification(text)
