from fastapi import FastAPI, UploadFile, File, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import redis
import os
import shutil
from uuid import uuid4
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# استيراد الـ Workflow من ملف الـ Graph
from graphs.graph_definition import run_contract_workflow
from graphs.state_schema import AgentState, ContractData

load_dotenv()
app = FastAPI(title="ContractFlow API")

# --- دوال مساعدة ---
def clear_contractflow_runtime_cache():
    try:
        from config.redis_connection import redis_client
        cache_keys = list(redis_client.scan_iter("extraction_session:*"))
        if cache_keys:
            redis_client.delete(*cache_keys)
    except: pass

def state_to_dict(state):
    return state.dict() if hasattr(state, "dict") else state

# --- المسارات ---
@app.post("/upload-contract")
async def upload_and_analyze(
    file: UploadFile = File(...),
    custom_clauses_file: Optional[UploadFile] = File(None),
):
    # 1. التحقق من نوع الملف
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    if custom_clauses_file and custom_clauses_file.filename:
        custom_suffix = Path(custom_clauses_file.filename).suffix.lower()
        if custom_suffix not in {".txt", ".json"}:
            raise HTTPException(
                status_code=400,
                detail="Custom clauses file must be a TXT or JSON file.",
            )

    # 2. إنشاء المجلد إذا لم يكن موجوداً
    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    
    # تصحيح: استخدام فقط اسم الملف الأخير وليس المسار الكامل
    safe_filename = Path(file.filename).name 
    file_path = temp_dir / f"{uuid4().hex}_{safe_filename}"
    custom_file_path = None

    try:
        clear_contractflow_runtime_cache()

        # 3. حفظ الملف
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
            contract_language="en",
            is_extraction_successful=False,
            contract_type="unknown",
            extracted_data=ContractData(),
            missing_clauses=[],
            is_compliance_checked=False,
            risks=[],
            final_report={"file_path": str(file_path)}
        )

        # 5. تشغيل الـ Workflow
        result_state = await run_contract_workflow(initial_state)
        return state_to_dict(result_state)
        
    finally:
        # مسح الملف بعد الانتهاء
        if file_path.exists():
            os.remove(file_path)
        if custom_file_path and custom_file_path.exists():
            os.remove(custom_file_path)
@app.get("/")
def read_root():
    return {"message": "ContractFlow API is Live!"}
