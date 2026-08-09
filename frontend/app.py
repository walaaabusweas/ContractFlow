import gradio as gr
import requests
import pandas as pd
import json

# --- CSS والتنسيقات المحدثة بالكامل ---
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght=400;600;700;800&family=Inter:wght=400;600;700&display=swap');

/* الخلفية العامة للمنصة بلمسة كحلية ملكية عميقة ومريحة جداً */
.gradio-container { 
    background-color: #090d16 !important; 
    color: #f1f5f9 !important; 
    font-family: 'Cairo', 'Inter', sans-serif !important; 
    position: relative !important;
}

/* تدرج لوني يعكس الاحترافية والدقة (الزمردي المضيء مع الأزرق السماوي) */
.main-title {
    background: linear-gradient(135deg, #34d399 0%, #06b6d4 50%, #3b82f6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800 !important;
    letter-spacing: -1px;
    margin-bottom: 5px !important;
}

/* حاوية اللغة العائمة - تضع زر التبديل في الزاوية العلوية اليمنى بأناقة ودون حجز مساحة رأسية */
.language-switch-container {
    position: absolute !important;
    top: 20px !important;
    right: 20px !important;
    z-index: 999 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    margin: 0 !important;
    padding: 0 !important;
    width: auto !important;
}

/* تصميم كبسولة تبديل اللغة الأنيقة والمدمجة */
.language-switch { 
    background: #111827 !important; 
    border: 1px solid #1f2937 !important; 
    border-radius: 20px !important; 
    padding: 3px 6px !important;
    display: inline-flex !important;
    align-items: center !important;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4) !important;
}

/* تحسين شكل الأزرار الداخلية لتبدو ككبسولة ناعمة وصغيرة */
.language-switch .gr-input-label {
    background: transparent !important;
    border: none !important;
    border-radius: 15px !important;
    padding: 4px 12px !important;
    margin: 0 2px !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    color: #94a3b8 !important;
    font-size: 0.85em !important;
    font-weight: 700 !important;
}

/* تأثير الخيار المحدد النشط */
.language-switch .gr-input-label.selected, 
.language-switch input[type="radio"]:checked + span {
    background: linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 2px 8px rgba(6, 182, 212, 0.3) !important;
    border-radius: 15px !important;
}

/* إلغاء وإخفاء الدوائر الداخلية والمؤشرات الخاصة بالـ Radio تماماً */
.language-switch input[type="radio"],
.language-switch .gr-check-radio,
.language-switch input[type="radio"] + span::before,
.language-switch input[type="radio"] + span::after,
.language-switch .gr-input-label::before,
.language-switch .gr-input-label::after {
    display: none !important; 
    opacity: 0 !important;
    width: 0 !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    visibility: hidden !important;
}

/* إلغاء أي حدود إضافية من Gradio على أداة الراديو */
.language-switch.gradio-container .gr-box {
    border: none !important;
    background: transparent !important;
}

/* تصميم كروت رفع الملفات والمدخلات */
.gradio-container .gr-box, .gradio-container .form {
    background: #111827 !important;
    border: 1px solid #1f2937 !important;
    border-radius: 14px !important;
    transition: all 0.3s ease;
}
.gradio-container .gr-box:hover {
    border-color: #06b6d4 !important;
    box-shadow: 0 0 15px rgba(6, 182, 212, 0.12);
}

/* تصميم كروت التلميح (Empty States) الهادئة بحدود متقطعة */
.empty-placeholder {
    text-align: center !important;
    padding: 40px 20px !important;
    border: 2px dashed #1f2937 !important;
    border-radius: 12px !important;
    color: #64748b !important;
    background: #0b0f19 !important;
    margin: 10px 0 !important;
}
.empty-placeholder-icon {
    font-size: 2.5em !important;
    margin-bottom: 12px !important;
    display: block !important;
    opacity: 0.6 !important;
}

/* ترقية زر التحليل الرئيسي بتدرج لوني فخم */
.gradio-container button.primary {
    background: linear-gradient(90deg, #4f46e5 0%, #06b6d4 100%) !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: 1.4em !important;
    padding: 12px 24px !important;
    box-shadow: 0 4px 15px rgba(6, 182, 212, 0.3) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.gradio-container button.primary:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(6, 182, 212, 0.45) !important;
    background: linear-gradient(90deg, #3b82f6 0%, #0891b2 100%) !important;
}

/* الاتجاهات وتنسيقات النصوص العامة */
.rtl { direction: rtl !important; text-align: right !important; }
.ltr { direction: ltr !important; text-align: left !important; }

.rtl .markdown-body, .rtl .markdown-body ul, .rtl .markdown-body li, .rtl .tab-item { direction: rtl !important; text-align: right !important; }
.ltr .markdown-body, .ltr .markdown-body ul, .ltr .markdown-body li, .ltr .tab-item { direction: ltr !important; text-align: left !important; }

/* كروت ملخص العقد والبيانات المستخرجة */
.summary-card { padding: 20px; background: #111827; border-radius: 12px; border: 1px solid #1f2937; margin-bottom: 20px; }
.summary-item { margin-bottom: 15px; }
.summary-label { color: #34d399; font-weight: 600; font-size: 0.9em; display: block; }
.summary-value { color: #f1f5f9; font-size: 1.1em; }

.extracted-card { 
    background: #111827; 
    border-radius: 10px; 
    border: 1px solid #1f2937; 
    padding: 16px; 
    margin-bottom: 12px; 
}
.extracted-field { 
    color: #38bdf8; 
    font-weight: 700; 
    font-size: 0.95em; 
    text-transform: uppercase; 
    margin-bottom: 6px; 
    display: block;
}
.extracted-val { 
    color: #e2e8f0; 
    font-size: 1.02em; 
    line-height: 1.6;
}

/* كروت التنبيهات والمخاطر */
.risk-card { 
    background: #1e1b1b !important; 
    border-left: 5px solid #f87171; 
    padding: 15px; 
    margin-bottom: 12px; 
    border-radius: 8px; 
    color: #fca5a5; 
}
.risk-title { font-weight: bold; color: #f87171; display: block; margin-bottom: 5px; }

/* تحسين شكل المراجعة القانونية داخل الـ Markdown Component */
.legal-markdown-container {
    background: #111827 !important;
    border: 1px solid #1f2937 !important;
    border-radius: 12px !important;
    padding: 24px !important;
}
.legal-markdown-container h3 {
    color: #34d399 !important;
    font-size: 1.6em !important;
    border-bottom: 1px solid #1f2937;
    padding-bottom: 12px;
    margin-bottom: 20px;
}
.legal-markdown-container h4 {
    color: #a5b4fc !important;
    font-size: 1.25em !important;
    margin-top: 25px !important;
    margin-bottom: 12px !important;
}
.legal-markdown-container p {
    color: #cbd5e1 !important;
    line-height: 1.8 !important;
    font-size: 1.1em !important;
}
.legal-markdown-container ul {
    margin-top: 10px !important;
    padding-right: 20px !important; /* لدعم المحاذاة العربية */
}
.legal-markdown-container li {
    color: #cbd5e1 !important;
    font-size: 1.1em !important;
    line-height: 1.8 !important;
    margin-bottom: 12px !important;
    list-style-type: disc !important;
}
"""

LABELS = {
    "ar": {
        "file_label": "ارفع ملف العقد (PDF)", "contract_type": "نوع العقد", "custom_file": "بنود مخصصة إضافية (TXT/JSON)", 
        "submit": "بدء التحليل", "risk_alert": "⚠️ تنبيه",
        "tabs": ["الملخص", "البيانات المستخرجة", "البنود المهمة", "البنود المخصصة", "البنود المفقودة", "المخاطر", "المراجعة القانونية"], 
        "empty": "غير محدد", "no_clauses": "لا توجد بنود.", "no_risks": "✅ لا توجد مخاطر.", "no_notes": "لا توجد ملاحظات.",
        "desc": "تحليل عقودك بذكاء، سرعة، ودقة قانونية متناهية.",
        "placeholder": "الرجاء رفع ملف العقد ثم الضغط على زر 'بدء التحليل' لعرض النتائج هنا."
    },
    "en": {
        "file_label": "Upload Contract (PDF)", "contract_type": "Contract Type", "custom_file": "Custom Clauses (TXT/JSON)", 
        "submit": "Start Analysis", "risk_alert": "⚠️ Risk Alert",
        "tabs": ["Summary", "Extracted Data", "Key Clauses", "Specific Clauses", "Missing Clauses", "Risks", "Legal Review"], 
        "empty": "Not specified", "no_clauses": "No clauses found.", "no_risks": "✅ No risks detected.", "no_notes": "No notes.",
        "desc": "Analyze your contracts intelligently, quickly, and with utmost legal accuracy.",
        "placeholder": "Please upload a contract file and click 'Start Analysis' to view the results here."
    }
}

# دالة لإنشاء كود الـ HTML للتلميح البصري (Empty State)
def get_placeholder_html(text):
    return f"""
    <div class="empty-placeholder">
        <span class="empty-placeholder-icon">📄</span>
        <p style="font-size: 1.1em; margin: 0; font-family: 'Cairo', sans-serif;">{text}</p>
    </div>
    """

# دالة لإنشاء تلميح بسيط للـ Markdown لتفادي الـ HTML المكسور في الـ Markdown component
def get_placeholder_markdown(text):
    return f"### 📄\n\n*{text}*"

# --- الدوال المعالجة والمحسنة للعرض التلقائي ---
def _render_value(value, lang):
    empty = LABELS[lang]["empty"]
    if value is None: return empty
    if isinstance(value, list): return "<br>".join([f"• {item}" for item in value]) if value else empty
    if isinstance(value, dict): return "<br>".join([f"• <strong>{key}:</strong> {val}" for key, val in value.items()]) if value else empty
    return str(value)

def format_extracted_data_html(data_dict, lang):
    if not data_dict: return get_placeholder_html(LABELS[lang]["placeholder"])
    filtered_data = {k: v for k, v in data_dict.items() if k != "specific_clauses"}
    direction, text_align = ("rtl", "right") if lang == "ar" else ("ltr", "left")
    html_content = f"<div style='direction: {direction}; text-align: {text_align};'>"
    for field, val in filtered_data.items():
        html_content += f"""
        <div class="extracted-card">
            <span class="extracted-field">{field.replace("_", " ").title()}</span>
            <div class="extracted-val">{_render_value(val, lang)}</div>
        </div>
        """
    html_content += "</div>"
    return html_content

def format_specific_clauses_html(specific_data, lang):
    if not specific_data: return f"<div class='summary-value'>{LABELS[lang]['no_clauses']}</div>"
    direction, text_align = ("rtl", "right") if lang == "ar" else ("ltr", "left")
    html_content = f"<div style='direction: {direction}; text-align: {text_align};'>"
    for clause_name, val in specific_data.items():
        html_content += f"""
        <div style="background: #1e293b; border-right: 4px solid #10b981; padding: 15px; margin-bottom: 15px; border-radius: 8px;">
            <strong style="color: #10b981; display: block; margin-bottom: 6px; font-size: 1.1em;">{clause_name.replace("_", " ").title()}</strong>
            <div style="color: #f1f5f9; line-height: 1.6;">{_render_value(val, lang)}</div>
        </div>
        """
    html_content += "</div>"
    return html_content

def format_risks_html(risks_list, lang):
    if not risks_list: return f"<div class='summary-value'>{LABELS[lang]['no_risks']}</div>"
    html_content = ""
    for risk in risks_list:
        text = risk.get('description', risk) if isinstance(risk, dict) else risk
        title = risk.get('title', LABELS[lang]['risk_alert']) if isinstance(risk, dict) else LABELS[lang]['risk_alert']
        html_content += f'<div class="risk-card"><span class="risk-title">{title}</span><span class="summary-value">{text}</span></div>'
    return html_content

def format_clauses_html(clauses_list, lang):
    if not clauses_list: return f"<div class='summary-value'>{LABELS[lang]['no_clauses']}</div>"
    html_content = ""
    for item in clauses_list:
        title = item.get('title', 'بند') if isinstance(item, dict) else "بند قانوني"
        summary = item.get('summary', str(item)) if isinstance(item, dict) else str(item)
        html_content += f"""
        <div style="background: #1e293b; border-right: 4px solid #818cf8; padding: 15px; margin-bottom: 15px; border-radius: 8px;">
            <strong style="color: #818cf8; display: block; margin-bottom: 5px;">{title}</strong>
            <span style="color: #f1f5f9;">{summary}</span>
        </div>
        """
    return html_content

def format_missing_clauses_html(missing_list, lang):
    if not missing_list: return f"<div style='color: #4ade80;'>✅ {LABELS[lang]['no_clauses']}</div>"
    direction, margin_style = ("rtl", "margin-left: 10px;") if lang == "ar" else ("ltr", "margin-right: 10px;")
    html_content = ""
    for item in missing_list:
        html_content += f"""
        <div style="background: #1e293b; border: 1px solid #f59e0b; padding: 12px; margin-bottom: 10px; border-radius: 8px; 
                    display: flex; align-items: center; direction: {direction}; text-align: {'right' if lang == 'ar' else 'left'};">
            <span style="font-size: 1.2em; {margin_style}">⚠️</span>
            <span style="color: #f59e0b; font-weight: 600;">{item.replace("⚠️", "").strip()}</span>
        </div>
        """
    return html_content

def format_result_sections(api_response, lang):
    l = LABELS[lang]
    data = api_response.get("extracted_data", {})
    final_report = api_response.get("final_report", {})
    key_terms = final_report.get("key_contract_terms", {})
    initial_notes = final_report.get("initial_review_notes", l["no_notes"])
    legal_notes_list = final_report.get("notes_for_legal_review", [])
    
    # 1. البحث الديناميكي عن مفتاح البنود المخصصة داخل القاموس
    specific_key = None
    for k in data.keys():
        # البحث عن أي مفتاح يحتوي على "specific" أو "مخصصة" أو "مخصص"
        if "specific" in k.lower() or "مخصصة" in k or "مخصص" in k:
            specific_key = k
            break
            
    # 2. استخلاص بيانات البنود المخصصة بناءً على المفتاح المكتشف
    specific_data = {}
    if specific_key:
        specific_data = data.get(specific_key, {})
        # إذا كانت القيمة الراجعة عبارة عن نصوص وليست قاموس فرعي، نحولها لقاموس لتسهيل العرض
        if not isinstance(specific_data, dict):
            specific_data = {specific_key: specific_data}
            
    # 3. معالجة البيانات المستخرجة العامة واستثناء مفتاح البنود المخصصة المكتشف ديناميكياً
    filtered_data = {k: v for k, v in data.items() if k != specific_key}
    
    # --- معالجة الملاحظات القانونية ---
    processed_notes = ""
    if initial_notes and initial_notes != l["no_notes"]:
        cleaned_notes = initial_notes.replace("▪", "").strip()
        if "." in cleaned_notes:
            sentences = [s.strip() for s in cleaned_notes.split(".") if s.strip()]
            processed_notes = "\n\n".join([f"* {sentence}." for sentence in sentences])
        else:
            processed_notes = f"* {cleaned_notes}"
    else:
        processed_notes = l["no_notes"]

    legal_content = f"### {l['tabs'][6]}\n\n{processed_notes}\n\n"
    if legal_notes_list:
        legal_content += "#### ملاحظات إضافية للمراجعة:\n\n" if lang == "ar" else "#### Additional Legal Notes:\n\n"
        legal_content += "\n\n".join([f"* {str(note).replace('▪', '').strip()}" for note in legal_notes_list])
    
    # 4. بناء الـ HTML للواجهات
    overview = f'<div class="summary-card"><div class="summary-item"><span class="summary-label">{l["contract_type"]}</span><span class="summary-value">{final_report.get("contract_type", l["empty"])}</span></div><div class="summary-item"><span class="summary-label">Parties</span><div class="summary-value">{_render_value(key_terms.get("parties", l["empty"]), lang)}</div></div></div>'
    
    # نمرر البيانات المفلترة ديناميكياً للدالة
    extracted_html = format_extracted_data_html_dynamic(filtered_data, lang)
    clauses = format_clauses_html(final_report.get("extracted_important_clauses", []), lang)
    specific_html = format_specific_clauses_html(specific_data, lang)
    missing = format_missing_clauses_html(final_report.get("missing_clauses", []), lang)
    risks = format_risks_html(final_report.get("risk_highlights", []), lang)
    
    return overview, extracted_html, clauses, specific_html, missing, risks, legal_content

def analyze_contract_ui(file_obj, custom_clauses_file, contract_type, lang):
    try:
        with open(file_obj.name, 'rb') as f:
            files = {'file': (file_obj.name, f, 'application/pdf')}
            data = {'contract_type': contract_type}
            if custom_clauses_file: files["custom_clauses_file"] = (custom_clauses_file.name, open(custom_clauses_file.name, "rb"), "text/plain")
            response = requests.post("http://app:8000/upload-contract", files=files, data=data)
        if response.status_code == 200: return format_result_sections(response.json(), lang)
        return ["Error", "", "", "", "", "", ""]
    except Exception as e: return [str(e), "", "", "", "", "", ""]
def format_extracted_data_html_dynamic(filtered_data, lang):
    if not filtered_data: return get_placeholder_html(LABELS[lang]["placeholder"])
    direction, text_align = ("rtl", "right") if lang == "ar" else ("ltr", "left")
    html_content = f"<div style='direction: {direction}; text-align: {text_align};'>"
    for field, val in filtered_data.items():
        html_content += f"""
        <div class="extracted-card">
            <span class="extracted-field">{field.replace("_", " ").title()}</span>
            <div class="extracted-val">{_render_value(val, lang)}</div>
        </div>
        """
    html_content += "</div>"
    return html_content
# --- البداية وتجهيز الواجهة الافتراضية ---
ar_placeholder = get_placeholder_html(LABELS["ar"]["placeholder"])
en_placeholder = get_placeholder_html(LABELS["en"]["placeholder"])
ar_md_placeholder = get_placeholder_markdown(LABELS["ar"]["placeholder"])
en_md_placeholder = get_placeholder_markdown(LABELS["en"]["placeholder"])

with gr.Blocks(title="ContractFlow AI", css=custom_css, theme=gr.themes.Soft()) as demo:
    
    # 1. زر تبديل اللغة العائم
    with gr.Row(variant="compact", elem_classes="language-switch-container"):
        lang_selector = gr.Radio(choices=["ar", "en"], value="ar", show_label=False, elem_classes="language-switch")
    
    # 2. الهيدر الرئيسي والوصف
    with gr.Column():
        description_text = gr.Markdown(
            f"""
            <div style="text-align: center; padding-top: 30px; margin-bottom: 20px;">
                <h1 class="main-title" style="font-size: 3.2em; margin: 0; font-weight: 800; letter-spacing: -1.5px;">ContractFlow AI</h1>
                <p style="color: #94a3b8; font-size: 1.25em; margin-top: 8px;">{LABELS['ar']['desc']}</p>
            </div>
            """
        )

    # 3. صندوق رفع الملفات والمدخلات
    with gr.Column(elem_classes="rtl") as main_container:
        with gr.Row():
            input_file = gr.File(label=LABELS["ar"]["file_label"], scale=0.5, height=200)
            custom_clauses_file = gr.File(label=LABELS["ar"]["custom_file"], scale=0.5, height=200)
            contract_type_input = gr.Dropdown(choices=["supply", "sow", "nda", "other"], label=LABELS["ar"]["contract_type"], value="other", scale=1)

        submit_btn = gr.Button(LABELS["ar"]["submit"], variant="primary")
        
        # تفعيل المظهر الافتراضي الجميل لكل تابة وهي فارغة
        with gr.Tabs() as tab_group:
            with gr.TabItem(LABELS["ar"]["tabs"][0]) as tab1: overview_output = gr.HTML(value=ar_placeholder)
            with gr.TabItem(LABELS["ar"]["tabs"][1]) as tab2: extracted_output = gr.HTML(value=ar_placeholder)
            with gr.TabItem(LABELS["ar"]["tabs"][2]) as tab3: clauses_output = gr.HTML(value=ar_placeholder)
            with gr.TabItem(LABELS["ar"]["tabs"][3]) as tab4: specific_output = gr.HTML(value=ar_placeholder)
            with gr.TabItem(LABELS["ar"]["tabs"][4]) as tab5: missing_output = gr.HTML(value=ar_placeholder)
            with gr.TabItem(LABELS["ar"]["tabs"][5]) as tab6: risks_output = gr.HTML(value=ar_placeholder)
            # تم تعديل هذا السطر ليكون gr.Markdown بدلاً من gr.HTML وحقنه بـ CSS مخصص
            with gr.TabItem(LABELS["ar"]["tabs"][6]) as tab7: 
                legal_output = gr.Markdown(value=ar_md_placeholder, elem_classes="legal-markdown-container")

    # تحديث اللغات وواجهات التلميح الفارغ ديناميكياً عند تحويل اللغة قبل بدء التحليل
    def update_ui(lang):
        direction_class = "rtl" if lang == "ar" else "ltr"
        l = LABELS[lang]
        new_desc = f"""
        <div style="text-align: center; padding-top: 30px; margin-bottom: 20px;">
            <h1 class="main-title" style="font-size: 3.2em; margin: 0; font-weight: 800; letter-spacing: -1.5px;">ContractFlow AI</h1>
            <p style="color: #94a3b8; font-size: 1.1em; margin-top: 8px;">{l['desc']}</p>
        </div>
        """
        current_placeholder = get_placeholder_html(l["placeholder"])
        current_md_placeholder = get_placeholder_markdown(l["placeholder"])
        
        return (
            gr.update(elem_classes=direction_class), gr.update(value=new_desc),
            gr.update(label=l["file_label"]), gr.update(label=l["contract_type"]), 
            gr.update(label=l["custom_file"]), gr.update(value=l["submit"]), 
            gr.update(label=l["tabs"][0]), gr.update(label=l["tabs"][1]), 
            gr.update(label=l["tabs"][2]), gr.update(label=l["tabs"][3]), 
            gr.update(label=l["tabs"][4]), gr.update(label=l["tabs"][5]), 
            gr.update(label=l["tabs"][6]),
            # تحديث محتوى التابات الفارغة فوراً باللغة الجديدة
            gr.update(value=current_placeholder), gr.update(value=current_placeholder),
            gr.update(value=current_placeholder), gr.update(value=current_placeholder),
            gr.update(value=current_placeholder), gr.update(value=current_placeholder),
            gr.update(value=current_md_placeholder) # المرجعية القانونية كـ Markdown
        )

    lang_selector.change(
        fn=update_ui, 
        inputs=[lang_selector], 
        outputs=[
            main_container, description_text, input_file, contract_type_input, custom_clauses_file, submit_btn, 
            tab1, tab2, tab3, tab4, tab5, tab6, tab7,
            overview_output, extracted_output, clauses_output, specific_output, missing_output, risks_output, legal_output
        ]
    )
    
    submit_btn.click(
        fn=analyze_contract_ui, 
        inputs=[input_file, custom_clauses_file, contract_type_input, lang_selector], 
        outputs=[overview_output, extracted_output, clauses_output, specific_output, missing_output, risks_output, legal_output], 
        show_progress="full"
    )

if __name__ == "__main__": demo.launch(server_name="0.0.0.0", server_port=7860)