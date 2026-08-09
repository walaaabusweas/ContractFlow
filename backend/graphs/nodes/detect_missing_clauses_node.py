import json
from typing import Any, Dict, List
from graphs.state_schema import AgentState, ContractData
from config.ChromaManager import ChromaManager
from graphs.nodes.qwen_client import get_embedding, qwen_chat_completion
from utils.decorators import track_tokens
from utils.helper import get_language_instruction

@track_tokens("detect_missing_clauses_node")
def detect_missing_clauses_node(state: AgentState) -> AgentState:
    print("\n--- [NODE] OPTIMIZED SEMANTIC AUDIT START ---", flush=True)
    
    if not state.contract_id:
        return state

    data_dict = state.extracted_data.__dict__.copy()
    specific_data = data_dict.get("specific_clauses", {}) or {}
    
    mapping = {
        "Parties": "parties", "Financial Value": "value", "Duration": "duration",
        "Payment Terms": "payment_terms", "Termination": "termination", 
        "Liability": "liability", "Confidentiality": "confidentiality", 
        "Governing Law": "governing_law", "Dispute Resolution": "dispute_resolution"
    }
    
    # تحسين: إرسال حالة المفاتيح فقط للموديل لتقليل الـ Input Tokens
    audit_status = {}
    for h, k in mapping.items():
        val = data_dict.get(k)
        audit_status[h] = "FOUND" if val and len(str(val)) > 5 else "MISSING"
    
    for k in specific_data.keys():
        val = specific_data.get(k)
        audit_status[f"Specific: {k}"] = "FOUND" if val and len(str(val)) > 5 else "MISSING"

    # سحب ملخص من الـ Context (أول 200 حرف لكل قطعة)
    collection = ChromaManager().get_collection()
    results = collection.query(
        query_embeddings=[get_embedding(f"Retrieve missing clauses for: {state.contract_id}", state=state)],
        n_results=3, where={"contract_id": state.contract_id}
    )
    context = "\n".join([doc[:200] for doc in results.get("documents", [[]])[0]])

    audit_prompt = f"""
    Role: Legal Auditor.
    Status: {json.dumps(audit_status)}
    Context: {context}
    
    Task: Identify if fields marked "MISSING" are truly missing. If found in Context, extract them.
    Return ONLY JSON: {{"audit": {{"Field": "COMPLETE/INCOMPLETE"}}, "extracted": {{"Field": "Value"}}}}
    No conversational text.
    - {get_language_instruction(state.contract_language)}
    "CRITICAL INSTRUCTION:The use of Chinese or any language other than the language of the contract is strictly prohibited under any circumstances."

    """

    try:
        response = qwen_chat_completion([{"role": "user", "content": audit_prompt}], temperature=0)
        cleaned = response.replace("```json", "").replace("```", "").strip()
        result = json.loads(cleaned)
        
        rag_json = result.get("extracted", {})
        
        # تحديث الـ State بالقيم الجديدة
        for field, val in rag_json.items():
            if field in mapping: data_dict[mapping[field]] = val
            elif field in specific_data: specific_data[field] = val
    except:
        pass

    # [إضافة التعديل الذكي]: فحص دقيق للمفقودات (يدعم العربية والإنجليزية)
    missing_clauses = []
    
    # قائمة العبارات التي تعني أن البند مفقود في اللغتين
    # قائمة العبارات التي تعني أن البند مفقود في اللغتين
    invalid_markers = [
        "not specified", "not found", "n/a", "none", "missing",  # أضفنا "missing" هنا
        "غير محدد", "غير موجود", "لا يوجد", "غير مذكور"
    ]
    
    # فحص الـ Data العادية
    for h, k in mapping.items():
        val = data_dict.get(k)
        if val is None or (isinstance(val, str) and str(val).lower().strip() in invalid_markers):
            missing_clauses.append(h)
            
    # فحص الـ Specific Clauses
    for k, val in specific_data.items():
        if val is None or (isinstance(val, str) and str(val).lower().strip() in invalid_markers):
            missing_clauses.append(f"Specific: {k}")

    data_dict["specific_clauses"] = specific_data
    state.update({
        "extracted_data": ContractData(**data_dict),
        "missing_clauses": missing_clauses,
        "is_compliance_checked": True,
        "history": state.history + ["Optimized Semantic Audit completed"]
    })
    
    print(f"🏁 Audit finished. Missing count: {len(missing_clauses)}", flush=True)
    return state