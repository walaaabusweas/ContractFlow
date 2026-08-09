import os
import shutil
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from graphs.graph_definition import run_contract_workflow
from graphs.state_schema import AgentState, ContractData

# 1️⃣ استيراد Mangum لتغليف التطبيق لـ AWS Lambda
from mangum import Mangum

load_dotenv()
app = FastAPI(title="ContractFlow API")

# --- دوال مساعدة ---
def clear_contractflow_runtime_cache():
    try:
        from config.redis_connection import redis_client
        cache_keys = list(redis_client.scan_iter("extraction_session:*"))
        if cache_keys:
            redis_client.delete(*cache_keys)
    except Exception:
        pass

def state_to_dict(state):
    if hasattr(state, "model_dump"):
        return state.model_dump()
    return state.dict() if hasattr(state, "dict") else state

@app.get("/")
def read_root():
    return {"status": "success", "message": "Hello! ContractFlow API is Live and working!"}

# --- المسارات ---
import asyncio

@app.post("/upload-contract")
def upload_and_analyze(  # 👈 جعلها def متزامنة
    file: UploadFile = File(...),
    contract_type: str = Form(..., description="Type of contract: supply, sow, nda, other"),
    custom_clauses_file: Optional[UploadFile] = File(None),
):
    # 1. التحقق من المدخلات
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    valid_types = ["sow", "supply", "nda", "other"]
    if contract_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid contract type. Must be one of {valid_types}")

    if custom_clauses_file and custom_clauses_file.filename:
        custom_suffix = Path(custom_clauses_file.filename).suffix.lower()
        if custom_suffix not in {".txt", ".json"}:
            raise HTTPException(status_code=400, detail="Custom clauses file must be a TXT or JSON file.")

    # 2. إعداد المجلدات والمسارات
    temp_dir = Path("/tmp/temp_uploads")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    safe_filename = Path(file.filename).name 
    file_path = temp_dir / f"{uuid4().hex}_{safe_filename}"
    custom_file_path = None

    try:
        clear_contractflow_runtime_cache()

        # 3. حفظ الملفات
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if custom_clauses_file and custom_clauses_file.filename:
            safe_custom_filename = Path(custom_clauses_file.filename).name
            custom_file_path = temp_dir / f"{uuid4().hex}_{safe_custom_filename}"
            with custom_file_path.open("wb") as buffer:
                shutil.copyfileobj(custom_clauses_file.file, buffer)
        
        # 4. تجهيز الـ State
        initial_state = AgentState(
            contract_text="",
            custom_file_path=str(custom_file_path) if custom_file_path else "",
            english_contract_text="",
            contract_language="ar",
            is_extraction_successful=False,
            contract_type=contract_type,
            extracted_data=ContractData(),
            missing_clauses=[],
            is_compliance_checked=False,
            risks=[],
            final_report={"file_path": str(file_path)}
        )

        # 5. إدارة الـ Event Loop لمنع مشكلة Event loop is closed في AWS Lambda
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # تشغيل الـ Workflow بسلام
        result_state = loop.run_until_complete(run_contract_workflow(initial_state))
        return state_to_dict(result_state)
        
    finally:
        # مسح الملفات
        if file_path.exists():
            os.remove(file_path)
        if custom_file_path and custom_file_path.exists():
            os.remove(custom_file_path)

# 2️⃣ الـ Handler الخاص بـ AWS Lambda
handler = Mangum(app)