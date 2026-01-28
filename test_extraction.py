# test_extraction.py
"""
Test invoice extraction
"""
from app.models.invoice_extractor import InvoiceExtractor
from datetime import datetime

print("="*60)
print("Testing Invoice Extraction")
print("="*60)

# Initialize extractor
print("\n1. Initializing extractor...")
extractor = InvoiceExtractor()
info = extractor.get_model_info()
print(f"   Model: {info['model']}")
print(f"   Supported: {', '.join(info['supported_formats'])}")

# Test with sample data (you'll need a real invoice file)
print("\n2. Testing extraction...")
print("   Note: This will work when you upload a real invoice")
print("   For now, testing with mock extraction...")

# Mock extraction result
mock_data = {
    'vendor_name': 'Acme Corporation',
    'invoice_number': 'INV-2024-001',
    'amount': 5000.00,
    'currency': 'USD',
    'due_date': '2024-02-15',
    'invoice_date': '2024-01-15',
    'line_items': [
        {
            'description': 'Software Licenses',
            'quantity': 10,
            'unit_price': 500.00,
            'total_price': 5000.00,
            'category': 'software'
        }
    ]
}

validated = extractor._validate_extraction(mock_data)

print(f"\n   Vendor: {validated['vendor_name']}")
print(f"   Invoice #: {validated['invoice_number']}")
print(f"   Amount: ${validated['amount']:,.2f}")
print(f"   Due Date: {validated.get('due_date')}")
print(f"   Line Items: {len(validated['line_items'])}")

# Test payment priority
print("\n3. Testing priority calculation...")
from app.models.payment_calculator import calculate_priority_score

priority = calculate_priority_score(
    amount=5000.00,
    due_date=datetime(2024, 2, 15),
    has_discount=True,
    discount_percentage=2.0,
    vendor_history={'is_critical': 'important'}
)

print(f"   Priority Score: {priority['priority_score']}/100")
print(f"   Urgency: {priority['urgency']}")
print(f"   Factors: {priority['factors']}")

print("\n" + "="*60)
print("✅ Extraction system ready!")
print("="*60)
print("\nNext: Upload a real invoice PDF/image to test extraction")