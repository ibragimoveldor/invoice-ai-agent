# app/models/invoice_extractor.py
"""
Invoice data extraction using Claude Vision
"""
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path
import magic  # python-magic for file type detection

from app.core.aws_bedrock import get_bedrock_client

class InvoiceExtractor:
    """Extract structured data from invoice documents"""
    
    def __init__(self):
        """Initialize extractor with Bedrock client"""
        self.bedrock = get_bedrock_client()
        
        # Supported file types
        self.supported_types = {
            'application/pdf': 'PDF',
            'image/jpeg': 'JPEG',
            'image/jpg': 'JPEG',
            'image/png': 'PNG',
            'image/webp': 'WEBP'
        }
    
    def validate_file(self, file_path: str) -> tuple[bool, str, str]:
        """
        Validate file type and size
        
        Returns:
            (is_valid, file_type, error_message)
        """
        path = Path(file_path)
        
        # Check file exists
        if not path.exists():
            return False, '', 'File not found'
        
        # Check file size (max 10MB)
        file_size = path.stat().st_size
        if file_size > 10 * 1024 * 1024:  # 10MB
            return False, '', 'File too large (max 10MB)'
        
        # Detect file type using magic bytes
        try:
            mime = magic.Magic(mime=True)
            file_type = mime.from_file(str(path))
        except Exception as e:
            return False, '', f'Could not detect file type: {e}'
        
        # Check if supported
        if file_type not in self.supported_types:
            return False, file_type, f'Unsupported file type: {file_type}'
        
        return True, file_type, ''
    
    def extract(self, file_path: str) -> Dict:
        """
        Extract invoice data from file
        
        Args:
            file_path: Path to invoice file
            
        Returns:
            Extracted invoice data
            
        Raises:
            ValueError: If file invalid or extraction fails
        """
        # Validate file
        is_valid, file_type, error = self.validate_file(file_path)
        if not is_valid:
            raise ValueError(f"Invalid file: {error}")
        
        print(f"📄 Extracting from {self.supported_types[file_type]} file...")
        
        # Read file
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        try:
            # Extract using Claude Vision
            data = self.bedrock.extract_invoice_data(file_content, file_type)
            
            # Validate extracted data
            validated = self._validate_extraction(data)
            
            print(f"   ✅ Extracted: {validated['vendor_name']} - ${validated['amount']:,.2f}")
            
            return validated
            
        except Exception as e:
            print(f"   ❌ Extraction failed: {e}")
            raise ValueError(f"Failed to extract invoice data: {e}")
    
    def _validate_extraction(self, data: Dict) -> Dict:
        """
        Validate and clean extracted data
        
        Ensures required fields exist and have correct types
        """
        # Required fields with defaults
        validated = {
            'vendor_name': data.get('vendor_name', 'Unknown Vendor'),
            'invoice_number': data.get('invoice_number', 'N/A'),
            'amount': float(data.get('amount', 0.0)),
            'currency': data.get('currency', 'USD'),
            'line_items': data.get('line_items', [])
        }
        
        # Parse dates if provided
        due_date = data.get('due_date')
        if due_date:
            validated['due_date'] = self._parse_date(due_date)
        
        invoice_date = data.get('invoice_date')
        if invoice_date:
            validated['invoice_date'] = self._parse_date(invoice_date)
        
        # Validate line items
        validated_items = []
        for item in validated['line_items']:
            if isinstance(item, dict):
                validated_items.append({
                    'description': item.get('description', ''),
                    'quantity': float(item.get('quantity', 0)),
                    'unit_price': float(item.get('unit_price', 0)),
                    'total_price': float(item.get('total_price', 0)),
                    'category': item.get('category', 'other')
                })
        
        validated['line_items'] = validated_items
        
        return validated
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string to datetime
        
        Supports formats: YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY
        """
        if not date_str:
            return None
        
        # Try different formats
        formats = [
            '%Y-%m-%d',      # 2024-01-15
            '%m/%d/%Y',      # 01/15/2024
            '%d/%m/%Y',      # 15/01/2024
            '%Y/%m/%d',      # 2024/01/15
            '%m-%d-%Y',      # 01-15-2024
            '%d-%m-%Y',      # 15-01-2024
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        print(f"   ⚠️ Could not parse date: {date_str}")
        return None
    
    def get_model_info(self) -> Dict:
        """Get extractor metadata"""
        return {
            'model': 'Claude 3.5 Sonnet (Vision)',
            'provider': 'AWS Bedrock',
            'supported_formats': list(self.supported_types.values()),
            'max_file_size': '10MB'
        }