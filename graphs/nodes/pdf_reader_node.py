import os
import re

from pypdf import PdfReader

from graphs.state_schema import AgentState, ContractData
from utils.decorators import track_tokens

@track_tokens("pdf_reader_node")
def pdf_reader_node(state: AgentState)-> AgentState:
    """
    Zero Node: Converting a PDF file to Raw Text.
    """
    print("--- STEP 0: READING PDF FILE ---")
    
    state.extracted_data = ContractData()
    state.missing_clauses = []
    state.risks = []
    state.final_report = {"file_path": state.final_report.get("file_path", "contract_sample.pdf")}
    state.english_contract_text = ""
    state.error = None
    state.is_extraction_successful = False
    
    # نفترض أن مسار الملف مخزن في الـ metadata أو مرسل في البداية
    # أو يمكننا تمريره عبر الـ state إذا كان لديكِ مسار محدد
    file_path = state.final_report.get("file_path", "contract_sample.pdf")
    
    if not os.path.exists(file_path):
        state.update({"error": f"File not found: {file_path}"})
        return state

    try:
        page_texts = []
        reader = PdfReader(file_path)
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                page_texts.append(page_text)
        
        text = "\n\n".join(page_texts)

        # Keep paragraph/section boundaries for retrieval, but normalize noisy spacing.
        clean_text = re.sub(r"[ \t]+", " ", text)
        clean_text = re.sub(r"\n{3,}", "\n\n", clean_text).strip()
        
        # تحديث الـ State بالنص المستخرج
        state.update({
            "contract_text": clean_text,
            "is_extraction_successful": True
        })
        print(f"✅ PDF converted to text. Length: {len(clean_text)} characters.")
        
    except Exception as e:
        print(f"❌ Error reading PDF: {e}")
        state.update({"error": str(e)})

    return state
