/**
 * E2E Tests for Claim Submission Wizard
 *
 * Source: Design Doc 08 - Document Extraction Preview Step
 * Verified: 2025-12-21
 *
 * Tests the 5-step wizard flow:
 * 1. Upload Documents
 * 2. Processing
 * 3. Preview Extraction
 * 4. Review Data
 * 5. Submit
 */

describe('Claim Submission Wizard', () => {
  beforeEach(() => {
    // Navigate to claim submission page
    cy.visit('/claims/submit');
  });

  describe('Wizard Navigation', () => {
    it('should display 5-step wizard with correct labels', () => {
      // Verify all 5 steps are displayed
      cy.get('.p-steps-item').should('have.length', 5);

      // Verify step labels
      cy.get('.p-steps-item').eq(0).should('contain', 'Upload Documents');
      cy.get('.p-steps-item').eq(1).should('contain', 'Processing');
      cy.get('.p-steps-item').eq(2).should('contain', 'Preview Extraction');
      cy.get('.p-steps-item').eq(3).should('contain', 'Review Data');
      cy.get('.p-steps-item').eq(4).should('contain', 'Submit');
    });

    it('should start at Upload Documents step', () => {
      // First step should be active
      cy.get('.p-steps-item').eq(0).should('have.class', 'p-highlight');

      // Upload component should be visible
      cy.get('app-step-upload-documents').should('be.visible');
    });

    it('should not allow skipping steps by clicking future steps', () => {
      // Try to click on Preview step directly
      cy.get('.p-steps-item').eq(2).click();

      // Should still be on Upload step
      cy.get('.p-steps-item').eq(0).should('have.class', 'p-highlight');
    });
  });

  describe('Step 1: Upload Documents', () => {
    it('should display file upload areas for policy and claim documents', () => {
      cy.get('[data-testid="policy-upload"]').should('be.visible');
      cy.get('[data-testid="claim-upload"]').should('be.visible');
    });

    it('should accept PDF files', () => {
      // Upload a test PDF file
      cy.get('[data-testid="claim-upload"] input[type="file"]')
        .selectFile('src/fixtures/test-claim.pdf', { force: true });

      // File should appear in the list
      cy.get('.uploaded-file').should('contain', 'test-claim.pdf');
    });

    it('should show Start Processing button when files are uploaded', () => {
      cy.get('[data-testid="claim-upload"] input[type="file"]')
        .selectFile('src/fixtures/test-claim.pdf', { force: true });

      cy.get('button').contains('Start Processing').should('be.visible');
    });
  });

  describe('Step 2: Processing', () => {
    beforeEach(() => {
      // Upload a file and proceed to processing
      cy.get('[data-testid="claim-upload"] input[type="file"]')
        .selectFile('src/fixtures/test-claim.pdf', { force: true });
      cy.get('button').contains('Start Processing').click();
    });

    it('should show processing progress indicators', () => {
      cy.get('app-step-processing').should('be.visible');
      cy.get('.processing-progress').should('be.visible');
    });

    it('should display OCR and parsing stages', () => {
      // These may appear as the processing progresses
      cy.get('.processing-stage').should('exist');
    });
  });

  describe('Step 3: Preview Extraction', () => {
    beforeEach(() => {
      // Mock the processing complete state and navigate to preview
      cy.intercept('POST', '/api/documents/upload', {
        statusCode: 200,
        body: { document_id: 'test-123', status: 'processing' }
      });

      cy.intercept('GET', '/api/documents/*/status', {
        statusCode: 200,
        body: {
          status: 'completed',
          extracted_data: {
            patient: { name: 'John Doe', member_id: 'MEM123' },
            provider: { name: 'Dr. Smith', npi: '1234567890' },
            diagnoses: [{ code: 'J06.9', description: 'Acute URI', is_primary: true }],
            procedures: [{ code: '99213', description: 'Office visit' }],
            financial: { total_charged: '$150.00' },
            overall_confidence: 0.85
          }
        }
      });

      // Navigate to preview step (would happen automatically after processing)
      cy.visit('/claims/submit?step=2');
    });

    it('should display Preview Extraction header', () => {
      cy.get('app-step-preview-extraction').should('be.visible');
      cy.get('h3').should('contain', 'Step 3: Preview Extraction');
    });

    it('should show Summary and Detailed tabs', () => {
      cy.get('.p-tabview-nav').should('be.visible');
      cy.get('.p-tabview-nav li').should('have.length', 2);
      cy.get('.p-tabview-nav li').eq(0).should('contain', 'Summary');
      cy.get('.p-tabview-nav li').eq(1).should('contain', 'Detailed');
    });

    it('should display overall confidence badge', () => {
      cy.get('.overall-confidence').should('be.visible');
      cy.get('.overall-confidence .confidence-badge').should('be.visible');
    });

    it('should show 4 summary cards in Summary view', () => {
      // Patient, Provider, Clinical, Financial cards
      cy.get('.preview-card').should('have.length', 4);
    });

    it('should display patient information card', () => {
      cy.get('.preview-card').contains('Patient Information').should('be.visible');
    });

    it('should display provider information card', () => {
      cy.get('.preview-card').contains('Provider Information').should('be.visible');
    });

    it('should display diagnoses and procedures card', () => {
      cy.get('.preview-card').contains('Diagnoses & Procedures').should('be.visible');
    });

    it('should display financial summary card', () => {
      cy.get('.preview-card').contains('Financial Summary').should('be.visible');
    });

    it('should switch to Detailed view when tab clicked', () => {
      cy.get('.p-tabview-nav li').eq(1).click();

      // Accordion should be visible
      cy.get('.p-accordion').should('be.visible');
    });

    it('should show accordion sections in Detailed view', () => {
      cy.get('.p-tabview-nav li').eq(1).click();

      cy.get('.p-accordion-tab').should('have.length.at.least', 4);
      cy.get('.p-accordion-header').contains('Patient Information').should('be.visible');
      cy.get('.p-accordion-header').contains('Provider Information').should('be.visible');
      cy.get('.p-accordion-header').contains('Diagnoses').should('be.visible');
      cy.get('.p-accordion-header').contains('Procedures').should('be.visible');
    });

    it('should expand accordion sections on click', () => {
      cy.get('.p-tabview-nav li').eq(1).click();

      // Click Patient Information accordion
      cy.get('.p-accordion-header').contains('Patient Information').click();

      // Table should be visible
      cy.get('.p-datatable').should('be.visible');
    });

    it('should show Back and Continue buttons', () => {
      cy.get('button').contains('Back to Processing').should('be.visible');
      cy.get('button').contains('Continue to Review').should('be.visible');
    });

    it('should navigate to Review step when Continue clicked', () => {
      cy.get('button').contains('Continue to Review').click();

      // Should be on Review step
      cy.get('.p-steps-item').eq(3).should('have.class', 'p-highlight');
    });

    it('should navigate back to Processing when Back clicked', () => {
      cy.get('button').contains('Back to Processing').click();

      // Should be on Processing step
      cy.get('.p-steps-item').eq(1).should('have.class', 'p-highlight');
    });

    it('should display processed documents summary', () => {
      cy.get('.documents-summary').should('be.visible');
      cy.get('.documents-summary h5').should('contain', 'Documents Processed');
    });

    it('should show confidence badges with correct colors', () => {
      // High confidence (>= 80%) should have green class
      cy.get('.confidence-high').should('exist');
    });
  });

  describe('Step 4: Review Data', () => {
    it('should allow editing extracted data', () => {
      // Navigate to Review step
      cy.visit('/claims/submit?step=3');

      // Form fields should be editable
      cy.get('input[formControlName="patientName"]').should('be.enabled');
    });
  });

  describe('Step 5: Submit', () => {
    it('should display submission confirmation', () => {
      // Navigate to Submit step
      cy.visit('/claims/submit?step=4');

      cy.get('button').contains('Submit Claim').should('be.visible');
    });
  });

  describe('Low Confidence Warning', () => {
    beforeEach(() => {
      // Mock data with low confidence
      cy.intercept('GET', '/api/documents/*/status', {
        statusCode: 200,
        body: {
          status: 'completed',
          extracted_data: {
            patient: { name: 'John Doe' },
            overall_confidence: 0.45 // Low confidence
          }
        }
      });

      cy.visit('/claims/submit?step=2');
    });

    it('should display warning message for low confidence fields', () => {
      cy.get('.p-message-warn').should('be.visible');
      cy.get('.p-message-warn').should('contain', 'low confidence');
    });
  });

  describe('Empty State Handling', () => {
    beforeEach(() => {
      // Mock data with missing fields
      cy.intercept('GET', '/api/documents/*/status', {
        statusCode: 200,
        body: {
          status: 'completed',
          extracted_data: {
            patient: null,
            provider: null,
            overall_confidence: 0
          }
        }
      });

      cy.visit('/claims/submit?step=2');
    });

    it('should display "No data extracted" messages', () => {
      cy.get('.no-data').should('be.visible');
    });
  });

  describe('Responsive Design', () => {
    it('should display properly on mobile viewport', () => {
      cy.viewport('iphone-x');
      cy.visit('/claims/submit?step=2');

      // Summary grid should stack on mobile
      cy.get('.summary-grid').should('be.visible');
      cy.get('.preview-card').should('be.visible');
    });

    it('should display properly on tablet viewport', () => {
      cy.viewport('ipad-2');
      cy.visit('/claims/submit?step=2');

      cy.get('.summary-grid').should('be.visible');
    });
  });

  describe('Accessibility', () => {
    beforeEach(() => {
      cy.visit('/claims/submit?step=2');
    });

    it('should have aria-labels on confidence badges', () => {
      cy.get('.confidence-badge').first()
        .should('have.attr', 'aria-label');
    });

    it('should be navigable by keyboard', () => {
      // Tab to the Continue button
      cy.get('body').tab();
      cy.get('button').contains('Continue to Review').should('have.focus');
    });
  });
});
