# Implementation Plan: Visual Extraction Display Step

**Feature:** Visual Extraction Display Step (Design Doc 10)
**Methodology:** 4-Pillar Implementation (implement.md v2.1)
**Date:** December 24, 2025
**Status:** PENDING APPROVAL

---

## Phase 1: Design-First Development (COMPLETED)

### 1.1 Design Document Reference

- **Design Document:** [10-visual-extraction-display-design.md](10-visual-extraction-display-design.md)
- **Status:** Approved for implementation
- **Version:** 1.0

### 1.2 Key Design Decisions Recap

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Step Position | After Upload (Step 1) | See raw extraction before transformation |
| Rendering Mode | Canvas-based overlay | Accurate position mapping with native API |
| Layout Engine | CSS Grid + Absolute positioning | Flexible document mirroring |
| View Modes | Overlay, Side-by-Side, Text-Only | Multiple verification options |
| Confidence Display | Color-coded regions | Visual quality assessment |
| New Dependencies | None | Native Canvas API sufficient |

### 1.3 Updated Wizard Flow

```
CURRENT 5-STEP FLOW:
[Upload] -> [Processing] -> [Preview] -> [Review] -> [Submit]
   0            1             2           3           4

NEW 6-STEP FLOW:
[Upload] -> [Visual Extraction] -> [Processing] -> [Preview] -> [Review] -> [Submit]
   0              1                     2             3           4           5
              (NEW STEP)
```

---

## Phase 2: Evidence-Based Development

### 2.1 Environment Understanding (MANDATORY)

| Aspect | Value | Location |
|--------|-------|----------|
| Frontend Framework | Angular 19.2.19 | `frontend/package.json` |
| UI Library | PrimeNG 17.18.11 | `frontend/package.json` |
| Build Tool | Nx 20.x | `frontend/nx.json` |
| Dev Server Port | 4200 | `config/ports.yaml` |
| Backend Framework | FastAPI 0.109.x | `requirements.txt` |
| Backend Port | 8002 (external) / 8000 (internal) | `config/ports.yaml` |
| OCR Service | PaddleOCR | `config/ports.yaml` (port 9091) |
| Storage | MinIO | `config/ports.yaml` (port 9000) |
| Development Mode | Docker + Local Angular | Hybrid |

**Build/Run Commands:**
```bash
# Frontend
cd frontend && npx nx serve claims-portal

# Backend (Docker)
docker compose -f docker/docker-compose.local.yml up -d

# Generate configs after port changes
python scripts/generate-config.py
```

### 2.2 Existing Component Structure

The claim submission wizard follows a consistent pattern with step components:

| Existing Component | Location | Purpose |
|-------------------|----------|---------|
| `step-claim-docs` | `claim-submit/step-claim-docs/` | Document upload (Step 0) |
| `step-processing` | `claim-submit/step-processing/` | OCR + LLM extraction (Step 1) |
| `step-preview-extraction` | `claim-submit/step-preview-extraction/` | Structured data preview (Step 2) |
| `step-review` | `claim-submit/step-review/` | Review & Submit (Steps 3,4) |

**Component Pattern:**
- Standalone components with `OnPush` change detection
- Angular Signals for state management
- `@Input()` for data, `@Output()` for events (`stepComplete`, `stepBack`)
- PrimeNG UI components

### 2.3 Dependency Research

**No new npm dependencies required.** All functionality uses existing stack:

| Component | Existing Dependency | Version | Purpose |
|-----------|-------------------|---------|---------|
| Layout | PrimeNG SplitterModule | 17.18.11 | Document/panel split |
| Cards | PrimeNG CardModule | 17.18.11 | Region details |
| Navigation | PrimeNG ButtonModule | 17.18.11 | Page/zoom controls |
| Dropdown | PrimeNG DropdownModule | 17.18.11 | View mode selector |
| Slider | PrimeNG SliderModule | 17.18.11 | Zoom control |
| Canvas | HTML5 Canvas API | Native | Document overlay rendering |

**Backend Dependencies Verified:**

| Package | Required | Installed | Purpose |
|---------|----------|-----------|---------|
| PyMuPDF (fitz) | >=1.24.0 | 1.24.14 | PDF to image conversion |
| aiohttp | >=3.9.0 | 3.11.18 | Async HTTP for OCR service |
| pillow | >=10.0.0 | 10.4.0 | Image processing |

### 2.4 Version Compatibility Matrix

| Dependency | Version | Requires | Conflicts With | Verified With |
|------------|---------|----------|----------------|---------------|
| @angular/core | 19.2.19 | Node >= 18.19 | - | Node 20.x |
| primeng | 17.18.11 | Angular 17-19 | - | Angular 19.2.19 |
| @angular/forms | 19.2.19 | @angular/core 19 | - | 19.2.19 |
| rxjs | 7.8.x | Angular 19 | rxjs-compat | 7.8.1 |
| typescript | 5.8.x | Angular 19 | < 5.0 | 5.8.2 |
| Canvas API | N/A | Modern browser | - | Chrome 120+, Firefox 120+, Safari 17+ |
| PyMuPDF | 1.24.14 | Python 3.8+ | - | Python 3.11 |
| FastAPI | 0.109.0 | Python 3.8+ | - | Python 3.11 |
| Pydantic | 2.10.3 | Python 3.8+ | Pydantic V1 | Python 3.11 |

**Verification Commands:**
```bash
# Frontend - Check peer deps
cd frontend && npm ls --all 2>&1 | grep -i "peer dep"

# Backend - Check conflicts
pip check

# Check outdated
cd frontend && npm outdated
pip list --outdated
```

### 2.5 Cross-Stack Compatibility

| Layer A | Layer B | Check | Status |
|---------|---------|-------|--------|
| Angular 19.x | PrimeNG 17.18.x | Official support matrix | Verified |
| Angular 19.x | TypeScript 5.8.x | Angular peer deps | Verified |
| Angular Signals | Components | Built-in (Angular 17+) | Native |
| FastAPI 0.109.x | Pydantic 2.x | FastAPI compatibility | Verified |
| PyMuPDF 1.24.x | Python 3.11 | Version matrix | Verified |
| MinIO | PyMuPDF Images | Image format support | Verified |
| Frontend | Backend API | JWT auth, JSON format | Existing |

### 2.6 URL/Port Configuration Verification (MANDATORY)

**Per `config/ports.yaml` (Single Source of Truth):**

| Service | Port | Internal Port | Config Location | Status |
|---------|------|---------------|-----------------|--------|
| Frontend | 4200 | 4200 | `config/ports.yaml` | Centralized |
| Backend API | 8002 | 8000 | `config/ports.yaml` | Centralized |
| MinIO | 9000 | 9000 | `config/ports.yaml` | Centralized |
| PaddleOCR | 9091 | 9090 | `config/ports.yaml` | Centralized |

**New API Endpoints (Backend):**

| Endpoint | Method | Type | Purpose | Consumer |
|----------|--------|------|---------|----------|
| `POST /api/v1/documents/quick-extract` | POST | WRITE | Quick OCR extraction | StepVisualExtractionComponent |
| `GET /api/v1/documents/{id}/page/{n}/image` | GET | READ | Page image | DocumentViewerComponent |
| `GET /api/v1/documents/{id}/pages/thumbnails` | GET | READ | Page thumbnails | PageNavigatorComponent |

**Interface-to-API Mapping:**

| Component/Service | API Endpoints Used | Config Reference |
|-------------------|-------------------|------------------|
| StepVisualExtractionComponent | POST /quick-extract | API_BASE_URL |
| DocumentViewerComponent | GET /page/{n}/image | API_BASE_URL |
| PageNavigatorComponent | GET /pages/thumbnails | API_BASE_URL |
| All via DocumentService | Proxied through environment.apiUrl | environment.ts |

**Hardcoded URL Check:**
```bash
# Run before implementation - must return no results
grep -rn "localhost:" --include="*.ts" frontend/apps/claims-portal/src/
grep -rn "127.0.0.1" --include="*.ts" frontend/apps/claims-portal/src/
grep -rn ":8002" --include="*.ts" frontend/apps/claims-portal/src/
```

---

## Phase 3: Test-Driven Implementation

### 3.1 Test Plan

#### Unit Tests (Write First)

| Test File | Test Cases | Priority |
|-----------|------------|----------|
| `step-visual-extraction.component.spec.ts` | Component creation, Input handling, Output events, Loading states, Error handling | P0 |
| `document-viewer.component.spec.ts` | Canvas rendering, Region highlighting, Click detection, Zoom/pan | P0 |
| `page-navigator.component.spec.ts` | Page navigation, Boundary checks | P1 |
| `zoom-controls.component.spec.ts` | Zoom in/out, Range limits | P1 |
| `confidence-legend.component.spec.ts` | Color display, Legend items | P2 |
| `full-text-display.component.spec.ts` | Text rendering, Region grouping | P1 |
| `region-details.component.spec.ts` | Detail display, Confidence badge | P1 |

#### Test Cases for StepVisualExtractionComponent

```typescript
describe('StepVisualExtractionComponent', () => {
  // Creation
  it('should create the component');
  it('should initialize with loading state');

  // Inputs
  it('should trigger extraction when documents provided');
  it('should handle empty documents array gracefully');

  // Outputs
  it('should emit stepComplete when Continue clicked');
  it('should emit stepBack when Back clicked');
  it('should pass extraction result to stepComplete');

  // Loading States
  it('should show loading spinner during extraction');
  it('should hide loading spinner after extraction');
  it('should disable Continue button while loading');

  // Error Handling
  it('should display error message when extraction fails');
  it('should allow retry on error');

  // View Modes
  it('should switch between Overlay, Side-by-Side, and Text-Only views');
  it('should default to Overlay view');

  // Confidence
  it('should display overall confidence score');
  it('should apply correct CSS class based on confidence level');
});
```

#### Test Cases for DocumentViewerComponent

```typescript
describe('DocumentViewerComponent', () => {
  // Canvas Rendering
  it('should create canvas element');
  it('should load and display page image');
  it('should scale canvas based on zoom level');

  // Region Overlay
  it('should draw regions on canvas');
  it('should apply green color for high confidence regions');
  it('should apply yellow color for medium confidence regions');
  it('should apply red color for low confidence regions');

  // Interaction
  it('should detect click on region');
  it('should emit regionClick event with clicked region');
  it('should highlight selected region with border');

  // Zoom
  it('should resize canvas on zoom change');
  it('should maintain region positions on zoom');
});
```

#### Backend Unit Tests

```python
# tests/unit/test_quick_extraction.py

class TestQuickExtraction:
    async def test_quick_extract_pdf_returns_pages():
        """Should return page data for PDF documents."""

    async def test_quick_extract_image_returns_single_page():
        """Should return single page for image documents."""

    async def test_quick_extract_returns_bounding_boxes():
        """Should return text regions with bounding boxes."""

    async def test_quick_extract_confidence_in_range():
        """Confidence scores should be between 0 and 1."""

    async def test_get_page_image_returns_png():
        """Should return page as PNG image."""

    async def test_get_page_image_404_for_invalid_page():
        """Should return 404 for non-existent page."""

    async def test_get_thumbnails_returns_all_pages():
        """Should return thumbnail URLs for all pages."""
```

### 3.2 Implementation Tasks

#### Task 1: Backend - Quick Extraction Endpoint (PREREQUISITE)

**Files to modify:**
- `src/api/routes/documents.py` - Add new endpoints
- `src/services/document_processor.py` - Add `quick_extract_with_boxes` method
- `src/schemas/extraction.py` - Add response models

**Implementation Details:**
```python
# src/schemas/extraction.py - Add models
class BoundingBox(BaseModel):
    x: float      # 0-1 normalized
    y: float      # 0-1 normalized
    width: float  # 0-1 normalized
    height: float # 0-1 normalized

class TextRegion(BaseModel):
    id: str
    text: str
    confidence: float
    bounding_box: BoundingBox
    category: Optional[str] = None
    field_name: Optional[str] = None

class PageExtraction(BaseModel):
    page_number: int
    width: int
    height: int
    image_url: str
    regions: list[TextRegion]

class QuickExtractionResponse(BaseModel):
    document_id: str
    filename: str
    total_pages: int
    overall_confidence: float
    processing_time_ms: int
    pages: list[PageExtraction]
```

#### Task 2: Backend - Page Image Endpoint

**Files to modify:**
- `src/api/routes/documents.py` - Add image endpoint
- `src/services/document_storage.py` - Add `get_page_image` method

**Implementation Details:**
- Convert PDF pages to PNG using PyMuPDF
- Cache generated images in MinIO
- Support width parameter for resizing
- Support PNG and JPEG formats

#### Task 3: Frontend - Document Viewer Component

**Location:** `frontend/apps/claims-portal/src/app/features/claims/components/claim-submit/step-visual-extraction/components/document-viewer/`

**Files:**
- `document-viewer.component.ts`
- `document-viewer.component.spec.ts`

**Key Features:**
- Canvas-based rendering
- Load image from URL
- Draw confidence-colored overlays for each region
- Handle click detection on regions
- Support zoom scaling

#### Task 4: Frontend - Page Navigator Component

**Location:** Same as Task 3, `/components/page-navigator/`

**Files:**
- `page-navigator.component.ts`
- `page-navigator.component.spec.ts`

**Key Features:**
- Page number display (Page X of Y)
- First/Previous/Next/Last buttons
- Direct page number input

#### Task 5: Frontend - Zoom Controls Component

**Location:** Same as Task 3, `/components/zoom-controls/`

**Files:**
- `zoom-controls.component.ts`
- `zoom-controls.component.spec.ts`

**Key Features:**
- Zoom in/out buttons
- Zoom percentage display
- Range: 50% - 200%
- Slider for fine control

#### Task 6: Frontend - Confidence Legend Component

**Location:** Same as Task 3, `/components/confidence-legend/`

**Files:**
- `confidence-legend.component.ts`
- `confidence-legend.component.spec.ts`

**Key Features:**
- Display color legend
- High (green), Medium (yellow), Low (red)
- Threshold values

#### Task 7: Frontend - Full Text Display Component

**Location:** Same as Task 3, `/components/full-text-display/`

**Files:**
- `full-text-display.component.ts`
- `full-text-display.component.spec.ts`

**Key Features:**
- Display all extracted text
- Group by page
- Highlight selected region text

#### Task 8: Frontend - Region Details Component

**Location:** Same as Task 3, `/components/region-details/`

**Files:**
- `region-details.component.ts`
- `region-details.component.spec.ts`

**Key Features:**
- Display selected region text
- Show confidence percentage
- Show position (page, coordinates)
- Show category if available

#### Task 9: Frontend - Step Visual Extraction Component (Main)

**Location:** `frontend/apps/claims-portal/src/app/features/claims/components/claim-submit/step-visual-extraction/`

**Files:**
- `step-visual-extraction.component.ts`
- `step-visual-extraction.component.spec.ts`

**Key Features:**
- Orchestrate child components
- Manage extraction state
- Handle view mode switching
- Emit stepComplete/stepBack events

#### Task 10: Frontend - Update Claim Submit Component

**File:** `frontend/apps/claims-portal/src/app/features/claims/components/claim-submit/claim-submit.component.ts`

**Changes:**
1. Add import for StepVisualExtractionComponent
2. Update steps array (6 steps instead of 5)
3. Add @switch case for step 1 (Visual Extraction)
4. Update step indices for all subsequent steps
5. Add `onVisualExtractionComplete` handler
6. Update `EnhancedClaimFormState` to include `rawExtractionResult`

**Before:**
```typescript
readonly steps: MenuItem[] = [
  { label: 'Upload Documents', icon: 'pi pi-upload' },      // 0
  { label: 'Processing', icon: 'pi pi-cog' },               // 1
  { label: 'Preview Extraction', icon: 'pi pi-eye' },       // 2
  { label: 'Review Data', icon: 'pi pi-pencil' },           // 3
  { label: 'Submit', icon: 'pi pi-check-square' },          // 4
];
```

**After:**
```typescript
readonly steps: MenuItem[] = [
  { label: 'Upload Documents', icon: 'pi pi-upload' },      // 0
  { label: 'Visual Extraction', icon: 'pi pi-image' },      // 1 (NEW)
  { label: 'Processing', icon: 'pi pi-cog' },               // 2
  { label: 'Preview Extraction', icon: 'pi pi-eye' },       // 3
  { label: 'Review Data', icon: 'pi pi-pencil' },           // 4
  { label: 'Submit', icon: 'pi pi-check-square' },          // 5
];
```

#### Task 11: Frontend - Document Service Update

**File:** `frontend/apps/claims-portal/src/app/core/services/document.service.ts`

**New Methods:**
```typescript
quickExtract(documentId: string): Observable<QuickExtractionResponse>;
getPageImage(documentId: string, pageNumber: number, width?: number): string;
getPageThumbnails(documentId: string): Observable<PageThumbnails>;
```

---

## Phase 4: Quality-First Delivery

### 4.1 Quality Checklist

#### Code Quality
- [ ] All components use OnPush change detection
- [ ] All components are standalone
- [ ] No hardcoded URLs/ports introduced
- [ ] Proper error handling for null/undefined data
- [ ] Consistent naming conventions (kebab-case files, PascalCase classes)
- [ ] No console.log statements in production code
- [ ] All public APIs have JSDoc comments
- [ ] Backend endpoints have OpenAPI documentation

#### Testing
- [ ] All unit tests passing
- [ ] Code coverage >= 80% for new components
- [ ] Integration tests for wizard flow
- [ ] Backend API tests for new endpoints
- [ ] E2E test for complete flow (upload -> visual -> processing)

#### Performance
- [ ] Canvas rendering < 100ms
- [ ] Page image load < 2s
- [ ] Memory usage validated for 10+ page documents
- [ ] Lazy loading for images
- [ ] TrackBy functions for ngFor loops

#### Accessibility
- [ ] ARIA labels on interactive elements
- [ ] Keyboard navigation for page/zoom controls
- [ ] Color contrast meets WCAG 2.1 AA
- [ ] Screen reader support for confidence levels

#### Security
- [ ] No sensitive data logged
- [ ] XSS protection maintained (no innerHTML)
- [ ] Same auth requirements as existing flow
- [ ] Signed URLs for images with expiration
- [ ] Tenant isolation verified

### 4.2 Deliverables Checklist

| Deliverable | Files | Priority | Status |
|-------------|-------|----------|--------|
| QuickExtractionResponse Schema | `src/schemas/extraction.py` | P0 | Pending |
| Quick Extract Endpoint | `src/api/routes/documents.py` | P0 | Pending |
| Page Image Endpoint | `src/api/routes/documents.py` | P0 | Pending |
| Document Processor Update | `src/services/document_processor.py` | P0 | Pending |
| DocumentViewerComponent | 2 files (.ts, .spec.ts) | P0 | Pending |
| PageNavigatorComponent | 2 files | P1 | Pending |
| ZoomControlsComponent | 2 files | P1 | Pending |
| ConfidenceLegendComponent | 2 files | P2 | Pending |
| FullTextDisplayComponent | 2 files | P1 | Pending |
| RegionDetailsComponent | 2 files | P1 | Pending |
| StepVisualExtractionComponent | 2 files | P0 | Pending |
| ClaimSubmitComponent Update | 1 file modified | P0 | Pending |
| DocumentService Update | 1 file modified | P0 | Pending |
| Unit Tests | 8+ spec files | P0 | Pending |
| Backend Tests | 2+ test files | P0 | Pending |

### 4.3 URL/API Configuration Report

| Check | Result |
|-------|--------|
| New endpoints added | 3 (quick-extract, page image, thumbnails) |
| All use API_BASE_URL | Yes |
| Hardcoded URLs introduced | None |
| Config variables used | environment.apiUrl via DocumentService |
| Interface-to-API mapping | Documented in Section 2.6 |

---

## Implementation Sequence

```
+---------------------------------------------------------------------+
|                    IMPLEMENTATION SEQUENCE                           |
+---------------------------------------------------------------------+
|                                                                      |
|  PHASE A (Backend Prerequisites):                                    |
|  +--------------------------------------------------------------+   |
|  | Task 1: Quick Extraction Endpoint (schemas + route)          |   |
|  | Task 2: Page Image Endpoint                                  |   |
|  | File: src/api/routes/documents.py                            |   |
|  | File: src/services/document_processor.py                     |   |
|  | Reason: Frontend depends on these APIs                       |   |
|  +--------------------------------------------------------------+   |
|                              |                                       |
|                              v                                       |
|  PHASE B (Child Components - Can be Parallel):                       |
|  +------------------+  +------------------+  +------------------+    |
|  | Task 3:          |  | Task 4:          |  | Task 5:          |   |
|  | Document Viewer  |  | Page Navigator   |  | Zoom Controls    |   |
|  | (Canvas)         |  |                  |  |                  |   |
|  +------------------+  +------------------+  +------------------+    |
|  +------------------+  +------------------+  +------------------+    |
|  | Task 6:          |  | Task 7:          |  | Task 8:          |   |
|  | Confidence       |  | Full Text        |  | Region Details   |   |
|  | Legend           |  | Display          |  |                  |   |
|  +------------------+  +------------------+  +------------------+    |
|                              |                                       |
|                              v                                       |
|  PHASE C (Main Component):                                           |
|  +--------------------------------------------------------------+   |
|  | Task 9: StepVisualExtractionComponent                        |   |
|  | Integrates Tasks 3-8                                         |   |
|  +--------------------------------------------------------------+   |
|                              |                                       |
|                              v                                       |
|  PHASE D (Integration):                                              |
|  +--------------------------------------------------------------+   |
|  | Task 10: Update ClaimSubmitComponent Wizard                  |   |
|  | Task 11: Update DocumentService                              |   |
|  | Add step, update indices, add template case                  |   |
|  +--------------------------------------------------------------+   |
|                              |                                       |
|                              v                                       |
|  PHASE E (Testing & Validation):                                     |
|  +--------------------------------------------------------------+   |
|  | Run all unit tests                                           |   |
|  | Run integration tests                                        |   |
|  | Verify wizard flow works end-to-end                          |   |
|  | Check performance metrics                                    |   |
|  | Accessibility audit                                          |   |
|  +--------------------------------------------------------------+   |
|                                                                      |
+---------------------------------------------------------------------+
```

### Time Estimate by Phase

| Phase | Tasks | Complexity | Notes |
|-------|-------|------------|-------|
| Phase A | 1-2 | MEDIUM | Backend API + PyMuPDF integration |
| Phase B | 3-8 | MEDIUM | 6 simple components, can be parallel |
| Phase C | 9 | MEDIUM | Main component orchestration |
| Phase D | 10-11 | LOW | Integration and service updates |
| Phase E | Testing | MEDIUM | Comprehensive test coverage |

---

## Risk Assessment

| ID | Risk | Probability | Impact | Mitigation |
|----|------|-------------|--------|------------|
| R-1 | OCR bounding boxes inaccurate | MEDIUM | HIGH | Fallback to text-only view; verify PaddleOCR output format |
| R-2 | Large documents slow to render | MEDIUM | MEDIUM | Progressive loading, pagination, image compression |
| R-3 | Memory issues on mobile | LOW | MEDIUM | Aggressive page unloading, reduced image quality |
| R-4 | Canvas not supported (old browsers) | LOW | HIGH | Fallback to positioned divs; minimum browser requirements |
| R-5 | Image loading fails from MinIO | LOW | MEDIUM | Retry mechanism, error state UI |
| R-6 | Extraction step adds perceived latency | MEDIUM | LOW | Show progress indicator, allow skip option |
| R-7 | Step index update breaks existing tests | LOW | MEDIUM | Update all test files simultaneously |

### Fallback Plans

| Risk | Fallback |
|------|----------|
| Canvas unsupported | Use positioned divs over image with CSS |
| Bounding boxes missing | Display text list with page numbers (text-only mode) |
| Image load failure | Show text extraction only with error message |
| Slow processing | Optional "Skip to Processing" button |

---

## Open Questions Requiring Decision

| ID | Question | Default Assumption | Impact | Decision Needed By |
|----|----------|-------------------|--------|-------------------|
| Q-1 | Should quick extraction happen during upload (parallel) or after upload completes? | After upload (simpler) | HIGH | Phase A start |
| Q-2 | Maximum document pages supported for visual display? | 50 pages | MEDIUM | Phase A start |
| Q-3 | Should "Skip to Processing" button be available? | No (must view extraction) | LOW | Phase C |
| Q-4 | Should we cache page images permanently or regenerate? | Cache for 24 hours | MEDIUM | Phase A |
| Q-5 | Should users be able to edit extraction in this step? | No (read-only per design) | LOW | Future enhancement |

---

## Approval Checklist

Before proceeding with implementation:

- [ ] Design document (10) reviewed and approved
- [ ] Implementation plan reviewed
- [ ] Open questions (Q-1 to Q-5) decisions made
- [ ] No blocking dependencies identified
- [ ] Test strategy approved
- [ ] Phase A (Backend) approved to start

---

## Next Steps

1. **Review this implementation plan**
2. **Make decisions on open questions (Q-1 to Q-5)**
3. **Approve Phase A to begin**
4. Start with Tasks 1-2 (Backend endpoints)
5. Proceed through phases B, C, D, E
6. Final validation and merge

---

**Document Status:** PENDING APPROVAL
**Approval Required From:** Tech Lead / User
**Last Updated:** December 24, 2025

---

## Appendix A: File Structure After Implementation

```
frontend/apps/claims-portal/src/app/features/claims/components/claim-submit/
├── step-visual-extraction/
│   ├── step-visual-extraction.component.ts
│   ├── step-visual-extraction.component.spec.ts
│   └── components/
│       ├── document-viewer/
│       │   ├── document-viewer.component.ts
│       │   └── document-viewer.component.spec.ts
│       ├── page-navigator/
│       │   ├── page-navigator.component.ts
│       │   └── page-navigator.component.spec.ts
│       ├── zoom-controls/
│       │   ├── zoom-controls.component.ts
│       │   └── zoom-controls.component.spec.ts
│       ├── confidence-legend/
│       │   ├── confidence-legend.component.ts
│       │   └── confidence-legend.component.spec.ts
│       ├── full-text-display/
│       │   ├── full-text-display.component.ts
│       │   └── full-text-display.component.spec.ts
│       └── region-details/
│           ├── region-details.component.ts
│           └── region-details.component.spec.ts
├── step-claim-docs/
├── step-processing/
├── step-preview-extraction/
├── step-review/
└── claim-submit.component.ts
```

```
src/
├── api/routes/
│   └── documents.py  (modified - add 3 endpoints)
├── schemas/
│   └── extraction.py (new - QuickExtractionResponse models)
├── services/
│   └── document_processor.py (modified - add quick_extract_with_boxes)
└── tests/
    └── unit/
        └── test_quick_extraction.py (new)
```

## Appendix B: Backend Endpoint Implementation Guide

### Quick Extraction Endpoint

```python
# src/api/routes/documents.py

@router.post("/quick-extract", response_model=QuickExtractionResponse)
async def quick_extract(
    file: UploadFile = File(...),
    return_images: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Perform quick OCR extraction with bounding boxes.

    This endpoint extracts text from documents with position information
    but does NOT perform LLM parsing. Used for Visual Extraction Display step.

    Source: Design Doc 10 - Visual Extraction Display
    """
    processor = get_document_processor()

    result = await processor.quick_extract_with_boxes(
        file_data=await file.read(),
        filename=file.filename,
        content_type=file.content_type,
        tenant_id=current_user.tenant_id,
        return_images=return_images,
    )

    return result
```

### Document Processor Update

```python
# src/services/document_processor.py

async def quick_extract_with_boxes(
    self,
    file_data: bytes,
    filename: str,
    content_type: str,
    tenant_id: str,
    return_images: bool = True,
) -> QuickExtractionResponse:
    """
    Perform quick OCR extraction returning text regions with bounding boxes.

    Unlike full extraction, this does NOT run LLM parsing - just OCR.
    Used for Visual Extraction Display step.
    """
    import fitz  # PyMuPDF
    import time
    import uuid

    start_time = time.time()
    document_id = str(uuid.uuid4())

    # Convert PDF to images
    if content_type == "application/pdf":
        images = await self._process_pdf_to_images(file_data)
    else:
        images = [file_data]

    pages = []
    total_confidence = 0.0

    for page_num, image_bytes in enumerate(images, 1):
        # Call OCR service with bounding boxes
        ocr_result = await self._call_ocr_with_boxes(image_bytes)

        # Get image dimensions
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size

        # Build image URL
        image_url = f"/api/v1/documents/{document_id}/page/{page_num}/image"

        # Convert OCR result to TextRegion list
        regions = []
        for box in ocr_result.get("boxes", []):
            region = TextRegion(
                id=str(uuid.uuid4())[:8],
                text=box["text"],
                confidence=box["confidence"],
                bounding_box=BoundingBox(
                    x=box["x"] / width,
                    y=box["y"] / height,
                    width=box["width"] / width,
                    height=box["height"] / height,
                ),
            )
            regions.append(region)
            total_confidence += box["confidence"]

        page = PageExtraction(
            page_number=page_num,
            width=width,
            height=height,
            image_url=image_url,
            regions=regions,
        )
        pages.append(page)

        # Store image in MinIO for later retrieval
        await self._store_page_image(document_id, page_num, image_bytes, tenant_id)

    # Calculate overall confidence
    region_count = sum(len(p.regions) for p in pages)
    overall_confidence = total_confidence / region_count if region_count > 0 else 0.0

    processing_time = int((time.time() - start_time) * 1000)

    return QuickExtractionResponse(
        document_id=document_id,
        filename=filename,
        total_pages=len(pages),
        overall_confidence=overall_confidence,
        processing_time_ms=processing_time,
        pages=pages,
    )
```
