# app/core/vector_store.py
"""
Vector store for RAG - Historical invoice pattern retrieval
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import json
from pathlib import Path

from app.config import settings

class InvoiceRAG:
    """
    RAG system for invoice intelligence
    
    Stores invoice analyses in vector database for:
    - Finding similar past invoices
    - Retrieving vendor payment patterns
    - Context-aware recommendations
    """
    
    def __init__(self):
        """Initialize ChromaDB client"""
        # Create persist directory
        persist_dir = Path(settings.vector_db_path)
        persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize client
        self.client = chromadb.PersistentClient(
            path=str(persist_dir)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="invoice_analyses",
            metadata={"description": "Invoice analysis embeddings for RAG"}
        )
        
        print(f"✅ RAG initialized: {self.collection.count()} documents indexed")
    
    def add_invoice(
        self,
        invoice_id: str,
        vendor_name: str,
        amount: float,
        priority_score: float,
        urgency: str,
        analysis: str,
        payment_strategy: str
    ) -> None:
        """
        Add invoice analysis to vector store
        
        Args:
            invoice_id: Unique invoice identifier
            vendor_name: Vendor name
            amount: Invoice amount
            priority_score: Priority score (0-100)
            urgency: Urgency level
            analysis: AI-generated analysis
            payment_strategy: Payment strategy recommendation
        """
        # Build document for embedding
        document = f"""
Vendor: {vendor_name}
Amount: ${amount:,.2f}
Priority: {priority_score}/100 ({urgency})

Analysis:
{analysis}

Strategy:
{payment_strategy}
"""
        
        # Metadata for filtering
        metadata = {
            'invoice_id': invoice_id,
            'vendor_name': vendor_name,
            'amount': float(amount),
            'priority_score': float(priority_score),
            'urgency': urgency
        }
        
        try:
            self.collection.add(
                documents=[document],
                metadatas=[metadata],
                ids=[invoice_id]
            )
            print(f"   ✅ Added to RAG: {invoice_id}")
        except Exception as e:
            print(f"   ⚠️ RAG add failed: {e}")
    
    def retrieve_similar_invoices(
        self,
        query: str,
        n_results: int = 3,
        vendor_filter: Optional[str] = None
    ) -> Dict:
        """
        Retrieve similar invoices based on query
        
        Args:
            query: Search query (natural language)
            n_results: Number of results to return
            vendor_filter: Optional vendor name filter
            
        Returns:
            Dict with documents, metadatas, distances
        """
        try:
            # Build where filter
            where = None
            if vendor_filter:
                where = {"vendor_name": vendor_filter}
            
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where
            )
            
            print(f"   🔍 RAG retrieved {len(results['documents'][0])} similar invoices")
            
            return {
                'documents': results['documents'][0],
                'metadatas': results['metadatas'][0],
                'distances': results['distances'][0]
            }
            
        except Exception as e:
            print(f"   ⚠️ RAG retrieval failed: {e}")
            return {
                'documents': [],
                'metadatas': [],
                'distances': []
            }
    
    def get_vendor_history(self, vendor_name: str) -> List[Dict]:
        """
        Get all past invoices for a specific vendor
        
        Args:
            vendor_name: Vendor name
            
        Returns:
            List of past invoice metadata
        """
        try:
            results = self.collection.get(
                where={"vendor_name": vendor_name}
            )
            
            history = []
            if results['metadatas']:
                for metadata in results['metadatas']:
                    history.append(metadata)
            
            print(f"   📊 Found {len(history)} past invoices for {vendor_name}")
            return history
            
        except Exception as e:
            print(f"   ⚠️ Vendor history retrieval failed: {e}")
            return []
    
    def search_by_amount_range(
        self,
        min_amount: float,
        max_amount: float,
        n_results: int = 10
    ) -> List[Dict]:
        """
        Find invoices within amount range
        
        Args:
            min_amount: Minimum amount
            max_amount: Maximum amount
            n_results: Max results
            
        Returns:
            List of matching invoice metadata
        """
        try:
            results = self.collection.get(
                where={
                    "$and": [
                        {"amount": {"$gte": min_amount}},
                        {"amount": {"$lte": max_amount}}
                    ]
                },
                limit=n_results
            )
            
            return results['metadatas'] if results['metadatas'] else []
            
        except Exception as e:
            print(f"   ⚠️ Amount range search failed: {e}")
            return []
    
    def get_urgent_patterns(self, n_results: int = 5) -> List[Dict]:
        """
        Retrieve urgent invoice patterns for learning
        
        Returns:
            List of urgent invoice metadata
        """
        try:
            results = self.collection.get(
                where={"urgency": "urgent"},
                limit=n_results
            )
            
            return results['metadatas'] if results['metadatas'] else []
            
        except Exception as e:
            print(f"   ⚠️ Urgent patterns retrieval failed: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get RAG statistics"""
        try:
            total = self.collection.count()
            
            # Get urgency distribution
            urgent = len(self.collection.get(where={"urgency": "urgent"})['ids'])
            high = len(self.collection.get(where={"urgency": "high"})['ids'])
            
            return {
                'total_indexed': total,
                'urgent_count': urgent,
                'high_priority_count': high
            }
        except:
            return {
                'total_indexed': 0,
                'urgent_count': 0,
                'high_priority_count': 0
            }


# Global instance
_rag_instance = None

def get_rag() -> InvoiceRAG:
    """Get or create RAG singleton"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = InvoiceRAG()
    return _rag_instance