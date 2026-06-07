import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from graphs.nodes.qwen_client import qwen_chat_completion
from utils.decorators import track_tokens

load_dotenv()
load_dotenv(Path(__file__).resolve().parents[2] / "config" / ".env")

@track_tokens("categorize_contract_node")
async def categorize_contract_node(state: Any): 
    """
    Node: Categorizer
    Function: Determine the type of contract (NDA, SOW, Supply) based on the text.
    """
    print("--- [NODE] CATEGORIZING CONTRACT ---")

    # 1. تعريف أنواع العقود
    supported_types = [
        {"id": "sow", "label": "Statement of Work / Service Agreement"},
        {"id": "nda", "label": "Non-Disclosure Agreement"},
        {"id": "supply", "label": "Supply Agreement"}
    ]
    print("Supported contract types:")
    for t in supported_types:
        print(f" - {t['id']}: {t['label']}")

    # 2. استخراج أول جزء من النص وتأمين المتغير (حل مشكلة الترتيب والـ Bug)
    contract_text = state.contract_text
    sample_text = contract_text[:3000] if contract_text else ""
    
    if not sample_text:
        print("⚠️ No contract text found in state.")
        state.update({"contract_type": "unknown", "error": "No text to categorize"})
        return state

    # 3. بناء الـ System Message (الدستور والثوابت)
    system_message = (
        "You are an expert legal document classifier.\n"
        "Your core task is to read the title and preamble of a contract and classify it strictly based on its current legal nature.\n\n"
        "Allowed Categories:\n"
        "- 'nda': For Non-Disclosure / Confidentiality Agreements.\n"
        "- 'sow': For Statements of Work / Technical Addendums / Execution Appendices.\n"
        "- 'supply': For Supply, Procurement, or Logistics Contracts.\n"
        "- 'unknown': For Commercial Services, Licensing, or any agreement that does NOT fit the above.\n\n"
        "CRITICAL RULES:\n"
        "1. ABSOLUTELY FORBIDDEN to reuse past classifications based on company names (like Matrix or NexaWare). Every document is independent.\n"
        "2. If the document is a 'Commercial Services and Licensing Agreement', it is NOT an SOW. You MUST return 'unknown'."
    )

    # 4. بناء الـ User Prompt (هنا المتغير sample_text جاهز ومعرف)
    user_prompt = (
        "Analyze the following contract text sample carefully.\n"
        "Focus heavily on the FIRST 2-3 paragraphs and the MAIN TITLE.\n\n"
        f"Contract Text Sample:\n\n{sample_text}\n\n"
        "STRICT OUTPUT INSTRUCTIONS:\n"
        "1. NO MARKDOWN BLOCKS: Do NOT wrap the JSON output in ```json or ``` code blocks. Output the raw JSON string directly.\n"
        "2. COMPLETE RESPONSE: Provide a single complete sentence in the reasoning field. Do not truncate mid-sentence.\n"
        "3. Exact Structure: Return ONLY a valid JSON with this exact schema:\n"
        "{\n"
        "  \"reasoning\": \"[A concise explanation of why this title fits or doesn't fit standard categories]\",\n"
        "  \"category\": \"[The exact lowercase category ID]\"\n"
        "}"
    )

    # 5. تنفيذ الطلب 
    try:
        response = qwen_chat_completion(
            [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
        
        # تنظيف النص المستلم احتياطاً من أي مسافات زائدة
        clean_response = response.strip()
        print(f"Raw Model Response:\n{clean_response}")
        
        # عمل Parse للـ JSON المستخرج للوصول للـ category الصافية
        try:
            parsed_json = json.loads(clean_response)
            category_id = parsed_json.get("category", "unknown").strip().lower()
            reasoning = parsed_json.get("reasoning", "")
            print(f"Reasoning: {reasoning}")
        except Exception as json_err:
            print(f"⚠️ Failed to parse JSON response directly, falling back to string check. Error: {str(json_err)}")
            # Fallback في حال كتب الموديل نصاً خارج الـ JSON رغم القيود
            if "nda" in clean_response: category_id = "nda"
            elif "sow" in clean_response: category_id = "sow"
            elif "supply" in clean_response: category_id = "supply"
            else: category_id = "unknown"

        print(f"Final Extracted Category ID: {category_id}")
        
        # 6. التحديث الديناميكي للـ State
        state.update({
            "contract_type": category_id,
            "is_extraction_successful": True if category_id != "unknown" else False
        })
        
        print(f"✅ Success: Contract identified as [{category_id.upper()}]")

    except Exception as e:
        print(f"❌ Error in Categorizer Node: {str(e)}")
        state.update({"error": f"Categorization failed: {str(e)}", "contract_type": "unknown"})

    return state
