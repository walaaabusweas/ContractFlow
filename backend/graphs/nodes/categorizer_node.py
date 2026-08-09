import json
from typing import Any
from utils.decorators import track_tokens

@track_tokens("categorize_contract_node")
async def categorize_contract_node(state: Any): 
    """
    Node: Categorizer
    Function: Uses user-selected type. No LLM calls involved.
    """
    print("--- [NODE] CATEGORIZER (NO LLM) ---")

    # 1. القيمة المختارة من المستخدم (تأتي من الـ API)
    selected_type = getattr(state, "contract_type", "other")
    
    # 2. تحديث الـ state مباشرة بناءً على اختيار المستخدم
    # إذا اختار 'other' ستبقى القيمة 'other' أو 'unknown' حسب ما تفضلين
    print(f"✅ Contract type set to: {selected_type}")
    
    state.update({
        "contract_type": selected_type,
        "is_extraction_successful": True if selected_type != "other" else False
    })
    
    return state