# test_db_setup.py
"""
Test database setup
"""
from app.database import init_db, get_db
from app.database.crud import create_invoice, get_invoice_stats
from datetime import datetime

print("="*60)
print("Testing Database Setup")
print("="*60)

# Initialize database
print("\n1. Initializing database...")
init_db()

# Get database session
db = next(get_db())

# Create test invoice
print("\n2. Creating test invoice...")
invoice = create_invoice(
    db=db,
    vendor_name="Acme Corporation",
    invoice_number="INV-2024-001",
    amount=5000.00,
    priority_score=85.0,
    urgency="high",
    analysis="Early payment discount available. Critical vendor.",
    payment_strategy="Pay by Friday to save 2% ($100)",
    file_path="uploads/invoices/test.pdf",
    due_date=datetime(2024, 2, 15),
    invoice_date=datetime(2024, 1, 15),
    line_items=[
        {
            'description': 'Software licenses',
            'quantity': 10,
            'unit_price': 500.00,
            'total_price': 5000.00,
            'category': 'software'
        }
    ]
)

print(f"   ✅ Created invoice: {invoice.invoice_id}")

# Get statistics
print("\n3. Getting statistics...")
stats = get_invoice_stats(db)
print(f"   Total invoices: {stats['total_invoices']}")
print(f"   Total amount: ${stats['total_amount']:,.2f}")
print(f"   Urgent count: {stats['urgent_count']}")

print("\n" + "="*60)
print("✅ Database setup successful!")
print("="*60)

db.close()