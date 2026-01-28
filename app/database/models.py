# app/database/models.py
"""
SQLAlchemy database models for Invoice Intelligence Agent
"""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class Invoice(Base):
    """Invoice assessment record"""
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(String(50), unique=True, index=True, nullable=False)
    
    # Extracted data
    vendor_name = Column(String(200), nullable=False)
    invoice_number = Column(String(100))
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    due_date = Column(DateTime)
    invoice_date = Column(DateTime)
    
    # Priority scoring
    priority_score = Column(Float, nullable=False)  # 0-100
    urgency = Column(String(20), nullable=False)  # urgent/high/medium/low
    
    # AI analysis
    analysis = Column(Text)
    payment_strategy = Column(Text)
    
    # File references
    file_path = Column(String(500))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    line_items = relationship("LineItem", back_populates="invoice", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="invoice", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Invoice {self.invoice_number} - {self.vendor_name}>"


class LineItem(Base):
    """Invoice line items"""
    __tablename__ = "line_items"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    
    description = Column(String(500))
    quantity = Column(Float)
    unit_price = Column(Float)
    total_price = Column(Float)
    category = Column(String(100))  # software, consulting, utilities, etc.
    
    # Relationship
    invoice = relationship("Invoice", back_populates="line_items")
    
    def __repr__(self):
        return f"<LineItem {self.description[:30]}>"


class ChatMessage(Base):
    """Chat conversation history"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    session_id = Column(String(50), index=True)
    
    role = Column(String(20), nullable=False)  # user or assistant
    content = Column(Text, nullable=False)
    
    # Metadata
    tokens_used = Column(Integer)
    cost = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    invoice = relationship("Invoice", back_populates="chat_messages")
    
    def __repr__(self):
        return f"<ChatMessage {self.role}: {self.content[:30]}>"


class VendorHistory(Base):
    """Vendor relationship tracking (for RAG)"""
    __tablename__ = "vendor_history"
    
    id = Column(Integer, primary_key=True, index=True)
    vendor_name = Column(String(200), index=True, nullable=False)
    
    # Aggregated metrics
    total_invoices = Column(Integer, default=0)
    total_amount_paid = Column(Float, default=0.0)
    average_payment_days = Column(Float)  # Days to pay on average
    on_time_payment_rate = Column(Float)  # Percentage
    
    # Relationship indicators
    is_critical = Column(String(20))  # critical/important/standard
    discount_terms = Column(String(100))  # e.g., "2/10 Net 30"
    
    # Last interaction
    last_invoice_date = Column(DateTime)
    last_payment_date = Column(DateTime)
    
    # Notes
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<VendorHistory {self.vendor_name}>"