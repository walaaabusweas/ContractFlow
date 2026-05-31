
import json
import os
import chromadb
from graphs.state_schema import AgentState, ContractData
from graphs.nodes.qwen_client import qwen_chat_completion
from config.ChromaManager import ChromaManager
from graphs.nodes.qwen_client import get_embedding

def embed_query(question: str):
    return get_embedding("query: " + question)

def get_collection():
    return ChromaManager().get_collection()

def specific_clause_extraction_node(state: AgentState) -> AgentState:
    print(f"--- [NODE] EXECUTING SPECIFIC CLAUSE EXTRACTION: {state.contract_id} ---", flush=True)
    
    if not state.contract_id:
        print("⚠️ Contract ID missing. Cannot perform RAG.")
        return state

    schema_filename = "phaseOneSchem-en.json"
    try:
        with open(schema_filename, 'r', encoding='utf-8') as f:
            config = json.load(f)
            base_checklist = config["config"]["compliance_checklists"]["type_specific_clauses"].get(state.contract_type.lower(), {})

            custom_checklist = getattr(state, "temp_custom_checklist", {})
            checklist = {**base_checklist, **custom_checklist}
    except Exception as e:
        print(f"❌ Error loading schema: {e}")
        return state

    if not checklist:
        print(f"⚠️ No specific clause checklist for contract type: {state.contract_type}", flush=True)
        return state

    collection = get_collection()

    rag_context_blocks = []
    for clause_key, clause_desc in checklist.items():
        print(f"🔍 Vector Retrieval for: {clause_key}")
        
        try:
            results = collection.query(
    query_embeddings=[get_embedding(clause_desc)],
    where={"contract_id": state.contract_id},
    n_results=2
)
        except Exception as e:
            print(f"⚠️ Specific clause retrieval failed for {clause_key}: {e}", flush=True)
            continue
        
        if results['documents'] and results['documents'][0]:
            context = "\n".join(results['documents'][0])
            rag_context_blocks.append(f"### FIELD: {clause_key}\nDESCRIPTION: {clause_desc}\nCONTEXT:\n{context}")

    all_retrieved_context = "\n\n".join(rag_context_blocks)
    if not all_retrieved_context:
        print("⚠️ No specific clause RAG context found. Skipping Qwen specific extraction.", flush=True)
        data_dict = state.extracted_data.__dict__.copy() if hasattr(state.extracted_data, "__dict__") else {}
        data_dict["specific_clauses"] = {k: "Not Specified" for k in checklist.keys()}
        state.update({"extracted_data": ContractData(**data_dict)})
        return state
    
    # 4. الاستخراج النهائي عبر Qwen
    lang = state.contract_language or "en"
    system_message = (
        "You are an expert legal extractor. Extract the requested fields as a flat JSON object based on the RAG context provided."
        "If a field is not present, use 'Not Specified' (or 'غير محدد'). Return ONLY valid JSON."
    )
    
    try:
        response = qwen_chat_completion(
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Target Fields: {list(checklist.keys())}\n\nContext:\n{all_retrieved_context}"},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        
        clean_json = response.strip().replace("```json", "").replace("```", "")
        extracted_specific = json.loads(clean_json)
        
    except Exception as e:
        print(f"❌ Extraction error: {e}")
        extracted_specific = {k: "Not Specified" for k in checklist.keys()}

    # 5. تحديث الـ State بأمان
    data_dict = state.extracted_data.__dict__.copy() if hasattr(state.extracted_data, "__dict__") else {}
    data_dict["specific_clauses"] = extracted_specific
    state.update({"extracted_data": ContractData(**data_dict)})
    
    print(f"✅ Success: Specific clauses injected.")
    return state
