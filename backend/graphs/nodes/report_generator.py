import json
import traceback
import re
from graphs.state_schema import AgentState
from graphs.nodes.qwen_client import qwen_chat_completion, get_embedding
from config.ChromaManager import ChromaManager
from utils.decorators import track_tokens
from utils.helper import get_language_instruction

def get_collection():
    """الوصول لقاعدة البيانات الثابتة"""
    return ChromaManager().get_collection()

def cleanup_text(text):
    """تنظيف النصوص من الرموز الصينية وتحويل الترقيم الرقمي إلى نقاط"""
    if not isinstance(text, str):
        return text
    # حذف الرموز الصينية
    text = re.sub(r'[\u4e00-\u9fff]', '', text)
    # استبدال أي بداية سطر برقم (مثل "1." أو "1-") بـ "•"
    text = re.sub(r'^\s*\d+[\.\-\)]\s*', '• ', text, flags=re.MULTILINE)
    return text.strip()

@track_tokens("report_generator_node")
def report_generator_node(state: AgentState) -> AgentState:
    print("\n--- [NODE] EXECUTING ADVANCED COMPLIANCE & LEGAL REPORT GENERATOR ---", flush=True)
    
    # تأمين جلب لغة العقد برمجياً
    lang = state.contract_language or "en"
    lang_str = str(lang).strip().lower()
    
    ext = state.extracted_data
    base_data_dict = ext.__dict__ if hasattr(ext, "__dict__") else ext
    specific_clauses_dict = getattr(ext, 'specific_clauses', {}) or {}
    if not isinstance(specific_clauses_dict, dict):
        specific_clauses_dict = {}

    # 1. تجميع البيانات المستخرجة
    compiled_extracted_data = {}
    for k, v in base_data_dict.items():
        if k != "specific_clauses" and v:
            compiled_extracted_data[k] = v
    for k, v in specific_clauses_dict.items():
        if v:
            compiled_extracted_data[k] = v

    # 2. خطوة RAG
    historical_legal_knowledge = "No historical legal knowledge found."
    try:
        collection = get_collection()
        search_query = f"Reviewed {state.contract_type} contract legal comments, risk mitigations, approval or rejection notes"
        results = collection.query(
            query_embeddings=[get_embedding(search_query, state=state)],
            where={"contract_id": state.contract_id} if state.contract_id else None,
            n_results=1
        )
        if results.get('documents') and results['documents'][0]:
            historical_legal_knowledge = "\n".join(results['documents'][0])
            print("✨ [RAG] Historical legal review guidelines retrieved successfully.", flush=True)
    except Exception as e:
        print(f"⚠️ Historical RAG knowledge retrieval skipped: {e}", flush=True)

    analysis_context = {
        "contract_type": state.contract_type.upper(),
        "all_extracted_text_data": compiled_extracted_data,
        "missing_clauses": state.missing_clauses,
        "risks": state.risks,
        "historical_legal_benchmarks": historical_legal_knowledge
    }

    # 3. صياغة التوجيهات مع تحذير شديد ضد الصينية والترقيم الرقمي
    system_message = (
            "You are an expert legal consultant. Generate an executive review report in strict JSON format.\n"
            "REQUIRED KEYS: 'initial_review_notes', 'notes_for_legal_review', 'extracted_important_clauses'.\n"
            "STRICT CONSTRAINTS:\n"
            "1. NO Chinese characters allowed.\n"
            "2. For 'notes_for_legal_review', use bullet points (•) ONLY. Do NOT use numbers (1, 2, 3).\n"
            "3. Ensure that extracted_important_clauses is a list of objects, where each object includes the 'title' of the clause and a 'summary' of its content based on the provided extracted data use Arabic or English depending on the language of the contract.\n"
            "4. Return ONLY a valid JSON object. No markdown, no conversational text."
            "5. Please provide the notes_for_legal_review as a clean JSON list of full sentences. Do not output characters or broken strings. Ensure each item is a complete, grammatically correct advice sentence."
            f"{get_language_instruction(state.contract_language)} in initial_review_notes and notes_for_legal_review."
        )

    # 4. استدعاء الموديل
    try:
        ai_response = qwen_chat_completion(
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Context for Report Generation:\n{json.dumps(analysis_context, ensure_ascii=False)}"},
            ],
            temperature=0,  
            response_format={"type": "json_object"},
        )
        clean_content = ai_response.replace("```json", "").replace("```", "").strip()
        parsed_report = json.loads(clean_content)
        
        # تطبيق التنظيف على النصوص قبل وضعها في الـ State
        initial_notes = cleanup_text(parsed_report.get("initial_review_notes", ""))
        legal_notes = [cleanup_text(n) for n in parsed_report.get("notes_for_legal_review", [])]
        extracted_important = [cleanup_text(c) for c in parsed_report.get("extracted_important_clauses", [])]
        
    except Exception as e:
        print(f"❌ Failed to parse AI structured report notes: {e}")
        initial_notes = "التقرير الاستشاري الآلي غير متوفر حالياً." if lang_str == "ar" else "AI analysis is temporarily unavailable."
        legal_notes = ["يرجى مراجعة لوحة تحكم المخاطر يدوياً."] if lang_str == "ar" else ["Please review risks manually."]
        extracted_important = []

    # 5. بناء هيكل المخرج النهائي
    fallback_not_specified = "غير محدد" if lang_str == "ar" else "Not specified"
    
    final_output = {
        "contract_type": state.contract_type.upper(),
        "key_contract_terms": {
            "parties": base_data_dict.get("parties") or fallback_not_specified,
            "value": base_data_dict.get("value") or fallback_not_specified,
            "duration": base_data_dict.get("duration") or fallback_not_specified,
            "payment_terms": base_data_dict.get("payment_terms") or fallback_not_specified,
            "governing_law": base_data_dict.get("governing_law") or fallback_not_specified
        },
        "missing_clauses": state.missing_clauses,
        "extracted_important_clauses": extracted_important,
        "risk_highlights": [
            {"id": r.get("id"), "title": r.get("title"), "description": r.get("description")} for r in state.risks
        ],
        "initial_review_notes": initial_notes,
        "notes_for_legal_review": legal_notes
    }

    # 6. تحديث الـ State
    state.update({
        "final_report": final_output,
        "is_compliance_checked": True,
        "history": state.history + ["Compliance & Legal Review Report generated successfully"]
    })

    print("✅ Successfully generated unified AI-driven Report with cleaning applied.")
    return state