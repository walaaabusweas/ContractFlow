import json
import os
import re
from graphs.state_schema import AgentState
from graphs.nodes.qwen_client import qwen_chat_completion
from utils.helper import get_language_instruction


def prepare_custom_clauses_node(state: AgentState) -> AgentState:
    user_file_path = state.custom_file_path
    if not user_file_path:
        return state

    if not os.path.exists(user_file_path):
        print(f"⚠️ Custom clauses file not found: {user_file_path}", flush=True)
        return state
    if os.path.splitext(user_file_path)[1].lower() not in {".txt", ".json"}:
        state.update({"error": "Custom clauses file must be a TXT or JSON file."})
        return state

    try:
        with open(user_file_path, "r", encoding="utf-8") as f:
            raw_data = f.read().strip()
    except UnicodeDecodeError:
        state.update({"error": "Custom clauses file must be valid UTF-8 text or JSON."})
        return state

    if not raw_data:
        return state
    custom_json = convert_text_to_json(raw_data)
    print(f"custom_json: {custom_json}")
    normalized_data = normalize_custom_checklist(custom_json)
    print(f"normalized_data: {normalized_data}")
    state.update({"temp_custom_checklist": normalized_data})
    print(f"✅ Custom clauses prepared and normalized. Count: {len(normalized_data)}", flush=True)
    if state.temp_custom_checklist:
        state.history.append(f"Custom clauses prepared: {len(state.temp_custom_checklist)}")
    print(f"cisssss{state.temp_custom_checklist}")
    return state

def normalize_custom_checklist(custom_json: dict) -> dict:
    """
    تقوم بتنظيف المفاتيح وتجهيز قيم دلالية (Semantic Values) للـ Query.
    """
    normalized = {}
    for key, value in (custom_json or {}).items():
        # تنظيف المفتاح
        clean_key = re.sub(r"[^a-zA-Z0-9_]+", "_", str(key).strip().lower()).strip("_")
        if not clean_key:
            continue

        # تجهيز قيمة دلالية قوية للبحث
        if isinstance(value, dict):
            # إذا كان الـ JSON يحتوي على description و content، ندمجهم للبحث الدلالي
            desc = value.get("description", "")
            cont = value.get("content", "")
            clean_value = f"{desc}: {cont}".strip(": ")
        elif isinstance(value, list):
            clean_value = ", ".join([str(item) for item in value])
        else:
            clean_value = str(value).strip()

        if clean_value:
            normalized[clean_key] = clean_value
            
    return normalized

def convert_text_to_json(user_text: str) -> dict:
    # 1. محاولة تحميل مباشر (ربما النص هو JSON أصلاً)
    try:
        return json.loads(user_text)
    except:
        pass

    system_prompt = (
        "You are an expert data parser. Convert the input into a valid JSON object. "
        "Strict rule: Return ONLY the JSON object. Do not include any text before or after the JSON. "
        # "Do not use markdown. If the input is a list, convert it to a dict where keys are 'custom_clause_1', 'custom_clause_2', etc."
        "CRITICAL INSTRUCTION:The use of Chinese or any language other than the language of the contract is strictly prohibited under any circumstances."

    )
    
    try:
        response = qwen_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Convert this text to valid JSON:\n{user_text}"},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        
        # التنظيف الصارم للنص قبل التحويل
        clean_json = response.strip()
        
        # إزالة أي شيء قبل الـ { وأي شيء بعد الـ }
        start = clean_json.find('{')
        end = clean_json.rfind('}') + 1
        if start != -1 and end != -1:
            clean_json = clean_json[start:end]
            
        return json.loads(clean_json)
        
    except Exception as e:
        print(f"❌ Strict Parsing Failed: {e}")
        return {}