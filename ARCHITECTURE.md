# Invoice Intelligence Agent - Architecture

## System Overview

AI-powered B2B invoice processing and payment optimization agent using AWS Bedrock, LangGraph, and FastAPI.

---

## High-Level System Flow
```mermaid
flowchart TD
    A[User Uploads Invoice PDF/Image] --> B[Gradio Frontend]
    B --> C[FastAPI Backend]
    C --> D{LangGraph Orchestration}
    
    D --> E[Workflow 1: Invoice Processing]
    D --> F[Workflow 2: Chat Q&A]
    
    E --> G[Step 1: Extract Data<br/>Claude Vision API]
    G --> H[Step 2: Calculate Priority<br/>Payment Scoring]
    H --> I[Step 3: AI Analysis<br/>Claude Reasoning]
    
    I --> J[(SQLite Database)]
    J --> K[Return Results]
    
    F --> L[Detect SQL Intent]
    L --> M{Needs SQL?}
    M -->|Yes| N[Generate SQL Query]
    M -->|No| O[Direct Answer]
    N --> P[Execute Query]
    P --> O
    O --> K
    
    K --> B
    
    style G fill:#FF6B6B,color:#fff
    style I fill:#FF6B6B,color:#fff
    style H fill:#51CF66,color:#fff
    style J fill:#868E96,color:#fff
```

---

## Invoice Processing Workflow (Detailed)
```mermaid
graph TB
    START([User Uploads Invoice]) --> UPLOAD[FastAPI Receives File]
    UPLOAD --> SAVE[Save to uploads/]
    
    SAVE --> LANG[LangGraph Invoice Workflow]
    
    subgraph "LangGraph State Machine"
        LANG --> NODE1[Node 1: Extract Invoice Data]
        
        NODE1 --> VISION[Claude Vision API]
        VISION --> PARSE[Parse JSON Response]
        PARSE --> VALIDATE[Validate Extraction]
        
        VALIDATE --> NODE2[Node 2: Calculate Priority]
        
        NODE2 --> SCORE[Priority Scoring Algorithm]
        SCORE --> FACTORS{Consider Factors}
        FACTORS --> |Due Date| FACTOR1[Days Until Due]
        FACTORS --> |Discount| FACTOR2[Early Payment Discount]
        FACTORS --> |Vendor| FACTOR3[Vendor Criticality]
        FACTORS --> |Amount| FACTOR4[Invoice Amount]
        
        FACTOR1 --> URGENCY[Determine Urgency Level]
        FACTOR2 --> URGENCY
        FACTOR3 --> URGENCY
        FACTOR4 --> URGENCY
        
        URGENCY --> NODE3[Node 3: AI Analysis]
        
        NODE3 --> CONTEXT[Build Context]
        CONTEXT --> CLAUDE[Claude 3.5 Sonnet]
        CLAUDE --> STRATEGY[Generate Payment Strategy]
        STRATEGY --> RECS[Generate Recommendations]
    end
    
    RECS --> DB[(Save to Database)]
    DB --> RESPONSE[Build API Response]
    RESPONSE --> UI[Display in Gradio]
    
    style VISION fill:#FF6B6B,color:#fff
    style CLAUDE fill:#FF6B6B,color:#fff
    style SCORE fill:#51CF66,color:#fff
    style DB fill:#868E96,color:#fff
```

---

## Chat Workflow (Conversational Q&A)
```mermaid
sequenceDiagram
    participant User
    participant Gradio
    participant FastAPI
    participant LangGraph
    participant IntentDetector
    participant SQLGen
    participant Database
    participant Claude
    
    User->>Gradio: "What's the total amount?"
    Gradio->>FastAPI: POST /api/v1/chat
    FastAPI->>LangGraph: Invoke chat_graph
    
    LangGraph->>IntentDetector: Analyze question
    IntentDetector->>IntentDetector: Check for SQL keywords
    
    alt Needs SQL Query
        IntentDetector-->>LangGraph: needs_sql = true
        LangGraph->>SQLGen: Generate SQL
        SQLGen->>Claude: Convert to SQL
        Claude-->>SQLGen: SELECT * FROM invoices...
        SQLGen->>Database: Execute query
        Database-->>SQLGen: Return results
        SQLGen-->>LangGraph: Formatted results
    else Direct Answer
        IntentDetector-->>LangGraph: needs_sql = false
    end
    
    LangGraph->>Claude: Answer with context
    Claude-->>LangGraph: Generate response
    
    LangGraph-->>FastAPI: Return answer
    FastAPI->>Database: Save chat message
    FastAPI-->>Gradio: JSON response
    Gradio-->>User: Display answer
```

---

## LangGraph State Machines

### Invoice Processing State
```mermaid
stateDiagram-v2
    [*] --> ExtractData
    
    ExtractData --> CalculatePriority: Extraction Success
    ExtractData --> Error: Extraction Failed
    
    CalculatePriority --> AIAnalysis: Priority Calculated
    CalculatePriority --> Error: Calculation Failed
    
    AIAnalysis --> SaveDatabase: Analysis Complete
    AIAnalysis --> FallbackAnalysis: Bedrock Unavailable
    
    FallbackAnalysis --> SaveDatabase: Rule-based Analysis
    
    SaveDatabase --> [*]
    Error --> [*]
    
    note right of ExtractData
        State: {file_path}
        Output: {vendor, amount, line_items}
    end note
    
    note right of CalculatePriority
        State: {amount, due_date}
        Output: {priority_score, urgency}
    end note
    
    note right of AIAnalysis
        State: {priority_score, vendor}
        Output: {analysis, strategy, recommendations}
    end note
```

### Chat Workflow State
```mermaid
stateDiagram-v2
    [*] --> DetectIntent
    
    DetectIntent --> GenerateSQL: needs_sql = true
    DetectIntent --> Answer: needs_sql = false
    
    GenerateSQL --> ExecuteSQL: SQL Generated
    GenerateSQL --> Answer: Generation Failed
    
    ExecuteSQL --> Answer: Results Retrieved
    
    Answer --> [*]
    
    note right of DetectIntent
        Check for: show, list, find,
        count, filter keywords
    end note
    
    note right of GenerateSQL
        Claude generates safe
        SELECT-only queries
    end note
```

---

## Database Schema
```mermaid
erDiagram
    INVOICES ||--o{ LINE_ITEMS : contains
    INVOICES ||--o{ CHAT_MESSAGES : has
    INVOICES }o--|| VENDOR_HISTORY : references
    
    INVOICES {
        int id PK
        string invoice_id UK
        string vendor_name
        string invoice_number
        float amount
        string currency
        datetime due_date
        datetime invoice_date
        float priority_score
        string urgency
        text analysis
        text payment_strategy
        string file_path
        datetime created_at
    }
    
    LINE_ITEMS {
        int id PK
        int invoice_id FK
        string description
        float quantity
        float unit_price
        float total_price
        string category
    }
    
    CHAT_MESSAGES {
        int id PK
        int invoice_id FK
        string session_id
        string role
        text content
        int tokens_used
        float cost
        datetime created_at
    }
    
    VENDOR_HISTORY {
        int id PK
        string vendor_name
        int total_invoices
        float total_amount_paid
        float average_payment_days
        float on_time_payment_rate
        string is_critical
        datetime last_invoice_date
    }
```

---

## Component Architecture
```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[Gradio Interface<br/>Port 7860]
    end
    
    subgraph "API Layer"
        API[FastAPI Backend<br/>Port 8000]
        
        subgraph "Routes"
            R1[POST /invoices/analyze]
            R2[GET /invoices/:id]
            R3[POST /chat]
            R4[GET /invoices/stats]
        end
    end
    
    subgraph "Orchestration Layer"
        LG[LangGraph Workflows]
        
        subgraph "Invoice Graph"
            IG1[Extract Node]
            IG2[Calculate Node]
            IG3[Analyze Node]
        end
        
        subgraph "Chat Graph"
            CG1[Intent Node]
            CG2[SQL Gen Node]
            CG3[Answer Node]
        end
    end
    
    subgraph "Processing Layer"
        EXT[Invoice Extractor<br/>Claude Vision]
        CALC[Payment Calculator<br/>Priority Scoring]
        AI[AI Reasoning<br/>Claude 3.5]
    end
    
    subgraph "Data Layer"
        DB[(SQLite Database)]
        FILES[File System<br/>uploads/]
    end
    
    subgraph "External Services"
        BEDROCK[AWS Bedrock<br/>us-east-1]
    end
    
    UI --> API
    API --> R1
    API --> R2
    API --> R3
    API --> R4
    
    R1 --> LG
    R3 --> LG
    
    LG --> IG1
    LG --> CG1
    
    IG1 --> EXT
    IG2 --> CALC
    IG3 --> AI
    
    CG2 --> AI
    CG3 --> AI
    
    EXT --> BEDROCK
    AI --> BEDROCK
    
    IG3 --> DB
    CG3 --> DB
    R1 --> FILES
    
    style UI fill:#4A90E2,color:#fff
    style BEDROCK fill:#FF922B,color:#fff
    style EXT fill:#FF6B6B,color:#fff
    style AI fill:#FF6B6B,color:#fff
    style DB fill:#868E96,color:#fff
```

---

## Data Flow: Complete Analysis
```mermaid
flowchart TD
    A[User: Upload Invoice] --> B[Frontend: File Upload]
    B --> C[API: POST /invoices/analyze]
    C --> D[Save File: uploads/invoice_123.pdf]
    
    D --> E[LangGraph: Start Workflow]
    
    E --> F1[Node 1: Extract Data]
    F1 --> F1A[Read File Bytes]
    F1A --> F1B[Encode Base64]
    F1B --> F1C[Claude Vision API Call]
    F1C --> F1D[Parse JSON Response]
    F1D --> F1E{Valid Data?}
    
    F1E -->|Yes| G1[Node 2: Calculate Priority]
    F1E -->|No| ERR[Return Error]
    
    G1 --> G1A[Check Due Date]
    G1A --> G1B[Check Discount]
    G1B --> G1C[Check Vendor History]
    G1C --> G1D[Calculate Score 0-100]
    G1D --> G1E[Classify Urgency]
    
    G1E --> H1[Node 3: AI Analysis]
    H1 --> H1A[Build Context Prompt]
    H1A --> H1B[Claude API Call]
    H1B --> H1C[Parse Analysis JSON]
    H1C --> H1D[Extract Strategy]
    H1D --> H1E[Extract Recommendations]
    
    H1E --> I[Save to Database]
    I --> I1[Insert Invoice Record]
    I1 --> I2[Insert Line Items]
    I2 --> I3[Update Vendor History]
    
    I3 --> J[Build Response JSON]
    J --> K[Return to Frontend]
    K --> L[Display Results]
    L --> M[Initialize Chat]
    
    style F1C fill:#FF6B6B,color:#fff
    style H1B fill:#FF6B6B,color:#fff
    style G1D fill:#51CF66,color:#fff
    style I fill:#868E96,color:#fff
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Gradio 4.19 | Interactive UI |
| **API** | FastAPI 0.109 | RESTful backend |
| **Orchestration** | LangGraph 0.0.45 | Multi-step workflows |
| **LLM** | AWS Bedrock | Claude 3.5 Sonnet |
| **Vision** | Claude Vision API | Invoice data extraction |
| **Database** | SQLite (dev) | Persistent storage |
| **File Processing** | python-magic | File type validation |
| **Cloud** | AWS | Bedrock service |

---

## Key Design Decisions

### 1. **LangGraph vs Simple Chains**
- **Choice:** LangGraph multi-step workflows
- **Reason:** Observable agent behavior, error recovery, conditional routing
- **Benefit:** Can see each step in workflow logs

### 2. **Claude Vision vs Traditional OCR**
- **Choice:** Claude Vision API
- **Reason:** Handles both PDFs and images, extracts structured data directly
- **Benefit:** No separate OCR + parsing steps needed

### 3. **Payment Priority Scoring**
- **Choice:** Rule-based algorithm + AI insights
- **Reason:** Deterministic scoring for consistency, AI for context
- **Benefit:** Explainable decisions for finance teams

### 4. **SQLite vs PostgreSQL**
- **Choice:** SQLite for demo, designed for PostgreSQL
- **Reason:** Zero setup, production migration ready
- **Trade-off:** Limited concurrency acceptable for demo

---

## Scalability Considerations

### Current (Demo):
- Single instance
- SQLite database
- Local file storage
- ~10 requests/minute

### Production (Scaled):
- Auto-scaling ECS containers
- RDS PostgreSQL
- S3 for file storage
- ~1000 requests/minute

### Bottlenecks & Solutions:
| Bottleneck | Solution |
|------------|----------|
| Claude API rate limits | Request queuing, caching |
| File processing | Async with Celery workers |
| Database connections | Connection pooling, read replicas |
| Storage | S3 + CloudFront CDN |

---

## Security Architecture
```mermaid
graph LR
    subgraph "Security Layers"
        AUTH[Authentication<br/>API Keys]
        VALID[Input Validation<br/>Pydantic Models]
        SQL[SQL Safety<br/>Read-only Queries]
        FILE[File Validation<br/>Type & Size Checks]
        ENCRYPT[Encryption<br/>TLS/SSL]
    end
    
    subgraph "Data Protection"
        PII[PII Handling<br/>Vendor Data]
        AUDIT[Audit Logging<br/>All Actions]
        BACKUP[Data Backup<br/>Regular Snapshots]
    end
    
    AUTH --> VALID
    VALID --> SQL
    SQL --> FILE
    FILE --> ENCRYPT
    ENCRYPT --> AUDIT
    
    PII --> AUDIT
    AUDIT --> BACKUP
```

---

## Cost Breakdown

| Component | Dev Cost | Production (1000 invoices/month) |
|-----------|----------|----------------------------------|
| AWS Bedrock (Claude) | $3-5/demo | ~$150/month |
| Compute (ECS) | $0 | ~$50/month |
| Database (RDS) | $0 | ~$30/month |
| Storage (S3) | $0 | ~$10/month |
| **Total** | **$3-5** | **~$240/month** |

### Cost Optimization:
- Cache common analyses
- Batch API requests
- Use reserved instances
- Implement request throttling

---

## Future Enhancements

1. **RAG Integration**
   - Vector database for historical patterns
   - Semantic search across invoices
   - "Find similar vendor invoices"

2. **Multi-Agent Architecture**
   - Extraction specialist agent
   - Payment strategy specialist agent
   - Coordinator routing agent

3. **Advanced Features**
   - Duplicate detection
   - Fraud detection
   - Budget tracking
   - Cash flow forecasting

4. **Integrations**
   - QuickBooks/Xero sync
   - Email invoice ingestion
   - Slack notifications
   - API webhooks

---

## Monitoring & Observability

### Metrics Tracked:
- Request latency (p50, p95, p99)
- Claude API token usage & cost
- Extraction success rate
- Database query performance
- Error rates by endpoint

### Logging:
- Structured JSON logs
- Agent decision traces
- LLM prompt/response logging
- Error stack traces with context

### Alerting:
- Error rate > 5%
- Latency p95 > 10s
- AWS costs > $100/day
- Database connection failures

---

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [AWS Bedrock](https://aws.amazon.com/bedrock/)
- [Claude Vision API](https://docs.anthropic.com/claude/docs/vision)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)