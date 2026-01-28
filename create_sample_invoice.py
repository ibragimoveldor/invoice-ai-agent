# create_sample_invoice.py
"""
Create a sample invoice PDF for testing
"""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime, timedelta

def create_sample_invoice():
    """Create a sample invoice PDF"""
    filename = "sample_invoice.pdf"
    
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Header
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "INVOICE")
    
    # Company info
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 100, "Acme Corporation")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 120, "123 Business St")
    c.drawString(50, height - 135, "New York, NY 10001")
    
    # Invoice details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(400, height - 100, f"Invoice #: INV-2024-001")
    c.setFont("Helvetica", 10)
    
    invoice_date = datetime.now()
    due_date = invoice_date + timedelta(days=30)
    
    c.drawString(400, height - 120, f"Date: {invoice_date.strftime('%Y-%m-%d')}")
    c.drawString(400, height - 135, f"Due: {due_date.strftime('%Y-%m-%d')}")
    
    # Bill to
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 180, "Bill To:")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 200, "Your Company Name")
    c.drawString(50, height - 215, "456 Client Ave")
    c.drawString(50, height - 230, "Boston, MA 02101")
    
    # Line items
    y = height - 280
    
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Description")
    c.drawString(300, y, "Quantity")
    c.drawString(380, y, "Unit Price")
    c.drawString(480, y, "Total")
    
    c.line(50, y - 5, 550, y - 5)
    
    y -= 30
    c.setFont("Helvetica", 10)
    
    # Item 1
    c.drawString(50, y, "Software Licenses - Annual Subscription")
    c.drawString(315, y, "10")
    c.drawString(380, y, "$500.00")
    c.drawString(480, y, "$5,000.00")
    
    # Total
    y -= 50
    c.line(400, y, 550, y)
    y -= 20
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(400, y, "Total Amount:")
    c.drawString(480, y, "$5,000.00")
    
    # Payment terms
    y -= 60
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Payment Terms:")
    c.setFont("Helvetica", 9)
    y -= 15
    c.drawString(50, y, "• Net 30 days")
    y -= 12
    c.drawString(50, y, "• 2% discount if paid within 10 days")
    y -= 12
    c.drawString(50, y, "• Late payments subject to 1.5% monthly interest")
    
    # Footer - FIX: Use Helvetica instead of Helvetica-Italic
    c.setFont("Helvetica", 8)  # ← Changed from Helvetica-Italic
    c.drawString(50, 50, "Thank you for your business!")
    c.drawString(50, 35, "Questions? Contact: billing@acmecorp.com | (555) 123-4567")
    
    c.save()
    
    print(f"✅ Created sample invoice: {filename}")
    print("📄 Upload this to test the system!")

if __name__ == "__main__":
    create_sample_invoice()