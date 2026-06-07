import json
import os
import chromadb
from graphs.state_schema import AgentState, ContractData
from graphs.nodes.qwen_client import qwen_chat_completion


import chromadb
from chromadb.config import Settings


# --- Singleton Pattern for ChromaDB Client ---
class ChromaManager:
    _instance = None
    _collection = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChromaManager, cls).__new__(cls)
            # إعداد الاتصال باستخدام متغيرات البيئة
            host = os.getenv("CHROMA_SERVER_HOST", "chromadb")
            port = int(os.getenv("CHROMA_SERVER_PORT", "8000"))
            cls._client = chromadb.HttpClient(host=host, port=port)
        return cls._instance

    def get_collection(self, name="contracts"):
        if self._collection is None:
            self._collection = self._client.get_or_create_collection(name="new_contracts_collection20")
        return self._collection
