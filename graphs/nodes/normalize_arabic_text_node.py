import unicodedata
import re
from graphs.state_schema import AgentState


def normalize_arabic_text_node(state: AgentState)-> AgentState:
    """
    تقوم هذه الدالة بمعايرة النصوص العربية المستخرجة من الـ OCR 
    وتحويل الأشكال العرضية للحروف (Presentation Forms) إلى حروف عربية قياسية نظيفة،
    مما يضمن فهم الموديل للنص بنسبة 100% دون أخطاء إملائية في المخرجات.
    """
    if not state.contract_text:
        return state

    # 1. معايرة اليونيكود بنمط NFKC (تفكيك وتركيب الأشكال المتوافقة)
    # هذا يحل مشكلة الحروف المربوطة والمدمجة التي ينتجها الـ OCR
    normalized = unicodedata.normalize('NFKC', state.contract_text)
    
    # 2. قاموس لاستبدال بعض محارف اليونيكود العرضية الشائعة التي قد لا تعالجها المعايرة الافتراضية
    presentation_forms_map = {
        # استبدال التنوين وأشكال الهمزات المدمجة لو وجدت بالخطأ
        '\uFE81': 'آ', '\uFE82': 'آ',
        '\uFE83': 'أ', '\uFE84': 'أ',
        '\uFE85': 'ؤ', '\uFE86': 'ؤ',
        '\uFE87': 'إ', '\uFE88': 'إ',
        '\uFE89': 'ئ', '\uFE8A': 'ئ', '\uFE8B': 'ئ', '\uFE8C': 'ئ',
        '\uFE8D': 'ا', '\uFE8E': 'ا',
        '\uFE8F': 'ب', '\uFE90': 'ب', '\uFE91': 'ب', '\uFE92': 'ب',
        '\uFE93': 'ة', '\uFE94': 'ة',
        '\uFE95': 'ت', '\uFE96': 'ت', '\uFE97': 'ت', '\uFE98': 'ت',
        '\uFE99': 'ث', '\uFE9A': 'ث', '\uFE9B': 'ث', '\uFE9C': 'ث',
        '\uFE9D': 'ج', '\uFE9E': 'ج', '\uFE9F': 'ج', '\uFEA0': 'ج',
        '\uFEA1': 'ح', '\uFEA2': 'ح', '\uFEA3': 'ح', '\uFEA4': 'ح',
        '\uFEA5': 'خ', '\uFEA6': 'خ', '\uFEA7': 'خ', '\uFEA8': 'خ',
        '\uFEA9': 'د', '\uFEAA': 'د',
        '\uFEAB': 'ذ', '\uFEAC': 'ذ',
        '\uFEAD': 'ر', '\uFEAE': 'ر',
        '\uFEAF': 'ز', '\uFEB0': 'ز',
        '\uFEB1': 'س', '\uFEB2': 'س', '\uFEB3': 'س', '\uFEB4': 'س',
        '\uFEB5': 'ش', '\uFEB6': 'ش', '\uFEB7': 'ش', '\uFEB8': 'ش',
        '\uFEB9': 'ص', '\uFEBA': 'ص', '\uFEBB': 'ص', '\uFEBC': 'ص',
        '\uFEBD': 'ض', '\uFEBE': 'ض', '\uFEBF': 'ض', '\uFEC0': 'ض',
        '\uFEC1': 'ط', '\uFEC2': 'ط', '\uFEC3': 'ط', '\uFEC4': 'ط',
        '\uFEC5': 'ظ', '\uFEC6': 'ظ', '\uFEC7': 'ظ', '\uFEC8': 'ظ',
        '\uFEC9': 'ع', '\uFECA': 'ع', '\uFECB': 'ع', '\uFECC': 'ع',
        '\uFECD': 'غ', '\uFECE': 'غ', '\uFECF': 'غ', '\uFED0': 'غ',
        '\uFED1': 'ف', '\uFED2': 'ف', '\uFED3': 'ف', '\uFED4': 'ف',
        '\uFED5': 'ق', '\uFED6': 'ق', '\uFED7': 'ق', '\uFED8': 'ق',
        '\uFED9': 'ك', '\uFEDA': 'ك', '\uFEDB': 'ك', '\uFEDC': 'ك',
        '\uFEDD': 'ل', '\uFEDE': 'ل', '\uFEDF': 'ل', '\uFEE0': 'ل',
        '\uFEE1': 'م', '\uFEE2': 'م', '\uFEE3': 'م', '\uFEE4': 'م',
        '\uFEE5': 'ن', '\uFEE6': 'ن', '\uFEE7': 'ن', '\uFEE8': 'ن',
        '\uFEE9': 'ه', '\uFEEA': 'ه', '\uFEEB': 'ه', '\uFEEC': 'ه',
        '\uFEED': 'و', '\uFEEE': 'و',
        '\uFEEF': 'ى', '\uFEF0': 'ى',
        '\uFEF1': 'ي', '\uFEF2': 'ي', '\uFEF3': 'ي', '\uFEF4': 'ي',
    }
    
    # استبدال الحروف بناءً على القاموس الحمائي
    for char, replacement in presentation_forms_map.items():
        normalized = normalized.replace(char, replacement)
    
    # 3. تنظيف أي مسافات صفرية (Zero-width spaces) أو علامات كشيدة زائدة قد تشتت الموديل
    normalized = normalized.replace('\u200b', '') # إزالة المسافة الصفرية
    normalized = normalized.replace('\u200c', '') # إزالة فاصل الصفر العريض
    normalized = normalized.replace('\u0640', '') # إزالة التطويل / الكشيدة لتوحيد الكلمات
    normalized = normalized.replace('ی', 'ي')
    normalized = normalized.replace('ک', 'ك')
    
    # 4. توحيد المسافات البيضاء مع الحفاظ على فواصل الأسطر المهمة للتقسيم.
    normalized = re.sub(r'[ \t]+', ' ', normalized)
    normalized = re.sub(r'\n{3,}', '\n\n', normalized).strip()
    state.update({"contract_text": normalized})

    return state
