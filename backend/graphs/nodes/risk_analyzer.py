import json
import traceback
from graphs.state_schema import AgentState
from graphs.nodes.qwen_client import qwen_chat_completion, get_embedding
from config.ChromaManager import ChromaManager
from utils.decorators import track_tokens
from utils.helper import get_language_instruction

def get_collection():
    return ChromaManager().get_collection()

@track_tokens("risk_analyzer_node")
def risk_analyzer_node(state: AgentState) -> AgentState:
    print(f"--- [NODE] EXECUTING FILTERED RISK ANALYSIS (Active Risks Only) ---", flush=True)
    
    config = json.load(open("phaseOneSchem-en.json", 'r', encoding='utf-8'))
    rules = config.get("config", {}).get("risk_analysis_rules", [])
    all_risks = []
    collection = get_collection()
    batch_size = 3
    
    # تقسيم القواعد إلى مجموعات لزيادة الدقة
    for i in range(0, len(rules), batch_size):
        rule_batch = rules[i : i + batch_size]
        batch_context = []
        
        # 1. المعالجة لكل مجموعة
        for rule in rule_batch:
            try:
                query_text = f"{rule.get('description')}"
                results = collection.query(
                    query_embeddings=[get_embedding(query_text, state=state)],
                    where={"contract_id": state.contract_id},
                    n_results=2
                )
                documents = results.get('documents', [[]])[0]
                
                if not documents:
                    # التحقق البرمجي: إذا لم يوجد نص، نصنفه كـ Absent فوراً
                    all_risks.append({
                        "id": rule.get('id'),
                        "title": "Clause Not Found",
                        "description": "This clause is not addressed in the contract."
                    })
                else:
                    # إذا وجد نص، نضيفه للسياق ليحلله الـ LLM
                    combined_context = "\n\n".join([f"Clause Part {j+1}: {doc}" for j, doc in enumerate(documents)])
                    batch_context.append(f"RULE ID: {rule.get('id')}\nDESCRIPTION: {rule.get('description')}\nCLAUSES:\n{combined_context}")
            except Exception as e:
                print(f"⚠️ Failed to retrieve context for rule {rule.get('id')}: {e}")

        # 2. استدعاء الـ LLM فقط للقواعد التي لها نصوص قانونية
        if batch_context:
            context_str = "\n\n===\n\n".join(batch_context)
            prompt = f"""
            You are a legal risk analyst. Analyze the following contract clauses.
            RULES AND CLAUSES TO ANALYZE:
            {context_str}
            INSTRUCTIONS:
            - Analyze the rules provided. Identify ONLY clauses that represent a LEGAL OR FINANCIAL RISK.
            - If a clause is standard and contains NO risk, IGNORE it (do not include it in the output).
            - If a clause contains a potential risk, extract it and explain why it is a risk.
            - IMPORTANT: When referring to a clause in your description, DO NOT use numbers like 'Clause 5' or 'Clause 2.3'.
            - ALWAYS use the descriptive title of the clause as it appears in the contract (e.g., 'Liability & Indemnification', 'Payment Terms').
            - {get_language_instruction(state.contract_language)}
            - Output ONLY a valid JSON object with a 'risks' list: 
            {{"risks": [{{"id": "RULE_ID", "title": "Risk Title", "description": "Explain the risk using the full clause title, not numbers"}}]}}
            - If no risks are found in this batch, return {{"risks": []}}
             CRITICAL INSTRUCTIONS:
            1. If a rule's STATUS is 'NOT FOUND IN CONTRACT', you MUST flag it as a HIGH RISK because the protective clause is absent.
            2. If a rule's STATUS is 'FOUND', analyze the content. If the content is balanced, ignore it. If it is one-sided or harmful, flag it as a risk.
            3. Use the logic: Absence of a mandatory protection = Risk.
            4. You must respond ONLY in Arabic or English depending on the language of the contract. Under no circumstances are you allowed to use Chinese, English, or any other language in the output. If the information is not clearly stated in the text, write 'غير محدد' (Not mentioned). Do not hallucinate or translate concepts into foreign languages. Strictly follow this constraint."

            """
            
            try:
                response = qwen_chat_completion([{"role": "user", "content": prompt}])
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end != -1:
                    data = json.loads(response[start:end])
                    if isinstance(data, dict) and "risks" in data:
                        all_risks.extend(data["risks"])
            except Exception as e:
                print(f"⚠️ Failed to parse JSON for batch: {e}")

    # Deduplication Step: تصفية المخاطر المكررة بناءً على الـ id
    unique_risks = []
    seen_ids = set()
    for risk in all_risks:
        risk_id = risk.get("id")
        if risk_id not in seen_ids:
            unique_risks.append(risk)
            seen_ids.add(risk_id)
            
    state.risks = unique_risks
    print(f"--- [NODE] ANALYSIS COMPLETE. TOTAL RISKS FOUND: {len(unique_risks)} ---")
    return state