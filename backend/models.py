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
    profile: Dict[str, Any] = {}

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
    email_value_alert: Optional[bool] = None
    tour_completed: Optional[bool] = None

class ChatInput(BaseModel):
    session_id: Optional[str] = None
    message: str = ""
    attachment_ids: Optional[List[str]] = None

class PushSubscriptionInput(BaseModel):
    endpoint: str
    keys: dict

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

class AdminNoteInput(BaseModel):
    note: str

class CampaignToggleInput(BaseModel):
    active: bool

class AdminUserUpdateInput(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_premium: Optional[bool] = None

class ResetPasswordInput(BaseModel):
    token: str
    password: str

class CostItem(BaseModel):
    name: str = "Custo"
    amount: float = 0

class FinancialProfileInput(BaseModel):
    monthly_revenue: float = 0
    fixed_costs: List[CostItem] = []
    variable_costs_pct: float = 0
    cash_balance: float = 0
    total_debt: float = 0
    assets: List[CostItem] = []
    liabilities: List[CostItem] = []

class GoalInput(BaseModel):
    target_value: Optional[float] = None
    target_revenue: Optional[float] = None
    deadline_type: Optional[str] = None      # "years" | "date"
    deadline_years: Optional[float] = None
    deadline_date: Optional[str] = None       # ISO date "YYYY-MM-DD" ou "YYYY-MM"
    ytd_revenue: Optional[float] = None
    ytd_as_of: Optional[str] = None           # data a que se refere a faturação YTD
    valuation_method: Optional[str] = None    # "auto" | "revenue" | "ebitda"
    value_multiple_custom: Optional[float] = None  # múltiplo ajustado manualmente pelo utilizador
