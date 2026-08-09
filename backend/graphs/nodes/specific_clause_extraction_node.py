import json
import os
import chromadb
from graphs.state_schema import AgentState, ContractData
from graphs.nodes.qwen_client import qwen_chat_completion
from config.ChromaManager import ChromaManager
from graphs.nodes.qwen_client import get_embedding
from utils.decorators import track_tokens
from utils.helper import get_language_instruction

def get_collection():
    return ChromaManager().get_collection()

@track_tokens("specific_clause_extraction_node")
def specific_clause_extraction_node(state: AgentState) -> AgentState:
    print(f"--- [NODE] EXECUTING DYNAMIC BATCH SPECIFIC CLAUSE EXTRACTION: {state.contract_id} ---", flush=True)
    
    if not state.contract_id:
        print("⚠️ Contract ID missing. Cannot perform RAG.")
        return state

    # 1. تحميل الـ Checklist وتجهيز البنود الديناميكية
    schema_filename = "phaseOneSchem-en.json"
    try:
        with open(schema_filename, 'r', encoding='utf-8') as f:
            config = json.load(f)
            base_checklist = config["config"]["compliance_checklists"]["type_specific_clauses"].get(state.contract_type.lower(), {})
            # القائمة التي ستكون متغيرة حسب نوع العقد أو مدخلات المستخدم
            custom_checklist = getattr(state, "temp_custom_checklist", {})
            checklist = {**base_checklist, **custom_checklist}
    except Exception as e:
        print(f"❌ Error loading schema: {e}")
        return state

    if not checklist:
        print(f"⚠️ No checklist found.", flush=True)
        return state

    # 2. جلب السياق
    collection = get_collection()
    query_text = "Specific contract clauses: " + ", ".join(checklist.values())
    query_embedding = get_embedding(query_text, state=state)
    
    results = collection.query(
        query_embeddings=[query_embedding],
        where={"contract_id": state.contract_id},
        n_results=10
    )
    all_retrieved_context = "\n".join(results.get('documents', [[]])[0])

    if not all_retrieved_context:
        data_dict = state.extracted_data.__dict__.copy()
        data_dict["specific_clauses"] = {k: "Not Specified" for k in checklist.keys()}
        state.update({"extracted_data": ContractData(**data_dict)})
        return state
    
    # 3. الاستخراج باستخدام التوجيه الديناميكي (Dynamic Mapping)
    # نرسل للـ LLM القائمة كقاموس (مفتاح: وصف) ليفهم ما يبحث عنه بالضبط
    target_mapping = json.dumps(checklist, ensure_ascii=False)
    
    system_message = (
        "You are a legal document extractor. "
        "Your task is to find the legal content related to each key provided in this mapping: " + target_mapping + ". "
        "For each key, extract the FULL corresponding legal text from the provided contract context. "
        "DO NOT return the name of the clause. Return the actual text found in the contract describing this clause. "
        "If the clause is not present in the text, return 'Not Specified'. "
        "Output must be a valid JSON object."
        f"{get_language_instruction(state.contract_language)}"
        "CRITICAL INSTRUCTION:The use of Chinese or any language other than the language of the contract is strictly prohibited under any circumstances."

    )
    
    try:
        response = qwen_chat_completion(
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Context:\n{all_retrieved_context}\n\nOutput only JSON:"},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        
        clean_json = response.strip().replace("```json", "").replace("```", "")
        extracted_specific = json.loads(clean_json)
        
    except Exception as e:
        print(f"❌ Extraction error: {e}")
        extracted_specific = {k: "Not Specified" for k in checklist.keys()}

    # 4. تحديث الـ State
    data_dict = state.extracted_data.__dict__.copy() if hasattr(state.extracted_data, "__dict__") else {}
    data_dict["specific_clauses"] = extracted_specific
    state.update({"extracted_data": ContractData(**data_dict)})
    
    print(f"✅ Success: Dynamic batch specific clauses injected.")
    return state