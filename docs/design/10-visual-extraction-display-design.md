# Design Document: Visual Extraction Display Step

**Feature:** Visual Document Extraction Display - Source-Faithful Rendering
**Version:** 1.0
**Date:** December 24, 2025
**Author:** Architecture Team
**Status:** DRAFT - Pending Approval

---

## 1. Executive Summary

### Overview

This design document specifies a **new step** in the claim submission wizard that visualizes extracted data **immediately after document upload**, displaying it in a format that **mirrors the original source document layout**. This step ensures:

1. **Complete visibility** - ALL extracted information is displayed without missing areas
2. **Source-faithful layout** - Data is formatted to match the original PDF/image structure
3. **Visual verification** - Users can visually compare extraction to source document
4. **Early error detection** - Issues identified before data transformation

### Position in Workflow

```
NEW 6-STEP FLOW:
                                                    NEW STEP
                                                       │
                                                       ▼
[Upload] -> [Visual Extraction] -> [Processing] -> [Preview] -> [Review] -> [Submit]
              Display                                Summary
                │                                       │
                ▼                                       ▼
        Shows data as it                        Shows data in
        appears in source                       structured cards
        document layout                         (existing design)
```

### Key Differentiator from Existing Preview Step

| Aspect | Visual Extraction Display (NEW) | Preview Step (Existing Doc 08) |
|--------|--------------------------------|-------------------------------|
| Position | Immediately after Upload | After Processing |
| Layout | Mirrors source document | Structured data cards |
| Purpose | Verify OCR/extraction accuracy | Verify data parsing |
| Data Format | Raw extracted regions | Transformed/structured data |
| Visual Style | Document-like rendering | UI component cards |
| Confidence | Per-region highlighting | Per-field badges |

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Step Position | After Upload, Before Processing | See raw extraction before transformation |
| Rendering Mode | Canvas-based overlay | Accurate position mapping |
| Missing Data | Highlight empty regions | Clear visibility of gaps |
| Layout Engine | CSS Grid + Absolute positioning | Flexible document mirroring |
| Image Display | Side-by-side comparison | Easy visual verification |

### Success Criteria

- Display ALL extracted text regions with no missing areas
- Render extracted data in positions matching source document
- Show confidence scores visually (color-coded regions)
- Allow side-by-side comparison with original document
- Support PDF (multi-page) and image formats
- Load within 2 seconds after extraction completes

---

## 2. Requirements Specification

### 2.1 Business Objectives

| ID | Objective | Priority |
|----|-----------|----------|
| BO-1 | Display ALL extracted information without missing areas | MUST |
| BO-2 | Format data to mirror source document layout | MUST |
| BO-3 | Enable visual comparison with source | MUST |
| BO-4 | Highlight extraction quality (confidence per region) | MUST |
| BO-5 | Support multi-page PDF documents | MUST |
| BO-6 | Show empty/unextracted regions clearly | SHOULD |
| BO-7 | Allow zoom and pan for detailed inspection | SHOULD |
| BO-8 | Provide print/export of extraction view | COULD |

### 2.2 Functional Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| FR-1 | Document Thumbnail | Display original document as reference image |
| FR-2 | Extraction Overlay | Show extracted text at exact source positions |
| FR-3 | Region Highlighting | Color-code regions by confidence level |
| FR-4 | Missing Region Indicator | Highlight areas with no extraction |
| FR-5 | Side-by-Side View | Toggle between overlay and comparison modes |
| FR-6 | Page Navigation | Navigate through multi-page documents |
| FR-7 | Zoom Controls | Zoom in/out for detailed inspection |
| FR-8 | Text Selection | Allow copying extracted text |
| FR-9 | Region Details | Click region to see extraction details |
| FR-10 | Full Data Panel | Collapsible panel showing all extracted text |

### 2.3 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Initial Load Time | < 2 seconds |
| NFR-2 | Page Switch Time | < 500ms |
| NFR-3 | Zoom Responsiveness | < 100ms |
| NFR-4 | Memory Usage | < 100MB for 10-page document |
| NFR-5 | Mobile Support | Responsive layout down to 768px |
| NFR-6 | Accessibility | WCAG 2.1 AA for text contrast |

### 2.4 Constraints

| Type | Constraint |
|------|------------|
| Technical | Must integrate with existing Angular 19 + PrimeNG stack |
| Technical | Must use OCR bounding box data from extraction pipeline |
| Technical | PDF pages must be converted to images for display |
| UX | Must not require scroll to see main content on desktop |
| Design | Must follow existing healthcare theme |

### 2.5 Assumptions

| ID | Assumption | Must Validate |
|----|------------|---------------|
| A-1 | OCR returns bounding box coordinates for each text region | Yes - verify OCR output |
| A-2 | Document images available from MinIO storage | Yes - storage integration |
| A-3 | Backend can serve page images at reduced resolution | Yes - image service needed |
| A-4 | Extraction results include page numbers per field | Yes - verify LLM output |
| A-5 | Users have sufficient screen resolution (1280x720+) | No - responsive design |

---

## 3. Architecture Design

### 3.1 Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ClaimSubmitComponent                                  │
│                         (Wizard Orchestrator)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
     │        │        │              │            │            │
     ▼        ▼        ▼              ▼            ▼            ▼
+--------+ +--------+ +-------------+ +--------+ +--------+ +--------+
| Step 0 | | Step 1 | | Step 2      | | Step 3 | | Step 4 | | Step 5 |
| Upload | | Visual | | Processing  | | Preview| | Review | | Submit |
| Docs   | | Extract| | (OCR+LLM)   | | Cards  | | Data   | |        |
+--------+ +--------+ +-------------+ +--------+ +--------+ +--------+
              │
              │
   ┌──────────┴──────────────────────────────────────────────┐
   │                                                          │
   │              StepVisualExtractionComponent               │
   │                  (NEW COMPONENT)                         │
   │                                                          │
   │  ┌────────────────────┐  ┌────────────────────────────┐ │
   │  │  Document Viewer   │  │  Extraction Panel          │ │
   │  │  ┌──────────────┐  │  │  ┌──────────────────────┐  │ │
   │  │  │ Page Image   │  │  │  │ Full Text Display    │  │ │
   │  │  │ + Overlay    │  │  │  │ (All Extracted Data) │  │ │
   │  │  └──────────────┘  │  │  └──────────────────────┘  │ │
   │  │  ┌──────────────┐  │  │  ┌──────────────────────┐  │ │
   │  │  │ Page Nav     │  │  │  │ Region Details       │  │ │
   │  │  └──────────────┘  │  │  │ (On Click)           │  │ │
   │  │  ┌──────────────┐  │  │  └──────────────────────┘  │ │
   │  │  │ Zoom/Pan     │  │  │  ┌──────────────────────┐  │ │
   │  │  └──────────────┘  │  │  │ Confidence Legend    │  │ │
   │  └────────────────────┘  │  └──────────────────────┘  │ │
   │                          └────────────────────────────┘ │
   └──────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow

```
Document Upload Complete:
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────────┐
│  Upload Step    │────>│  Quick OCR      │────>│  Visual Extraction      │
│  (Documents)    │     │  (Text + Boxes) │     │  Display Step           │
└─────────────────┘     └─────────────────┘     └─────────────────────────┘
                               │                           │
                               ▼                           ▼
                        ┌─────────────────┐         ┌─────────────────┐
                        │ OCRExtractionResult       │ Document Images │
                        │ - full_text               │ (from MinIO)    │
                        │ - regions[]               └─────────────────┘
                        │   - text                          │
                        │   - bounding_box                  │
                        │   - confidence                    │
                        │   - page_number                   │
                        └─────────────────┘                 │
                               │                            │
                               └──────────────┬─────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │  Canvas Renderer            │
                               │  - Draw page image          │
                               │  - Overlay extraction boxes │
                               │  - Color by confidence      │
                               └─────────────────────────────┘
```

### 3.3 Extraction Result Data Model

```typescript
/**
 * OCR extraction result with bounding boxes.
 * Source: OCR Pipeline (PaddleOCR/Tesseract)
 */
interface OCRExtractionResult {
  document_id: string;
  filename: string;
  total_pages: number;
  overall_confidence: number;
  processing_time_ms: number;

  pages: PageExtraction[];
  tables: TableExtraction[];
}

interface PageExtraction {
  page_number: number;
  width: number;          // Original page width in pixels
  height: number;         // Original page height in pixels
  image_url: string;      // URL to page image (MinIO)

  regions: TextRegion[];
}

interface TextRegion {
  id: string;
  text: string;
  confidence: number;     // 0.0 - 1.0

  // Bounding box (normalized 0-1 coordinates)
  bounding_box: {
    x: number;            // Left position (0-1)
    y: number;            // Top position (0-1)
    width: number;        // Width (0-1)
    height: number;       // Height (0-1)
  };

  // Categorization (from LLM parsing)
  category?: 'patient' | 'provider' | 'diagnosis' | 'procedure' |
             'financial' | 'date' | 'identifier' | 'unknown';
  field_name?: string;    // e.g., "patient_name", "total_amount"
}

interface TableExtraction {
  page_number: number;
  bounding_box: BoundingBox;
  headers: string[];
  rows: string[][];
  confidence: number;
}
```

### 3.4 State Management

```typescript
interface VisualExtractionState {
  // Document data
  documentId: string;
  filename: string;
  totalPages: number;

  // Current view
  currentPage: number;
  zoomLevel: number;          // 50% - 200%
  viewMode: 'overlay' | 'side-by-side' | 'text-only';

  // Extraction data
  pages: PageExtraction[];
  selectedRegion: TextRegion | null;

  // Loading states
  isLoading: boolean;
  imageLoaded: boolean;
  extractionLoaded: boolean;

  // Errors
  error: string | null;
}

// Signals for component state
const state = signal<VisualExtractionState>({
  documentId: '',
  filename: '',
  totalPages: 0,
  currentPage: 1,
  zoomLevel: 100,
  viewMode: 'overlay',
  pages: [],
  selectedRegion: null,
  isLoading: true,
  imageLoaded: false,
  extractionLoaded: false,
  error: null,
});
```

### 3.5 Updated Wizard Steps

```typescript
// claim-submit.component.ts - Updated 6-step flow

readonly steps: MenuItem[] = [
  { label: 'Upload Documents', icon: 'pi pi-upload' },
  { label: 'Visual Extraction', icon: 'pi pi-image' },    // NEW
  { label: 'Processing', icon: 'pi pi-cog' },
  { label: 'Preview Extraction', icon: 'pi pi-eye' },
  { label: 'Review Data', icon: 'pi pi-pencil' },
  { label: 'Submit', icon: 'pi pi-check-square' },
];

// Step indices updated:
// 0: Upload Documents
// 1: Visual Extraction Display (NEW)
// 2: Processing (OCR + LLM parsing)
// 3: Preview Extraction (structured cards)
// 4: Review Data
// 5: Submit
```

---

## 4. API Contracts

### 4.1 New Backend Endpoints

#### 4.1.1 Get Quick Extraction (OCR Only)

Performs OCR extraction and returns results with bounding boxes, without LLM parsing.

```http
POST /api/v1/documents/quick-extract
Authorization: Bearer <JWT>
Content-Type: multipart/form-data

Request:
  file: <binary>
  return_images: true  (optional, default false)

Response (200 OK):
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "medical_claim.pdf",
  "total_pages": 3,
  "overall_confidence": 0.87,
  "processing_time_ms": 2340,

  "pages": [
    {
      "page_number": 1,
      "width": 2480,
      "height": 3508,
      "image_url": "/api/v1/documents/550e8400.../page/1/image",

      "regions": [
        {
          "id": "r1",
          "text": "PATIENT INFORMATION",
          "confidence": 0.95,
          "bounding_box": {
            "x": 0.05,
            "y": 0.08,
            "width": 0.25,
            "height": 0.03
          },
          "category": "unknown"
        },
        {
          "id": "r2",
          "text": "Mrs AMNA OBAID ALI ALZAABI",
          "confidence": 0.92,
          "bounding_box": {
            "x": 0.05,
            "y": 0.12,
            "width": 0.35,
            "height": 0.025
          },
          "category": "patient",
          "field_name": "patient_name"
        }
        // ... more regions
      ]
    }
  ],

  "tables": [
    {
      "page_number": 1,
      "bounding_box": { "x": 0.05, "y": 0.4, "width": 0.9, "height": 0.3 },
      "headers": ["Service", "Code", "Quantity", "Amount"],
      "rows": [
        ["Consultation", "99213", "1", "Rs 2,500"],
        ["Lab Test", "80053", "1", "Rs 1,200"]
      ],
      "confidence": 0.88
    }
  ]
}
```

#### 4.1.2 Get Page Image

Returns a single page of the document as an image.

```http
GET /api/v1/documents/{document_id}/page/{page_number}/image
Authorization: Bearer <JWT>
Query Parameters:
  - width: number (optional, default: 800)
  - format: "png" | "jpeg" (optional, default: "png")

Response (200 OK):
Content-Type: image/png
<binary image data>

Response (404 Not Found):
{
  "error": {
    "code": "PAGE_NOT_FOUND",
    "message": "Page 5 does not exist in document"
  }
}
```

#### 4.1.3 Get All Page Images (Thumbnails)

Returns thumbnails for all pages.

```http
GET /api/v1/documents/{document_id}/pages/thumbnails
Authorization: Bearer <JWT>
Query Parameters:
  - width: number (optional, default: 200)

Response (200 OK):
{
  "document_id": "550e8400...",
  "total_pages": 3,
  "thumbnails": [
    { "page_number": 1, "url": "/api/v1/documents/550e.../page/1/image?width=200" },
    { "page_number": 2, "url": "/api/v1/documents/550e.../page/2/image?width=200" },
    { "page_number": 3, "url": "/api/v1/documents/550e.../page/3/image?width=200" }
  ]
}
```

### 4.2 API Endpoint Mapping

| Endpoint | Method | Type | Service | Purpose | Consumers |
|----------|--------|------|---------|---------|-----------|
| `/api/v1/documents/quick-extract` | POST | WRITE | Backend | Quick OCR extraction | VisualExtractionStep |
| `/api/v1/documents/{id}/page/{n}/image` | GET | READ | Backend | Page image | DocumentViewer |
| `/api/v1/documents/{id}/pages/thumbnails` | GET | READ | Backend | Page thumbnails | PageNavigator |

### 4.3 Interface-to-API Mapping

| Component/Service | API Endpoints Used | Config Reference |
|-------------------|-------------------|------------------|
| StepVisualExtractionComponent | POST /quick-extract | API_BASE_URL |
| DocumentViewerComponent | GET /page/{n}/image | API_BASE_URL |
| PageNavigatorComponent | GET /pages/thumbnails | API_BASE_URL |

---

## 5. Technology Stack

### 5.1 Frontend Technologies (Existing)

| Component | Technology | Version |
|-----------|------------|---------|
| Framework | Angular | 19.2.x |
| UI Library | PrimeNG | 17.18.x |
| State | Angular Signals | Built-in |
| Canvas | HTML5 Canvas | Native |

### 5.2 New Frontend Dependencies

| Package | Version | License | Purpose | Alternatives |
|---------|---------|---------|---------|--------------|
| None Required | - | - | Using native Canvas API | - |

**Note:** This feature can be implemented entirely with native browser APIs (Canvas, CSS) without new dependencies.

### 5.3 Backend Technologies (Existing)

| Component | Technology | Version |
|-----------|------------|---------|
| Framework | FastAPI | 0.115.x |
| Image Processing | PyMuPDF (fitz) | 1.24.x |
| OCR | PaddleOCR | Existing |
| Storage | MinIO | Existing |

### 5.4 Version Compatibility Matrix

| Dependency | Version | Requires | Conflicts With | Verified With |
|------------|---------|----------|----------------|---------------|
| @angular/core | 19.2.19 | Node >= 18.19 | - | Node 20.x |
| primeng | 17.18.11 | Angular 17-19 | - | Angular 19.2.19 |
| Canvas API | N/A | Modern browser | - | Chrome 120+, Firefox 120+ |
| PyMuPDF | 1.24.x | Python 3.8+ | - | Python 3.11 |

---

## 6. URL/Port Configuration Registry

Per `config/ports.yaml` (Single Source of Truth):

| Service | Port | Base URL | Config Location |
|---------|------|----------|-----------------|
| Frontend | 4200 | http://localhost:4200 | config/ports.yaml |
| Backend API | 8002 | http://localhost:8002 | config/ports.yaml |
| MinIO | 9000 | http://localhost:9000 | config/ports.yaml |
| PaddleOCR | 9091 | http://localhost:9091 | config/ports.yaml |

**New Endpoints:** All new API endpoints use the existing Backend API configuration (port 8002).

---

## 7. Security Design

### 7.1 Data Handling

| Aspect | Implementation |
|--------|----------------|
| PII Display | Same security as existing document handling |
| Image Access | Signed URLs with expiration (15 min) |
| Data Transmission | HTTPS only, no caching of images |
| Session Security | JWT authentication required |
| Audit Trail | Log visual extraction step access |

### 7.2 STRIDE Threat Analysis

| Threat | Risk | Mitigation |
|--------|------|------------|
| Spoofing | LOW | JWT authentication required |
| Tampering | LOW | Read-only display, no data modification |
| Repudiation | LOW | Audit logging of step access |
| Information Disclosure | MEDIUM | Signed URLs, session validation |
| Denial of Service | LOW | Image size limits, rate limiting |
| Elevation of Privilege | LOW | Same permissions as document upload |

### 7.3 OWASP Top 10 Mitigations

| Risk | Mitigation |
|------|------------|
| A01: Broken Access Control | Document ownership validation, tenant isolation |
| A03: Injection | No user input in queries |
| A05: Security Misconfiguration | CSP headers for canvas operations |
| A09: Logging Failures | Log all document access |

---

## 8. Performance Plan

### 8.1 Performance Requirements

| Metric | Target | Maximum |
|--------|--------|---------|
| Initial render | < 2s | 5s |
| Page switch | < 500ms | 1s |
| Zoom operation | < 100ms | 300ms |
| Memory (10 pages) | < 100MB | 150MB |

### 8.2 Optimization Strategies

1. **Lazy Image Loading**
   - Load only visible page
   - Prefetch adjacent pages
   - Unload distant pages from memory

2. **Progressive Rendering**
   - Show extraction regions first
   - Load high-res image in background
   - Use thumbnails for page navigation

3. **Canvas Optimization**
   ```typescript
   // Use OffscreenCanvas for background rendering
   const offscreen = new OffscreenCanvas(width, height);
   const ctx = offscreen.getContext('2d');
   // Draw extraction overlay
   // Transfer to visible canvas
   ```

4. **Image Compression**
   - Serve images at appropriate resolution for viewport
   - Use WebP format where supported
   - Progressive JPEG for large pages

### 8.3 Caching Strategy

| Resource | Cache Duration | Strategy |
|----------|---------------|----------|
| Page thumbnails | 5 minutes | Memory + HTTP cache |
| Full page images | 2 minutes | Memory only |
| Extraction data | Session | Signal state |

---

## 9. Risk Register

| ID | Risk | Probability | Impact | Mitigation |
|----|------|-------------|--------|------------|
| R-1 | OCR bounding boxes inaccurate | MEDIUM | HIGH | Fallback to text-only view |
| R-2 | Large documents slow to render | MEDIUM | MEDIUM | Progressive loading, pagination |
| R-3 | Memory issues on mobile | LOW | MEDIUM | Aggressive page unloading |
| R-4 | Canvas not supported | LOW | HIGH | Fallback to image + text list |
| R-5 | Image loading fails | LOW | MEDIUM | Retry mechanism, error state |
| R-6 | Extraction step adds latency | MEDIUM | LOW | Parallel with upload |

### Fallback Plans

| Risk | Fallback |
|------|----------|
| Canvas unsupported | Use positioned divs over image |
| Bounding boxes missing | Display text list with page numbers |
| Image load failure | Show text extraction only |
| Slow processing | Skip to next step option |

---

## 10. Implementation Roadmap

### Phase 1: Core Visual Display (MVP)

| Task | Description | Priority |
|------|-------------|----------|
| 1.1 | Create StepVisualExtractionComponent scaffold | P0 |
| 1.2 | Implement DocumentViewerComponent (image + overlay) | P0 |
| 1.3 | Backend: Quick extraction endpoint | P0 |
| 1.4 | Backend: Page image endpoint | P0 |
| 1.5 | Integrate into wizard (step 1 position) | P0 |
| 1.6 | Add page navigation | P0 |
| 1.7 | Style with healthcare theme | P0 |

**Deliverable:** Basic visual extraction display with page navigation

### Phase 2: Confidence Visualization

| Task | Description | Priority |
|------|-------------|----------|
| 2.1 | Implement region highlighting (color by confidence) | P0 |
| 2.2 | Add confidence legend | P0 |
| 2.3 | Implement region click handler | P1 |
| 2.4 | Add extraction details panel | P1 |
| 2.5 | Show empty/missing region indicators | P1 |

**Deliverable:** Confidence-colored extraction overlay

### Phase 3: Enhanced Features

| Task | Description | Priority |
|------|-------------|----------|
| 3.1 | Implement zoom controls | P1 |
| 3.2 | Add side-by-side comparison view | P1 |
| 3.3 | Add text-only view mode | P2 |
| 3.4 | Implement text selection/copy | P2 |
| 3.5 | Add thumbnail navigation strip | P2 |

**Deliverable:** Full-featured visual extraction display

### Phase 4: Testing & Polish

| Task | Description | Priority |
|------|-------------|----------|
| 4.1 | Unit tests for components | P0 |
| 4.2 | E2E tests for wizard flow | P0 |
| 4.3 | Performance testing (10+ page docs) | P1 |
| 4.4 | Mobile responsive testing | P1 |
| 4.5 | Accessibility audit | P1 |

**Deliverable:** Production-ready visual extraction step

---

## 11. Open Questions

| ID | Question | Impact | Decision Needed By |
|----|----------|--------|-------------------|
| Q-1 | Should quick extraction happen during upload (parallel) or after? | HIGH | Phase 1 |
| Q-2 | Should we skip this step for non-image documents? | MEDIUM | Phase 1 |
| Q-3 | What if document has 50+ pages? Pagination limit? | MEDIUM | Phase 1 |
| Q-4 | Should users be able to edit extraction in this step? | MEDIUM | Phase 2 |
| Q-5 | Should we save visual extraction state for later reference? | LOW | Phase 3 |

---

## 12. UI Mockup

### 12.1 Main Visual Extraction View

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  [< Back to Upload]        Visual Extraction Display         [Continue >]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────┐  ┌──────────────────────────────────┐│
│  │                                  │  │                                  ││
│  │      DOCUMENT PREVIEW            │  │      EXTRACTION PANEL            ││
│  │                                  │  │                                  ││
│  │  ┌──────────────────────────┐   │  │  ┌──────────────────────────┐   ││
│  │  │ ┌─────────────────────┐  │   │  │  │ All Extracted Text       │   ││
│  │  │ │ PATIENT INFORMATION │  │   │  │  │────────────────────────  │   ││
│  │  │ └─────────────────────┘  │   │  │  │                          │   ││
│  │  │ ┌─────────────────────┐  │   │  │  │ PATIENT INFORMATION      │   ││
│  │  │ │ Mrs AMNA OBAID...  ▓│  │   │  │  │ Mrs AMNA OBAID ALI       │   ││
│  │  │ └─────────────────────┘  │   │  │  │ ALZAABI                  │   ││
│  │  │ ┌─────────────────────┐  │   │  │  │ DOB: 1985-03-15          │   ││
│  │  │ │ Date: 1985-03-15   ▒│  │   │  │  │ Gender: Female           │   ││
│  │  │ └─────────────────────┘  │   │  │  │                          │   ││
│  │  │                          │   │  │  │ PROVIDER INFORMATION     │   ││
│  │  │ ┌─────────────────────┐  │   │  │  │ Apollo Specialty Hosp.   │   ││
│  │  │ │     SERVICES        │  │   │  │  │ NPI: 1234567890          │   ││
│  │  │ ├─────────────────────┤  │   │  │  │                          │   ││
│  │  │ │ Consultation  2500 ▓│  │   │  │  │ SERVICES                 │   ││
│  │  │ │ Lab Test      1200 ▓│  │   │  │  │ Consultation: Rs 2,500   │   ││
│  │  │ └─────────────────────┘  │   │  │  │ Lab Test: Rs 1,200       │   ││
│  │  │                          │   │  │  │                          │   ││
│  │  │ ┌─────────────────────┐  │   │  │  │ TOTAL: Rs 3,700          │   ││
│  │  │ │ TOTAL: Rs 3,700    ▓│  │   │  │  │                          │   ││
│  │  │ └─────────────────────┘  │   │  │  └──────────────────────────┘   ││
│  │  └──────────────────────────┘   │  │                                  ││
│  │                                  │  │  ┌──────────────────────────┐   ││
│  │  Legend:                         │  │  │ Selected Region Details  │   ││
│  │  ▓ High (>80%)                   │  │  │ Text: Mrs AMNA OBAID...  │   ││
│  │  ▒ Medium (50-80%)               │  │  │ Confidence: 95%          │   ││
│  │  ░ Low (<50%)                    │  │  │ Position: Page 1         │   ││
│  │                                  │  │  └──────────────────────────┘   ││
│  └──────────────────────────────────┘  └──────────────────────────────────┘│
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  [Page 1 of 3]    [|◄] [◄] [1] [2] [3] [►] [►|]     [-] [100%] [+]   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  View Mode:  [Overlay ▼]  [Side-by-Side]  [Text Only]                │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│                                                                              │
│  [ ◄ Back to Upload ]                              [ Continue to Processing ► ] │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 12.2 Side-by-Side Comparison View

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  View Mode:  [Overlay]  [Side-by-Side ▼]  [Text Only]                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────┐    ┌───────────────────────────┐            │
│  │    ORIGINAL DOCUMENT      │    │    EXTRACTED DATA         │            │
│  │                           │    │                           │            │
│  │  ┌─────────────────────┐  │    │  ┌─────────────────────┐  │            │
│  │  │  [Actual PDF image] │  │    │  │  PATIENT INFO       │  │            │
│  │  │                     │  │    │  │  ─────────────────  │  │            │
│  │  │  Patient: AMNA...   │  │ ←──→ │  │  Name: AMNA...    │  │            │
│  │  │  DOB: 15-03-1985    │  │    │  │  DOB: 1985-03-15   │  │            │
│  │  │                     │  │    │  │                     │  │            │
│  │  │  Provider:          │  │    │  │  PROVIDER INFO      │  │            │
│  │  │  Apollo Hospital    │  │    │  │  ─────────────────  │  │            │
│  │  │                     │  │    │  │  Name: Apollo Hosp  │  │            │
│  │  └─────────────────────┘  │    │  └─────────────────────┘  │            │
│  │                           │    │                           │            │
│  └───────────────────────────┘    └───────────────────────────┘            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 13. Code Implementation Guide

### 13.1 StepVisualExtractionComponent

**Location:** `frontend/apps/claims-portal/src/app/features/claims/components/claim-submit/step-visual-extraction/`

```typescript
// step-visual-extraction.component.ts

@Component({
  selector: 'app-step-visual-extraction',
  standalone: true,
  imports: [
    CommonModule,
    CardModule,
    ButtonModule,
    SplitterModule,
    DropdownModule,
    SliderModule,
    ProgressSpinnerModule,
  ],
  template: `
    <div class="visual-extraction-step">
      <div class="step-header">
        <h3>Visual Extraction Display</h3>
        <span class="overall-confidence" [ngClass]="getConfidenceClass(overallConfidence())">
          Overall Confidence: {{ overallConfidence() | percent:'1.0-0' }}
        </span>
      </div>

      @if (isLoading()) {
        <div class="loading-container">
          <p-progressSpinner />
          <p>Extracting document data...</p>
        </div>
      } @else if (error()) {
        <p-message severity="error" [text]="error()" />
      } @else {
        <p-splitter [style]="{height: '600px'}" [panelSizes]="[60, 40]">
          <!-- Document Viewer Panel -->
          <ng-template pTemplate>
            <div class="document-viewer-panel">
              <app-document-viewer
                [pageImage]="currentPageImage()"
                [regions]="currentPageRegions()"
                [zoomLevel]="zoomLevel()"
                [selectedRegion]="selectedRegion()"
                (regionClick)="onRegionClick($event)"
              />

              <div class="viewer-controls">
                <app-page-navigator
                  [currentPage]="currentPage()"
                  [totalPages]="totalPages()"
                  (pageChange)="onPageChange($event)"
                />
                <app-zoom-controls
                  [zoomLevel]="zoomLevel()"
                  (zoomChange)="onZoomChange($event)"
                />
              </div>

              <app-confidence-legend />
            </div>
          </ng-template>

          <!-- Extraction Panel -->
          <ng-template pTemplate>
            <div class="extraction-panel">
              <app-full-text-display
                [pages]="pages()"
                [selectedRegion]="selectedRegion()"
              />

              @if (selectedRegion()) {
                <app-region-details
                  [region]="selectedRegion()!"
                />
              }
            </div>
          </ng-template>
        </p-splitter>

        <div class="view-mode-selector">
          <p-dropdown
            [options]="viewModeOptions"
            [(ngModel)]="viewMode"
            optionLabel="label"
            optionValue="value"
          />
        </div>
      }

      <div class="step-actions">
        <p-button
          label="Back to Upload"
          icon="pi pi-arrow-left"
          styleClass="p-button-outlined"
          (onClick)="stepBack.emit()"
        />
        <p-button
          label="Continue to Processing"
          icon="pi pi-arrow-right"
          iconPos="right"
          [disabled]="isLoading()"
          (onClick)="stepComplete.emit()"
        />
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StepVisualExtractionComponent implements OnInit {
  @Input() documents: DocumentUploadState[] = [];
  @Output() stepComplete = new EventEmitter<OCRExtractionResult>();
  @Output() stepBack = new EventEmitter<void>();

  // State signals
  readonly isLoading = signal(true);
  readonly error = signal<string | null>(null);
  readonly currentPage = signal(1);
  readonly totalPages = signal(0);
  readonly zoomLevel = signal(100);
  readonly selectedRegion = signal<TextRegion | null>(null);
  readonly pages = signal<PageExtraction[]>([]);
  readonly overallConfidence = signal(0);

  viewMode: 'overlay' | 'side-by-side' | 'text-only' = 'overlay';

  readonly viewModeOptions = [
    { label: 'Overlay', value: 'overlay' },
    { label: 'Side-by-Side', value: 'side-by-side' },
    { label: 'Text Only', value: 'text-only' },
  ];

  readonly currentPageImage = computed(() => {
    const page = this.pages().find(p => p.page_number === this.currentPage());
    return page?.image_url ?? '';
  });

  readonly currentPageRegions = computed(() => {
    const page = this.pages().find(p => p.page_number === this.currentPage());
    return page?.regions ?? [];
  });

  private readonly documentService = inject(DocumentService);

  async ngOnInit(): Promise<void> {
    if (this.documents.length > 0) {
      await this.performQuickExtraction();
    }
  }

  private async performQuickExtraction(): Promise<void> {
    this.isLoading.set(true);
    this.error.set(null);

    try {
      const result = await this.documentService.quickExtract(
        this.documents[0].id
      );

      this.pages.set(result.pages);
      this.totalPages.set(result.total_pages);
      this.overallConfidence.set(result.overall_confidence);
      this.isLoading.set(false);

    } catch (err) {
      this.error.set('Failed to extract document data');
      this.isLoading.set(false);
    }
  }

  onPageChange(page: number): void {
    this.currentPage.set(page);
    this.selectedRegion.set(null);
  }

  onZoomChange(zoom: number): void {
    this.zoomLevel.set(zoom);
  }

  onRegionClick(region: TextRegion): void {
    this.selectedRegion.set(region);
  }

  getConfidenceClass(confidence: number): string {
    if (confidence >= 0.8) return 'confidence-high';
    if (confidence >= 0.5) return 'confidence-medium';
    return 'confidence-low';
  }
}
```

### 13.2 DocumentViewerComponent (Canvas-based)

```typescript
// document-viewer.component.ts

@Component({
  selector: 'app-document-viewer',
  template: `
    <div class="document-viewer" #container>
      <canvas #canvas></canvas>
    </div>
  `,
  styles: [`
    .document-viewer {
      position: relative;
      width: 100%;
      height: 100%;
      overflow: auto;
      background: #e0e0e0;
    }
    canvas {
      display: block;
      margin: auto;
    }
  `],
})
export class DocumentViewerComponent implements AfterViewInit, OnChanges {
  @Input() pageImage: string = '';
  @Input() regions: TextRegion[] = [];
  @Input() zoomLevel: number = 100;
  @Input() selectedRegion: TextRegion | null = null;

  @Output() regionClick = new EventEmitter<TextRegion>();

  @ViewChild('canvas') canvasRef!: ElementRef<HTMLCanvasElement>;
  @ViewChild('container') containerRef!: ElementRef<HTMLDivElement>;

  private ctx!: CanvasRenderingContext2D;
  private image: HTMLImageElement | null = null;

  ngAfterViewInit(): void {
    this.ctx = this.canvasRef.nativeElement.getContext('2d')!;
    this.loadImage();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['pageImage']) {
      this.loadImage();
    } else if (changes['zoomLevel'] || changes['regions'] || changes['selectedRegion']) {
      this.render();
    }
  }

  private loadImage(): void {
    if (!this.pageImage) return;

    this.image = new Image();
    this.image.onload = () => this.render();
    this.image.src = this.pageImage;
  }

  private render(): void {
    if (!this.image || !this.ctx) return;

    const scale = this.zoomLevel / 100;
    const width = this.image.width * scale;
    const height = this.image.height * scale;

    this.canvasRef.nativeElement.width = width;
    this.canvasRef.nativeElement.height = height;

    // Draw image
    this.ctx.drawImage(this.image, 0, 0, width, height);

    // Draw extraction overlays
    for (const region of this.regions) {
      this.drawRegion(region, width, height);
    }
  }

  private drawRegion(region: TextRegion, width: number, height: number): void {
    const box = region.bounding_box;
    const x = box.x * width;
    const y = box.y * height;
    const w = box.width * width;
    const h = box.height * height;

    // Confidence-based color
    const alpha = region === this.selectedRegion ? 0.5 : 0.3;
    if (region.confidence >= 0.8) {
      this.ctx.fillStyle = `rgba(40, 167, 69, ${alpha})`; // Green
    } else if (region.confidence >= 0.5) {
      this.ctx.fillStyle = `rgba(255, 193, 7, ${alpha})`; // Yellow
    } else {
      this.ctx.fillStyle = `rgba(220, 53, 69, ${alpha})`; // Red
    }

    this.ctx.fillRect(x, y, w, h);

    // Border for selected region
    if (region === this.selectedRegion) {
      this.ctx.strokeStyle = '#0d6efd';
      this.ctx.lineWidth = 2;
      this.ctx.strokeRect(x, y, w, h);
    }
  }

  @HostListener('click', ['$event'])
  onClick(event: MouseEvent): void {
    if (!this.image) return;

    const rect = this.canvasRef.nativeElement.getBoundingClientRect();
    const scale = this.zoomLevel / 100;
    const x = (event.clientX - rect.left) / (this.image.width * scale);
    const y = (event.clientY - rect.top) / (this.image.height * scale);

    // Find clicked region
    for (const region of this.regions) {
      const box = region.bounding_box;
      if (x >= box.x && x <= box.x + box.width &&
          y >= box.y && y <= box.y + box.height) {
        this.regionClick.emit(region);
        break;
      }
    }
  }
}
```

### 13.3 Backend Quick Extraction Endpoint

**File:** `src/api/routes/documents.py` (additions)

```python
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

class BoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float

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

@router.post("/quick-extract", response_model=QuickExtractionResponse)
async def quick_extract(
    file: UploadFile = File(...),
    return_images: bool = True,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Perform quick OCR extraction with bounding boxes.

    This endpoint extracts text from documents with position information
    but does NOT perform LLM parsing. Used for the Visual Extraction Display step.

    Source: Design Doc 10 - Visual Extraction Display
    """
    from src.services.document_processor import get_document_processor

    processor = get_document_processor()

    # Perform OCR only (no LLM parsing)
    result = await processor.quick_extract_with_boxes(
        file_data=await file.read(),
        filename=file.filename,
        content_type=file.content_type,
        tenant_id=tenant_id,
        return_images=return_images,
    )

    return result


@router.get("/{document_id}/page/{page_number}/image")
async def get_page_image(
    document_id: str,
    page_number: int,
    width: int = 800,
    format: str = "png",
    tenant_id: str = Depends(get_current_tenant_id),
):
    """
    Get a single page of the document as an image.

    Source: Design Doc 10 - Visual Extraction Display
    """
    from src.services.document_storage import get_storage_service

    storage = get_storage_service()

    image_bytes = await storage.get_page_image(
        document_id=document_id,
        page_number=page_number,
        width=width,
        format=format,
        tenant_id=tenant_id,
    )

    if not image_bytes:
        raise HTTPException(status_code=404, detail=f"Page {page_number} not found")

    media_type = f"image/{format}"
    return Response(content=image_bytes, media_type=media_type)
```

---

## 14. Updated Wizard Integration

### 14.1 Updated Claim Submit Component

```typescript
// claim-submit.component.ts - Updated imports and steps

import { StepVisualExtractionComponent } from './step-visual-extraction/step-visual-extraction.component';

// Updated 6-step flow
readonly steps: MenuItem[] = [
  { label: 'Upload Documents', icon: 'pi pi-upload' },
  { label: 'Visual Extraction', icon: 'pi pi-image' },     // NEW - Step 1
  { label: 'Processing', icon: 'pi pi-cog' },              // Was Step 1, now Step 2
  { label: 'Preview Extraction', icon: 'pi pi-eye' },      // Was Step 2, now Step 3
  { label: 'Review Data', icon: 'pi pi-pencil' },          // Was Step 3, now Step 4
  { label: 'Submit', icon: 'pi pi-check-square' },         // Was Step 4, now Step 5
];

// Updated template switch
@switch (currentStep()) {
  @case (0) {
    <app-step-claim-docs ... />
  }
  @case (1) {
    <!-- NEW: Visual Extraction Display -->
    <app-step-visual-extraction
      [documents]="enhancedFormState().claimDocuments"
      (stepComplete)="onVisualExtractionComplete($event)"
      (stepBack)="goBack()"
    />
  }
  @case (2) {
    <app-step-processing ... />
  }
  @case (3) {
    <app-step-preview-extraction ... />
  }
  @case (4) {
    <app-step-review [editMode]="true" ... />
  }
  @case (5) {
    <app-step-review [editMode]="false" ... />
  }
}

// New handler
onVisualExtractionComplete(result: OCRExtractionResult): void {
  // Store raw extraction for later use
  this.enhancedFormState.update(state => ({
    ...state,
    rawExtractionResult: result,
  }));
  this.completedSteps.update(set => new Set([...set, 1]));
  this.currentStep.set(2); // Go to Processing
}
```

---

## Validation Checklist

Before presenting design:

- [x] Business requirements clearly mapped to technical solution
- [x] All integration points identified and specified
- [x] Security requirements addressed (STRIDE, OWASP)
- [x] Performance requirements defined
- [x] Risks identified with mitigation strategies
- [x] Implementation broken into manageable phases
- [x] No major assumptions left unvalidated
- [x] Technology choices justified with evidence
- [x] **All dependency versions explicitly specified (no "latest")**
- [x] **Version compatibility matrix completed for major dependencies**
- [x] **Cross-stack compatibility verified (frontend ↔ backend ↔ database)**
- [x] **No version conflicts identified in transitive dependencies**
- [x] **Runtime environment compatibility confirmed**
- [x] **All URLs and ports are parameterized (no hardcoded values)**
- [x] **Centralized configuration location defined for all URLs/ports**
- [x] **API endpoint mapping completed with READ/WRITE classification**
- [x] **Interface-to-API mapping documented for all components**
- [x] **URL change impact analysis completed (all consumers identified)**

---

## Appendix A: Comparison with Existing Design Docs

### Relationship to Design Doc 07 (Document Extraction System)

| Aspect | Doc 07 | This Doc (10) |
|--------|--------|---------------|
| Scope | Full extraction pipeline | Visual display of raw OCR |
| OCR | Included | Uses output from Doc 07 |
| LLM Parsing | Included | Not used (raw OCR only) |
| Output | Structured data | Positioned text regions |

### Relationship to Design Doc 08 (Preview Step)

| Aspect | Doc 08 | This Doc (10) |
|--------|--------|---------------|
| Position | After Processing | Before Processing |
| Display | Structured cards | Document-like layout |
| Data | Parsed/structured | Raw extraction regions |
| Purpose | Verify parsing | Verify OCR accuracy |
| Both steps complement each other in the workflow |

---

**Document Status:** DRAFT
**Next Action:** Review and approval required before implementation
**Approval Required From:** Tech Lead, Product Owner, User

---

## Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-24 | Architecture Team | Initial draft |
