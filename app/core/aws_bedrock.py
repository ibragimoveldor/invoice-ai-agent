# app/core/aws_bedrock.py
"""
AWS Bedrock client for Claude AI
"""
import boto3
import json
from typing import List, Dict, Optional
from app.config import settings

class BedrockClient:
    """AWS Bedrock client wrapper for Claude"""
    
    def __init__(self):
        """Initialize Bedrock client"""
        self.client = boto3.client(
            service_name='bedrock-runtime',
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
        
        # Use inference profile for Claude 3.5 Sonnet
        self.model_id = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        
    def invoke(
        self,
        messages: List[Dict],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0
    ) -> Dict:
        """
        Invoke Claude via Bedrock
        
        Args:
            messages: List of message dicts [{"role": "user", "content": "..."}]
            system: System prompt (optional)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Response dict with content and usage
        """
        # Build request body
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature
        }
        
        if system:
            body["system"] = system
        
        try:
            # Invoke model
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            return {
                'content': response_body['content'][0]['text'],
                'usage': response_body.get('usage', {}),
                'stop_reason': response_body.get('stop_reason')
            }
            
        except Exception as e:
            print(f"❌ Bedrock error: {e}")
            raise
    
    def extract_invoice_data(self, file_content: bytes, file_type: str) -> Dict:
        """
        Extract structured data from invoice using Claude Vision
        
        Args:
            file_content: File bytes (PDF or image)
            file_type: 'application/pdf' or 'image/jpeg' etc.
            
        Returns:
            Extracted invoice data as dict
        """
        import base64
        
        # Encode file to base64
        file_b64 = base64.b64encode(file_content).decode('utf-8')
        
        # Determine source type
        if file_type == 'application/pdf':
            source_type = 'document'
        else:
            source_type = 'image'
        
        # Build message with vision
        messages = [{
            "role": "user",
            "content": [
                {
                    "type": source_type,
                    "source": {
                        "type": "base64",
                        "media_type": file_type,
                        "data": file_b64
                    }
                },
                {
                    "type": "text",
                    "text": """Extract invoice data and return ONLY valid JSON (no markdown, no explanation):

{
  "vendor_name": "Company name",
  "invoice_number": "Invoice number",
  "amount": 0.0,
  "currency": "USD",
  "due_date": "YYYY-MM-DD",
  "invoice_date": "YYYY-MM-DD",
  "line_items": [
    {
      "description": "Item description",
      "quantity": 0,
      "unit_price": 0.0,
      "total_price": 0.0,
      "category": "software/consulting/utilities/office_supplies/other"
    }
  ]
}

Important: Return ONLY the JSON object, no additional text."""
                }
            ]
        }]
        
        try:
            response = self.invoke(messages, max_tokens=2048)
            
            # Parse JSON from response
            content = response['content'].strip()
            
            # Remove markdown code fences if present
            if content.startswith('```'):
                content = content.split('\n', 1)[1]
                content = content.rsplit('\n', 1)[0]
                if content.startswith('json'):
                    content = content[4:].strip()
            
            data = json.loads(content)
            return data
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {e}")
            print(f"Response content: {content}")
            raise ValueError(f"Failed to parse invoice data: {e}")
    
    def analyze_invoice(
        self,
        vendor_name: str,
        amount: float,
        due_date: str,
        priority_score: float,
        vendor_history: Optional[Dict] = None,
        rag_context: str = ""  # ← ADD THIS PARAMETER
    ) -> Dict:
        """
        Generate payment strategy and analysis
        
        Returns:
            {
                'analysis': str,
                'payment_strategy': str,
                'recommendations': List[str]
            }
        """
        # Build context
        context = f"""
    Analyze this invoice and provide payment strategy:

    Invoice Details:
    - Vendor: {vendor_name}
    - Amount: ${amount:,.2f}
    - Due Date: {due_date}
    - Priority Score: {priority_score}/100

    """
        
        if vendor_history:
            context += f"""
    Vendor History:
    - Total invoices: {vendor_history.get('total_invoices', 0)}
    - Average amount: ${vendor_history.get('average_amount', 0):,.2f}
    - On-time payment rate: {vendor_history.get('on_time_rate', 0)}%
    - Relationship: {vendor_history.get('is_critical', 'standard')}

    """
        
        # ADD RAG CONTEXT
        if rag_context:
            context += rag_context
        
        context += """
    Provide:
    1. Brief analysis of payment priority
    2. Recommended payment strategy
    3. Key considerations

    Format as JSON:
    {
    "analysis": "Brief analysis (2-3 sentences)",
    "payment_strategy": "Recommended action (1-2 sentences)",
    "recommendations": ["rec1", "rec2", "rec3"]
    }

    Return ONLY valid JSON."""
        
        messages = [{
            "role": "user",
            "content": context
        }]
        
        try:
            response = self.invoke(messages, max_tokens=1024)
            content = response['content'].strip()
            
            # Clean JSON
            if content.startswith('```'):
                content = content.split('\n', 1)[1].rsplit('\n', 1)[0]
                if content.startswith('json'):
                    content = content[4:].strip()
            
            data = json.loads(content)
            return data
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error in analysis: {e}")
            # Fallback
            return {
                'analysis': f"Invoice from {vendor_name} for ${amount:,.2f}",
                'payment_strategy': "Review and pay according to terms",
                'recommendations': ["Verify invoice details", "Check budget availability"]
            }
    
    def answer_question(
        self,
        question: str,
        context: Dict,
        chat_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Answer user question about invoice with context
        
        Args:
            question: User's question
            context: Invoice context (data, analysis, etc.)
            chat_history: Previous messages
            
        Returns:
            Answer string
        """
        # Build system prompt
        system = """You are a helpful finance assistant analyzing invoices.
Provide clear, concise answers based on the invoice data provided.
If asked about costs, break down the reasoning.
If asked about timing, consider due dates and cash flow."""
        
        # Build messages
        messages = []
        
        # Add chat history if available
        if chat_history:
            messages.extend(chat_history[-10:])  # Last 10 messages
        
        # Add current question with context
        content = f"""
Invoice Context:
{json.dumps(context, indent=2)}

Question: {question}

Answer concisely and clearly."""
        
        messages.append({
            "role": "user",
            "content": content
        })
        
        response = self.invoke(messages, system=system, max_tokens=1024)
        return response['content']


# Global instance
_bedrock_client = None

def get_bedrock_client() -> BedrockClient:
    """Get or create Bedrock client singleton"""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = BedrockClient()
    return _bedrock_client