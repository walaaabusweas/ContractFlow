import json
from typing import Optional, Dict, Any
from config.redis_connection import redis_client
from graphs.state_schema import AgentState, ContractData # افترضنا اسم الملف هكذا

CACHE_TTL = 3600  

def load_extraction_session(email_id: str) -> Optional[AgentState]:
    """
    تحميل حالة استخراج فاتورة معينة بناءً على معرف الإيميل (Email ID).
    """
    try:
        cache_key = f"extraction_session:{email_id}"
        cached_data = redis_client.get(cache_key)

        if cached_data:
            data = json.loads(cached_data)
            return _dict_to_extraction_state(data)

        return None
    except Exception as e:
        print(f"[Redis] Error loading extraction session for {email_id}: {e}")
        return None

def save_extraction_session(email_id: str, state: AgentState):
    """
    حفظ حالة الاستخراج الحالية في Redis.
    """
    try:
        cache_key = f"extraction_session:{email_id}"
        
        # نستخدم to_dict() اللي عرفناها في الـ dataclass
        redis_client.setex(
            cache_key, 
            CACHE_TTL, 
            json.dumps(state.to_dict(), ensure_ascii=False)
        )
    except Exception as e:
        print(f"[Redis] Save extraction session error for {email_id}: {e}")

def _dict_to_extraction_state(data: dict) -> AgentState:
    "Converting the Redis reference dictionary to an ExtractionState object."
    s = AgentState()
    s.contract_text = data.get("contract_text", "")
    s.contract_language = data.get("contract_language", "en")
    s.english_contract_text = data.get("english_contract_text", "")
    s.is_extraction_successful = data.get("is_extraction_successful", False)
    s.contract_type = data.get("contract_type", "")
    extracted_data = data.get("extracted_data", {})
    s.extracted_data = ContractData(**extracted_data) if isinstance(extracted_data, dict) else extracted_data
    s.missing_clauses = data.get("missing_clauses", [])
    s.risks = data.get("risks", [])
    s.final_report = data.get("final_report", {})
    return s
