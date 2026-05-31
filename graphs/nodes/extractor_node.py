import json
import os
import re

from graphs.nodes.qwen_client import qwen_chat_completion
from graphs.state_schema import AgentState, ContractData

EXTRACTION_FIELDS = [
    "parties",
    "value",
    "duration",
    "payment_terms",
    "termination",
    "liability",
    "confidentiality",
    "governing_law",
    "dispute_resolution",
]

ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
FOREIGN_DRIFT_RE = re.compile(r"[\u4E00-\u9FFF]|[A-Za-zÀ-ÖØ-öø-ÿ]{3,}")


def _short_text(value):
    if value is None:
        return None
    value = str(value).strip()
    if not value or value.lower() in {"null", "none", "not specified", "n/a"}:
        return None
    return value


def _clean_json_response(response_text: str) -> str:
    clean_text = response_text.strip()
    if clean_text.startswith("```"):
        lines = clean_text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        clean_text = "\n".join(lines).strip()

    start = clean_text.find("{")
    end = clean_text.rfind("}")
    if start != -1 and end != -1 and start < end:
        return clean_text[start:end + 1]
    return clean_text


def _parse_json_response(response_text: str) -> dict:
    parsed = json.loads(_clean_json_response(response_text))
    if not isinstance(parsed, dict):
        raise ValueError("Qwen extraction response must be a JSON object.")
    return parsed


def _repair_json_response(response_text: str) -> dict:
    repair_prompt = (
        "Fix the following invalid JSON and return only one valid json object. "
        "Keep the same keys and values. Do not add markdown or explanations.\n\n"
        f"{response_text}"
    )
    repaired_response = qwen_chat_completion(
        messages=[
            {
                "role": "system",
                "content": "You repair invalid JSON. Return only valid json.",
            },
            {"role": "user", "content": repair_prompt},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return _parse_json_response(repaired_response)


def _is_arabic_contract(state: AgentState) -> bool:
    if state.contract_language == "ar":
        return True
    return bool(ARABIC_RE.search(state.contract_text or ""))


def _has_foreign_drift(value: str) -> bool:
    return bool(ARABIC_RE.search(value) and FOREIGN_DRIFT_RE.search(value))


def _strip_foreign_drift(value: str) -> str:
    value = re.sub(r"[\u4E00-\u9FFF]+", "", value)
    value = re.sub(r"[A-Za-zÀ-ÖØ-öø-ÿ'’]+", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" .،؛:-")


def _rewrite_arabic_only(value: str) -> str:
    rewrite_response = qwen_chat_completion(
        messages=[
            {
                "role": "system",
                "content": (
                    "أنت محرر قانوني عربي. أعد صياغة النص باللغة العربية الفصحى فقط. "
                    "احذف أي كلمات صينية أو فرنسية أو إنجليزية. أرجع JSON صالح فقط بالمفتاح text."
                ),
            },
            {"role": "user", "content": value},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    parsed = _parse_json_response(rewrite_response)
    cleaned = parsed.get("text")
    if not cleaned:
        return _strip_foreign_drift(value)
    return str(cleaned).strip()


def _normalize_arabic_value(value):
    if value is None:
        return None
    if isinstance(value, list):
        return [_normalize_arabic_value(item) for item in value]

    text = str(value).strip()
    if not _has_foreign_drift(text):
        return text

    try:
        cleaned = _rewrite_arabic_only(text)
    except Exception as cleanup_error:
        print(f"⚠️ Arabic cleanup failed, stripping foreign drift locally: {cleanup_error}", flush=True)
        cleaned = _strip_foreign_drift(text)

    return cleaned or None


def _normalize_arabic_extraction(parsed: dict, state: AgentState) -> dict:
    if not _is_arabic_contract(state):
        return parsed

    normalized = parsed.copy()
    for key in [*EXTRACTION_FIELDS, "reasoning"]:
        if key in normalized:
            normalized[key] = _normalize_arabic_value(normalized[key])
    return normalized


def extraction_node(state: AgentState) -> AgentState:
    print("--- [NODE] EXTRACTING STRUCTURED DATA VIA QWEN ---", flush=True)

    # 1. تجميع الـ Context المسترجع
    context_text = "\n\n".join(
        f"{key.upper()}: {value}"
        for key, value in state.retrieved_context.items()
        if value
    )

    system_prompt = """
    You are an expert legal data extraction agent.
    Extract these fields from the provided document:
    parties, value, duration, payment_terms, termination, liability, confidentiality, governing_law, dispute_resolution.

    CRITICAL RULES:
    1. Return ONLY valid JSON. Do not add markdown, comments, explanations, or text outside the JSON object.
    2. Use exactly these keys:
       "parties", "value", "duration", "payment_terms", "termination", "liability",
       "confidentiality", "governing_law", "dispute_resolution", "reasoning".
    3. "parties" must be an array of strings. All other values must be a single-line string or null.
    4. Do not use bullet points. Do not put newline characters inside values.
    5. Escape quotation marks inside Arabic text if needed.
    6. Summaries must be short single sentences. Preserve all numbers, percentages, and deadlines.
    7. Write values in the same language as the contract.
    8. If any field is missing after thorough searching, return null.
    9. For "parties", extract the two main entities signing the document.
    10. If "value" is not explicitly a contract price, look for liquidated damages or compensation and explain the context in "reasoning".
    """

    # 2. بناء الـ Messages بالبنية الصحيحة المتوقعة من الـ Client الخاص بكِ
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Context:\n{context_text}"}
    ]

    # 3. استدعاء الموديل وتأمين الـ JSON من الـ Markdown Blocks
    response_text = qwen_chat_completion(
        messages=messages,
        temperature=0,
        response_format={"type": "json_object"},
    )
        
    try:
        parsed = _parse_json_response(response_text)
    except (json.JSONDecodeError, ValueError) as parse_error:
        print(f"⚠️ Invalid JSON from extraction model: {parse_error}", flush=True)
        print(f"⚠️ Raw extraction response preview: {response_text[:500]}", flush=True)
        try:
            parsed = _repair_json_response(response_text)
        except Exception as repair_error:
            print(f"❌ Failed to repair extraction JSON: {repair_error}", flush=True)
            parsed = {field: None for field in EXTRACTION_FIELDS}
            parsed["parties"] = []
            parsed["reasoning"] = f"Extraction JSON repair failed: {repair_error}"
            state.update({"error": parsed["reasoning"]})

    parsed = _normalize_arabic_extraction(parsed, state)

    # 4. معالجة وتأمين مصفوفة الأطراف
    parties = parsed.get("parties") or []
    if isinstance(parties, str):
        parties = [parties]

    # 5. تحديث الـ State بالمخرجات الذكية والمحمية
    state.update({
        "extracted_data": {
            "parties": [str(p).strip()[:2000] for p in parties if str(p).strip()],
            "value": _short_text(parsed.get("value")),
            "duration": _short_text(parsed.get("duration")),
            "payment_terms": _short_text(parsed.get("payment_terms")),
            "termination": _short_text(parsed.get("termination")),
            "liability": _short_text(parsed.get("liability")),
            "confidentiality": _short_text(parsed.get("confidentiality")),
            "governing_law": _short_text(parsed.get("governing_law")),
            "dispute_resolution": _short_text(parsed.get("dispute_resolution")),
            "specific_clauses": {},
        },
        "is_extraction_successful": True,
        "history": state.history + ["Extraction Complete via Qwen"],
    })

    print("✅ Success: Intelligently summarized data saved to state.", flush=True)
    return state
