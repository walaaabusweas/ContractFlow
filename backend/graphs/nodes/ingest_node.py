import hashlib
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.ChromaManager import ChromaManager
from graphs.nodes.qwen_client import get_embedding
from graphs.state_schema import AgentState
from utils.decorators import track_tokens

# ==================================================
# دالة التقسيم المرن (تعتمد على تنسيق الفقرات فقط)
# ==================================================

def block_based_splitter(text: str) -> List[str]:
    """
    تقسم النص بناءً على الهيكلية البصرية (الفراغات المزدوجة والأسطر).
    تضمن بقاء العناوين والفقرات كوحدات متماسكة دون الاعتماد على كلمات مفتاحية.
    """
    # نستخدم فواصل تحافظ على الفقرات والعناوين ككتل متكاملة
    # "\n\n" هي الفاصل الأقوى للفقرات في المستندات
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", ".", "●", "•"] 
    )
    return splitter.split_text(text)

# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from typing import List

# def block_based_splitter(text: str) -> List[str]:
#     """
#     نستخدم استراتيجية تفضل الفقرات والعناوين وتتجاهل الرموز الداخلية.
#     """
#     splitter = RecursiveCharacterTextSplitter(
#         chunk_size=1000,
#         chunk_overlap=200,
#         # الترتيب هنا حيوي: يبدأ بالبحث عن الفواصل الكبيرة أولاً
#         separators=[
#             "\n\n",       # 1. الفقرات المتباعدة
#             "\n●",        # 2. بداية نقاط التعداد في سطر جديد
#             "\n",         # 3. الأسطر الجديدة
#             " "           # 4. المسافات (الملاذ الأخير)
#         ]
#     )
#     return splitter.split_text(text)


# ==================================================
# Ingestion Node
# ==================================================

import hashlib
from utils.decorators import track_tokens  # أو المكان المخصص للـ decorator

@track_tokens("ingest_node")
def ingest_node(state: AgentState) -> AgentState:
    print("\n--- [NODE] STARTING BLOCK-BASED INGESTION ---")

    contract_text = state.contract_text
    if not contract_text or not contract_text.strip():
        return state

    contract_id = hashlib.sha256(contract_text[:1000].encode("utf-8")).hexdigest()[:12]
    
    # تنفيذ التقسيم بناءً على الفراغات والفقرات
    chunks = block_based_splitter(contract_text)

    # تنظيف الفراغات الزائدة من كل قطعة
    texts = [c.strip() for c in chunks if len(c.strip()) > 20]
    
    if not texts:
        print("⚠️ No valid chunks found after cleaning.")
        return state

    metadatas = [
        {"contract_id": contract_id, "chunk_index": i, "lang": state.contract_language} 
        for i in range(len(texts))
    ]
    ids = [f"{contract_id}_chunk_{i}" for i in range(len(texts))]

    # 1. استخراج الـ Embeddings وتنظيف أي قيم غريبة (tuples/strings/ndarray)
    raw_embeddings = [get_embedding(t, state=state) for t in texts]
    
    clean_embeddings = []
    for emb in raw_embeddings:
        # لو الدالة بترجع tuple زي (embedding_list, tokens_count)
        if isinstance(emb, tuple):
            emb = emb[0]
            
        # لو الـ embedding كائن numpy قم بتحويله إلى list
        if hasattr(emb, "tolist"):
            emb = emb.tolist()
            
        clean_embeddings.append(emb)

    # 2. التخزين في ChromaDB
    collection = ChromaManager().get_collection()
    try:
        collection.delete(where={"contract_id": contract_id})
    except Exception:
        pass

    if not clean_embeddings or not isinstance(clean_embeddings, list):
        raise ValueError(f"Invalid embeddings format returned: {type(clean_embeddings)}")

    # التحقق من عدم وجود أي عنصر كـ str داخل القائمة
    for i, emb in enumerate(clean_embeddings):
        if isinstance(emb, str):
            raise ValueError(f"Embedding at index {i} returned an error string instead of vector: {emb}")

    # التخزين في ChromaDB

    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=clean_embeddings,
        metadatas=metadatas
    )

    state.update({
        "contract_id": contract_id,
        "history": state.history + [f"Ingestion Complete: {contract_id} ({len(texts)} chunks)"]
    })

    print(f"Successfully indexed {len(texts)} chunks.")
    return state