# app/database/crud.py
"""
Database CRUD operations
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid

from app.database.models import Invoice, LineItem, ChatMessage, VendorHistory

# ==================== INVOICE OPERATIONS ====================

def create_invoice(
    db: Session,
    vendor_name: str,
    invoice_number: str,
    amount: float,
    priority_score: float,
    urgency: str,
    analysis: str,
    payment_strategy: str,
    file_path: str,
    due_date: Optional[datetime] = None,
    invoice_date: Optional[datetime] = None,
    line_items: Optional[List[dict]] = None
) -> Invoice:
    """Create new invoice record"""
    
    # Generate unique invoice ID
    invoice_id = str(uuid.uuid4())
    
    # Create invoice
    invoice = Invoice(
        invoice_id=invoice_id,
        vendor_name=vendor_name,
        invoice_number=invoice_number,
        amount=amount,
        due_date=due_date,
        invoice_date=invoice_date,
        priority_score=priority_score,
        urgency=urgency,
        analysis=analysis,
        payment_strategy=payment_strategy,
        file_path=file_path
    )
    
    db.add(invoice)
    db.flush()  # Get invoice.id
    
    # Add line items if provided
    if line_items:
        for item in line_items:
            line_item = LineItem(
                invoice_id=invoice.id,
                description=item.get('description'),
                quantity=item.get('quantity'),
                unit_price=item.get('unit_price'),
                total_price=item.get('total_price'),
                category=item.get('category')
            )
            db.add(line_item)
    
    db.commit()
    db.refresh(invoice)
    
    return invoice


def get_invoice(db: Session, invoice_id: str) -> Optional[Invoice]:
    """Get invoice by ID"""
    return db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()


def get_invoices(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    urgency: Optional[str] = None
) -> List[Invoice]:
    """Get list of invoices"""
    query = db.query(Invoice)
    
    if urgency:
        query = query.filter(Invoice.urgency == urgency)
    
    return query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()


def get_invoices_by_vendor(db: Session, vendor_name: str) -> List[Invoice]:
    """Get all invoices from a specific vendor"""
    return db.query(Invoice).filter(Invoice.vendor_name == vendor_name).all()


# ==================== CHAT OPERATIONS ====================

def create_chat_message(
    db: Session,
    invoice_id: Optional[int],
    session_id: str,
    role: str,
    content: str,
    tokens_used: Optional[int] = None,
    cost: Optional[float] = None
) -> ChatMessage:
    """Create chat message"""
    message = ChatMessage(
        invoice_id=invoice_id,
        session_id=session_id,
        role=role,
        content=content,
        tokens_used=tokens_used,
        cost=cost
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    return message


def get_chat_history(
    db: Session,
    session_id: str,
    limit: int = 50
) -> List[ChatMessage]:
    """Get chat history for a session"""
    return db.query(ChatMessage)\
        .filter(ChatMessage.session_id == session_id)\
        .order_by(ChatMessage.created_at.asc())\
        .limit(limit)\
        .all()


# ==================== VENDOR OPERATIONS ====================

def get_or_create_vendor_history(
    db: Session,
    vendor_name: str
) -> VendorHistory:
    """Get or create vendor history record"""
    vendor = db.query(VendorHistory).filter(VendorHistory.vendor_name == vendor_name).first()
    
    if not vendor:
        vendor = VendorHistory(vendor_name=vendor_name)
        db.add(vendor)
        db.commit()
        db.refresh(vendor)
    
    return vendor


def update_vendor_history(
    db: Session,
    vendor_name: str,
    invoice_amount: float,
    invoice_date: datetime
) -> VendorHistory:
    """Update vendor history with new invoice"""
    vendor = get_or_create_vendor_history(db, vendor_name)
    
    # Update metrics
    vendor.total_invoices += 1
    vendor.total_amount_paid += invoice_amount
    vendor.last_invoice_date = invoice_date
    vendor.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(vendor)
    
    return vendor


# ==================== ANALYTICS ====================

def get_invoice_stats(db: Session) -> dict:
    """Get invoice statistics"""
    from sqlalchemy import func
    
    total = db.query(func.count(Invoice.id)).scalar()
    total_amount = db.query(func.sum(Invoice.amount)).scalar() or 0
    
    urgent = db.query(func.count(Invoice.id))\
        .filter(Invoice.urgency == 'urgent').scalar()
    
    high = db.query(func.count(Invoice.id))\
        .filter(Invoice.urgency == 'high').scalar()
    
    return {
        'total_invoices': total,
        'total_amount': total_amount,
        'urgent_count': urgent,
        'high_priority_count': high,
        'average_amount': total_amount / total if total > 0 else 0
    }