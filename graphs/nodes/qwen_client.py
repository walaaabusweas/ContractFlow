import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from openai import OpenAI
import dashscope
from dashscope import TextEmbedding # تأكدي من تثبيت مكتبة dashscope

# تحميل ملفات البيئة والإعدادات
load_dotenv()
load_dotenv(Path(__file__).resolve().parents[2] / "config" / ".env")

# الموديل الافتراضي الجديد لـ DashScope
DEFAULT_QWEN_MODEL = "qwen2.5-72b-instruct"
DEFAULT_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

api_key = os.getenv("DASHSCOPE_API_KEY")
if api_key:
    dashscope.api_key = api_key
else:
    print("⚠️ WARNING: DASHSCOPE_API_KEY not found in environment variables!")

def qwen_chat_completion(
    messages: List[Dict[str, str]],
    *,
    temperature: float = 0,
    max_tokens: int = 2500,
    response_format: Optional[Dict[str, Any]] = None,
) -> str:
    """
     الفانكش   مدعومة بـ OpenAI Client 
    ومتصلة مباشرة بـ Alibaba DashScope لتشغيل موديلات Qwen باستقرار كامل.
    """
    # جلب مفتاح الـ API والـ Model من الـ .env
    model_name = os.getenv("QWEN_MODEL_NAME", DEFAULT_QWEN_MODEL)
    base_url = os.getenv("DASHSCOPE_BASE_URL", DEFAULT_BASE_URL)

    if not dashscope.api_key:
        raise RuntimeError(
            "DASHSCOPE_API_KEY is missing from your .env file. "
            "Please add it to run Qwen via Alibaba Cloud."
        )

    # تهيئة الـ Client المتوافق مع OpenAI
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    # تجهيز المعاملات الديناميكية الممررة من الـ Nodes
    kwargs = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    # دعم صيغة الـ JSON الممررة من نود الاستخراج
    if response_format is not None:
        kwargs["response_format"] = response_format

    try:
        # استدعاء الموديل عبر الـ Chat Completion الموحد
        response = client.chat.completions.create(**kwargs)
        
        # إرجاع النص الصافي مباشرة كما تتوقعه النودز السابقة
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"❌ Error during DashScope Qwen Inference: {e}")
        raise RuntimeError(f"Qwen API Execution failed: {str(e)}") from e
    

# from http import HTTPStatus, client
# import dashscope
# import os
# import requests
# from typing import List
# from dotenv import load_dotenv
# # text-embedding-v3
# def get_embedding(text: str) -> List[float]:
#     """استخدام طلب HTTP مباشر لموديل Embeddings (أكثر استقراراً)"""
#     api_key = os.getenv("DASHSCOPE_API_KEY")
    
#     # رابط موديل Embedding الخاص بـ DashScope
#     url = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding-v3"
    
#     headers = {
#         "Authorization": f"Bearer {api_key}",
#         "Content-Type": "application/json"
#     }
    
#     payload = {
#         "model": "text-embedding-v3",
#         "input": {
#             "text": text
#         }
#     }
    
#     try:
#         response = requests.post(url, headers=headers, json=payload)
#         data = response.json()
        
#         if response.status_code == 200:
#             return data['output']['embeddings'][0]['embedding']
#         else:
#             # هنا ستظهر الرسالة الحقيقية
#             print(f"DEBUG: Response Body: {data}")
#             raise RuntimeError(f"Embedding failed with status {response.status_code}: {data.get('message')}")
            
#     except Exception as e:
#         raise RuntimeError(f"Request failed: {str(e)}")

import os
from typing import List
from openai import OpenAI
from dotenv import load_dotenv


def get_embedding(text: str) -> List[float]:
    """
    استخدام OpenAI API للقيام بالـ Embedding.
    هذا الكود يعتمد على OPENAI_API_KEY الموجود في ملف الـ .env
    """
    
    try:
        # تهيئة الكلاينت الخاص بـ OpenAI
        # تأكدي أن OPENAI_API_KEY موجود في ملف .env
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # استدعاء موديل الـ Embedding (أرخص وأسرع موديل هو text-embedding-3-small)
        response = client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        
        # استرجاع الـ Vector
        return response.data[0].embedding
        
    except Exception as e:
        print(f"❌ Error during OpenAI Embedding: {e}")
        raise RuntimeError(f"Embedding failed: {str(e)}")
