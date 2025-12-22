# Design Document: Document Extraction System

**Feature:** Document Upload and Structured Data Extraction System
**Version:** 1.0
**Date:** December 20, 2025
**Author:** Architecture Team
**Status:** DRAFT - Pending Approval

---

## 1. Executive Summary

### Overview

This design document specifies a document processing system that allows users to upload PDF and image files, extract all information in tabular format, and organize extracted data into two linked sections:

1. **Person Demographics** - Name, gender, date of birth, ID, etc.
2. **Associated Information** - All other data linked to the person

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| OCR Engine | docTR | Best accuracy, Apache 2.0 license, PyTorch ecosystem |
| PDF Library | pypdf | BSD license, pure Python, no AGPL concerns |
| NER Library | spaCy | Industry standard, MIT license, excellent performance |
| LLM Extraction | Ollama + LLaVA | Local processing, privacy-preserving, no API costs |
| Processing | Async (Celery) | Non-blocking UI, scalable workers |
| Storage | PostgreSQL + MinIO | Structured data + original files |

### Success Criteria

- Process PDF/image uploads within 30 seconds for typical documents
- Extract demographics with >90% accuracy on typed documents
- Provide intuitive 3-step user journey (Upload -> Process -> View Results)
- Zero PII exposure to external services (local-first processing)

---

## 2. Requirements Specification

### 2.1 Business Objectives

| ID | Objective | Priority |
|----|-----------|----------|
| BO-1 | Extract all document information into structured tables | MUST |
| BO-2 | Separate person demographics into dedicated section | MUST |
| BO-3 | Link associated information to person records | MUST |
| BO-4 | Support PDF and image file formats | MUST |
| BO-5 | Fast processing (user-perceived < 30s) | SHOULD |
| BO-6 | Easy, intuitive UX/UI | MUST |

### 2.2 Functional Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-1 | File Upload | Accept PDF, PNG, JPG, JPEG, TIFF files up to 50MB |
| FR-2 | OCR Processing | Extract text from scanned/image-based documents |
| FR-3 | Demographics Extraction | Identify: Name, Gender, DOB, ID numbers, Address, Phone, Email |
| FR-4 | Data Structuring | Present all data in table format with field labels |
| FR-5 | Person-Data Linking | Foreign key relationship between demographics and associated data |
| FR-6 | Progress Indication | Real-time processing status updates |
| FR-7 | Result Display | Tabular view with section separation |
| FR-8 | Data Export | Export results as JSON/CSV |

### 2.3 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Response Time | < 30s for 10-page PDF |
| NFR-2 | Availability | 99.5% uptime |
| NFR-3 | Concurrent Users | Support 50 simultaneous uploads |
| NFR-4 | File Size Limit | 50MB per file |
| NFR-5 | Data Retention | 30 days default, configurable |
| NFR-6 | Security | HTTPS, encrypted storage, audit logs |

### 2.4 Constraints

| Type | Constraint |
|------|------------|
| Technical | Must integrate with existing FastAPI + Streamlit stack |
| Technical | Must use PostgreSQL for structured data |
| Technical | GPU recommended but not required |
| Legal | No AGPL dependencies (commercial use) |
| Regulatory | GDPR-compliant PII handling |
| Budget | Prefer local/open-source over paid APIs |

### 2.5 Assumptions

| ID | Assumption | Must Validate |
|----|------------|---------------|
| A-1 | Documents are primarily in English | No |
| A-2 | Most documents are typed, not handwritten | Yes - POC needed |
| A-3 | Demographics follow common formats (dates, IDs) | No |
| A-4 | Server has at least 16GB RAM | No |
| A-5 | GPU available for production deployment | Yes - confirm |

---

## 3. Architecture Design

### 3.1 System Boundaries

```
+------------------------------------------------------------------+
|                        SYSTEM BOUNDARY                            |
|                                                                   |
|  +-------------+     +----------------+     +------------------+  |
|  |  Streamlit  |<--->|    FastAPI     |<--->|   PostgreSQL     |  |
|  |  Frontend   |     |    Backend     |     |   (Structured)   |  |
|  +-------------+     +-------+--------+     +------------------+  |
|                              |                                    |
|                              v                                    |
|                      +-------+--------+     +------------------+  |
|                      |     Celery     |<--->|      Redis       |  |
|                      |    Workers     |     |   (Queue/Cache)  |  |
|                      +-------+--------+     +------------------+  |
|                              |                                    |
|                              v                                    |
|  +-------------+     +-------+--------+     +------------------+  |
|  |    MinIO    |<--->|   Processing   |<--->|     Ollama       |  |
|  |  (Files)    |     |    Pipeline    |     |   (LLM Local)    |  |
|  +-------------+     +----------------+     +------------------+  |
|                                                                   |
+------------------------------------------------------------------+
                              |
                              v (Optional Fallback)
                    +------------------+
                    |   OpenAI API     |
                    |   (Cloud LLM)    |
                    +------------------+
```

### 3.2 Component Interactions

```
User Journey Flow:

[User] --> [Streamlit Upload Page]
              |
              | 1. Select file(s)
              v
        [File Validation]
              |
              | 2. Validate type, size
              v
        [FastAPI Endpoint]
              |
              | 3. Store in MinIO, create job
              v
        [Celery Task Queue]
              |
              | 4. Async processing
              v
        [Processing Pipeline]
              |
              +---> [pypdf] PDF to images
              |
              +---> [docTR] OCR extraction
              |
              +---> [spaCy] NER demographics
              |
              +---> [Ollama/LLM] Structured extraction
              |
              v
        [PostgreSQL Storage]
              |
              | 5. Store results
              v
        [Streamlit Results Page]
              |
              | 6. Display tables
              v
         [User Views Results]
```

### 3.3 Data Flow

```
Input Flow:
+-----------+     +-----------+     +-----------+     +-----------+
|   File    | --> |   MinIO   | --> |  Celery   | --> | Pipeline  |
| (PDF/IMG) |     | (Storage) |     |  (Queue)  |     | (Process) |
+-----------+     +-----------+     +-----------+     +-----------+

Processing Flow:
+-----------+     +-----------+     +-----------+     +-----------+
|   pypdf   | --> |   docTR   | --> |   spaCy   | --> |  Ollama   |
| (PDF->Img)|     |   (OCR)   |     |   (NER)   |     |  (Struct) |
+-----------+     +-----------+     +-----------+     +-----------+

Output Flow:
+-----------+     +-----------+     +-----------+
| Extracted | --> |PostgreSQL | --> | Streamlit |
|   Data    |     | (Tables)  |     |  (Display)|
+-----------+     +-----------+     +-----------+
```

### 3.4 Data Models

#### 3.4.1 Document Model

```python
class Document(Base):
    """Uploaded document metadata"""
    __tablename__ = "documents"

    id: UUID = Column(UUID, primary_key=True, default=uuid4)
    filename: str = Column(String(255), nullable=False)
    file_type: str = Column(String(50), nullable=False)  # pdf, png, jpg
    file_size: int = Column(Integer, nullable=False)
    storage_path: str = Column(String(500), nullable=False)  # MinIO path
    status: str = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message: str = Column(Text, nullable=True)
    uploaded_by: UUID = Column(UUID, ForeignKey("users.id"), nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    persons = relationship("Person", back_populates="document")
    raw_extractions = relationship("RawExtraction", back_populates="document")
```

#### 3.4.2 Person Demographics Model

```python
class Person(Base):
    """Extracted person demographics - Section 1"""
    __tablename__ = "persons"

    id: UUID = Column(UUID, primary_key=True, default=uuid4)
    document_id: UUID = Column(UUID, ForeignKey("documents.id"), nullable=False)

    # Demographics fields
    full_name: str = Column(String(255), nullable=True)
    first_name: str = Column(String(100), nullable=True)
    last_name: str = Column(String(100), nullable=True)
    gender: str = Column(String(20), nullable=True)
    date_of_birth: date = Column(Date, nullable=True)

    # Identification
    national_id: str = Column(String(100), nullable=True)
    passport_number: str = Column(String(100), nullable=True)
    driver_license: str = Column(String(100), nullable=True)

    # Contact
    email: str = Column(String(255), nullable=True)
    phone: str = Column(String(50), nullable=True)
    address: str = Column(Text, nullable=True)

    # Metadata
    confidence_score: float = Column(Float, default=0.0)
    extraction_source: str = Column(String(50))  # ocr, ner, llm
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="persons")
    associated_data = relationship("AssociatedData", back_populates="person")
```

#### 3.4.3 Associated Data Model

```python
class AssociatedData(Base):
    """Associated information linked to person - Section 2"""
    __tablename__ = "associated_data"

    id: UUID = Column(UUID, primary_key=True, default=uuid4)
    person_id: UUID = Column(UUID, ForeignKey("persons.id"), nullable=False)
    document_id: UUID = Column(UUID, ForeignKey("documents.id"), nullable=False)

    # Flexible key-value structure
    category: str = Column(String(100), nullable=False)  # employment, medical, financial, etc.
    field_name: str = Column(String(255), nullable=False)
    field_value: str = Column(Text, nullable=True)
    field_type: str = Column(String(50), default="text")  # text, number, date, currency

    # Source tracking
    page_number: int = Column(Integer, nullable=True)
    bounding_box: str = Column(String(255), nullable=True)  # JSON coordinates
    confidence_score: float = Column(Float, default=0.0)

    created_at: datetime = Column(DateTime, default=datetime.utcnow)

    # Relationships
    person = relationship("Person", back_populates="associated_data")
```

#### 3.4.4 Raw Extraction Model

```python
class RawExtraction(Base):
    """Raw OCR output for audit/debugging"""
    __tablename__ = "raw_extractions"

    id: UUID = Column(UUID, primary_key=True, default=uuid4)
    document_id: UUID = Column(UUID, ForeignKey("documents.id"), nullable=False)

    page_number: int = Column(Integer, nullable=False)
    raw_text: str = Column(Text, nullable=True)
    structured_json: str = Column(Text, nullable=True)  # JSON blob

    processing_time_ms: int = Column(Integer, nullable=True)
    ocr_engine: str = Column(String(50))  # doctr, tesseract, etc.

    created_at: datetime = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="raw_extractions")
```

### 3.5 State Management

```
Document Processing States:

    [PENDING] --> [UPLOADING] --> [QUEUED] --> [PROCESSING] --> [COMPLETED]
        |             |              |              |               |
        v             v              v              v               v
     (created)    (file save)   (celery job)   (pipeline)     (results)
        |             |              |              |
        +-------------+--------------+--------------+
                      |
                      v
                  [FAILED]
                      |
                      v
              (error_message)
```

---

## 4. API Contracts

### 4.1 Document Upload API

#### POST /api/v1/documents/upload

**Request:**
```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data
Authorization: Bearer <token>

file: <binary>
```

**Response (202 Accepted):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "passport_scan.pdf",
  "status": "queued",
  "message": "Document queued for processing",
  "estimated_time_seconds": 15,
  "links": {
    "status": "/api/v1/documents/550e8400-e29b-41d4-a716-446655440000/status",
    "result": "/api/v1/documents/550e8400-e29b-41d4-a716-446655440000/result"
  }
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": {
    "code": "INVALID_FILE_TYPE",
    "message": "File type not supported. Allowed: pdf, png, jpg, jpeg, tiff",
    "details": {
      "received_type": "application/zip",
      "allowed_types": ["application/pdf", "image/png", "image/jpeg", "image/tiff"]
    }
  }
}
```

### 4.2 Processing Status API

#### GET /api/v1/documents/{document_id}/status

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": {
    "current_step": "ocr_extraction",
    "steps_completed": 2,
    "total_steps": 4,
    "percentage": 50
  },
  "steps": [
    {"name": "file_validation", "status": "completed", "duration_ms": 120},
    {"name": "pdf_conversion", "status": "completed", "duration_ms": 2340},
    {"name": "ocr_extraction", "status": "in_progress", "duration_ms": null},
    {"name": "entity_extraction", "status": "pending", "duration_ms": null}
  ]
}
```

### 4.3 Results API

#### GET /api/v1/documents/{document_id}/result

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "passport_scan.pdf",
  "status": "completed",
  "processed_at": "2025-12-20T10:30:00Z",
  "processing_time_ms": 12450,

  "persons": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "demographics": {
        "full_name": "John Michael Smith",
        "first_name": "John",
        "last_name": "Smith",
        "gender": "Male",
        "date_of_birth": "1985-03-15",
        "national_id": "123-45-6789",
        "passport_number": "AB1234567",
        "email": "john.smith@email.com",
        "phone": "+1-555-123-4567",
        "address": "123 Main Street, New York, NY 10001"
      },
      "confidence_scores": {
        "full_name": 0.98,
        "date_of_birth": 0.95,
        "national_id": 0.92
      }
    }
  ],

  "associated_data": [
    {
      "person_id": "660e8400-e29b-41d4-a716-446655440001",
      "category": "employment",
      "fields": [
        {"name": "employer", "value": "Acme Corporation", "confidence": 0.94},
        {"name": "job_title", "value": "Software Engineer", "confidence": 0.91},
        {"name": "start_date", "value": "2020-01-15", "confidence": 0.88}
      ]
    },
    {
      "person_id": "660e8400-e29b-41d4-a716-446655440001",
      "category": "financial",
      "fields": [
        {"name": "bank_name", "value": "First National Bank", "confidence": 0.96},
        {"name": "account_type", "value": "Checking", "confidence": 0.93}
      ]
    }
  ],

  "raw_text": {
    "available": true,
    "link": "/api/v1/documents/550e8400-e29b-41d4-a716-446655440000/raw"
  }
}
```

### 4.4 Export API

#### GET /api/v1/documents/{document_id}/export?format={json|csv}

**Response (200 OK - CSV):**
```csv
section,field_name,field_value,confidence
demographics,full_name,John Michael Smith,0.98
demographics,date_of_birth,1985-03-15,0.95
associated,employer,Acme Corporation,0.94
associated,job_title,Software Engineer,0.91
```

### 4.5 Authentication

All endpoints require JWT authentication:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Scopes required:
- `documents:upload` - Upload new documents
- `documents:read` - View document results
- `documents:export` - Export document data

---

## 5. Technology Stack

### 5.1 Core Stack (Existing)

| Component | Technology | Version |
|-----------|------------|---------|
| Backend Framework | FastAPI | 0.121.2 |
| Frontend | Streamlit | 1.51.0 |
| Database | PostgreSQL | 17 |
| Cache/Queue | Redis | 8.2.0 |
| Object Storage | MinIO | Latest |
| Task Queue | Celery | 5.x |
| ORM | SQLAlchemy | 2.0+ |

### 5.2 New Dependencies

| Package | Version | License | Justification |
|---------|---------|---------|---------------|
| pypdf | ^6.4.2 | BSD-3 | PDF parsing, no AGPL issues |
| python-doctr | ^1.0.0 | Apache 2.0 | Best OCR accuracy, PyTorch ecosystem |
| spacy | ^3.8.11 | MIT | Industry-standard NER |
| pdf2image | ^1.17.0 | MIT | PDF to image conversion |
| pillow | ^10.0.0 | HPND | Image processing |
| poppler-utils | System | GPL-2 | Required by pdf2image (system dep) |

### 5.3 Optional Dependencies

| Package | Version | License | When to Use |
|---------|---------|---------|-------------|
| ollama | Latest | MIT | Local LLM extraction |
| openai | ^1.0.0 | MIT | Cloud LLM fallback |
| torch | ^2.0.0 | BSD | GPU acceleration for docTR |

### 5.4 Environment Requirements

| Environment | Requirement |
|-------------|-------------|
| Python | >= 3.10 |
| RAM | Minimum 8GB, Recommended 16GB |
| GPU | Optional but recommended (CUDA 12.2) |
| Disk | 20GB for models and cache |
| Docker | Recommended for deployment |

---

## 6. Security Design

### 6.1 Threat Model (STRIDE)

| Threat | Category | Mitigation |
|--------|----------|------------|
| Malicious file upload | Tampering | MIME validation, file scanning, size limits |
| PII data exposure | Information Disclosure | Local processing, encryption, access control |
| Unauthorized access | Spoofing | JWT authentication, role-based access |
| Processing DoS | Denial of Service | Rate limiting, queue limits, timeouts |
| Data integrity | Tampering | Checksums, audit logs |
| Privilege escalation | Elevation | Principle of least privilege, input validation |

### 6.2 OWASP Top 10 Mitigations

| Risk | Mitigation |
|------|------------|
| A01: Broken Access Control | JWT with scopes, document ownership validation |
| A02: Cryptographic Failures | TLS 1.3, AES-256 at rest, secure key management |
| A03: Injection | Parameterized queries, input sanitization |
| A04: Insecure Design | Security reviews, threat modeling |
| A05: Security Misconfiguration | Hardened Docker images, security headers |
| A06: Vulnerable Components | Dependency scanning, regular updates |
| A07: Auth Failures | Strong passwords, JWT expiration, refresh tokens |
| A08: Data Integrity Failures | Signed uploads, integrity verification |
| A09: Logging Failures | Structured logging, audit trail |
| A10: SSRF | URL validation, network segmentation |

### 6.3 PII Handling

```
PII Processing Flow:

[Document Upload]
       |
       v
[Server-side ONLY] <-- Never send to browser before processing
       |
       v
[Local OCR (docTR)] <-- No external API calls
       |
       v
[Local NER (spaCy)] <-- No external API calls
       |
       v
[Local LLM (Ollama)] <-- Privacy-preserving
       |
       v
[Encrypted Storage] <-- AES-256
       |
       v
[Access-controlled API] <-- JWT + ownership check
```

### 6.4 File Upload Security

```python
# Validation rules
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff"
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_FILES_PER_REQUEST = 10

# Validation steps:
# 1. Check file extension
# 2. Validate MIME type (magic bytes)
# 3. Check file size
# 4. Scan for malware (optional: ClamAV)
# 5. Generate unique storage path (no user input in path)
```

---

## 7. Performance Plan

### 7.1 Performance Requirements

| Metric | Target | Maximum |
|--------|--------|---------|
| Upload response time | < 2s | 5s |
| Processing time (10 pages) | < 30s | 60s |
| Status check latency | < 100ms | 500ms |
| Results fetch latency | < 500ms | 2s |
| Concurrent uploads | 50 | 100 |

### 7.2 Bottleneck Analysis

| Component | Bottleneck Risk | Mitigation |
|-----------|-----------------|------------|
| OCR (docTR) | HIGH - CPU/GPU intensive | GPU acceleration, batch processing |
| LLM (Ollama) | MEDIUM - Memory intensive | Model caching, request queuing |
| File I/O | LOW - MinIO optimized | Async uploads, streaming |
| Database | LOW - Simple queries | Connection pooling, indexing |

### 7.3 Optimization Strategies

1. **GPU Acceleration**
   - docTR with CUDA 12.2
   - Batch page processing
   - Model warm-up on startup

2. **Async Processing**
   - Celery workers for OCR tasks
   - Non-blocking file uploads
   - WebSocket for real-time status

3. **Caching**
   - Redis for processing status
   - Model caching in memory
   - Result caching (TTL: 1 hour)

4. **Resource Limits**
   - Max 5 concurrent OCR tasks per worker
   - Memory limits per Celery worker
   - Timeout: 120s per document

### 7.4 Scaling Strategy

```
Horizontal Scaling:

                    +------------------+
                    |   Load Balancer  |
                    +--------+---------+
                             |
            +----------------+----------------+
            |                |                |
     +------v------+  +------v------+  +------v------+
     |  FastAPI 1  |  |  FastAPI 2  |  |  FastAPI N  |
     +------+------+  +------+------+  +------+------+
            |                |                |
            +----------------+----------------+
                             |
                    +--------v---------+
                    |      Redis       |
                    | (Queue + Cache)  |
                    +--------+---------+
                             |
            +----------------+----------------+
            |                |                |
     +------v------+  +------v------+  +------v------+
     |  Worker 1   |  |  Worker 2   |  |  Worker N   |
     |  (GPU)      |  |  (GPU)      |  |  (CPU)      |
     +-------------+  +-------------+  +-------------+
```

---

## 8. Risk Register

| ID | Risk | Probability | Impact | Mitigation | Owner |
|----|------|-------------|--------|------------|-------|
| R-1 | OCR accuracy below 90% on handwritten docs | HIGH | HIGH | LLM fallback, user correction UI | Tech Lead |
| R-2 | GPU not available in production | MEDIUM | MEDIUM | CPU fallback mode (slower), cloud GPU option | DevOps |
| R-3 | Ollama model too large for memory | LOW | MEDIUM | Use smaller model variant, quantization | Tech Lead |
| R-4 | Processing timeout on large documents | MEDIUM | LOW | Page limits, chunked processing | Backend Dev |
| R-5 | PII compliance violation | LOW | HIGH | Local processing only, audit logs, encryption | Security |
| R-6 | License compliance (AGPL) | LOW | HIGH | Avoided PyMuPDF, using BSD/MIT/Apache only | Legal |
| R-7 | Third-party API dependency | LOW | MEDIUM | Local-first design, API is optional fallback | Architect |
| R-8 | Model updates break extraction | MEDIUM | MEDIUM | Version pinning, regression tests | QA |

### Fallback Plans

| Risk | Fallback |
|------|----------|
| OCR fails | Return raw text, flag for manual review |
| LLM unavailable | Use rule-based extraction (regex patterns) |
| GPU unavailable | CPU mode with longer timeouts |
| Storage full | Alert, reject new uploads, cleanup old files |

---

## 9. Implementation Roadmap

### Phase 1: Foundation (MVP)

**Scope:** Basic upload and OCR extraction

| Task | Description | Priority |
|------|-------------|----------|
| 1.1 | Database migrations (Document, RawExtraction) | P0 |
| 1.2 | MinIO integration for file storage | P0 |
| 1.3 | File upload API endpoint | P0 |
| 1.4 | pypdf + docTR integration | P0 |
| 1.5 | Celery task for async processing | P0 |
| 1.6 | Basic Streamlit upload UI | P0 |
| 1.7 | Processing status endpoint | P0 |

**Deliverable:** Users can upload PDF/images and see raw OCR text

### Phase 2: Entity Extraction

**Scope:** Demographics extraction and structuring

| Task | Description | Priority |
|------|-------------|----------|
| 2.1 | Person and AssociatedData models | P0 |
| 2.2 | spaCy NER integration | P0 |
| 2.3 | Demographics field mapping | P0 |
| 2.4 | Confidence scoring | P1 |
| 2.5 | Results API endpoint | P0 |
| 2.6 | Streamlit results display | P0 |

**Deliverable:** Extracted demographics in structured format

### Phase 3: LLM Enhancement

**Scope:** Intelligent extraction with Ollama

| Task | Description | Priority |
|------|-------------|----------|
| 3.1 | Ollama integration | P0 |
| 3.2 | Structured extraction prompts | P0 |
| 3.3 | Associated data categorization | P0 |
| 3.4 | Fallback to cloud LLM (optional) | P2 |
| 3.5 | Extraction quality validation | P1 |

**Deliverable:** Intelligent document understanding

### Phase 4: UX Polish

**Scope:** Production-ready user experience

| Task | Description | Priority |
|------|-------------|----------|
| 4.1 | Drag-and-drop upload | P1 |
| 4.2 | Real-time progress (WebSocket) | P1 |
| 4.3 | Export functionality (JSON/CSV) | P1 |
| 4.4 | Error handling and user feedback | P0 |
| 4.5 | Mobile-responsive design | P2 |
| 4.6 | Batch upload support | P2 |

**Deliverable:** Polished, user-friendly interface

### Phase 5: Production Hardening

**Scope:** Security, performance, monitoring

| Task | Description | Priority |
|------|-------------|----------|
| 5.1 | Security audit and fixes | P0 |
| 5.2 | Performance optimization | P1 |
| 5.3 | Monitoring and alerting | P1 |
| 5.4 | Documentation | P1 |
| 5.5 | Load testing | P1 |

**Deliverable:** Production-ready system

---

## 10. Open Questions

| ID | Question | Impact | Decision Needed By |
|----|----------|--------|-------------------|
| Q-1 | Should we support multi-language documents? | HIGH - affects OCR model choice | Phase 1 |
| Q-2 | Is GPU available in production environment? | MEDIUM - affects performance | Phase 1 |
| Q-3 | What is the expected document volume per day? | MEDIUM - affects scaling design | Phase 1 |
| Q-4 | Are there specific document types to prioritize? (passport, invoice, etc.) | MEDIUM - affects extraction rules | Phase 2 |
| Q-5 | Should extracted data be editable by users? | LOW - affects UI complexity | Phase 4 |
| Q-6 | What is the data retention policy? | MEDIUM - affects storage planning | Phase 5 |
| Q-7 | Is there a preference for cloud LLM provider as fallback? | LOW - OpenAI vs Claude | Phase 3 |

---

## Validation Checklist

- [x] Business requirements clearly mapped to technical solution
- [x] All integration points identified and specified
- [x] Security requirements addressed (STRIDE, OWASP)
- [x] Performance requirements defined
- [x] Risks identified with mitigation strategies
- [x] Implementation broken into manageable phases
- [x] Technology choices justified with evidence (see Research doc)
- [ ] **PENDING:** GPU availability confirmation
- [ ] **PENDING:** Expected document volume clarification
- [ ] **PENDING:** Multi-language support decision

---

## Appendix A: Pydantic Schemas

```python
# schemas/document.py

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class DocumentUploadResponse(BaseModel):
    id: UUID
    filename: str
    status: str
    message: str
    estimated_time_seconds: int
    links: dict

class ProcessingStep(BaseModel):
    name: str
    status: str  # pending, in_progress, completed, failed
    duration_ms: Optional[int]

class DocumentStatusResponse(BaseModel):
    id: UUID
    status: str
    progress: dict
    steps: List[ProcessingStep]

class DemographicsResponse(BaseModel):
    full_name: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    gender: Optional[str]
    date_of_birth: Optional[str]
    national_id: Optional[str]
    passport_number: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]

class AssociatedField(BaseModel):
    name: str
    value: str
    confidence: float

class AssociatedDataResponse(BaseModel):
    person_id: UUID
    category: str
    fields: List[AssociatedField]

class PersonResponse(BaseModel):
    id: UUID
    demographics: DemographicsResponse
    confidence_scores: dict

class DocumentResultResponse(BaseModel):
    id: UUID
    filename: str
    status: str
    processed_at: datetime
    processing_time_ms: int
    persons: List[PersonResponse]
    associated_data: List[AssociatedDataResponse]
```

---

## Appendix B: Environment Variables

```bash
# Document Processing Configuration
DOCUMENT_MAX_FILE_SIZE_MB=50
DOCUMENT_ALLOWED_EXTENSIONS=pdf,png,jpg,jpeg,tiff
DOCUMENT_PROCESSING_TIMEOUT_SECONDS=120
DOCUMENT_RETENTION_DAYS=30

# OCR Configuration
OCR_ENGINE=doctr  # doctr, tesseract, easyocr
OCR_USE_GPU=true
OCR_MODEL_PATH=/models/doctr

# NER Configuration
SPACY_MODEL=en_core_web_trf

# LLM Configuration
LLM_PROVIDER=ollama  # ollama, openai
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llava
OPENAI_API_KEY=  # Optional fallback

# Celery Configuration
CELERY_OCR_CONCURRENCY=5
CELERY_OCR_MEMORY_LIMIT_MB=4096
```

---

**Document Status:** DRAFT
**Next Action:** Review and approval required before implementation
**Approval Required From:** Tech Lead, Security, Product Owner
