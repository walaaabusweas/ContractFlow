import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from openai import OpenAI

# تحميل ملفات البيئة والإعدادات
load_dotenv()
load_dotenv(Path(__file__).resolve().parents[2] / "config" / ".env")

# # الموديل الافتراضي الجديد لـ DashScope
# DEFAULT_QWEN_MODEL = "qwen2.5-72b-instruct"
# DEFAULT_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

# api_key = os.getenv("DASHSCOPE_API_KEY")
# if api_key:
#     dashscope.api_key = api_key
# else:
#     print("⚠️ WARNING: DASHSCOPE_API_KEY not found in environment variables!")


# def qwen_chat_completion(
#     messages: List[Dict[str, str]],
#     *,
#     temperature: float = 0,
#     max_tokens: int = 2500,
#     response_format: Optional[Dict[str, Any]] = None,
# ) -> str:
#     """
#     دالة موحدة لاستدعاء موديلات OpenAI (مثل gpt-4o).
#     """
#     # جلب مفتاح الـ API والـ Model من الـ .env
#     # تأكد من تسمية المتغير في ملف .env بـ OPENAI_API_KEY
#     api_key = os.getenv("OPENAI_API_KEY")
#     model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")

#     if not api_key:
#         raise RuntimeError(
#             "OPENAI_API_KEY is missing from your .env file."
#         )

#     # تهيئة الـ Client الخاص بـ OpenAI
#     client = OpenAI(api_key=api_key)

#     # تجهيز المعاملات
#     kwargs = {
#         "model": model_name,
#         "messages": messages,
#         "temperature": temperature,
#         "max_tokens": max_tokens,
#     }

#     # دعم صيغة الـ JSON (مهم جداً لنودز الاستخراج)
#     if response_format is not None:
#         kwargs["response_format"] = response_format

#     try:
#         # استدعاء الموديل
#         response = client.chat.completions.create(**kwargs)
        
#         # إرجاع النص
#         return response.choices[0].message.content.strip()
        
#     except Exception as e:
#         print(f"❌ Error during OpenAI Inference: {e}")
#         raise RuntimeError(f"OpenAI API Execution failed: {str(e)}") from e
    
    

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



# def qwen_chat_completion(
#     messages: List[Dict[str, str]],
#     *,
#     temperature: float = 0,
#     max_tokens: int = 2500,
#     response_format: Optional[Dict[str, Any]] = None,
# ) -> str:
#     """
#     دالة موحدة لاستدعاء موديلات OpenAI (مثل gpt-4o).
#     """
#     # جلب مفتاح الـ API والـ Model من الـ .env
#     # تأكد من تسمية المتغير في ملف .env بـ OPENAI_API_KEY
#     api_key = os.getenv("OPENAI_API_KEY")
#     model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")

#     if not api_key:
#         raise RuntimeError(
#             "OPENAI_API_KEY is missing from your .env file."
#         )

#     # تهيئة الـ Client الخاص بـ OpenAI
#     client = OpenAI(api_key=api_key)

#     # تجهيز المعاملات
#     kwargs = {
#         "model": model_name,
#         "messages": messages,
#         "temperature": temperature,
#         "max_tokens": max_tokens,
#     }

#     # دعم صيغة الـ JSON (مهم جداً لنودز الاستخراج)
#     if response_format is not None:
#         kwargs["response_format"] = response_format

#     try:
#         # استدعاء الموديل
#         response = client.chat.completions.create(**kwargs)
        
#         # إرجاع النص
#         return response.choices[0].message.content.strip()
        
#     except Exception as e:
#         print(f"❌ Error during OpenAI Inference: {e}")
#         raise RuntimeError(f"OpenAI API Execution failed: {str(e)}") from e
    
import os
from typing import List
from openai import OpenAI
from dotenv import load_dotenv

from huggingface_hub import InferenceClient
import os

# تهيئة العميل (يستخدم الـ Token الخاص بك)
client = InferenceClient(api_key=os.getenv("HF_TOKEN"))

def get_embedding(text: str) -> List[float]:
    """
    استخدام الـ API الخاص بـ Hugging Face لعمل Embedding
    (لا يستهلك موارد جهازك).
    """
    try:
        # يمكنك تغيير الموديل لأي موديل Embedding متوفر على HF
        response = client.feature_extraction(
            model="BAAI/bge-m3",
            text=text
        )
        # response يكون عادة numpy array أو list
        return response.tolist()
    except Exception as e:
        print(f"❌ Error during HF API Embedding: {e}")
        raise RuntimeError(f"Embedding failed: {str(e)}")

    # def get_embedding(text: str) -> List[float]:
    #     """
    #     استخدام OpenAI API للقيام بالـ Embedding.
    #     هذا الكود يعتمد على OPENAI_API_KEY الموجود في ملف الـ .env
    #     """
    
#     try:
#         # تهيئة الكلاينت الخاص بـ OpenAI
#         # تأكدي أن OPENAI_API_KEY موجود في ملف .env
#         client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
#         # استدعاء موديل الـ Embedding (أرخص وأسرع موديل هو text-embedding-3-small)
#         response = client.embeddings.create(
#             input=text,
#             model="text-embedding-3-small"
#         )
        
#         # استرجاع الـ Vector
#         return response.data[0].embedding
        
#     except Exception as e:
#         print(f"❌ Error during OpenAI Embedding: {e}")
#         raise RuntimeError(f"Embedding failed: {str(e)}")


import os
from typing import List, Dict, Any, Optional
from huggingface_hub import InferenceClient

from utils.decorators import record_model_usage # تأكد من استيرادها من ملف الـ decorators

def qwen_chat_completion(
    messages: List[Dict[str, str]],
    *,
    temperature: float = 0,
    max_tokens: int = 2500,
    response_format: Optional[Dict[str, Any]] = None,
) -> str:
    """
    استدعاء موديل Qwen2.5-7B-Instruct عبر Hugging Face Inference API مع تتبع التوكنات.
    """
    api_key = os.getenv("HF_TOKEN")
    model_name = "Qwen/Qwen2.5-7B-Instruct"

    if not api_key:
        raise RuntimeError("HF_TOKEN is missing from your .env file.")

    client = InferenceClient(model=model_name, token=api_key)

    try:
        response = client.chat_completion(
            messages=messages,
            temperature=temperature if temperature > 0 else 0.1,
            max_tokens=max_tokens,
            stream=False
        )
        
        # --- إضافة التعديل لتتبع التوكنات ---
        if hasattr(response, 'usage') and response.usage:
            record_model_usage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens
            )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"❌ Error during Hugging Face Inference: {e}")
        raise RuntimeError(f"Hugging Face API Execution failed: {str(e)}") from e