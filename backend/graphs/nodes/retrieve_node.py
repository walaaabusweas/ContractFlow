import os
import hashlib
import json
import time
from typing import List
import cohere
from langchain_text_splitters import RecursiveCharacterTextSplitter
from graphs.state_schema import AgentState
from config.ChromaManager import ChromaManager
from graphs.nodes.qwen_client import get_embedding, qwen_chat_completion 
from utils.decorators import track_tokens,record_model_usage
from utils.helper import get_language_instruction

co = cohere.Client(api_key=os.getenv("COHERE_API_KEY"))
CACHE_FILE = "rerank_cache.json"

def get_collection():
    return ChromaManager().get_collection()


def embed_chunks(chunks_texts: List[str], state: AgentState) -> List[List[float]]:
    return [get_embedding(text, state=state) for text in chunks_texts]

def embed_query(question: str, state: AgentState):
    tokens = len(question.split()) # أو استخدام tiktoken للدقة
    record_model_usage(input_tokens=tokens, output_tokens=0)
    return get_embedding(question, state=state)

def get_retrieval_strategy(field: str):
    strategy = {
        "parties": "parties",
        "value": "value",
        "duration": "duration",
        "payment_terms": "payment_terms",
        "termination": "termination",
        "liability": "liability",
        "confidentiality": "confidentiality",
        "governing_law": "governing_law",
        "dispute_resolution": "dispute_resolution",
    }
    return strategy.get(field, [])

def get_best_reranked_doc(question: str, documents: list[str]) -> str:
    if not documents: return ""
    if len(documents) == 1:
        return documents[0]
    

    time.sleep(1)
    
    reranked = co.rerank(query=question, documents=documents, top_n=1, model="rerank-multilingual-v3.0")
    # داخل دالة get_best_reranked_doc
    if hasattr(reranked, 'meta') and reranked.meta.billed_units:
        # سجل استهلاك Cohere كـ input_tokens
        record_model_usage(
            input_tokens=reranked.meta.billed_units.input_tokens,
            output_tokens=0
        )

    if not reranked or not reranked.results: 
        return ""
    
    # طريقة آمنة لاستخراج النص
    best_res = reranked.results[0]
    best_doc_text = ""
    
    if hasattr(best_res.document, 'text'):
        best_doc_text = best_res.document.text
    elif hasattr(best_res.document, 'content'):
        best_doc_text = best_res.document.content
    elif isinstance(best_res.document, dict):
        best_doc_text = best_res.document.get('text') or best_res.document.get('content')

    if not best_doc_text and hasattr(best_res, "index"):
        best_doc_text = documents[best_res.index]
    
    if not best_doc_text:
        return ""

    # حفظ في الكاش
    return best_doc_text



@track_tokens("retrieve_node")
def retrieve_node(state: AgentState) -> AgentState:
    print("--- [NODE] RETRIEVING WITH SEMANTIC SEARCH & RERANKING ---")
    collection = get_collection()
    
    queries_to_fetch = {
        "parties": "What are the full legal names of the contracting parties mentioned in the preamble?",
        "value": "What is the total contract value?",
        "duration": "What is the duration of the contract?",
        "payment_terms": "What are the payment terms?",
        "termination": "What are the conditions for contract termination?",
        "liability": "What is the limitation of liability?",
        "confidentiality": "What are the confidentiality obligations?",
        "governing_law": "What is the governing law?",
        "dispute_resolution": "What is the dispute resolution protocol?"
    }
    
    retrieved_data = {}
    
    # الفلتر الوحيد المطلوب هو الـ contract_id لضمان عدم خلط عقود مختلفة
    filter_dict = {"contract_id": state.contract_id}
    
    for field, query_text in queries_to_fetch.items():
        # البحث الدلالي المباشر (Vector Search)
        results = collection.query(
            query_embeddings=[embed_query(query_text,state=state)], 
            n_results=5, # زيادة النتائج لتعزيز دقة الـ Reranker
            where=filter_dict
        )
        
        all_candidates = results.get("documents", [[]])[0]
        
        # استخدام Cohere Rerank لاختيار الأفضل دلالياً
        # الـ Reranker سيقارن بين السؤال وبين نصوص الـ Markdown المسترجعة
        best_doc = get_best_reranked_doc(query_text, all_candidates)
        
        retrieved_data[field] = best_doc if best_doc else "Not specified"
        print(f"✅ Retrieved info for {field}")

    state.update({
        "retrieved_context": retrieved_data,
        "history": state.history + ["Retrieval & Semantic Reranking completed"]
    })
    return state