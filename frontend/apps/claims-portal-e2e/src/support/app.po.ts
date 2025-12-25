/**
 * Page Objects for Claims Portal E2E Tests
 *
 * Source: Design Doc 08 - Document Extraction Preview Step
 * Verified: 2025-12-21
 */

// =============================================================================
// General Page Objects
// =============================================================================

export const getGreeting = () => cy.get('h1');

// =============================================================================
// Wizard Step Navigation
// =============================================================================

export const wizardSteps = {
  /**
   * Get all wizard step items
   */
  getAll: () => cy.get('.p-steps-item'),

  /**
   * Get specific step by index (0-based)
   */
  getStep: (index: number) => cy.get('.p-steps-item').eq(index),

  /**
   * Get the currently active step
   */
  getActiveStep: () => cy.get('.p-steps-item.p-highlight'),

  /**
   * Verify current step by index
   */
  verifyActiveStep: (index: number) => {
    cy.get('.p-steps-item').eq(index).should('have.class', 'p-highlight');
  },

  /**
   * Click on a step (may not navigate if step is locked)
   */
  clickStep: (index: number) => {
    cy.get('.p-steps-item').eq(index).click();
  },
};

// =============================================================================
// Upload Documents Step (Step 1)
// =============================================================================

export const uploadStep = {
  /**
   * Get the upload component
   */
  getComponent: () => cy.get('app-step-upload-documents'),

  /**
   * Get policy document upload area
   */
  getPolicyUpload: () => cy.get('[data-testid="policy-upload"]'),

  /**
   * Get claim document upload area
   */
  getClaimUpload: () => cy.get('[data-testid="claim-upload"]'),

  /**
   * Upload a file to claim documents
   */
  uploadClaimDocument: (filePath: string) => {
    cy.get('[data-testid="claim-upload"] input[type="file"]')
      .selectFile(filePath, { force: true });
  },

  /**
   * Upload a file to policy documents
   */
  uploadPolicyDocument: (filePath: string) => {
    cy.get('[data-testid="policy-upload"] input[type="file"]')
      .selectFile(filePath, { force: true });
  },

  /**
   * Click Start Processing button
   */
  startProcessing: () => {
    cy.get('button').contains('Start Processing').click();
  },
};

// =============================================================================
// Processing Step (Step 2)
// =============================================================================

export const processingStep = {
  /**
   * Get the processing component
   */
  getComponent: () => cy.get('app-step-processing'),

  /**
   * Get progress indicator
   */
  getProgress: () => cy.get('.processing-progress'),

  /**
   * Wait for processing to complete
   */
  waitForComplete: (timeout = 30000) => {
    cy.get('.processing-complete', { timeout }).should('be.visible');
  },
};

// =============================================================================
// Preview Extraction Step (Step 3)
// =============================================================================

export const previewStep = {
  /**
   * Get the preview component
   */
  getComponent: () => cy.get('app-step-preview-extraction'),

  /**
   * Get overall confidence badge
   */
  getOverallConfidence: () => cy.get('.overall-confidence .confidence-badge'),

  /**
   * Get low confidence warning message
   */
  getLowConfidenceWarning: () => cy.get('.p-message-warn'),

  /**
   * Get Summary tab
   */
  getSummaryTab: () => cy.get('.p-tabview-nav li').eq(0),

  /**
   * Get Detailed tab
   */
  getDetailedTab: () => cy.get('.p-tabview-nav li').eq(1),

  /**
   * Switch to Summary view
   */
  switchToSummary: () => {
    cy.get('.p-tabview-nav li').eq(0).click();
  },

  /**
   * Switch to Detailed view
   */
  switchToDetailed: () => {
    cy.get('.p-tabview-nav li').eq(1).click();
  },

  /**
   * Get all preview cards
   */
  getCards: () => cy.get('.preview-card'),

  /**
   * Get patient card
   */
  getPatientCard: () => cy.get('.preview-card').contains('Patient Information').parents('.preview-card'),

  /**
   * Get provider card
   */
  getProviderCard: () => cy.get('.preview-card').contains('Provider Information').parents('.preview-card'),

  /**
   * Get clinical data card
   */
  getClinicalCard: () => cy.get('.preview-card').contains('Diagnoses & Procedures').parents('.preview-card'),

  /**
   * Get financial card
   */
  getFinancialCard: () => cy.get('.preview-card').contains('Financial Summary').parents('.preview-card'),

  /**
   * Get accordion sections in detailed view
   */
  getAccordionSections: () => cy.get('.p-accordion-tab'),

  /**
   * Expand an accordion section by header text
   */
  expandAccordion: (headerText: string) => {
    cy.get('.p-accordion-header').contains(headerText).click();
  },

  /**
   * Get processed documents list
   */
  getProcessedDocuments: () => cy.get('.documents-summary .doc-chips'),

  /**
   * Click Back button
   */
  goBack: () => {
    cy.get('button').contains('Back to Processing').click();
  },

  /**
   * Click Continue button
   */
  continue: () => {
    cy.get('button').contains('Continue to Review').click();
  },
};

// =============================================================================
// Review Step (Step 4)
// =============================================================================

export const reviewStep = {
  /**
   * Get the review component
   */
  getComponent: () => cy.get('app-step-review-data'),

  /**
   * Get form fields
   */
  getFormField: (fieldName: string) => cy.get(`[formControlName="${fieldName}"]`),

  /**
   * Click Proceed to Submit button
   */
  proceedToSubmit: () => {
    cy.get('button').contains('Proceed to Submit').click();
  },
};

// =============================================================================
// Submit Step (Step 5)
// =============================================================================

export const submitStep = {
  /**
   * Get the submit component
   */
  getComponent: () => cy.get('app-step-submit-claim'),

  /**
   * Click Submit Claim button
   */
  submitClaim: () => {
    cy.get('button').contains('Submit Claim').click();
  },

  /**
   * Get submission confirmation
   */
  getConfirmation: () => cy.get('.submission-confirmation'),
};

// =============================================================================
// Confidence Badge Helpers
// =============================================================================

export const confidenceBadge = {
  /**
   * Get all confidence badges
   */
  getAll: () => cy.get('.confidence-badge'),

  /**
   * Get high confidence badges (green)
   */
  getHigh: () => cy.get('.confidence-high'),

  /**
   * Get medium confidence badges (yellow)
   */
  getMedium: () => cy.get('.confidence-medium'),

  /**
   * Get low confidence badges (red)
   */
  getLow: () => cy.get('.confidence-low'),

  /**
   * Verify confidence level of a specific badge
   */
  verifyLevel: (selector: string, level: 'high' | 'medium' | 'low' | 'unknown') => {
    cy.get(selector).should('have.class', `confidence-${level}`);
  },
};
