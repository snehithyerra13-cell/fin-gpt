import logging
import re
from functools import lru_cache
from pathlib import Path


logger = logging.getLogger("genifi.pdf_qa")
MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "qa_model_roberta"
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}


@lru_cache(maxsize=1)
def _load_pipeline():
    try:
        import torch
        from transformers import AutoModelForQuestionAnswering, AutoTokenizer, pipeline
    except ImportError as exc:
        raise RuntimeError("torch and transformers are not installed") from exc

    if not MODEL_PATH.exists():
        raise RuntimeError(f"PDF Q&A model folder not found: {MODEL_PATH}")

    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_PATH), local_files_only=True)
    model = AutoModelForQuestionAnswering.from_pretrained(
        str(MODEL_PATH),
        local_files_only=True,
    )
    device = 0 if torch.cuda.is_available() else -1
    return pipeline("question-answering", model=model, tokenizer=tokenizer, device=device)


def _sentences(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", cleaned) if sentence.strip()]


def _keywords(question: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]+", question.lower())
        if word not in STOPWORDS and len(word) > 2
    }


def _fallback_answer(question: str, context: str) -> str:
    question_words = _keywords(question)
    if not question_words:
        return "Please ask a more specific question about the PDF."

    ranked = []
    for index, sentence in enumerate(_sentences(context)):
        sentence_words = set(re.findall(r"[A-Za-z][A-Za-z0-9_-]+", sentence.lower()))
        overlap = len(question_words & sentence_words)
        number_bonus = 0.5 if re.search(r"\d", sentence) else 0
        ranked.append((overlap + number_bonus, index, sentence))

    ranked = [item for item in ranked if item[0] > 0]
    if not ranked:
        return "I could not find a matching answer in the PDF text."

    _score, _index, sentence = max(ranked, key=lambda item: item[0])
    return sentence[:1200]


def _text_chunks(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        chunk = text[start:start + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def answer_pdf_query(question: str, context: str) -> str:
    if not question or not question.strip():
        return "Please provide a question."
    if not context or not context.strip():
        return "No PDF text is available to answer from."

    try:
        qa_pipeline = _load_pipeline()
        answers = []

        for chunk in _text_chunks(context):
            try:
                result = qa_pipeline(
                    question=question,
                    context=chunk,
                    handle_impossible_answer=True,
                )
            except Exception as exc:
                logger.debug("PDF QA chunk failed: %s", exc)
                continue

            answer = str(result.get("answer", "")).strip()
            score = float(result.get("score", 0) or 0)
            if answer and score == score:
                answers.append((score, answer))
                if score > 0.85:
                    break

        if answers:
            _score, answer = max(answers, key=lambda item: item[0])
            return answer
    except Exception as exc:
        logger.info("Using PDF Q&A fallback: %s", exc)

    return _fallback_answer(question, context)
