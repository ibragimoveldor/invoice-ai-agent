# app/models/payment_calculator.py
"""
Payment priority scoring and cost calculation
"""
from typing import Dict, List
from datetime import datetime, timedelta

def calculate_priority_score(
    amount: float,
    due_date: datetime,
    vendor_history: Dict = None,
    has_discount: bool = False,
    discount_percentage: float = 0.0
) -> Dict:
    """
    Calculate payment priority score (0-100)
    
    Higher score = Higher priority
    
    Factors:
    - Days until due date
    - Early payment discount
    - Vendor criticality
    - Amount (relative)
    """
    score = 50  # Base score
    urgency = "medium"
    
    # Days until due date
    if due_date:
        days_until_due = (due_date - datetime.now()).days
        
        if days_until_due < 0:
            # Overdue
            score += 40
            urgency = "urgent"
        elif days_until_due <= 7:
            # Due within week
            score += 30
            urgency = "high"
        elif days_until_due <= 14:
            # Due within 2 weeks
            score += 15
        elif days_until_due <= 30:
            # Due within month
            score += 5
        else:
            # More than 30 days
            score -= 10
    
    # Early payment discount
    if has_discount and discount_percentage > 0:
        # Add points based on discount value
        discount_value = amount * (discount_percentage / 100)
        if discount_value > 100:
            score += 20
            urgency = "high"
        elif discount_value > 50:
            score += 15
        elif discount_value > 20:
            score += 10
    
    # Vendor criticality
    if vendor_history:
        is_critical = vendor_history.get('is_critical', 'standard')
        
        if is_critical == 'critical':
            score += 20
            if urgency == "medium":
                urgency = "high"
        elif is_critical == 'important':
            score += 10
    
    # Amount-based adjustment (large amounts get slight boost)
    if amount > 10000:
        score += 5
    elif amount > 50000:
        score += 10
    
    # Cap score at 100
    score = min(100, max(0, score))
    
    # Final urgency classification
    if score >= 80:
        urgency = "urgent"
    elif score >= 60:
        urgency = "high"
    elif score >= 40:
        urgency = "medium"
    else:
        urgency = "low"
    
    return {
        'priority_score': round(score, 1),
        'urgency': urgency,
        'factors': {
            'due_date_impact': days_until_due if due_date else None,
            'has_discount': has_discount,
            'discount_value': amount * (discount_percentage / 100) if has_discount else 0,
            'vendor_criticality': vendor_history.get('is_critical') if vendor_history else 'unknown'
        }
    }


def get_urgency_label(urgency: str) -> str:
    """Get emoji label for urgency"""
    labels = {
        'urgent': '🔴 URGENT',
        'high': '🟠 HIGH',
        'medium': '🟡 MEDIUM',
        'low': '🟢 LOW'
    }
    return labels.get(urgency, urgency.upper())


def calculate_payment_timeline(
    invoices: List[Dict],
    available_cash: float = None
) -> Dict:
    """
    Calculate optimal payment timeline
    
    Args:
        invoices: List of invoice dicts with priority_score
        available_cash: Available cash (optional)
        
    Returns:
        Payment schedule recommendations
    """
    # Sort by priority score (highest first)
    sorted_invoices = sorted(
        invoices,
        key=lambda x: x['priority_score'],
        reverse=True
    )
    
    schedule = {
        'immediate': [],  # Pay this week
        'short_term': [],  # Pay within 2 weeks
        'long_term': [],   # Pay within month
        'defer': []        # Can defer beyond 30 days
    }
    
    running_total = 0
    
    for invoice in sorted_invoices:
        amount = invoice['amount']
        urgency = invoice['urgency']
        
        # Check cash constraint
        if available_cash and running_total + amount > available_cash:
            # Cash constrained
            if urgency in ['urgent', 'high']:
                schedule['immediate'].append({
                    **invoice,
                    'note': 'Critical - find additional cash'
                })
            else:
                schedule['defer'].append({
                    **invoice,
                    'note': 'Defer due to cash constraints'
                })
        else:
            # Assign based on urgency
            if urgency == 'urgent':
                schedule['immediate'].append(invoice)
            elif urgency == 'high':
                schedule['short_term'].append(invoice)
            elif urgency == 'medium':
                schedule['long_term'].append(invoice)
            else:
                schedule['defer'].append(invoice)
            
            running_total += amount
    
    return {
        'schedule': schedule,
        'total_committed': running_total,
        'cash_remaining': available_cash - running_total if available_cash else None
    }


def estimate_discount_savings(
    amount: float,
    discount_percentage: float,
    discount_days: int,
    due_days: int
) -> Dict:
    """
    Calculate early payment discount savings
    
    Args:
        amount: Invoice amount
        discount_percentage: Discount percentage (e.g., 2 for 2%)
        discount_days: Days to get discount (e.g., 10)
        due_days: Normal payment terms (e.g., 30)
        
    Returns:
        Discount analysis
    """
    discount_amount = amount * (discount_percentage / 100)
    days_early = due_days - discount_days
    
    # Annualized rate (rough approximation)
    if days_early > 0:
        annualized_rate = (discount_percentage / days_early) * 365
    else:
        annualized_rate = 0
    
    return {
        'discount_amount': round(discount_amount, 2),
        'discount_percentage': discount_percentage,
        'days_early': days_early,
        'annualized_rate': round(annualized_rate, 2),
        'recommendation': 'TAKE DISCOUNT' if annualized_rate > 15 else 'EVALUATE'
    }