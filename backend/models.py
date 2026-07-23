from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any

class RegisterInput(BaseModel):
    email: EmailStr
    password: str
    name: str

class LoginInput(BaseModel):
    email: EmailStr
    password: str

class CompanyInput(BaseModel):
    name: str
    region: str = "PT"
    currency: str = "EUR"
    sector: str = ""
    employees_count: int = 0
    clients_count: int = 0
    bank_balance: float = 0
    monthly_tax_estimate: float = 0

class DNAInput(BaseModel):
    answers: Dict[str, Any]
    dream: str = ""
    target_revenue: float = 0
    work_hours: str = ""
    exit_plan: str = ""
    five_year_vision: str = ""
    ceo_mode: str = "crescimento"

class EntryInput(BaseModel):
    type: str
    category: str
    amount: float
    date: str
    description: str = ""

class MemoryInput(BaseModel):
    content: str
    category: str = "geral"

class SettingsInput(BaseModel):
    ceo_mode: Optional[str] = None
    theme: Optional[str] = None
    briefing_count: Optional[int] = None
    briefing_tone: Optional[str] = None
    model: Optional[str] = None
    monitored_widgets: Optional[List[str]] = None
    email_briefing: Optional[bool] = None

class ChatInput(BaseModel):
    session_id: Optional[str] = None
    message: str

class SimInput(BaseModel):
    scenario: str
    detail: str = ""

class ActiveCompanyInput(BaseModel):
    company_id: str

class CheckoutRequest(BaseModel):
    lookup_key: str
    origin_url: str

class OriginRequest(BaseModel):
    origin_url: str = ""

class ContactInput(BaseModel):
    name: str
    email: EmailStr
    message: str

class DecisionActInput(BaseModel):
    key: str
    title: str = ""
    status: str  # done | snoozed
