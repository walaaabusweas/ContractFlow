import os
import hashlib
import re
from typing import List
from graphs.state_schema import AgentState
from config.ChromaManager import ChromaManager
from graphs.nodes.qwen_client import get_embedding,qwen_chat_completion # تأكد من استيراد دالة الموديل
from utils.decorators import track_tokens

def get_collection():
    return ChromaManager().get_collection()

def get_parties_fallback(text: str) -> str:
    """استخراج الأطراف بشكل ثابت من أول 1000 حرف من العقد."""
    sample = text[:1000]
    prompt = "Extract the full names of the two contracting parties from the following contract text. Return only the names separated by 'and'."
    try:
        parties = qwen_chat_completion(prompt + "\n\n" + sample)
        return parties.strip()
    except Exception as e:
        return "Unknown Parties"

FIELD_BY_SECTION_TITLE = {
    "CONTRACT VALUE": "value",
    "VALUE": "value",
    "DURATION": "duration",
    "PAYMENT TERMS": "payment_terms",
    "PAYMENT": "payment_terms",
    "TERMINATION": "termination",
    "LIABILITY": "liability",
    "CONFIDENTIALITY": "confidentiality",
    "GOVERNING LAW": "governing_law",
    "DISPUTE RESOLUTION": "dispute_resolution",
}

SECTION_RE = re.compile(
    r"(?i)("
    r"SECTION\s+\d+\s*:\s*"
    r"(?:CONTRACT VALUE|DURATION|PAYMENT TERMS|PAYMENT|TERMINATION|LIABILITY|"
    r"CONFIDENTIALITY|GOVERNING LAW|DISPUTE RESOLUTION)"
    r"|"
    r"البند\s+(?:الأول|الاول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر)"
    r"\s*:\s*.{0,180}?"
    r"(?:VALUE|DURATION|PAYMENT TERMS|PAYMENT|TERMINATION|LIABILITY|"
    r"CONFIDENTIALITY|GOVERNING LAW|DISPUTE RESOLUTION|SUPPLY SPECIFICATIONS)"
    r"\)?"
    r"|"
    r"البند\s+(?:الأول|الاول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر)"
    r"\s*:\s*"
    r"(?:القيمة|القيمه|مدة|شروط|الية|آلية|انهاء|إنهاء|الغاء|إلغاء|المسؤولية|المسؤوليه|"
    r"السرية|السريه|القانون|تسوية|النزاعات|المواصفات)"
    r"[^:\n]{0,160}"
    r")"
)


def _normalize_text_for_chunking(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text or "")
    text = text.replace("ی", "ي").replace("ک", "ك")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _field_from_heading(heading: str) -> str:
    upper_heading = heading.upper()
    for title, field in sorted(FIELD_BY_SECTION_TITLE.items(), key=lambda item: len(item[0]), reverse=True):
        if title in upper_heading:
            return field

    arabic_heading = heading.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    if "القيمة" in arabic_heading or "القيمه" in arabic_heading:
        return "value"
    if "مدة" in arabic_heading or "الجدول الزمني" in arabic_heading:
        return "duration"
    if "الدفع" in arabic_heading:
        return "payment_terms"
    if "انهاء" in arabic_heading or "الغاء" in arabic_heading:
        return "termination"
    if "المسؤولية" in arabic_heading or "التعويض" in arabic_heading:
        return "liability"
    if "السرية" in arabic_heading or "الافصاح" in arabic_heading:
        return "confidentiality"
    if "القانون" in arabic_heading:
        return "governing_law"
    if "النزاعات" in arabic_heading or "القضائية" in arabic_heading:
        return "dispute_resolution"

    return "general"


def _fallback_chunks(text: str):
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) > 50]
    if not paragraphs and text:
        paragraphs = [text]

    chunks = []
    for i, paragraph in enumerate(paragraphs):
        chunks.append({
            "content": paragraph,
            "section": f"PARAGRAPH {i + 1}",
            "clause_type": "general",
        })
    return chunks

def parse_and_build_chunks(text: str):
    text = _normalize_text_for_chunking(text)
    if not text:
        return []

    matches = list(SECTION_RE.finditer(text))
    if not matches:
        return _fallback_chunks(text)

    chunks = []
    preamble = text[:matches[0].start()].strip()
    if len(preamble) > 50:
        chunks.append({
            "content": preamble,
            "section": "PREAMBLE",
            "clause_type": "general",
        })

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()
        section_name = match.group(1).upper()

        if not section_text:
            continue

        chunks.append({
            "content": section_text,
            "section": section_name,
            "clause_type": _field_from_heading(section_name),
        })

    return chunks

def embed_chunks(chunks_texts: List[str]) -> List[List[float]]:
    return [get_embedding(text) for text in chunks_texts]


@track_tokens("ingest_node")
def ingest_node(state: AgentState) -> AgentState:
    print("--- [NODE] STARTING SMART INGESTION WITH STATIC PARTIES EXTRACTION ---")

    contract_id = generate_contract_id(state.contract_text)
    
    # استخراج الأطراف بشكل ثابت (Static)
    extracted_parties = get_parties_fallback(state.contract_text)
    
    chunks = parse_and_build_chunks(state.contract_text)
    texts = [chunk["content"] for chunk in chunks]

    print(f"Generating embeddings for {len(texts)} chunks...")
    embeddings = embed_chunks(texts)
    
    collection = get_collection()
    chunk_ids = [f"{contract_id}_chunk_{i}" for i in range(len(texts))]
    
    try:
        collection.delete(where={"contract_id": contract_id})
    except Exception as cleanup_error:
        print(f"⚠️ Could not clear old chunks for {contract_id}: {cleanup_error}")

    collection.upsert(
        documents=texts,
        embeddings=embeddings,
        metadatas=[{
            "section": c["section"], 
            "clause_type": c["clause_type"],
            "lang": state.contract_language,
            "contract_id": contract_id,
            "parties": extracted_parties 
        } for c in chunks],
        ids=chunk_ids
    )

    state.update({
        "contract_id": contract_id,
        "history": state.history + [f"Ingestion Complete: {contract_id}"],
        "parties": extracted_parties 
    })

    print(f"✅ Success: Contract {contract_id} ingested with parties: {extracted_parties}")
    return state

def generate_contract_id(text: str) -> str:
    hash_object = hashlib.sha256(text[:1000].encode())
    return hash_object.hexdigest()[:12]
