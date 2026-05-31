import gradio as gr
import requests
from pathlib import Path

# تنسيق CSS المخصص
custom_css = """
.gradio-container { background-color: #0f172a !important; color: #f1f5f9 !important; }
.tab-nav { border-bottom: 1px solid #334155 !important; }
.tab-item { background-color: #1e293b !important; color: #cbd5e1 !important; }
h1 { color: #818cf8 !important; }
"""

FIELD_LABELS = [
    ("parties", "الأطراف"),
    ("value", "القيمة المالية"),
    ("duration", "مدة العقد"),
    ("payment_terms", "شروط الدفع"),
    ("termination", "إنهاء العقد"),
    ("liability", "المسؤولية"),
    ("confidentiality", "السرية"),
    ("governing_law", "القانون الواجب التطبيق"),
    ("dispute_resolution", "تسوية النزاعات"),
]


def _value_for(key, data, key_terms):
    value = key_terms.get(key)
    if value in (None, "", [], {}):
        value = data.get(key)
    return value if value not in (None, "", [], {}) else "غير محدد"


def _render_value(value):
    if isinstance(value, list):
        return "\n".join([f"- {item}" for item in value]) if value else "غير محدد"
    if isinstance(value, dict):
        return "\n".join([f"- **{key}:** {val}" for key, val in value.items()]) if value else "غير محدد"
    return str(value)


def _render_list(items, empty_text):
    if not items:
        return empty_text

    rendered = []
    for item in items:
        if isinstance(item, dict):
            title = item.get("title") or item.get("id") or item.get("level") or "بند"
            description = item.get("description") or item.get("message") or ""
            rendered.append(f"- **{title}:** {description}".rstrip())
        else:
            rendered.append(f"- {item}")
    return "\n".join(rendered)


def _build_error_sections(message):
    text = f"### ❌ خطأ في النظام\n{message}"
    return {}, text, text, text, text, text, text


def format_result_sections(api_response):
    """تقسيم نتيجة التحليل إلى تبويبات واضحة للواجهة."""
    if not api_response:
        return _build_error_sections("لم يتم استلام أي بيانات من الخادم.")

    if api_response.get("error"):
        return _build_error_sections(api_response["error"])

    data = api_response.get("extracted_data") or {}
    final_report = api_response.get("final_report") or {}
    key_terms = final_report.get("key_contract_terms") or {}
    missing = final_report.get("missing_clauses") or api_response.get("missing_clauses") or []
    important_clauses = final_report.get("extracted_important_clauses") or []
    risks = final_report.get("risk_highlights") or api_response.get("risks") or []
    legal_notes = final_report.get("notes_for_legal_review") or []
    specific_clauses = data.get("specific_clauses") or {}
    contract_type = final_report.get("contract_type") or api_response.get("contract_type", "غير محدد")

    overview = f"""
### ملخص العقد
---
**نوع العقد:** {contract_type}

**الأطراف:**
{_render_value(_value_for("parties", data, key_terms))}

**القيمة المالية:** {_render_value(_value_for("value", data, key_terms))}

**مدة العقد:** {_render_value(_value_for("duration", data, key_terms))}

**حالة الفحص:** {"تم الفحص" if api_response.get("is_compliance_checked") else "لم يكتمل الفحص"}
"""

    extracted_terms = "\n\n".join(
        f"### {label}\n{_render_value(_value_for(key, data, key_terms))}"
        for key, label in FIELD_LABELS
    )
    extracted = f"""
### البيانات المستخرجة
---
{extracted_terms}
"""

    clauses = f"""
### البنود المهمة
---
{_render_list(important_clauses, "لا توجد بنود مهمة إضافية مستخرجة.")}

### البنود التخصصية
{_render_value(specific_clauses) if specific_clauses else "لا توجد بنود تخصصية مستخرجة."}
"""

    missing_text = f"""
### البنود المفقودة
---
{_render_list([f"⚠️ {item}" for item in missing], "✅ جميع البنود المطلوبة مستوفاة.")}
"""

    risks_text = f"""
### المخاطر
---
{_render_list(risks, "✅ لم يتم رصد مخاطر عالية.")}
"""

    legal_review = f"""
### ملاحظات المراجعة القانونية
---
{final_report.get("initial_review_notes", "لا توجد ملاحظات عامة.")}

### توصيات للمراجعة
{_render_list(legal_notes, "لا توجد توصيات إضافية.")}
"""

    return api_response, overview, extracted, clauses, missing_text, risks_text, legal_review

def analyze_contract_ui(file_obj, custom_clauses_file=None):
    """دالة الاتصال بالـ API"""
    if file_obj is None:
        return _build_error_sections("يرجى رفع ملف PDF للبدء.")
    if custom_clauses_file is not None:
        custom_suffix = Path(custom_clauses_file.name).suffix.lower()
        if custom_suffix not in {".txt", ".json"}:
            return _build_error_sections("ملف البنود المخصصة يجب أن يكون TXT أو JSON.")
        
    try:
        with open(file_obj.name, 'rb') as f:
            files = {'file': (file_obj.name, f, 'application/pdf')}
            custom_handle = None
            if custom_clauses_file is not None:
                custom_handle = open(custom_clauses_file.name, "rb")
                files["custom_clauses_file"] = (
                    custom_clauses_file.name,
                    custom_handle,
                    "text/plain",
                )
            # الرابط الصحيح داخل دوكر هو المنفذ الداخلي 8000
            try:
                response = requests.post("http://app:8000/upload-contract", files=files)
            finally:
                if custom_handle is not None:
                    custom_handle.close()
        
        if response.status_code == 200:
            json_data = response.json()
            return format_result_sections(json_data)
        else:
            try:
                error_detail = response.json().get("detail")
            except Exception:
                error_detail = None
            message = error_detail or f"فشل الاتصال بالـ API (كود: {response.status_code})"
            return _build_error_sections(message)
    except Exception as e:
        return _build_error_sections(f"حدث خطأ داخلي: {str(e)}")

# بناء الواجهة
with gr.Blocks(title="ContractFlow AI", css=custom_css, theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 📜 ContractFlow AI - لوحة مراجعة العقود")
    
    with gr.Row():
        with gr.Column(scale=1):
            input_file = gr.File(label="ارفع ملف العقد (PDF)", file_types=[".pdf"])
            custom_clauses_file = gr.File(
                label="بنود مخصصة إضافية (TXT/JSON اختياري)",
                file_types=[".txt", ".json"],
            )
            submit_btn = gr.Button("بدء التحليل", variant="primary")
            
        with gr.Column(scale=3):
            with gr.Tabs():
                with gr.TabItem("الملخص"):
                    output_overview = gr.Markdown("انتظر النتيجة...")
                with gr.TabItem("البيانات المستخرجة"):
                    output_extracted = gr.Markdown("انتظر النتيجة...")
                with gr.TabItem("البنود المهمة"):
                    output_clauses = gr.Markdown("انتظر النتيجة...")
                with gr.TabItem("البنود المفقودة"):
                    output_missing = gr.Markdown("انتظر النتيجة...")
                with gr.TabItem("المخاطر"):
                    output_risks = gr.Markdown("انتظر النتيجة...")
                with gr.TabItem("المراجعة القانونية"):
                    output_legal = gr.Markdown("انتظر النتيجة...")
                with gr.TabItem("البيانات التقنية (JSON)"):
                    output_json = gr.JSON(label="الهيكل البرمجي")

    submit_btn.click(
        fn=analyze_contract_ui, 
        inputs=[input_file, custom_clauses_file], 
        outputs=[
            output_json,
            output_overview,
            output_extracted,
            output_clauses,
            output_missing,
            output_risks,
            output_legal,
        ]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, debug=True)
