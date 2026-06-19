import logging
import os
import re
from functools import lru_cache


logger = logging.getLogger("genifi.chat")


SYSTEM_PROMPT = (
    "You are GeniFi, a concise finance assistant. Answer in plain language, "
    "include practical caveats, and avoid pretending to be a licensed financial advisor."
)


@lru_cache(maxsize=1)
def _load_openai_client():
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except ImportError as exc:
        logger.info("OpenAI package is not installed: %s", exc)
        return None

    return OpenAI(api_key=api_key)


@lru_cache(maxsize=1)
def _load_local_generator():
    if os.getenv("GENIFI_ENABLE_LOCAL_LLM", "false").strip().lower() not in {"1", "true", "yes"}:
        return None

    try:
        import torch
        from transformers import pipeline
    except ImportError as exc:
        logger.info("Local text generation dependencies unavailable: %s", exc)
        return None

    model_name = os.getenv("LOCAL_CHAT_MODEL", "distilgpt2").strip() or "distilgpt2"
    try:
        return pipeline(
            "text-generation",
            model=model_name,
            device=0 if torch.cuda.is_available() else -1,
        )
    except Exception as exc:
        logger.warning("Local chat model unavailable: %s", exc)
        return None


def _answer_with_openai(question: str) -> str | None:
    client = _load_openai_client()
    if client is None:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
            temperature=0.3,
            max_tokens=250,
        )
        answer = response.choices[0].message.content
        return answer.strip() if answer else None
    except Exception as exc:
        logger.warning("OpenAI chat failed: %s", exc)
        return None


def _answer_with_local_generator(question: str) -> str | None:
    generator = _load_local_generator()
    if generator is None:
        return None

    prompt = f"{SYSTEM_PROMPT}\n\nQuestion: {question}\nAnswer:"
    try:
        result = generator(
            prompt,
            max_new_tokens=140,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            truncation=True,
            pad_token_id=generator.tokenizer.eos_token_id,
        )
        generated_text = result[0]["generated_text"]
        answer = generated_text.split("Answer:", 1)[-1].strip()
        return answer or None
    except Exception as exc:
        logger.warning("Local chat generation failed: %s", exc)
        return None


def _fallback_answer(question: str) -> str:
    lower = question.lower()
    if any(term in lower for term in ["loan", "emi", "interest", "mortgage"]):
        return (
            "For loans, compare the annual percentage rate, processing fees, tenure, "
            "prepayment rules, and total interest paid. A lower EMI can still cost more "
            "if the tenure is much longer."
        )
    if any(term in lower for term in ["invest", "stock", "mutual fund", "portfolio"]):
        return (
            "Start with your goal, time horizon, and risk tolerance. Diversified funds "
            "usually suit beginners better than concentrated single-stock bets, and an "
            "emergency fund should come before high-risk investing."
        )
    if any(term in lower for term in ["budget", "saving", "expense", "spend"]):
        return (
            "Track fixed expenses, variable spending, debt payments, and savings rate. "
            "A practical target is to automate savings first, then adjust discretionary "
            "spending around what remains."
        )
    if any(term in lower for term in ["tax", "deduction", "income tax"]):
        return (
            "Tax choices depend on your jurisdiction, income, and filing status. Keep "
            "records of income, deductions, and investments, then verify the final filing "
            "rules with a qualified tax professional."
        )

    compact_question = re.sub(r"\s+", " ", question).strip()
    return (
        "I can help with finance questions about budgeting, loans, investing, taxes, "
        f"and documents. For this question, the safest next step is to identify the key numbers, "
        f"time horizon, and risk constraints: {compact_question}"
    )


def answer_general_query(question: str) -> str:
    question = question.strip()
    if not question:
        return "Please enter a finance question."

    for provider in (_answer_with_openai, _answer_with_local_generator):
        answer = provider(question)
        if answer:
            return answer

    return _fallback_answer(question)
