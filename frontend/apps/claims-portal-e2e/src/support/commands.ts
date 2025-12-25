/**
 * Custom Cypress Commands
 *
 * Source: Design Doc 08 - Document Extraction Preview Step
 * Verified: 2025-12-21
 */

// Add custom commands here
// Cypress.Commands.add('login', (email, password) => { ... })

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace Cypress {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    interface Chainable<Subject> {
      login(email: string, password: string): Chainable<void>;
    }
  }
}

/**
 * Custom command to login with email and password
 */
Cypress.Commands.add('login', (email: string, password: string) => {
  // TODO: Implement actual login flow
  cy.log(`Logging in as ${email}`);

  // Visit login page
  cy.visit('/auth/login');

  // Fill in credentials
  cy.get('input[type="email"], input[name="email"]').type(email);
  cy.get('input[type="password"], input[name="password"]').type(password);

  // Submit form
  cy.get('button[type="submit"]').click();

  // Wait for navigation
  cy.url().should('not.include', '/login');
});

export {};
