import json
import os
from typing import List, Dict, Any
from graphs.state_schema import AgentState, ContractData
from config.ChromaManager import ChromaManager
from graphs.nodes.qwen_client import get_embedding, qwen_chat_completion
from utils.decorators import track_tokens

def get_collection():
    """الوصول للـ Collection الثابتة عبر الـ Singleton"""
    return ChromaManager().get_collection()

@track_tokens("detect_missing_clauses_node")
def detect_missing_clauses_node(state: AgentState) -> AgentState:
    """
    نود تدقيق الامتثال النهائي باستخدام الـ RAG:
    تقوم بمسح العقد للتأكد من وجود البنود العامة والتخصصية بناءً على سكيما الـ JSON فقط.
    إذا وجد بنداً مفقوداً في الاستخراج الأولي، يقوم بعمل استعلام ذكي في ChromaDB للتأكد من غيابه فعلياً.
    """
    print("\n--- [NODE] STARTING RAG-BASED COMPLIANCE AUDIT ---", flush=True)
    
    if not state.contract_id:
        print("⚠️ Contract ID missing. Cannot perform Compliance Audit RAG.")
        return state

    # 1. تحميل الـ Checklist من ملف الـ JSON المعتمد في نفس المسار الرئيسي للبرنامج
    schema_filename = "phaseOneSchem-en.json"
    try:
        with open(schema_filename, 'r', encoding='utf-8') as f:
            schema_data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading schema '{schema_filename}': {e}")
        return state

    compliance_config = schema_data.get("config", {}).get("compliance_checklists", {})
    
    # 2. جلب معلومات العقد الحالي من الـ State
    contract_type = (state.contract_type or "sow").lower()
    contract_id = state.contract_id
    
    # تأمين جلب البيانات المستخرجة وتحويلها لقاموس للتعامل المرن معها
    extracted_data_obj = state.extracted_data
    base_data_dict = extracted_data_obj.__dict__.copy() if hasattr(extracted_data_obj, "__dict__") else dict(extracted_data_obj)
    
    # تحويل التنسيقات والكلمات الافتراضية لسهولة التحقق برمجياً من القيم الفارغة
    exclude_list = ["null", "none", "not specified", "n/a", "", "false", "غير محدد", "غير محددة"]
    
    # 3. بناء قائمة البنود المطلوبة ديناميكياً من السكيما المقروءة
    global_required = compliance_config.get("global_required_clauses", [])
    type_specific_dict = compliance_config.get("type_specific_clauses", {}).get(contract_type, {})
    custom_checklist = getattr(state, "temp_custom_checklist", {}) or {}
    if isinstance(custom_checklist, dict):
        type_specific_dict = {**type_specific_dict, **custom_checklist}
    
    # خريطة لربط مسميات البنود العامة بمفاتيح الـ JSON المستخرج لضمان توافق الأسماء
    global_mapping = {
        "Parties": "parties",
        "Contractual / Financial Value": "value",
        "Contract Duration / Validity": "duration",
        "Payment Terms and Conditions": "payment_terms",
        "Termination of Agreement": "termination",
        "Liability and Indemnification": "liability",
        "Confidentiality and Privacy": "confidentiality",
        "Governing / Regulating Law": "governing_law",
        "Dispute Resolution and Settlement": "dispute_resolution",
        "Contract Renewal": "renewal"
    }

    collection = get_collection()
    missing_clauses = []

    # --- أولاً: فحص البنود العامة (Global Clauses) ---
    for clause in global_required:
        state_key = global_mapping.get(clause)
        if not state_key:
            continue
            
        val = base_data_dict.get(state_key)
        val_str = str(val).lower().strip() if val else ""
        
        # إذا كان البند فارغاً أو غير محدد، نقوم بتدقيق الـ RAG للتأكد من غيابه فعلياً
        if not val or any(x == val_str for x in exclude_list):
            print(f"🔍 [RAG Audit] Verification triggered for Global Clause: '{clause}'", flush=True)
            
            try:
                # 1. عمل Embedding لوصف البند للبحث الدلالي
                query_embedding = get_embedding(f"Extract text about: {clause}")
                
                # 2. الاستعلام من ChromaDB
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=2,
                    where={"contract_id": contract_id}
                )
            except Exception as e:
                print(f"⚠️ Global clause retrieval failed for {clause}: {e}", flush=True)
                missing_clauses.append(clause)
                continue
            
            documents = results.get("documents", [[]])[0] if results else []
            
            if documents:
                context = "\n\n".join(documents)
                # 3. إرسال القطع المسترجعة لـ Qwen للتحقق النهائي والذكي
                prompt = [
                    {"role": "system", "content": "You are a legal auditor. Your task is to verify if the provided text context contains information about the requested clause. If yes, extract it precisely in the language of the context. If no, reply ONLY with 'Not Specified'."},
                    {"role": "user", "content": f"Clause to search for: {clause}\n\nContext:\n{context}\n\nStrict Output:"}
                ]
                
                try:
                    verification_result = qwen_chat_completion(prompt, temperature=0.1)
                except Exception as e:
                    print(f"⚠️ Qwen completion failed during global clause verification: {e}", flush=True)
                    verification_result = "Not Specified"
                
                if verification_result and verification_result.strip().lower() != "not specified":
                    # تعافي ذاتي: تم العثور على البند وتحديثه في البيانات المستخرجة
                    print(f"✨ [Self-Healing] Successfully recovered Global Clause '{clause}' via RAG!", flush=True)
                    base_data_dict[state_key] = verification_result.strip()
                else:
                    # البند مفقود فعلياً من نص العقد
                    print(f"❌ [Confirmed Missing] Global Clause '{clause}' is absent.", flush=True)
                    missing_clauses.append(clause)
            else:
                missing_clauses.append(clause)
        else:
            print(f"✅ [Verified] Global Clause '{clause}' is already present.", flush=True)

    # --- ثانياً: فحص البنود التخصصية (Type Specific Clauses) ---
    specific_extracted = base_data_dict.get("specific_clauses", {})
    if not isinstance(specific_extracted, dict):
        specific_extracted = {}

    for spec_key, spec_desc in type_specific_dict.items():
        val = specific_extracted.get(spec_key)
        val_str = str(val).lower().strip() if val else ""
        
        if not val or any(x == val_str for x in exclude_list):
            print(f"🔍 [RAG Audit] Verification triggered for Specific Clause: '{spec_key}'", flush=True)
            
            try:
                # 1. البحث الدلالي في كروما
                query_embedding = get_embedding(f"Find clause details for: {spec_key}. Description: {spec_desc}")
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=2,
                    where={"contract_id": contract_id}
                )
            except Exception as e:
                print(f"⚠️ Specific clause retrieval failed for {spec_key}: {e}", flush=True)
                missing_clauses.append(spec_key)
                continue
            
            documents = results.get("documents", [[]])[0] if results else []
            
            if documents:
                context = "\n\n".join(documents)
                # 2. التحقق الذكي عبر Qwen
                prompt = [
                    {"role": "system", "content": f"You are an expert contract parser. Identify and extract information regarding '{spec_key}' (defined as: {spec_desc}). If found, extract the sentence or paragraph. If completely missing, reply with 'Not Specified'."},
                    {"role": "user", "content": f"Context:\n{context}\n\nExtraction:"}
                ]
                
                try:
                    verification_result = qwen_chat_completion(prompt, temperature=0.1)
                except Exception as e:
                    print(f"⚠️ Qwen completion failed during specific clause verification: {e}", flush=True)
                    verification_result = "Not Specified"
                
                if verification_result and verification_result.strip().lower() != "not specified":
                    print(f"✨ [Self-Healing] Successfully recovered Specific Clause '{spec_key}'!", flush=True)
                    specific_extracted[spec_key] = verification_result.strip()
                else:
                    print(f"❌ [Confirmed Missing] Specific Clause '{spec_key}' is absent.", flush=True)
                    missing_clauses.append(spec_key)
            else:
                missing_clauses.append(spec_key)
        else:
            print(f"✅ [Verified] Specific Clause '{spec_key}' is already present.", flush=True)

    # 4. تحديث الـ State بأمان
    base_data_dict["specific_clauses"] = specific_extracted
    
    state.update({
        "extracted_data": ContractData(**base_data_dict),
        "missing_clauses": missing_clauses,
        "is_compliance_checked": True,
        "history": state.history + ["RAG Compliance & Missing Clause Detection completed"]
    })
    
    print(f"🏁 Finished Compliance Audit. Confirmed Missing Clauses: {missing_clauses}\n", flush=True)
    return state
