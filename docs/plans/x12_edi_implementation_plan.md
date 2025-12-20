# X12 EDI Integration Implementation Plan

**Created**: December 19, 2025
**Design Reference**: [06_high_value_enhancements_design.md](../design/06_high_value_enhancements_design.md)
**Status**: APPROVED - In Progress
**Priority**: CRITICAL (Tier 1)

---

## Executive Summary

This plan implements X12 EDI integration for industry-standard claims processing, enabling:
- **837P/837I Parsing**: Receive professional and institutional claims
- **835 Generation**: Generate remittance advice for adjudicated claims
- **270/271 Eligibility**: Real-time member eligibility verification

---

## Phase 1.1: X12 Core Infrastructure

### Files to Create

```
src/services/edi/
├── __init__.py
├── x12_base.py              # Base X12 tokenizer and models
├── x12_837_parser.py        # 837P/837I claim parser
├── x12_835_generator.py     # 835 remittance generator
├── x12_270_builder.py       # 270 eligibility request builder
├── x12_271_parser.py        # 271 eligibility response parser
├── edi_validator.py         # X12 syntax validation
└── edi_service.py           # Main EDI orchestration service

src/models/
└── edi_transaction.py       # EDI transaction models

src/schemas/
└── edi.py                   # Pydantic schemas for EDI

src/api/routes/
└── edi.py                   # EDI API endpoints

database/migrations/flyway/
└── V4__add_edi_tables.sql   # EDI database tables
```

### Database Schema

```sql
-- EDI Transaction Log
CREATE TABLE edi_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    transaction_type VARCHAR(10) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    control_number VARCHAR(50) NOT NULL,
    sender_id VARCHAR(50),
    receiver_id VARCHAR(50),
    raw_content TEXT,
    parsed_claims_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'received',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

CREATE INDEX idx_edi_tenant ON edi_transactions(tenant_id);
CREATE INDEX idx_edi_control ON edi_transactions(control_number);
CREATE INDEX idx_edi_status ON edi_transactions(status);
```

### Implementation Order

1. X12 Base Parser (tokenizer, segment models)
2. 837P Professional Claims Parser
3. 837I Institutional Claims Parser
4. 835 Remittance Generator
5. API Endpoints
6. Integration Tests

---

## Acceptance Criteria

- [ ] Parse valid 837P claims with all required loops
- [ ] Parse valid 837I claims with all required loops
- [ ] Generate valid 835 remittance advice
- [ ] Handle batch transactions (multiple claims per file)
- [ ] Validate X12 syntax and return detailed errors
- [ ] Support ISA/GS envelope processing
- [ ] Log all EDI transactions for audit
- [ ] >95% test coverage for EDI module

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| None required | - | Custom implementation for full control |

Note: We're implementing a custom X12 parser for:
- Full control over parsing logic
- Better error messages
- Integration with existing models
- No external dependencies

---

## Timeline

| Task | Duration | Status |
|------|----------|--------|
| X12 Base Parser | 2 days | In Progress |
| 837P Parser | 3 days | Pending |
| 837I Parser | 2 days | Pending |
| 835 Generator | 2 days | Pending |
| API Endpoints | 1 day | Pending |
| Testing | 2 days | Pending |
| **Total** | **12 days** | |
