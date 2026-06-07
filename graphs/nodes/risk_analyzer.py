import json
import traceback
from graphs.state_schema import AgentState
from graphs.nodes.qwen_client import qwen_chat_completion, get_embedding
from config.ChromaManager import ChromaManager
from utils.decorators import track_tokens

def get_collection():
    return ChromaManager().get_collection()

@track_tokens("risk_analyzer_node")
def risk_analyzer_node(state: AgentState) -> AgentState:
    print(f"--- [NODE] EXECUTING RISK ANALYSIS (WITH RAG): {state.contract_id} ---", flush=True)
    
    try:
        with open("phaseOneSchem-en.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
            rules = config.get("config", {}).get("risk_analysis_rules", [])
            query_terms = ", ".join([r.get("title", r.get("id", "")) for r in rules])
    except:
        rules, query_terms = [], "liability, payment, termination, risks"

    context = ""
    try:
        collection = get_collection()
        results = collection.query(
            query_embeddings=[get_embedding(query_terms)],
            where={"contract_id": state.contract_id},
            n_results=3
        )
        if results.get('documents') and results['documents'][0]:
            context = "\n".join(results['documents'][0])
    except Exception as e:
        print(f"⚠️ Chroma retrieval failed: {e}")

    ext_data = state.extracted_data.__dict__ if hasattr(state.extracted_data, "__dict__") else state.extracted_data
    prompt_payload = {
        "rules": rules,
        "contract_summary": {
            "value": ext_data.get("value"),
            "liability": ext_data.get("liability"),
            "payment": ext_data.get("payment_terms"),
            "termination": ext_data.get("termination")
        },
        "missing": state.missing_clauses,
        "retrieved_context": context 
    }

    system_msg = (
        "You are a strict Legal Auditor. Analyze the contract against the provided rules and retrieved context. "
        "Output ONLY JSON: {'risks': [{'id': '...', 'level': '...', 'title': '...', 'description': '...'}]}. "
        "If no violations are found, return {'risks': []}."
        "CLAUSE INTERPRETATION: If the contract contains a Penalty Clause (الشرط الجزائي) "
        "with a cap (e.g., 'max 10%'), do NOT categorize the entire contract as 'Unlimited Liability'. "
        "Treat the contract as having 'Limited Liability' or 'Qualified Liability'. "
        "'Unlimited Liability' is reserved ONLY for clauses where absolutely no cap exists "
        "and there is no indemnity/penalty limitation provided."
        "NUMERICAL ACCURACY: When evaluating payment terms, strictly calculate the timeline based ONLY on the total contract duration . Do not assume extra days for project completion unless explicitly stated."
        "Analyze the contract for risks. If a specific clause like 'Automatic Renewal' is not explicitly stated in the text, you MUST return 'Not applicable' or 'None', do not invent risks."
    )

    try:
        response = qwen_chat_completion(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": json.dumps(prompt_payload)}
            ],
            temperature=0,
        )
        
        start = response.find('{')
        end = response.rfind('}') + 1
        data = json.loads(response[start:end])
        
        state.update({"risks": data.get("risks", [])})
        print(f"✅ Analysis finished: {len(state.risks)} risks found.")

    except Exception as e:
        print(f"❌ ERROR: {traceback.format_exc()}")
        state.update({"risks": []})

    return state