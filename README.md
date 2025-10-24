# Contract Intelligence System

A production-ready AI-powered contract intelligence API built with FastAPI that ingests PDFs, extracts structured fields, answers questions using RAG, and performs clause-risk auditing.

## Features

- 📄 **PDF Ingestion**: Upload and process multiple contract PDFs
- 🔍 **Smart Extraction**: Extract structured data (parties, dates, terms, etc.) using LLM + rule-based fallback
- 💬 **RAG Q&A**: Ask questions about contracts with citations
- ⚠️ **Risk Auditing**: Detect risky clauses (auto-renewal, unlimited liability, etc.)
- 🌊 **Streaming**: WebSocket for real-time responses
- 🔔 **Webhooks**: Event notifications for long-running tasks
- 📊 **Monitoring**: Health checks, metrics, and Prometheus integration
- 🔒 **Security**: PII redaction in logs, input validation
- 🐳 **Dockerized**: Full Docker Compose setup for local development

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- OpenAI API key

### 1. Clone and Setup

```bash
git clone <repository-url>
cd contract-intelligence-system

# Copy environment template
cp .env.example .env

# Add your OpenAI API key
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

### 2. Start with Docker

```bash
# Build and start all services
make up

# Or manually:
docker-compose up -d
```

The API will be available at `http://localhost:8000`

### 3. Verify Installation

```bash
# Check health
curl http://localhost:8000/healthz

# View API documentation
open http://localhost:8000/docs
```

## API Endpoints

### 📄 Ingest Documents

Upload one or more PDF contracts:

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "files=@contract1.pdf" \
  -F "files=@contract2.pdf"
```

**Response:**
```json
{
  "documents": [
    {
      "document_id": "123e4567-e89b-12d3-a456-426614174000",
      "filename": "contract1.pdf",
      "status": "completed",
      "page_count": 10
    }
  ]
}
```

### 🔍 Extract Structured Data

Extract key fields from a document:

```bash
curl -X POST http://localhost:8000/api/v1/extract \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "123e4567-e89b-12d3-a456-426614174000"
  }'
```

**Toggle LLM vs Rule-Based:**
```bash
# Use LLM extraction (default)
curl -X POST http://localhost:8000/api/v1/extract?use_llm=true \
  -H "Content-Type: application/json" \
  -d '{"document_id": "..."}'

# Use rule-based extraction (faster, no API calls)
curl -X POST http://localhost:8000/api/v1/extract?use_llm=false \
  -H "Content-Type: application/json" \
  -d '{"document_id": "..."}'
```

**Response:**
```json
{
  "document_id": "123e4567-e89b-12d3-a456-426614174000",
  "extracted_data": {
    "parties": ["TechCorp Inc.", "ServiceProvider LLC"],
    "effective_date": "2024-01-01",
    "term": "24 months",
    "governing_law": "State of California",
    "payment_terms": "$10,000 USD monthly",
    "termination": "60 days written notice",
    "auto_renewal": "12-month periods with 90 days notice",
    "confidentiality": "Both parties maintain confidentiality",
    "indemnity": "Mutual indemnification",
    "liability_cap": {
      "amount": 120000,
      "currency": "USD"
    },
    "signatories": [
      {"name": "John Smith", "title": "CEO"}
    ]
  }
}
```

### 💬 Ask Questions (RAG)

Ask questions about ingested contracts:

```bash
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the payment terms?",
    "document_ids": ["123e4567-e89b-12d3-a456-426614174000"]
  }'
```

**Response:**
```json
{
  "question": "What are the payment terms?",
  "answer": "The payment terms are $10,000 USD monthly, payable within 30 days of invoice.",
  "sources": [
    {
      "document_id": "123e4567-e89b-12d3-a456-426614174000",
      "page": 2,
      "relevance_score": 0.95
    }
  ]
}
```

### 🌊 Streaming Q&A (WebSocket)

Get real-time streaming responses via WebSocket:

**Using `websocat` (WebSocket CLI tool):**
```bash
# Install: cargo install websocat
echo '{"question": "What are the payment terms?", "document_ids": ["123e4567-e89b-12d3-a456-426614174000"]}' | \
  websocat ws://localhost:8000/api/v1/ask/stream
```

**Using Python:**
```python
import asyncio
import websockets
import json

async def stream_question():
    uri = "ws://localhost:8000/api/v1/ask/stream"
    async with websockets.connect(uri) as websocket:
        # Send question
        await websocket.send(json.dumps({
            "question": "What are the payment terms?",
            "document_ids": ["123e4567-e89b-12d3-a456-426614174000"]
        }))

        # Receive streaming response
        while True:
            message = await websocket.recv()
            data = json.loads(message)

            if data["type"] == "token":
                print(data["content"], end="", flush=True)
            elif data["type"] == "done":
                print()  # New line
                break
            elif data["type"] == "error":
                print(f"Error: {data['content']}")
                break

asyncio.run(stream_question())
```

**Response Format:**
- `{"type": "token", "content": "partial text"}` - Streaming tokens
- `{"type": "done", "content": ""}` - Stream complete
- `{"type": "error", "content": "error message"}` - Error occurred

### ⚠️ Audit for Risks

Detect risky clauses:

```bash
curl -X POST http://localhost:8000/api/v1/audit \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "123e4567-e89b-12d3-a456-426614174000"
  }'
```

**Toggle LLM vs Rule-Based:**
```bash
# LLM-based audit (more accurate)
curl -X POST http://localhost:8000/api/v1/audit?use_llm=true \
  -H "Content-Type: application/json" \
  -d '{"document_id": "..."}'

# Rule-based audit (faster)
curl -X POST http://localhost:8000/api/v1/audit?use_llm=false \
  -H "Content-Type: application/json" \
  -d '{"document_id": "..."}'
```

**Response:**
```json
{
  "document_id": "123e4567-e89b-12d3-a456-426614174000",
  "findings": [
    {
      "finding_type": "auto_renewal",
      "severity": "medium",
      "description": "Contract auto-renews with less than 90 days notice",
      "evidence_text": "automatically renew... 30 days notice",
      "recommendation": "Negotiate longer notice period (90+ days)"
    },
    {
      "finding_type": "unlimited_liability",
      "severity": "high",
      "description": "No liability cap specified",
      "evidence_text": null,
      "recommendation": "Add liability cap clause"
    }
  ],
  "total_findings": 2,
  "risk_score": 6.5
}
```

### 🔔 Webhooks

Register a webhook to receive event notifications:

```bash
# Register webhook
curl -X POST http://localhost:8000/api/v1/webhook/register \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-server.com/webhook",
    "events": ["document.ingested", "audit.completed"],
    "secret": "optional-secret-key"
  }'

# List webhooks
curl http://localhost:8000/api/v1/webhook/list

# Test webhook
curl -X POST "http://localhost:8000/api/v1/webhook/test?url=https://httpbin.org/post"
```

### 📊 Admin & Monitoring

```bash
# Health check
curl http://localhost:8000/healthz

# Metrics
curl http://localhost:8000/metrics

# Prometheus metrics
curl http://localhost:8000/metrics/prometheus

# Reset metrics
curl -X POST http://localhost:8000/metrics/reset
```

## Environment Variables

Create a `.env` file with:

```bash
# Required
OPENAI_API_KEY=sk-your-key-here

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/contracts

# Application
APP_NAME=Contract Intelligence System
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Vector Store
VECTOR_STORE_TYPE=chroma  # or qdrant
CHROMA_PERSIST_DIR=./data/chroma

# LLM Settings
LLM_MODEL=gpt-4-turbo-preview
LLM_TEMPERATURE=0.0
MAX_TOKENS=2000

# Processing
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_CHUNKS_PER_QUERY=5
```

## Project Structure

```
.
├── app/
│   ├── api/              # API endpoints
│   │   ├── ingest.py
│   │   ├── extract.py
│   │   ├── ask.py
│   │   ├── audit.py
│   │   ├── webhook.py
│   │   └── admin.py
│   ├── core/             # Core configuration
│   │   ├── config.py
│   │   ├── database.py
│   │   └── logging_config.py
│   ├── models/           # Database models & schemas
│   │   ├── document.py
│   │   └── schemas.py
│   ├── services/         # Business logic
│   │   ├── pdf_processor.py
│   │   ├── extraction_service.py
│   │   ├── rag_service.py
│   │   ├── vector_store.py
│   │   └── audit_service.py
│   └── main.py           # Application entry point
├── alembic/              # Database migrations
├── tests/                # Tests
│   ├── unit/
│   └── integration/
├── eval/                 # Evaluation framework
├── prompts/              # LLM prompts
├── sample_contracts/     # Sample PDFs
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── README.md
```

## Development

### Local Development (without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
# Run all tests
make test

# Or manually:
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_extraction_service.py -v
```

### Running Evaluation

```bash
# Ingest test documents first
curl -X POST http://localhost:8000/api/v1/ingest -F "files=@sample_contracts/test.pdf"

# Run evaluation with document IDs
python eval/run_evaluation.py <document_id_1> <document_id_2>

# View results
cat eval/SCORE.txt
```

## Makefile Commands

```bash
make up          # Start all services
make down        # Stop all services
make logs        # View logs
make build       # Build Docker images
make test        # Run tests
make migrate     # Run database migrations
make shell       # Open Python shell
make clean       # Clean up containers and volumes
```

## Architecture & Trade-offs

### LLM vs Rule-Based Extraction

**LLM Extraction** (use_llm=true):
- ✅ More accurate for complex contracts
- ✅ Handles variations in format
- ✅ Better at understanding context
- ❌ Slower (API call required)
- ❌ Costs money per request
- ❌ Requires internet connectivity

**Rule-Based Extraction** (use_llm=false):
- ✅ Fast and deterministic
- ✅ No API costs
- ✅ Works offline
- ✅ Predictable results
- ❌ Less flexible
- ❌ May miss edge cases
- ❌ Requires pattern maintenance

**Trade-off Decision**: Default to LLM with rule-based fallback for robustness.

### Vector Store Choice

**ChromaDB** (Default):
- ✅ Simple, no external service
- ✅ Good for development/testing
- ✅ Persistent storage
- ❌ Not ideal for production scale

**Qdrant**:
- ✅ Production-ready
- ✅ Better performance at scale
- ✅ Advanced filtering
- ❌ Requires separate service

**Trade-off Decision**: ChromaDB for simplicity, easy to switch to Qdrant.

### Chunking Strategy

- **Chunk Size**: 1000 tokens
  - Balances context vs granularity
  - Fits within embedding model limits

- **Overlap**: 200 tokens
  - Prevents information loss at boundaries
  - Improves retrieval quality

**Trade-off**: Larger chunks = more context but less precise retrieval.

### Security Considerations

1. **PII Redaction**: Automatic redaction of emails, SSNs, etc. in logs
2. **Input Validation**: Pydantic schemas validate all inputs
3. **SQL Injection**: SQLAlchemy ORM prevents injection
4. **API Rate Limiting**: TODO - Should add for production
5. **Authentication**: TODO - Should add for production

### Scalability

**Current**: Single-server deployment suitable for:
- Development/testing
- Small teams (< 100 users)
- < 1000 documents

**For Production Scale**:
- Add Redis for caching
- Use Celery for async processing
- Deploy multiple API instances
- Use managed Postgres (RDS/Cloud SQL)
- Add CDN for static content

## Known Limitations

1. **PDF Processing**: Complex tables may not extract perfectly
2. **Language**: Optimized for English contracts only
3. **LLM Dependency**: Requires OpenAI API (could add local LLM support)
4. **Authentication**: Not implemented (should use OAuth2/JWT in production)
5. **Rate Limiting**: Not implemented (should add for production)

## Troubleshooting

### "Connection refused" errors
```bash
# Ensure services are running
docker-compose ps

# Check logs
docker-compose logs api
```

### "OpenAI API error"
```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Check .env file
cat .env | grep OPENAI_API_KEY
```

### Database migration errors
```bash
# Reset database
docker-compose down -v
docker-compose up -d
make migrate
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Run tests: `make test`
5. Submit pull request

## License

MIT License - See LICENSE file for details

## Contact

For questions or issues, please open a GitHub issue.
