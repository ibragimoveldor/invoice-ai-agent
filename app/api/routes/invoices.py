# app/api/routes/invoices.py
"""
Invoice processing endpoints
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from pathlib import Path
import shutil
import uuid

from app.database import get_db
from app.database.crud import create_invoice, get_invoice, get_invoices, get_invoice_stats
from app.agents.graph import invoice_graph
from app.config import settings
from pydantic import BaseModel

from app.core.vector_store import get_rag

router = APIRouter(prefix="/invoices", tags=["invoices"])

# ==================== PYDANTIC MODELS ====================

class LineItemResponse(BaseModel):
    description: str
    quantity: float
    unit_price: float
    total_price: float
    category: str

class InvoiceResponse(BaseModel):
    invoice_id: str
    vendor_name: str
    invoice_number: str
    amount: float
    currency: str
    due_date: Optional[str]
    invoice_date: Optional[str]
    priority_score: float
    urgency: str
    analysis: str
    payment_strategy: str
    recommendations: List[str]
    line_items: List[LineItemResponse]
    file_url: str

class InvoiceListItem(BaseModel):
    invoice_id: str
    vendor_name: str
    invoice_number: str
    amount: float
    priority_score: float
    urgency: str
    created_at: str

class StatsResponse(BaseModel):
    total_invoices: int
    total_amount: float
    urgent_count: int
    high_priority_count: int
    average_amount: float

# ==================== ENDPOINTS ====================

@router.post("/analyze", response_model=InvoiceResponse)
async def analyze_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Analyze invoice document
    
    Workflow:
    1. Upload file
    2. Extract data (Claude Vision)
    3. Calculate priority
    4. AI analysis
    5. Save to database
    6. Return results
    """
    print("\n" + "="*60)
    print("📄 Invoice Analysis Request")
    print("="*60)
    
    # Validate file type
    if not file.content_type:
        raise HTTPException(400, "Could not determine file type")
    
    allowed_types = [
        'application/pdf',
        'image/jpeg',
        'image/jpg', 
        'image/png',
        'image/webp'
    ]
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            400, 
            f"Unsupported file type: {file.content_type}. Allowed: PDF, JPEG, PNG"
        )
    
    try:
        # Save uploaded file
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix or '.pdf'
        filename = f"{file_id}{file_ext}"
        file_path = upload_dir / filename
        
        print(f"💾 Saving file: {filename}")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Run LangGraph workflow
        print("\n🤖 Running LangGraph workflow...")
        
        result = invoice_graph.invoke({
            "file_path": str(file_path),
            "vendor_name": "",
            "invoice_number": "",
            "amount": 0.0,
            "due_date": None,
            "invoice_date": None,
            "line_items": [],
            "priority_score": 0.0,
            "urgency": "",
            "analysis": "",
            "payment_strategy": "",
            "recommendations": [],
            "error": ""
        })
        
        # Check for errors
        if result.get('error'):
            raise HTTPException(500, f"Processing failed: {result['error']}")
        
        print("\n💾 Saving to database...")
        
        invoice = create_invoice(
            db=db,
            vendor_name=result['vendor_name'],
            invoice_number=result['invoice_number'],
            amount=result['amount'],
            priority_score=result['priority_score'],
            urgency=result['urgency'],
            analysis=result['analysis'],
            payment_strategy=result['payment_strategy'],
            file_path=str(file_path),
            due_date=result.get('due_date'),
            invoice_date=result.get('invoice_date'),
            line_items=result.get('line_items', [])
        )
        
        print(f"✅ Saved to database: {invoice.invoice_id}")
        
        # ===== ADD TO RAG =====
        print("🔍 Adding to RAG vector store...")
        try:
            rag = get_rag()
            rag.add_invoice(
                invoice_id=invoice.invoice_id,
                vendor_name=invoice.vendor_name,
                amount=invoice.amount,
                priority_score=invoice.priority_score,
                urgency=invoice.urgency,
                analysis=invoice.analysis,
                payment_strategy=invoice.payment_strategy
            )
        except Exception as e:
            print(f"⚠️ RAG indexing failed (non-critical): {e}")
        # Build response
        recommendations = result.get('recommendations', [])
        if isinstance(recommendations, str):
            recommendations = [recommendations]
        
        response = InvoiceResponse(
            invoice_id=invoice.invoice_id,
            vendor_name=invoice.vendor_name,
            invoice_number=invoice.invoice_number,
            amount=invoice.amount,
            currency=invoice.currency,
            due_date=invoice.due_date.isoformat() if invoice.due_date else None,
            invoice_date=invoice.invoice_date.isoformat() if invoice.invoice_date else None,
            priority_score=invoice.priority_score,
            urgency=invoice.urgency,
            analysis=invoice.analysis,
            payment_strategy=invoice.payment_strategy,
            recommendations=recommendations,
            line_items=[
                LineItemResponse(
                    description=item.description or '',
                    quantity=item.quantity or 0,
                    unit_price=item.unit_price or 0,
                    total_price=item.total_price or 0,
                    category=item.category or 'other'
                )
                for item in invoice.line_items
            ],
            file_url=f"/api/v1/invoices/files/{filename}"
        )
        
        print("="*60)
        print("✅ Analysis Complete\n")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice_by_id(
    invoice_id: str,
    db: Session = Depends(get_db)
):
    """Get invoice by ID"""
    invoice = get_invoice(db, invoice_id)
    
    if not invoice:
        raise HTTPException(404, f"Invoice not found: {invoice_id}")
    
    # Parse recommendations
    recommendations = []
    if invoice.payment_strategy:
        recommendations = [invoice.payment_strategy]
    
    return InvoiceResponse(
        invoice_id=invoice.invoice_id,
        vendor_name=invoice.vendor_name,
        invoice_number=invoice.invoice_number,
        amount=invoice.amount,
        currency=invoice.currency,
        due_date=invoice.due_date.isoformat() if invoice.due_date else None,
        invoice_date=invoice.invoice_date.isoformat() if invoice.invoice_date else None,
        priority_score=invoice.priority_score,
        urgency=invoice.urgency,
        analysis=invoice.analysis or '',
        payment_strategy=invoice.payment_strategy or '',
        recommendations=recommendations,
        line_items=[
            LineItemResponse(
                description=item.description or '',
                quantity=item.quantity or 0,
                unit_price=item.unit_price or 0,
                total_price=item.total_price or 0,
                category=item.category or 'other'
            )
            for item in invoice.line_items
        ],
        file_url=f"/api/v1/invoices/files/{Path(invoice.file_path).name}"
    )


@router.get("/", response_model=List[InvoiceListItem])
async def list_invoices(
    skip: int = 0,
    limit: int = 20,
    urgency: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all invoices"""
    invoices = get_invoices(db, skip=skip, limit=limit, urgency=urgency)
    
    return [
        InvoiceListItem(
            invoice_id=inv.invoice_id,
            vendor_name=inv.vendor_name,
            invoice_number=inv.invoice_number,
            amount=inv.amount,
            priority_score=inv.priority_score,
            urgency=inv.urgency,
            created_at=inv.created_at.isoformat()
        )
        for inv in invoices
    ]


@router.get("/stats/summary", response_model=StatsResponse)
async def get_statistics(db: Session = Depends(get_db)):
    """Get invoice statistics"""
    stats = get_invoice_stats(db)
    
    return StatsResponse(**stats)


@router.get("/files/{filename}")
async def get_invoice_file(filename: str):
    """Serve invoice file"""
    file_path = Path(settings.upload_dir) / filename
    
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    
    return FileResponse(file_path)