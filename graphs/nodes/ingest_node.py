from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from graphs.state_schema import AgentState
from config.ChromaManager import ChromaManager
from graphs.nodes.qwen_client import get_embedding, qwen_chat_completion
from utils.decorators import track_tokens
import hashlib

from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding

from llama_index.core import Document
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.core.embeddings import BaseEmbedding
from typing import List, Any
from graphs.state_schema import AgentState
from config.ChromaManager import ChromaManager
from graphs.nodes.qwen_client import get_embedding, qwen_chat_completion
from utils.decorators import track_tokens
import hashlib

# 1. إنشاء Wrapper بسيط لربط دالتك بـ LlamaIndex
class MyCustomEmbedding(BaseEmbedding):
    def _get_query_embedding(self, query: str) -> List[float]:
        return get_embedding(query)

    def _get_text_embedding(self, text: str) -> List[float]:
        return get_embedding(text)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return get_embedding(query)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        return get_embedding(text)

@track_tokens("ingest_node")
def ingest_node(state: AgentState) -> AgentState:
    print("--- [NODE] STARTING SMART SEMANTIC INGESTION ---")

    contract_id = generate_contract_id(state.contract_text)
    
    doc = Document(text=state.contract_text)
    
    # 2. استخدام الموديل الخاص بك عبر الـ Wrapper
    embed_model = MyCustomEmbedding() 
    
    # 3. التقطيع الدلالي
    parser = SemanticSplitterNodeParser(
        buffer_size=1, 
        breakpoint_percentile_threshold=95, 
        embed_model=embed_model
    )
    
    nodes = parser.get_nodes_from_documents([doc])
    
    texts = []
    metadatas = []
    chunk_ids = []

    print(f"Enriching {len(nodes)} semantic nodes with metadata...")
    for i, node in enumerate(nodes):
        content = node.get_content()
        prompt = f"Extract the specific legal section title. Return ONLY the title:\n{content[:300]}"
        section_title = qwen_chat_completion(prompt).strip()
        
        texts.append(content)
        metadatas.append({
            "contract_id": contract_id,
            "section": section_title,
            "lang": state.contract_language
        })
        chunk_ids.append(f"{contract_id}_chunk_{i}")

    # 4. الرفع إلى ChromaDB
    print("Uploading to ChromaDB...")
    collection = ChromaManager().get_collection()    
    collection.delete(where={"contract_id": contract_id})
    
    # تحويل النصوص لـ Embeddings باستخدام وظيفتك الأصلية (مجانية/خاصة)
    embeddings = [get_embedding(text) for text in texts]
    
    collection.upsert(
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=chunk_ids
    )

    state.update({
        "contract_id": contract_id,
        "history": state.history + [f"Ingestion Complete: {contract_id} with {len(nodes)} semantic chunks."]
    })

    return state

def generate_contract_id(text: str) -> str:
    hash_object = hashlib.sha256(text[:1000].encode())
    return hash_object.hexdigest()[:12]


def generate_contract_id(text: str) -> str:
    hash_object = hashlib.sha256(text[:1000].encode())
    return hash_object.hexdigest()[:12]