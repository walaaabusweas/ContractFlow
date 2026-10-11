import os
import shutil
import tarfile
from pathlib import Path
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from langsmith import traceable

# ---------------------------------------------------------
# إعداد متغيرات البيئة
# ---------------------------------------------------------
env_path = Path(__file__).resolve().parents[2] / "config" / ".env"

if env_path.exists():
    load_dotenv(env_path)

# ---------------------------------------------------------
# إعداد المسار المحلي المباشر للموديل داخل صورة الـ Docker
# ---------------------------------------------------------
MODEL_PATH = "/opt/ml/models/bge-m3"

# متغير عام لإعادة استخدام الموديل المفتوح بالذاكرة عبر الـ Warm Starts
model = None


def get_model():
    """تحميل الموديل من المجلد المحلي المباشر داخل الصورة إلى الذاكرة مرة واحدة فقط."""
    global model

    if model is None:
        from sentence_transformers import SentenceTransformer
        print("🧠 جاري تحميل الموديل المدمج إلى الذاكرة لأول مرة...")
        
        # الاعتماد على المسار المباشر يمنع أي محاولة اتصال خارجية أو بحث في S3
        model = SentenceTransformer(
            MODEL_PATH, 
            device="cpu",
            local_files_only=True
        )
        print("✅ تم تحميل الموديل إلى الذاكرة بنجاح.")

    return model


def get_embedding(text: str, state: dict = None, **kwargs) -> List[float]:
    """توليد Embedding لنص واحد."""
    if not text or not text.strip():
        raise ValueError("النص المدخل فارغ ولا يمكن توليد Embedding له.")

    # جلب الموديل من الذاكرة (سيحمله أول مرة فقط)
    loaded_model = get_model()

    embedding = loaded_model.encode(
        text.strip(),
        convert_to_numpy=True,
        normalize_embeddings=True
    )
    return embedding.tolist()





@traceable(name="qwen_chat_completion", run_type="llm")
def qwen_chat_completion(
    messages: List[Dict[str, str]],
    *,
    temperature: float = 0,
    max_tokens: int = 2500,
    response_format: Optional[Dict[str, Any]] = None,
) -> str:
    # ⚡ Lazy Imports داخل الدالة لمنع تباطؤ إقلاع Lambda
    from huggingface_hub import InferenceClient
    from utils.decorators import record_model_usage

    api_key = os.getenv("HF_TOKEN")
    model_name = "Qwen/Qwen2.5-7B-Instruct"
    client = InferenceClient(token=api_key)

    try:
        response = client.chat_completion(
            model=model_name,
            messages=messages,
            temperature=temperature if temperature > 0 else 0.1,
            max_tokens=max_tokens,
            stream=False,
            provider="featherless"
        )

        if hasattr(response, 'usage') and response.usage:
            record_model_usage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens
            )

            try:
                from langsmith.run_helpers import get_current_run_tree
                run_tree = get_current_run_tree()
                if run_tree:
                    run_tree.extra["metadata"] = {
                        "input_tokens": response.usage.prompt_tokens,
                        "output_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                    run_tree.patch()
            except Exception:
                pass

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"❌ Error during Hugging Face Inference: {e}")
        raise RuntimeError(f"Hugging Face API Execution failed: {str(e)}") from e