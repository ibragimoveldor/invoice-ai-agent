# test_bedrock.py
"""
Test AWS Bedrock connection and invoice extraction
"""
from app.core.aws_bedrock import get_bedrock_client

print("="*60)
print("Testing AWS Bedrock Connection")
print("="*60)

# Get client
print("\n1. Initializing Bedrock client...")
bedrock = get_bedrock_client()
print("   ✅ Client created")

# Test simple message
print("\n2. Testing simple message...")
messages = [{
    "role": "user",
    "content": "Say 'AWS Bedrock is working!' in a professional tone."
}]

response = bedrock.invoke(messages)
print(f"   Response: {response['content']}")
print(f"   Tokens: {response['usage']}")

# Test invoice analysis
print("\n3. Testing invoice analysis...")
analysis = bedrock.analyze_invoice(
    vendor_name="Acme Corporation",
    amount=5000.00,
    due_date="2024-02-15",
    priority_score=85.0,
    vendor_history={
        'total_invoices': 12,
        'average_amount': 4500.00,
        'on_time_rate': 95,
        'is_critical': 'important'
    }
)

print(f"   Analysis: {analysis['analysis']}")
print(f"   Strategy: {analysis['payment_strategy']}")
print(f"   Recommendations: {len(analysis['recommendations'])} items")

# Test Q&A
print("\n4. Testing question answering...")
context = {
    'vendor': 'Acme Corporation',
    'amount': 5000.00,
    'due_date': '2024-02-15'
}

answer = bedrock.answer_question(
    question="What is the payment amount?",
    context=context
)

print(f"   Answer: {answer}")

print("\n" + "="*60)
print("✅ AWS Bedrock tests successful!")
print("="*60)