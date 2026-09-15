from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserBase(BaseModel):
    username: str
    role: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class VendorBase(BaseModel):
    vendor_id: str
    name: str
    category: str
    country: str
    risk_tier: str

class Vendor(VendorBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
    
class InvoiceBase(BaseModel):
    invoice_id: str
    vendor_id: int
    po_id: Optional[int]
    amount: float
    invoice_date: datetime
    due_date: datetime
    status: str
    
class Invoice(InvoiceBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
