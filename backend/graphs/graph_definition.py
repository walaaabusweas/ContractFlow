import os
import uuid
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from langsmith import traceable

# استيراد الـ Nodes
from graphs.nodes.categorizer_node import categorize_contract_node
from graphs.nodes.extractor_node import extraction_node
from graphs.nodes.ingest_node import ingest_node
from graphs.nodes.pdf_reader_node import pdf_reader_node
from graphs.nodes.report_generator import report_generator_node
from graphs.nodes.retrieve_node import retrieve_node
from graphs.nodes.specific_clause_extraction_node import specific_clause_extraction_node
from graphs.nodes.risk_analyzer import risk_analyzer_node
from graphs.nodes.detect_missing_clauses_node import detect_missing_clauses_node
from graphs.nodes.language_detector_node import language_detector_node
from graphs.nodes.normalize_arabic_text_node import normalize_arabic_text_node
from graphs.state_schema import AgentState
from graphs.nodes.prepare_custom_clauses_node import prepare_custom_clauses_node
# تحميل الإعدادات
load_dotenv()
load_dotenv(Path(__file__).resolve().parents[1] / "config" / ".env")

def check_contract_language_router(state: AgentState) -> Literal["normalize_arabic", "bypass_normalization"]:
    """
    دالة التوجيه الشرطي للغة العقد
    """
    lang = state.contract_language.lower() if state.contract_language else "en"
    if lang == "ar":
        return "normalize_arabic"
    else:
        return "bypass_normalization"

def build_contract_graph():
    """
    بناء الـ Graph الخاص بمعالجة العقود
    """
    builder = StateGraph(AgentState)

    # إضافة الـ Nodes
    builder.add_node("pdf_reader", pdf_reader_node)
    builder.add_node("language_detector", language_detector_node)
    builder.add_node("normalize_arabic", normalize_arabic_text_node)
    builder.add_node("prepare_custom_clauses_node", prepare_custom_clauses_node)
    builder.add_node("ingest_node", ingest_node)
    builder.add_node("retrieve_node", retrieve_node)
    builder.add_node("categorize_contract", categorize_contract_node)
    builder.add_node("extract_data", extraction_node) 
    builder.add_node("specific_clause_extraction_node", specific_clause_extraction_node)
    builder.add_node("risk_analyzer_node", risk_analyzer_node)
    builder.add_node("detect_missing_clauses", detect_missing_clauses_node)
    builder.add_node("report_generator", report_generator_node)
    

    builder.set_entry_point("pdf_reader")
    builder.add_edge("pdf_reader", "prepare_custom_clauses_node")
    builder.add_edge("prepare_custom_clauses_node", "language_detector")
    builder.add_conditional_edges(
        "language_detector",
        check_contract_language_router,
        {
            "normalize_arabic": "normalize_arabic",
            "bypass_normalization": "categorize_contract"
        }
    )
    
    builder.add_edge("normalize_arabic", "categorize_contract")
    builder.add_edge("categorize_contract", "ingest_node")
    builder.add_edge("ingest_node", "retrieve_node")
    builder.add_edge("retrieve_node", "extract_data")
    builder.add_edge("extract_data", "specific_clause_extraction_node")
    builder.add_edge("specific_clause_extraction_node", "detect_missing_clauses")
    builder.add_edge("detect_missing_clauses", "risk_analyzer_node")
    builder.add_edge("risk_analyzer_node", "report_generator")
    builder.add_edge("report_generator", END)
    
    return builder.compile()

@traceable(name="contract_workflow", run_type="chain")
async def run_contract_workflow(initial_state: AgentState) -> AgentState:
    """
    دالة تشغيل الـ Workflow
    """
    try:
        config = {"configurable": {"thread_id": uuid.uuid4().hex}}
        compiled_graph = build_contract_graph()
        output = await compiled_graph.ainvoke(initial_state, config=config)
        return output
    except Exception as e:
        print(f"[Graph Error] {str(e)}")
        raise e


def check_contract_language_router(state: AgentState) -> Literal["normalize_arabic", "bypass_normalization"]:
    """
    دالة التوجيه الشرطي (Conditional Router):
    تقرأ لغة العقد المكتشفة من الـ State وتحدد المسار التالي للـ Graph.
    """
    lang = state.contract_language.lower() if state.contract_language else "en"
    if lang == "ar":
        print("🔀 Router: Language is Arabic. Directing to Normalization Node.", flush=True)
        return "normalize_arabic"
    else:
        print("🔀 Router: Language is English/Other. Bypassing Normalization Node.", flush=True)
        return "bypass_normalization"
def clear_contractflow_runtime_cache():
    try:
        from config.redis_connection import redis_client
        cache_keys = list(redis_client.scan_iter("extraction_session:*"))
        if cache_keys:
            redis_client.delete(*cache_keys)
    except: pass

def state_to_dict(state):
    return state.dict() if hasattr(state, "dict") else state
