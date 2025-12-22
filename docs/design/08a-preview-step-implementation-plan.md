# Implementation Plan: Document Extraction Preview Step

**Feature:** Document Extraction Preview Step (Design Doc 08)
**Methodology:** 4-Pillar Implementation (implement.md v2.1)
**Date:** December 21, 2025
**Status:** PENDING APPROVAL

---

## Phase 1: Design-First Development (COMPLETED)

### 1.1 Design Document Reference

- **Design Document:** [08-document-extraction-preview-step-design.md](08-document-extraction-preview-step-design.md)
- **Status:** Approved for implementation
- **Version:** 1.1

### 1.2 Key Design Decisions Recap

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Step Position | After Processing (Step 2) | Natural flow - see extracted data before editing |
| View Modes | Summary + Detailed tabs | Quick overview + verification capability |
| Navigation | Back/Continue buttons | Flexible user control |
| Data Display | Read-only | Preview only, editing in Review step |
| Validation | None in Preview | All 19 rules execute at Submit step |

---

## Phase 2: Evidence-Based Development

### 2.1 Environment Understanding

| Aspect | Value | Location |
|--------|-------|----------|
| Frontend Framework | Angular 19.2.19 | `frontend/package.json` |
| UI Library | PrimeNG 17.18.x | `frontend/package.json` |
| Build Tool | Nx 20.x | `frontend/nx.json` |
| Dev Server Port | 4202 | `frontend/apps/claims-portal/project.json` |
| Backend Framework | FastAPI | `pyproject.toml` |
| Backend Port | 8002 | `docker/docker-compose.local.yml` |
| Development Mode | Docker + Local Angular | Hybrid |

**Build/Run Commands:**
```bash
# Frontend
cd frontend && npx nx serve claims-portal --port=4202

# Backend (Docker)
docker compose -f docker/docker-compose.local.yml up -d
```

### 2.2 Dependency Research

**No new dependencies required.** All functionality uses existing stack:

| Component | Existing Dependency | Version | Purpose |
|-----------|-------------------|---------|---------|
| Cards | PrimeNG CardModule | 17.18.x | Summary cards |
| Tabs | PrimeNG TabViewModule | 17.18.x | Summary/Detailed toggle |
| Accordion | PrimeNG AccordionModule | 17.18.x | Detailed view sections |
| Tags | PrimeNG TagModule | 17.18.x | Confidence badges |
| Buttons | PrimeNG ButtonModule | 17.18.x | Navigation |

### 2.3 Version Compatibility Matrix

| Dependency | Version | Requires | Verified With | Status |
|------------|---------|----------|---------------|--------|
| @angular/core | 19.2.19 | Node >= 18.19 | Node 20.x | ✅ Compatible |
| primeng | 17.18.11 | Angular 17-19 | Angular 19.2.19 | ✅ Compatible |
| @angular/forms | 19.2.19 | @angular/core 19 | 19.2.19 | ✅ Compatible |
| rxjs | 7.8.x | Angular 19 | 7.8.1 | ✅ Compatible |
| typescript | 5.4.x | Angular 19 | 5.4.5 | ✅ Compatible |

**Verification Commands:**
```bash
cd frontend && npm ls --all 2>&1 | grep -i "peer dep"  # Check peer deps
cd frontend && npm outdated                              # Check outdated
```

### 2.4 Cross-Stack Compatibility

| Layer A | Layer B | Check | Status |
|---------|---------|-------|--------|
| Angular 19.x | PrimeNG 17.18.x | Official support matrix | ✅ Verified |
| Angular 19.x | TypeScript 5.4.x | Angular peer deps | ✅ Verified |
| Angular | Signals | Built-in (Angular 17+) | ✅ Native |
| Preview Component | MergedExtractedData | Shared types | ✅ Existing |

### 2.5 URL/Port Configuration Verification

**Per config-compatibility.md standards:**

| Service | Port | Config Location | Status |
|---------|------|-----------------|--------|
| Frontend | 4202 | `project.json`, `proxy.conf.json` | ✅ Centralized |
| Backend API | 8002 | `.env`, `docker-compose.local.yml` | ✅ Centralized |
| Proxy Target | 8002 | `proxy.conf.json` | ✅ Verified |

**API Endpoints Used by Preview Step:**

| Endpoint | Method | Type | Config Variable | Consumer |
|----------|--------|------|-----------------|----------|
| (None) | - | - | - | Preview uses in-memory data |

**Note:** Preview step requires NO new API endpoints. It consumes `MergedExtractedData` already fetched during Processing step.

**Hardcoded URL Check:**
```bash
# Run before implementation
grep -rn "localhost:" --include="*.ts" frontend/apps/claims-portal/src/
grep -rn "127.0.0.1" --include="*.ts" frontend/apps/claims-portal/src/
```

---

## Phase 3: Test-Driven Implementation

### 3.1 Test Plan

#### Unit Tests (Write First)

| Test File | Test Cases | Priority |
|-----------|------------|----------|
| `step-preview-extraction.component.spec.ts` | Component creation, Input handling, Output events, Empty state | P0 |
| `preview-summary.component.spec.ts` | Card rendering, Confidence display, Data grouping | P0 |
| `preview-detailed.component.spec.ts` | Accordion expansion, Field rendering, Source display | P1 |
| `confidence-badge.component.spec.ts` | Color thresholds, Percentage formatting | P0 |

#### Test Cases for StepPreviewExtractionComponent

```typescript
describe('StepPreviewExtractionComponent', () => {
  // Creation
  it('should create the component');

  // Inputs
  it('should display extracted data when provided');
  it('should handle null mergedExtractedData gracefully');
  it('should show empty state when no data extracted');

  // Outputs
  it('should emit stepComplete when Continue clicked');
  it('should emit stepBack when Back clicked');

  // View Toggle
  it('should switch between Summary and Detailed views');
  it('should default to Summary view');

  // Confidence
  it('should count low confidence fields correctly');
  it('should display warning when low confidence fields exist');
});
```

#### Test Cases for ConfidenceBadgeComponent

```typescript
describe('ConfidenceBadgeComponent', () => {
  it('should display green for scores >= 80%');
  it('should display yellow for scores 50-79%');
  it('should display red for scores < 50%');
  it('should format percentage correctly');
  it('should handle undefined score');
});
```

### 3.2 Implementation Tasks

#### Task 1: Create ConfidenceBadgeComponent (Shared)

**Location:** `frontend/apps/claims-portal/src/app/shared/components/confidence-badge/`

**Files:**
- `confidence-badge.component.ts`
- `confidence-badge.component.spec.ts`

**Implementation:**
```typescript
@Component({
  selector: 'app-confidence-badge',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span class="confidence-badge" [class]="confidenceClass">
      {{ formattedScore }}
    </span>
  `,
  styles: [`
    .confidence-badge {
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
    }
    .confidence-high { background: #d4edda; color: #155724; }
    .confidence-medium { background: #fff3cd; color: #856404; }
    .confidence-low { background: #f8d7da; color: #721c24; }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ConfidenceBadgeComponent {
  @Input() score: number | undefined = 0;

  get confidenceClass(): string {
    const s = this.score ?? 0;
    if (s >= 0.8) return 'confidence-high';
    if (s >= 0.5) return 'confidence-medium';
    return 'confidence-low';
  }

  get formattedScore(): string {
    return `${Math.round((this.score ?? 0) * 100)}%`;
  }
}
```

#### Task 2: Create PreviewSummaryComponent

**Location:** `frontend/apps/claims-portal/src/app/features/claims/components/claim-submit/step-preview-extraction/`

**Files:**
- `preview-summary.component.ts`
- `preview-summary.component.spec.ts`

**Key Features:**
- Patient Information Card
- Provider Information Card
- Clinical Data Card (Diagnoses + Procedures)
- Financial Summary Card
- Confidence badges per field

#### Task 3: Create PreviewDetailedComponent

**Location:** Same as Task 2

**Files:**
- `preview-detailed.component.ts`
- `preview-detailed.component.spec.ts`

**Key Features:**
- Accordion sections per category
- Field-level confidence scores
- Source indicators (OCR/LLM)
- Page references

#### Task 4: Create StepPreviewExtractionComponent (Main)

**Location:** Same as Task 2

**Files:**
- `step-preview-extraction.component.ts`
- `step-preview-extraction.component.spec.ts`

**Key Features:**
- TabView for Summary/Detailed toggle
- Low confidence warning message
- Navigation buttons (Back/Continue)
- Integration with child components

#### Task 5: Update ClaimSubmitComponent (Wizard)

**File:** `frontend/apps/claims-portal/src/app/features/claims/components/claim-submit/claim-submit.component.ts`

**Changes:**
1. Add Preview step to steps array (position 2)
2. Update step indices for Review and Submit
3. Add @switch case for Preview step
4. Update navigation logic for 5 steps

**Before:**
```typescript
readonly steps: MenuItem[] = [
  { label: 'Upload Documents', icon: 'pi pi-upload' },
  { label: 'Processing', icon: 'pi pi-cog' },
  { label: 'Review Data', icon: 'pi pi-pencil' },
  { label: 'Submit', icon: 'pi pi-check-square' },
];
```

**After:**
```typescript
readonly steps: MenuItem[] = [
  { label: 'Upload Documents', icon: 'pi pi-upload' },
  { label: 'Processing', icon: 'pi pi-cog' },
  { label: 'Preview Extraction', icon: 'pi pi-eye' },  // NEW
  { label: 'Review Data', icon: 'pi pi-pencil' },
  { label: 'Submit', icon: 'pi pi-check-square' },
];
```

#### Task 6: Fix PDF-to-Image Conversion (Backend Prerequisite)

**File:** `src/services/document_processor.py`

**Implementation:**
```python
async def _process_pdf_to_images(self, pdf_bytes: bytes) -> list[bytes]:
    """Convert PDF pages to PNG images for OCR processing."""
    import fitz  # PyMuPDF

    images = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        mat = fitz.Matrix(300/72, 300/72)  # 300 DPI
        pix = page.get_pixmap(matrix=mat)
        images.append(pix.tobytes("png"))

    doc.close()
    return images
```

---

## Phase 4: Quality-First Delivery

### 4.1 Quality Checklist

#### Code Quality
- [ ] All components use OnPush change detection
- [ ] All components are standalone
- [ ] No hardcoded URLs/ports introduced
- [ ] Proper error handling for null/undefined data
- [ ] Consistent naming conventions
- [ ] No console.log statements

#### Testing
- [ ] All unit tests passing
- [ ] Code coverage >= 80% for new components
- [ ] E2E test for wizard flow updated

#### Performance
- [ ] Lazy loading for preview components
- [ ] TrackBy functions for ngFor loops
- [ ] No unnecessary re-renders

#### Accessibility
- [ ] ARIA labels on interactive elements
- [ ] Keyboard navigation support
- [ ] Color contrast meets WCAG 2.1 AA

#### Security
- [ ] No sensitive data logged
- [ ] XSS protection maintained
- [ ] Same auth requirements as existing flow

### 4.2 Deliverables Checklist

| Deliverable | Files | Status |
|-------------|-------|--------|
| ConfidenceBadgeComponent | 2 files (.ts, .spec.ts) | Pending |
| PreviewSummaryComponent | 2 files | Pending |
| PreviewDetailedComponent | 2 files | Pending |
| StepPreviewExtractionComponent | 2 files | Pending |
| ClaimSubmitComponent Updates | 1 file modified | Pending |
| PDF-to-Image Fix (Backend) | 1 file modified | Pending |
| Unit Tests | 4 spec files | Pending |

### 4.3 URL/API Configuration Report

| Check | Result |
|-------|--------|
| New endpoints added | None |
| Hardcoded URLs introduced | None |
| Config variables used | N/A (no API calls) |
| Interface-to-API mapping | N/A (in-memory data) |

---

## Implementation Order

### Recommended Sequence

```
┌─────────────────────────────────────────────────────────────────────┐
│                    IMPLEMENTATION SEQUENCE                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  PREREQUISITE (Backend):                                             │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Task 6: PDF-to-Image Conversion Fix                           │   │
│  │ File: src/services/document_processor.py                      │   │
│  │ Reason: Preview needs accurate extraction data                │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  PHASE A (Shared Component):                                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Task 1: ConfidenceBadgeComponent                              │   │
│  │ Write tests first, then implement                             │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  PHASE B (Child Components - Parallel):                              │
│  ┌─────────────────────┐    ┌─────────────────────────────────┐     │
│  │ Task 2: Preview     │    │ Task 3: Preview                 │     │
│  │ Summary Component   │    │ Detailed Component              │     │
│  └─────────────────────┘    └─────────────────────────────────┘     │
│                              │                                       │
│                              ▼                                       │
│  PHASE C (Main Component):                                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Task 4: StepPreviewExtractionComponent                        │   │
│  │ Integrates Tasks 1, 2, 3                                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  PHASE D (Integration):                                              │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Task 5: Update ClaimSubmitComponent Wizard                    │   │
│  │ Add step, update indices, add template case                   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  PHASE E (Testing & Validation):                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Run all tests, verify wizard flow, check performance          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| MergedExtractedData missing confidence | MEDIUM | HIGH | Add default values, show "N/A" |
| State loss on navigation | LOW | MEDIUM | Use existing wizard state management |
| Performance with large documents | LOW | MEDIUM | Virtual scrolling in detailed view |
| OCR still failing (PDF fix) | LOW | HIGH | Implement PDF-to-image fix first |

---

## Approval Checklist

Before proceeding with implementation:

- [ ] Design document (08) approved
- [ ] Implementation plan reviewed
- [ ] No blocking dependencies
- [ ] Test strategy approved
- [ ] PDF-to-image fix approved for backend

---

## Next Steps

1. **Approve this implementation plan**
2. Start with Task 6 (PDF-to-Image fix) as prerequisite
3. Implement Task 1 (ConfidenceBadge) with TDD
4. Proceed through phases B, C, D, E
5. Final validation and merge

---

**Document Status:** PENDING APPROVAL
**Approval Required From:** Tech Lead / User

