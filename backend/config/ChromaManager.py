import os
import chromadb

# --- Singleton Pattern for ChromaDB Client ---
class ChromaManager:
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChromaManager, cls).__new__(cls)
            
            # قراءة المتغيرات
            host = os.getenv("CHROMA_SERVER_HOST")
            port = os.getenv("CHROMA_SERVER_PORT", "8000")
            
            # إذا كنا داخل بيئة AWS Lambda أو لم نحدد سيرفر كروما خارجي
            if not host or host == "chromadb":
                # نستخدم PersistentClient يحفظ البيانات محلياً في /tmp (الخاص بـ Lambda)
                persist_dir = os.getenv("CHROMA_PERSIST_DIR", "/tmp/chroma_db")
                cls._client = chromadb.PersistentClient(path=persist_dir)
            else:
                # إذا كان هناك Host خارجي محدد (مثل EC2 أو IP سيرفر حقيقي)
                cls._client = chromadb.HttpClient(host=host, port=int(port))
                
        return cls._instance

    def get_client(self):
        """إرجاع الـ client الذي تم إنشاؤه في __new__"""
        return self._client
    
    def get_collection(self):
        model_dim = 384 
        collection_name = f"contracts_dim_{model_dim}"
    
        return self.get_client().get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )