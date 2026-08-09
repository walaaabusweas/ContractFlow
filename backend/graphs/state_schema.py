from dataclasses import dataclass, field, asdict, fields
from typing import Any, Dict, List, Optional

@dataclass
class ContractData:
    parties: List[str] = field(default_factory=list)
    value: Optional[str] = None
    duration: Optional[str] = None
    payment_terms: Optional[str] = None
    termination: Optional[str] = None
    liability: Optional[str] = None
    confidentiality: Optional[str] = None
    governing_law: Optional[str] = None
    dispute_resolution: Optional[str] = None
    specific_clauses: Dict[str, str] = field(default_factory=dict)
    renewal: Optional[str] = None

@dataclass
class AgentState:
    contract_id: str = ""
    contract_text: str = ""
    custom_file_path: str = ""
    temp_custom_checklist: Dict[str, Any] = field(default_factory=dict)
    retrieved_context: dict = field(default_factory=dict)
    contract_language: str = "en"
    english_contract_text: str = ""
    is_extraction_successful: bool = False
    contract_type: str = "unknown"
    history: List[str] = field(default_factory=list)
    # لاحظي هنا نمرر كلاس ContractData ككائن
    extracted_data: ContractData = field(default_factory=ContractData)
    missing_clauses: List[str] = field(default_factory=list)
    is_compliance_checked: bool = False
    risks: List[Dict[str, Any]] = field(default_factory=list)
    final_report: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    token_usage: Dict[str, Any] = field(default_factory=dict)
    execution_time: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """تحويل الـ State كاملاً إلى قاموس (مفيد للـ FastAPI)"""
        return asdict(self)
    
    def update(self, data: Dict[str, Any]):
        """تحديث الحقول ديناميكياً بنفس منطق مشروع الـ Email"""
        for key, value in data.items():
            if hasattr(self, key):
                if key == "extracted_data" and isinstance(value, dict):
                    allowed_fields = {field.name for field in fields(ContractData)}
                    value = ContractData(**{
                        data_key: data_value
                        for data_key, data_value in value.items()
                        if data_key in allowed_fields
                    })
                setattr(self, key, value)
