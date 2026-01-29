# app/api/routes/chat.py
"""
Chat endpoints for conversational Q&A
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel
import uuid

from app.database import get_db
from app.database.crud import get_invoice, create_chat_message, get_chat_history
from app.agents.graph import chat_graph

router = APIRouter(prefix="/chat", tags=["chat"])

# ==================== PYDANTIC MODELS ====================

class ChatRequest(BaseModel):
    invoice_id: Optional[str] = None
    question: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    response: str
    sql_query: Optional[str] = None

class ChatHistoryItem(BaseModel):
    role: str
    content: str
    created_at: str

# ==================== ENDPOINTS ====================

@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Chat with AI about invoices
    
    Supports:
    - Questions about specific invoice
    - Text-to-SQL queries across all invoices (working!)
    - Follow-up questions in conversation
    """
    print("\n" + "="*60)
    print(f"💬 Chat Request: {request.question}")
    print("="*60)
    
    # Get or create session ID
    session_id = request.session_id or str(uuid.uuid4())
    
    # Build context
    context = {}
    
    if request.invoice_id:
        invoice = get_invoice(db, request.invoice_id)
        if not invoice:
            raise HTTPException(404, f"Invoice not found: {request.invoice_id}")
        
        context = {
            'invoice_id': invoice.invoice_id,
            'vendor': invoice.vendor_name,
            'invoice_number': invoice.invoice_number,
            'amount': invoice.amount,
            'due_date': invoice.due_date.isoformat() if invoice.due_date else None,
            'priority_score': invoice.priority_score,
            'urgency': invoice.urgency,
            'analysis': invoice.analysis,
            'payment_strategy': invoice.payment_strategy
        }
    
    # Get chat history
    history = get_chat_history(db, session_id, limit=10)
    chat_history = [
        {"role": msg.role, "content": msg.content}
        for msg in history
    ]
    
    # Run chat workflow
    try:
        result = chat_graph.invoke({
            "user_question": request.question,
            "invoice_context": context,
            "chat_history": chat_history,
            "needs_sql_query": False,
            "sql_query": "",
            "sql_results": "",
            "response": "",
            "error": ""
        })
        
        if result.get('error') and not result.get('sql_results'):
            raise HTTPException(500, f"Chat failed: {result['error']}")
        
        response_text = result['response']
        sql_query = result.get('sql_query')
        
        # Save messages to database
        create_chat_message(
            db=db,
            invoice_id=invoice.id if request.invoice_id and invoice else None,
            session_id=session_id,
            role="user",
            content=request.question
        )
        
        create_chat_message(
            db=db,
            invoice_id=invoice.id if request.invoice_id and invoice else None,
            session_id=session_id,
            role="assistant",
            content=response_text
        )
        
        print(f"✅ Response generated")
        print("="*60 + "\n")
        
        return ChatResponse(
            session_id=session_id,
            response=response_text,
            sql_query=sql_query if sql_query else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Chat error: {e}")
        raise HTTPException(500, f"Chat failed: {str(e)}")


@router.get("/history/{session_id}", response_model=List[ChatHistoryItem])
async def get_session_history(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get chat history for a session"""
    messages = get_chat_history(db, session_id)
    
    return [
        ChatHistoryItem(
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at.isoformat()
        )
        for msg in messages
    ]