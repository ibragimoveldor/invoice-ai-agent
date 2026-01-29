# test_text_to_sql.py
"""
Test working Text-to-SQL implementation
"""
import requests

API_URL = "http://localhost:8000/api/v1"

print("="*60)
print("Testing Text-to-SQL (Now Working!)")
print("="*60)

# SQL-triggering questions
sql_questions = [
    "Show me all urgent invoices",
    "List all invoices from Acme Corporation",
    "What's the total amount of all invoices?",
    "Show me high priority invoices",
    "How many invoices do we have?"
]

# Non-SQL questions (for comparison)
direct_questions = [
    "What is an invoice?",
    "How does payment prioritization work?"
]

print("\n🔍 SQL QUERIES (Should generate and execute SQL):\n")

for i, question in enumerate(sql_questions, 1):
    print(f"{i}. Question: {question}")
    print("-" * 60)
    
    response = requests.post(
        f"{API_URL}/chat",
        json={"question": question}
    )
    
    if response.status_code == 200:
        data = response.json()
        
        if data.get('sql_query'):
            print(f"📊 Generated SQL:\n{data['sql_query']}\n")
        
        print(f"💬 Response:\n{data['response']}\n")
    else:
        print(f"❌ Error: {response.status_code}\n")

print("\n💭 DIRECT ANSWERS (Should skip SQL):\n")

for i, question in enumerate(direct_questions, 1):
    print(f"{i}. Question: {question}")
    print("-" * 60)
    
    response = requests.post(
        f"{API_URL}/chat",
        json={"question": question}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"💬 Response:\n{data['response']}\n")

print("="*60)
print("✅ Text-to-SQL Test Complete!")
print("="*60)