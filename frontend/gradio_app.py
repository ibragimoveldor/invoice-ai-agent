# frontend/gradio_app.py
"""
Gradio Frontend for Invoice Intelligence Agent
"""
import gradio as gr
import requests
from PIL import Image
import io
import os
from datetime import datetime

# API Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")

# ==================== HELPER FUNCTIONS ====================

def format_currency(amount: float) -> str:
    """Format amount as currency"""
    return f"${amount:,.2f}"

def get_urgency_emoji(urgency: str) -> str:
    """Get emoji for urgency level"""
    emojis = {
        'urgent': '🔴',
        'high': '🟠',
        'medium': '🟡',
        'low': '🟢'
    }
    return emojis.get(urgency.lower(), '⚪')

# ==================== MAIN FUNCTIONS ====================

def analyze_invoice(pdf_file):
    """
    Analyze uploaded invoice
    
    Returns: (invoice_id, results_markdown, chat_history, logs)
    """
    if pdf_file is None:
        return None, "⚠️ Please upload an invoice first.", [], "No file uploaded"
    
    logs = f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Starting analysis...\n"
    
    try:
        logs += f"[{datetime.now().strftime('%H:%M:%S')}] 📤 Uploading to API...\n"
        
        # Upload file
        with open(pdf_file.name, 'rb') as f:
            files = {"file": (os.path.basename(pdf_file.name), f, "application/pdf")}
            
            logs += f"[{datetime.now().strftime('%H:%M:%S')}] 🔗 POST {API_URL}/invoices/analyze\n"
            
            response = requests.post(f"{API_URL}/invoices/analyze", files=files)
        
        if response.status_code != 200:
            logs += f"[{datetime.now().strftime('%H:%M:%S')}] ❌ API Error: {response.status_code}\n"
            return None, f"❌ Error: {response.text}", [], logs
        
        logs += f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Response received\n"
        
        result = response.json()
        
        logs += f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Extraction: {result['vendor_name']}\n"
        logs += f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Priority: {result['priority_score']}/100\n"
        logs += f"[{datetime.now().strftime('%H:%M:%S')}] 🤖 AI Analysis complete\n"
        logs += f"[{datetime.now().strftime('%H:%M:%S')}] 💾 Saved to database\n"
        
        invoice_id = result['invoice_id']
        
        # Format results
        urgency_emoji = get_urgency_emoji(result['urgency'])
        
        results_md = f"""
# 📊 Invoice Analysis Results

## Invoice Details
- **Vendor:** {result['vendor_name']}
- **Invoice Number:** {result['invoice_number']}
- **Amount:** {format_currency(result['amount'])} {result['currency']}
- **Due Date:** {result['due_date'] or 'Not specified'}

## Priority Assessment
- **Priority Score:** {result['priority_score']}/100
- **Urgency:** {urgency_emoji} **{result['urgency'].upper()}**

## 🤖 AI Analysis
{result['analysis']}

## 💡 Payment Strategy
{result['payment_strategy']}

## 📋 Recommendations
"""
        for i, rec in enumerate(result.get('recommendations', []), 1):
            results_md += f"{i}. {rec}\n"
        
        # Add line items if available
        if result.get('line_items'):
            results_md += "\n## 📦 Line Items\n\n"
            results_md += "| Description | Quantity | Unit Price | Total | Category |\n"
            results_md += "|-------------|----------|------------|-------|----------|\n"
            
            for item in result['line_items']:
                results_md += f"| {item['description'][:30]} | {item['quantity']} | {format_currency(item['unit_price'])} | {format_currency(item['total_price'])} | {item['category']} |\n"
        
        # Initialize chat
        chat_history = [
            {
                "role": "assistant", 
                "content": f"✅ Invoice analyzed! Priority: {result['urgency'].upper()} ({result['priority_score']}/100). Ask me anything!"
            }
        ]
        
        logs += f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Analysis complete!\n"
        logs += f"[{datetime.now().strftime('%H:%M:%S')}] Invoice ID: {invoice_id}\n"
        
        return invoice_id, results_md, chat_history, logs
        
    except Exception as e:
        logs += f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error: {str(e)}\n"
        return None, f"❌ Error: {str(e)}", [], logs

def chat_with_invoice(message, chat_history, invoice_id_state, session_id_state, current_logs):
    """Chat about the invoice"""
    
    logs = current_logs + f"\n[{datetime.now().strftime('%H:%M:%S')}] 💬 User: {message}\n"
    
    if not message.strip():
        return "", chat_history, session_id_state, logs
    
    try:
        # Add user message
        chat_history.append({"role": "user", "content": message})
        
        logs += f"[{datetime.now().strftime('%H:%M:%S')}] 🔗 POST {API_URL}/chat\n"
        
        # Call chat API
        payload = {
            "invoice_id": invoice_id_state,
            "question": message,
            "session_id": session_id_state
        }
        
        response = requests.post(f"{API_URL}/chat", json=payload)
        
        if response.status_code != 200:
            logs += f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Chat error\n"
            chat_history.append({
                "role": "assistant",
                "content": f"❌ Error: {response.text}"
            })
            return "", chat_history, session_id_state, logs
        
        result = response.json()
        
        logs += f"[{datetime.now().strftime('%H:%M:%S')}] 🤖 LangGraph processing...\n"
        
        if result.get('sql_query'):
            logs += f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 SQL: {result['sql_query']}\n"
        
        logs += f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Response generated\n"
        
        # Add assistant response
        chat_history.append({
            "role": "assistant",
            "content": result['response']
        })
        
        # Update session ID
        session_id = result['session_id']
        
        return "", chat_history, session_id, logs
        
    except Exception as e:
        logs += f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error: {str(e)}\n"
        chat_history.append({
            "role": "assistant",
            "content": f"❌ Error: {str(e)}"
        })
        return "", chat_history, session_id_state, logs

def clear_chat():
    """Clear chat history"""
    return [], None

def get_stats():
    """Get invoice statistics"""
    try:
        response = requests.get(f"{API_URL}/invoices/stats/summary")
        
        if response.status_code != 200:
            return "❌ Could not load statistics"
        
        stats = response.json()
        
        stats_md = f"""
## 📊 Invoice Statistics

- **Total Invoices:** {stats['total_invoices']}
- **Total Amount:** {format_currency(stats['total_amount'])}
- **Average Amount:** {format_currency(stats['average_amount'])}
- **Urgent:** 🔴 {stats['urgent_count']}
- **High Priority:** 🟠 {stats['high_priority_count']}
"""
        return stats_md
        
    except:
        return "Statistics unavailable"

# ==================== GRADIO INTERFACE ====================

with gr.Blocks(title="Invoice Intelligence Agent") as demo:
    
    gr.Markdown("""
    # 💰 Invoice Intelligence Agent
    ### AI-powered invoice processing and payment optimization
    
    Upload an invoice to get instant priority scoring, payment strategy, and conversational Q&A.
    """)
    
    # State variables
    invoice_id_state = gr.State(None)
    session_id_state = gr.State(None)
    logs_state = gr.State("")
    
    with gr.Row():
        # Left Column - Analysis
        with gr.Column(scale=2):
            gr.Markdown("### 📤 Upload Invoice")
            
            file_input = gr.File(
                label="Invoice Document (PDF, JPEG, PNG)",
                file_types=[".pdf", ".jpg", ".jpeg", ".png"],
                type="filepath"
            )
            
            analyze_btn = gr.Button(
                "🔍 Analyze Invoice",
                variant="primary",
                size="lg"
            )
            
            gr.Markdown("### 📊 Analysis Results")
            
            results_output = gr.Markdown(
                value="Upload an invoice and click 'Analyze Invoice' to get started."
            )
        
        # Right Column - Chat
        with gr.Column(scale=1):
            gr.Markdown("### 💬 Chat Assistant")
            
            chatbot = gr.Chatbot(
                label="AI Assistant",
                height=400
                #type="messages"
            )
            
            with gr.Row():
                msg_input = gr.Textbox(
                    placeholder="Ask about payment strategy, costs, timing...",
                    label="Question",
                    scale=4,
                    lines=1
                )
                send_btn = gr.Button("Send", scale=1, variant="primary")
            
            clear_btn = gr.Button("Clear Chat", size="sm")
            
            gr.Markdown("### 💡 Quick Questions")
            
            with gr.Column():
                q1 = gr.Button("💵 What's the payment amount?", size="sm")
                q2 = gr.Button("⏰ When is this due?", size="sm")
                q3 = gr.Button("🎯 What's the recommended strategy?", size="sm")
                q4 = gr.Button("📊 Show invoice statistics", size="sm")
            
            # Collapsible Logs
            with gr.Accordion("📋 Agent Workflow Logs", open=False):
                logs_output = gr.Textbox(
                    label="",
                    value="No logs yet. Analyze an invoice to see workflow.",
                    lines=12,
                    max_lines=20,
                    show_label=False,
                    interactive=False
                )
    
    gr.Markdown("---")
    gr.Markdown("**Tech Stack:** AWS Bedrock (Claude 3.5) | LangGraph | FastAPI | Custom Vision Extraction")
    
    # ==================== EVENT HANDLERS ====================
    
    # Analyze invoice
    analyze_btn.click(
        fn=analyze_invoice,
        inputs=[file_input],
        outputs=[invoice_id_state, results_output, chatbot, logs_output]
    )
    
    # Send chat message
    send_btn.click(
        fn=chat_with_invoice,
        inputs=[msg_input, chatbot, invoice_id_state, session_id_state, logs_output],
        outputs=[msg_input, chatbot, session_id_state, logs_output]
    )
    
    msg_input.submit(
        fn=chat_with_invoice,
        inputs=[msg_input, chatbot, invoice_id_state, session_id_state, logs_output],
        outputs=[msg_input, chatbot, session_id_state, logs_output]
    )
    
    # Clear chat
    clear_btn.click(
        fn=clear_chat,
        outputs=[chatbot, session_id_state]
    )
    
    # Quick questions
    q1.click(lambda: "What's the payment amount?", outputs=[msg_input])
    q2.click(lambda: "When is this invoice due?", outputs=[msg_input])
    q3.click(lambda: "What's the recommended payment strategy?", outputs=[msg_input])
    q4.click(lambda: "Show me invoice statistics", outputs=[msg_input])

# ==================== LAUNCH ====================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 Invoice Intelligence Agent - Gradio Frontend")
    print("="*60)
    print(f"API: {API_URL}")
    print("="*60 + "\n")
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )