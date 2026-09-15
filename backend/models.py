from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, JSON, Text
from sqlalchemy.orm import relationship
from .database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String) # Admin, Procurement Manager, Finance, Auditor
    is_active = Column(Boolean, default=True)

class Vendor(Base):
    __tablename__ = "vendors"
    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(String, unique=True, index=True)
    name = Column(String)
    risk_tier = Column(String) # High, Medium, Low
    category = Column(String)
    country = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    invoices = relationship("Invoice", back_populates="vendor")
    purchase_orders = relationship("PurchaseOrder", back_populates="vendor")
    contracts = relationship("Contract", back_populates="vendor")
    risk_scores = relationship("RiskScore", back_populates="vendor")

class Contract(Base):
    __tablename__ = "contracts"
    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(String, unique=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    item_category = Column(String)
    negotiated_rate = Column(Float)
    valid_from = Column(DateTime)
    valid_to = Column(DateTime)

    vendor = relationship("Vendor", back_populates="contracts")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id = Column(Integer, primary_key=True, index=True)
    po_id = Column(String, unique=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    amount = Column(Float)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_split = Column(Boolean, default=False)
    
    vendor = relationship("Vendor", back_populates="purchase_orders")
    invoices = relationship("Invoice", back_populates="purchase_order")

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(String, unique=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
    amount = Column(Float)
    invoice_date = Column(DateTime)
    due_date = Column(DateTime)
    status = Column(String) # Pending, Paid, Flagged
    
    vendor = relationship("Vendor", back_populates="invoices")
    purchase_order = relationship("PurchaseOrder", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice")
    recommendations = relationship("Recommendation", back_populates="invoice")
    agent_traces = relationship("AgentTrace", back_populates="invoice")

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String, unique=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    amount_paid = Column(Float)
    payment_date = Column(DateTime)
    discount_taken = Column(Float, default=0.0)
    
    invoice = relationship("Invoice", back_populates="payments")

class RiskScore(Base):
    __tablename__ = "risk_scores"
    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    score = Column(Float)
    factors = Column(JSON) # e.g., {"late_deliveries": 0.5, "price_variance": 0.3}
    calculated_at = Column(DateTime, default=datetime.datetime.utcnow)

    vendor = relationship("Vendor", back_populates="risk_scores")

class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    ml_flag = Column(String)
    confidence = Column(Float)
    suggested_action = Column(String) # Reject Invoice, Escalate, etc.
    justification = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="Pending Review")

    invoice = relationship("Invoice", back_populates="recommendations")

class AgentTrace(Base):
    __tablename__ = "agent_traces"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    agent_name = Column(String) # Analyst, Investigation, Recommendation
    input_data = Column(JSON)
    output_data = Column(JSON)
    reasoning = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    invoice = relationship("Invoice", back_populates="agent_traces")
