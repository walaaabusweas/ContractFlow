import json
import traceback
from graphs.state_schema import AgentState
from graphs.nodes.qwen_client import qwen_chat_completion, get_embedding
from config.ChromaManager import ChromaManager
from utils.decorators import track_tokens

def get_collection():
    """الوصول لقاعدة البيانات الثابتة"""
    return ChromaManager().get_collection()


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

    # 1. تجميع البيانات المستخرجة في قاموس نظيف لتقديمه كسياق للموديل
    compiled_extracted_data = {}
    for k, v in base_data_dict.items():
        if k != "specific_clauses" and v:
            compiled_extracted_data[k] = v
    for k, v in specific_clauses_dict.items():
        if v:
            compiled_extracted_data[k] = v

    # 2. خطوة RAG المعرفة القانونية السابقة (Few-Shot Legal Knowledge Retrieval):
    # نبحث في قاعدة البيانات عن مراجعات أو توجيهات سابقة تخص هذا النوع من العقود لتوجيه ذكاء الموديل
    historical_legal_knowledge = "No historical legal knowledge found."
    try:
        collection = get_collection()
        # الاستعلام باستخدام نوع العقد الحالي لجلب تعليقات قانونية وصيغ مراجعة نموذجية تم اعتمادها سابقاً
        search_query = f"Reviewed {state.contract_type} contract legal comments, risk mitigations, approval or rejection notes"
        results = collection.query(
            query_embeddings=[get_embedding(search_query)],
            where={"contract_id": state.contract_id} if state.contract_id else None,
            n_results=1 # نجلب أهم نموذج مرجعي لضمان عدم تجاوز حجم الـ context
        )
        if results.get('documents') and results['documents'][0]:
            historical_legal_knowledge = "\n".join(results['documents'][0])
            print("✨ [RAG] Historical legal review guidelines retrieved successfully.", flush=True)
    except Exception as e:
        print(f"⚠️ Historical RAG knowledge retrieval skipped: {e}", flush=True)

    # تجهيز السياق التحليلي النظيف والموثوق للموديل
    analysis_context = {
        "contract_type": state.contract_type.upper(),
        "all_extracted_text_data": compiled_extracted_data,
        "missing_clauses": state.missing_clauses,
        "risks": state.risks,
        "historical_legal_benchmarks": historical_legal_knowledge # دمج المراجعات السابقة
    }

    # 3. صياغة التوجيهات اللغوية الصارمة بناءً على اللغة لفرض دقة الصياغة ومنع الركاكة
    if lang_str == "ar":
        system_message = (
            "أنت مستشار قانوني محترف وخبير في صياغة مراجعات العقود والامتثال الفني للشركات.\n"
            "مهمتك هي تحليل السياق الممرر لك وتوليد تقرير مراجعة ختامي فخم بصيغة JSON صارمة.\n"
            "استفد من الملاحظات التاريخية (historical_legal_benchmarks) لمحاكاة أسلوب الصياغة القانونية الرصين المعتمد لدى الشركة.\n\n"
            "يجب الالتزام بالمفاتيح الإنجليزية القياسية التالية في كائن الـ JSON (لصالح الـ UI):\n"
            "- initial_review_notes: ملخص استشاري رفيع المستوى (فقرة واحدة متماسكة من 3-4 أسطر باللغة العربية الفصحى) يقيم مدى توازن وجاهزية العقد للتوقيع أو يسلط الضوء على الثغرات الاستراتيجية فيه.\n"
            "- notes_for_legal_review: مصفوفة تحتوي على نقاط واضحة ومحددة (Bullet-points باللغة العربية) للإجراءات القانونية البديلة أو بنود التعديل الصارمة التي يجب على المحامي فرضها فوراً لحماية الشركة.\n"
            "- extracted_important_clauses: مصفوفة نصوص (List of Strings)؛ قم بجمع أهم البنود المستوفاة في العقد ولخص كلاً منها بعبارة فصيحة (مثال: 'سرية المعلومات: يلتزم الطرف المستقبل بحفظ السرية لمدة 5 سنوات من انتهاء العقد').\n\n"
            "قوانين معالجة صارمة (Anti-Hallucination Constraints):\n"
            "1. التزم التزاماً مطلقاً بنوع العملة والأرقام المذكورة في السياق دون تزييف أو استبدال.\n"
            "2. لا تبتكر أو تخترع مخاطر وهمية، واعتمد التقرير على البيانات المستخرجة والنواقص المثبتة.\n"
            "3. أرجع كائن الـ JSON المباشر فقط دون أي مقدمات أو علامات ماركداون."
        )
    else:
        system_message = (
            "You are an expert legal consultant specializing in corporate contract compliance and executive reporting.\n"
            "Your task is to analyze the provided contract details along with historical legal benchmarks (historical_legal_benchmarks) to generate an executive review report in strict JSON format.\n\n"
            "REQUIRED JSON KEYS:\n"
            "- initial_review_notes: A sharp executive summary paragraph (in English) assessing the contract's overall legal and business safety based on extracted terms.\n"
            "- notes_for_legal_review: A bullet-pointed list of actionable, precise legal countermeasures and drafting corrections a corporate lawyer must apply.\n"
            "- extracted_important_clauses: A compiled list of present clauses summarized concisely (formatted as 'Clause Name: Brief summary of the text').\n\n"
            "STRICT CONSTRAINTS:\n"
            "1. Strictly conform to the exact numbers, currencies, and entities identified in the context.\n"
            "2. Match the style and quality found in historical legal benchmarks if applicable.\n"
            "3. Return ONLY a valid JSON object. No conversational text, no markdown."
        )

    # 4. استدعاء الموديل بـ Temperature صفر لضمان الالتزام القطعي بالبيانات والمقارنة
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
        
        initial_notes = parsed_report.get("initial_review_notes", "")
        legal_notes = parsed_report.get("notes_for_legal_review", [])
        extracted_important = parsed_report.get("extracted_important_clauses", [])
        
    except Exception as e:
        print(f"❌ Failed to parse AI structured report notes: {e}")
        initial_notes = "التقرير الاستشاري الآلي غير متوفر حالياً بسبب عطل في المعالجة." if lang_str == "ar" else "AI analysis is temporarily unavailable."
        legal_notes = ["يرجى مراجعة لوحة تحكم المخاطر يدوياً."] if lang_str == "ar" else ["Please review risks manually."]
        extracted_important = []

    # 5. بناء هيكل المخرج النهائي المستقر والثابت للـ UI بمفاتيح إنجليزية دائماً وعمياء عن لغة العقد
    fallback_not_specified = "غير حدد" if lang_str == "ar" else "Not specified"
    
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
            {
                "id": r.get("id"),
                "level": r.get("level"),
                "title": r.get("title"),
                "description": r.get("description")
            } for r in state.risks
        ],
        "initial_review_notes": initial_notes,
        "notes_for_legal_review": legal_notes
    }

    # 6. تحديث الـ State بالتقرير النظيف والنهائي
    state.update({
        "final_report": final_output,
        "is_compliance_checked": True,
        "history": state.history + ["Compliance & Legal Review Report generated successfully"]
    })

    print("✅ Successfully generated unified AI-driven Report with Historical Legal Knowledge integration.")
    return state