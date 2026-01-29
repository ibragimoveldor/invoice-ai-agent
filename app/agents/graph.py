# app/agents/graph.py
"""
LangGraph workflows for invoice processing
"""
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from datetime import datetime

from app.models.invoice_extractor import InvoiceExtractor
from app.models.payment_calculator import calculate_priority_score
from app.core.aws_bedrock import get_bedrock_client
from app.database.crud import get_or_create_vendor_history

from app.core.vector_store import get_rag

# ==================== STATE DEFINITIONS ====================

class InvoiceState(TypedDict):
    """State for invoice processing workflow"""
    # Input
    file_path: str
    
    # Extraction results
    vendor_name: str
    invoice_number: str
    amount: float
    due_date: Optional[datetime]
    invoice_date: Optional[datetime]
    line_items: List[dict]
    
    # Priority calculation
    priority_score: float
    urgency: str
    
    # AI analysis
    analysis: str
    payment_strategy: str
    recommendations: List[str]
    
    # Error handling
    error: str


class ChatState(TypedDict):
    """State for chat workflow"""
    # Input
    user_question: str
    invoice_context: dict
    chat_history: List[dict]
    
    # SQL handling
    needs_sql_query: bool
    sql_query: str
    sql_results: str
    
    # Output
    response: str
    error: str


# ==================== INVOICE PROCESSING NODES ====================

def extract_invoice_data(state: InvoiceState) -> InvoiceState:
    """Node 1: Extract data from invoice file"""
    print("🔍 Step 1: Extracting invoice data...")
    
    try:
        extractor = InvoiceExtractor()
        data = extractor.extract(state['file_path'])
        
        # Update state
        state['vendor_name'] = data['vendor_name']
        state['invoice_number'] = data['invoice_number']
        state['amount'] = data['amount']
        state['due_date'] = data.get('due_date')
        state['invoice_date'] = data.get('invoice_date')
        state['line_items'] = data['line_items']
        
        print(f"   ✅ Extracted: {data['vendor_name']} - ${data['amount']:,.2f}")
        
    except Exception as e:
        print(f"   ❌ Extraction failed: {e}")
        state['error'] = str(e)
    
    return state


def calculate_payment_priority(state: InvoiceState) -> InvoiceState:
    """Node 2: Calculate payment priority score"""
    print("📊 Step 2: Calculating priority...")
    
    if state.get('error'):
        return state  # Skip if previous error
    
    try:
        # Calculate priority
        priority = calculate_priority_score(
            amount=state['amount'],
            due_date=state.get('due_date'),
            has_discount=False,  # TODO: Extract from invoice
            discount_percentage=0.0
        )
        
        state['priority_score'] = priority['priority_score']
        state['urgency'] = priority['urgency']
        
        print(f"   ✅ Priority: {priority['priority_score']}/100 ({priority['urgency']})")
        
    except Exception as e:
        print(f"   ❌ Priority calculation failed: {e}")
        state['error'] = str(e)
    
    return state



def analyze_with_ai(state: InvoiceState) -> InvoiceState:
    """Node 3: AI analysis and strategy"""
    print("🤖 Step 3: AI analysis with RAG context...")
    
    if state.get('error'):
        return state  # Skip if previous error
    
    try:
        bedrock = get_bedrock_client()
        rag = get_rag()
        
        # ===== RAG: Retrieve similar invoices =====
        print("   🔍 Retrieving similar invoices from RAG...")
        
        # Build query for similar invoices
        rag_query = f"Invoice from {state['vendor_name']} for ${state['amount']:,.2f}"
        
        similar_invoices = rag.retrieve_similar_invoices(
            query=rag_query,
            n_results=3
        )
        
        # Get vendor history
        vendor_history_rag = rag.get_vendor_history(state['vendor_name'])
        
        # Build vendor history context
        vendor_history = {
            'total_invoices': len(vendor_history_rag),
            'average_amount': sum(v['amount'] for v in vendor_history_rag) / len(vendor_history_rag) if vendor_history_rag else 0,
            'on_time_rate': 95,  # Mock for now
            'is_critical': 'important' if len(vendor_history_rag) > 5 else 'standard'
        }
        
        # Add RAG context to analysis
        rag_context = ""
        if similar_invoices['documents']:
            rag_context = "\n\nSimilar Past Invoices:\n"
            for i, (doc, meta) in enumerate(zip(similar_invoices['documents'], similar_invoices['metadatas']), 1):
                rag_context += f"\n{i}. {meta['vendor_name']} - ${meta['amount']:,.2f} ({meta['urgency']})\n"
        
        print(f"   📊 Found {len(vendor_history_rag)} past invoices from this vendor")
        print(f"   🔍 Retrieved {len(similar_invoices['documents'])} similar invoices")
        
        # Analyze with RAG context
        analysis = bedrock.analyze_invoice(
            vendor_name=state['vendor_name'],
            amount=state['amount'],
            due_date=state['due_date'].isoformat() if state.get('due_date') else 'Not specified',
            priority_score=state['priority_score'],
            vendor_history=vendor_history,
            rag_context=rag_context  # Pass RAG context
        )
        
        state['analysis'] = analysis['analysis']
        state['payment_strategy'] = analysis['payment_strategy']
        state['recommendations'] = analysis['recommendations']
        
        print(f"   ✅ Analysis complete with RAG enrichment")
        
    except Exception as e:
        print(f"   ❌ AI analysis failed: {e}")
        # Fallback to rule-based
        state['analysis'] = f"Invoice from {state['vendor_name']} for ${state['amount']:,.2f}"
        state['payment_strategy'] = "Review and process according to standard terms"
        state['recommendations'] = ["Verify invoice details", "Check budget availability"]
    
    return state

# ==================== BUILD INVOICE GRAPH ====================

def create_invoice_graph():
    """Create invoice processing workflow"""
    workflow = StateGraph(InvoiceState)
    
    # Add nodes
    workflow.add_node("extract", extract_invoice_data)
    workflow.add_node("calculate_priority", calculate_payment_priority)
    workflow.add_node("analyze", analyze_with_ai)
    
    # Define edges
    workflow.set_entry_point("extract")
    workflow.add_edge("extract", "calculate_priority")
    workflow.add_edge("calculate_priority", "analyze")
    workflow.add_edge("analyze", END)
    
    return workflow.compile()


# ==================== CHAT WORKFLOW NODES ====================

def detect_sql_intent(state: ChatState) -> ChatState:
    """Detect if question needs SQL query"""
    question = state['user_question'].lower()
    
    # Keywords that indicate SQL need
    sql_keywords = ['show', 'list', 'find', 'count', 'filter', 'all', 'get']
    
    state['needs_sql_query'] = any(kw in question for kw in sql_keywords)
    
    return state


def generate_sql_query(state: ChatState) -> ChatState:
    """Generate SQL query from question"""
    if not state['needs_sql_query']:
        return state
    
    print("🔍 Generating SQL query...")
    
    try:
        bedrock = get_bedrock_client()
        
        schema = """
Available tables:
- invoices: id, vendor_name, invoice_number, amount, due_date, priority_score, urgency
- line_items: id, invoice_id, description, quantity, unit_price, total_price, category
"""
        
        messages = [{
            "role": "user",
            "content": f"""Given this database schema:
{schema}

Generate a SQL query for: {state['user_question']}

Return ONLY the SQL query, no explanation."""
        }]
        
        response = bedrock.invoke(messages, max_tokens=512)
        sql = response['content'].strip()
        
        # Clean SQL
        if sql.startswith('```'):
            sql = sql.split('\n', 1)[1].rsplit('\n', 1)[0]
        
        state['sql_query'] = sql
        print(f"   SQL: {sql}")
        
    except Exception as e:
        print(f"   ❌ SQL generation failed: {e}")
        state['error'] = str(e)
    
    return state

def execute_sql_query(state: ChatState) -> ChatState:
    """Execute SQL query safely and format results"""
    
    if not state.get('needs_sql_query'):
        return state
    
    sql = state.get('sql_query', '').strip()
    
    if not sql:
        return state
    
    print("   📊 Executing SQL query...")
    
    try:
        # Safety check - only SELECT allowed
        if not sql.upper().startswith('SELECT'):
            state['sql_results'] = "⚠️ Only SELECT queries are allowed for safety"
            return state
        
        # Execute query
        from app.database import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        try:
            result = db.execute(text(sql))
            rows = result.fetchall()
            
            # Format results as markdown table
            if rows:
                # Get column names
                columns = result.keys()
                
                # Build markdown table
                table = "| " + " | ".join(columns) + " |\n"
                table += "|" + "|".join(["---" for _ in columns]) + "|\n"
                
                # Add rows (limit to 20 for display)
                for row in rows[:20]:
                    formatted_row = []
                    for val in row:
                        if val is None:
                            formatted_row.append("NULL")
                        elif isinstance(val, float):
                            formatted_row.append(f"{val:,.2f}")
                        else:
                            formatted_row.append(str(val))
                    table += "| " + " | ".join(formatted_row) + " |\n"
                
                if len(rows) > 20:
                    table += f"\n*(Showing first 20 of {len(rows)} results)*"
                
                state['sql_results'] = table
                print(f"   ✅ Query returned {len(rows)} rows")
            else:
                # ← IMPROVED: Better handling of no results
                state['sql_results'] = "ℹ️ Query executed successfully but returned no results."
                print("   ℹ️ Query returned no results")
                
        finally:
            db.close()
            
    except Exception as e:
        # ← IMPROVED: Better error messages
        error_msg = f"Error executing query: {str(e)}"
        print(f"   ❌ {error_msg}")
        state['sql_results'] = f"⚠️ {error_msg}\n\nNote: Available urgency values are 'urgent', 'high', 'medium', 'low'"
        # Don't set state['error'] - let Claude handle it gracefully
    
    return state

# In answer_question function in chat workflow:

def answer_question(state: ChatState) -> ChatState:
    """Generate final answer with RAG context"""
    print("💬 Generating answer with RAG...")
    
    try:
        bedrock = get_bedrock_client()
        rag = get_rag()
        
        context = state['invoice_context']
        
        # ===== RAG: Retrieve relevant context =====
        if state['user_question']:
            similar = rag.retrieve_similar_invoices(
                query=state['user_question'],
                n_results=2
            )
            
            if similar['documents']:
                context['similar_cases'] = [
                    {
                        'vendor': meta['vendor_name'],
                        'amount': meta['amount'],
                        'urgency': meta['urgency']
                    }
                    for meta in similar['metadatas']
                ]
        
        if state.get('sql_results'):
            context['query_results'] = state['sql_results']
        
        response = bedrock.answer_question(
            question=state['user_question'],
            context=context,
            chat_history=state.get('chat_history')
        )
        
        state['response'] = response
        
    except Exception as e:
        print(f"   ❌ Answer generation failed: {e}")
        state['response'] = "I'm sorry, I couldn't process your question. Please try again."
    
    return state


# ==================== BUILD CHAT GRAPH ====================

def create_chat_graph():
    """Create chat workflow with SQL execution"""
    workflow = StateGraph(ChatState)
    
    # Add nodes
    workflow.add_node("detect_intent", detect_sql_intent)
    workflow.add_node("generate_sql", generate_sql_query)
    workflow.add_node("execute_sql", execute_sql_query)  # ← NEW NODE
    workflow.add_node("answer", answer_question)
    
    # Define edges
    workflow.set_entry_point("detect_intent")
    
    # Conditional routing after intent detection
    def route_after_intent(state):
        return "generate_sql" if state['needs_sql_query'] else "answer"
    
    workflow.add_conditional_edges(
        "detect_intent",
        route_after_intent,
        {
            "generate_sql": "generate_sql",
            "answer": "answer"
        }
    )
    
    # After SQL generation, execute it
    workflow.add_edge("generate_sql", "execute_sql")  # ← NEW EDGE
    
    # After execution, answer
    workflow.add_edge("execute_sql", "answer")  # ← NEW EDGE
    
    workflow.add_edge("answer", END)
    
    return workflow.compile()


# ==================== GRAPH INSTANCES ====================

# Create compiled graphs
invoice_graph = create_invoice_graph()
chat_graph = create_chat_graph()