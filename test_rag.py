# test_rag.py
"""
Test RAG system
"""
from app.core.vector_store import get_rag
from datetime import datetime

print("="*60)
print("Testing RAG System")
print("="*60)

# Initialize RAG
rag = get_rag()

# Add test invoices
print("\n1. Adding test invoices to RAG...")

test_invoices = [
    {
        'invoice_id': 'test-001',
        'vendor_name': 'Acme Corporation',
        'amount': 5000.00,
        'priority_score': 85.0,
        'urgency': 'high',
        'analysis': 'Critical vendor with early payment discount available',
        'payment_strategy': 'Pay within 10 days to save 2%'
    },
    {
        'invoice_id': 'test-002',
        'vendor_name': 'Tech Solutions Inc',
        'amount': 12000.00,
        'priority_score': 75.0,
        'urgency': 'medium',
        'analysis': 'Large software license renewal',
        'payment_strategy': 'Standard 30-day payment terms'
    },
    {
        'invoice_id': 'test-003',
        'vendor_name': 'Acme Corporation',
        'amount': 4800.00,
        'priority_score': 80.0,
        'urgency': 'high',
        'analysis': 'Recurring vendor, maintain good relationship',
        'payment_strategy': 'Pay on time to preserve relationship'
    }
]

for inv in test_invoices:
    rag.add_invoice(**inv)

# Test retrieval
print("\n2. Testing similarity search...")
results = rag.retrieve_similar_invoices(
    query="Acme Corporation invoice for consulting services",
    n_results=2
)

print(f"\n   Found {len(results['documents'])} similar invoices:")
for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas']), 1):
    print(f"\n   {i}. {meta['vendor_name']} - ${meta['amount']:,.2f}")
    print(f"      Priority: {meta['priority_score']}/100 ({meta['urgency']})")

# Test vendor history
print("\n3. Testing vendor history retrieval...")
history = rag.get_vendor_history("Acme Corporation")
print(f"\n   Acme Corporation: {len(history)} past invoices")
for inv in history:
    print(f"   - ${inv['amount']:,.2f} ({inv['urgency']})")

# Test stats
print("\n4. RAG Statistics...")
stats = rag.get_stats()
print(f"\n   Total indexed: {stats['total_indexed']}")
print(f"   Urgent: {stats['urgent_count']}")
print(f"   High priority: {stats['high_priority_count']}")

print("\n" + "="*60)
print("✅ RAG System Working!")
print("="*60)