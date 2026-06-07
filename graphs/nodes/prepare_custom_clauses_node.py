import json
import os
import re
from graphs.state_schema import AgentState
from graphs.nodes.qwen_client import qwen_chat_completion
from utils.decorators import track_tokens


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

    state.temp_custom_checklist = normalize_custom_checklist(custom_json)
    if state.temp_custom_checklist:
        state.history.append(f"Custom clauses prepared: {len(state.temp_custom_checklist)}")
    return state

@track_tokens("normalize_custom_checklist")
def normalize_custom_checklist(custom_json: dict) -> dict:
    normalized = {}
    for key, value in (custom_json or {}).items():
        clean_key = re.sub(r"[^a-zA-Z0-9_]+", "_", str(key).strip().lower()).strip("_")
        if not clean_key:
            continue

        if isinstance(value, (dict, list)):
            clean_value = json.dumps(value, ensure_ascii=False)
        else:
            clean_value = str(value).strip()

        if clean_value:
            normalized[clean_key] = clean_value
    return normalized


def convert_text_to_json(user_text: str) -> dict:
    """
    تحويل نص البنود التخصصية المخصص من المستخدم إلى JSON مهيكل.
    """
    try:
        parsed = json.loads(user_text)
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            return {
                f"custom_clause_{index + 1}": str(item).strip()
                for index, item in enumerate(parsed)
                if str(item).strip()
            }
    except json.JSONDecodeError:
        pass

    system_prompt = (
        "You are an expert data parser. Convert the user's provided text into a valid JSON object. "
        "The format must be: {'Clause_Name': 'Description/Instructions'}. "
        "The Clause_Name should be a clean, snake_case string. "
        "Return ONLY the raw JSON object, no explanation, no markdown blocks."
    )
    
    try:
        response = qwen_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Convert this text to JSON: {user_text}"},
            ],
            temperature=0,  
            response_format={"type": "json_object"},
        )
        
        clean_json = response.strip().replace("```json", "").replace("```", "")
        return json.loads(clean_json)
        
    except Exception as e:
        print(f"❌ Failed to convert custom text to JSON: {e}")
        return {} 
