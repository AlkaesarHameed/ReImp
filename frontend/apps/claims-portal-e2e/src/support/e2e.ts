/**
 * E2E Support File
 *
 * This file runs before every spec file.
 * Put global configuration and behavior here.
 */

// Import commands
import './commands';

// Alternatively you can use CommonJS syntax:
// require('./commands')

// Hide XHR requests from command log
Cypress.on('uncaught:exception', (err) => {
  // Returning false here prevents Cypress from failing the test
  // This is useful for third-party scripts that throw errors
  if (err.message.includes('ResizeObserver')) {
    return false;
  }
  return true;
});
