/**
 * Environment Configuration Interface.
 * Source: Design Document Section 5.0
 *
 * All environment files must implement this interface to ensure
 * consistent configuration across development, staging, and production.
 */
export interface Environment {
  /** Whether this is a production build */
  production: boolean;

  /** Base URL for API calls (e.g., 'http://localhost:8000/api/v1' or '/api/v1') */
  apiUrl: string;

  /** WebSocket URL for real-time updates */
  wsUrl: string;

  /** Session timeout in milliseconds */
  sessionTimeout: number;

  /** Enable audit logging */
  enableAuditLogging: boolean;

  /** Log level: 'debug' | 'info' | 'warn' | 'error' */
  logLevel: 'debug' | 'info' | 'warn' | 'error';

  /** Optional security settings (production only) */
  security?: {
    enableCSP: boolean;
    enableHSTS: boolean;
    maxIdleTime: number;
    maxSessionTime: number;
    requireHttps: boolean;
  };

  /** Optional feature flags */
  features?: {
    enableWebSocket: boolean;
    enableOfflineMode: boolean;
    enableAnalytics: boolean;
  };
}

/**
 * API Configuration Constants.
 * Use these for consistent API path construction.
 */
export const API_PATHS = {
  // Claims endpoints
  CLAIMS: '/claims',
  CLAIMS_STATS: '/claims/stats/summary',
  CLAIMS_BULK: '/claims/bulk',
  CLAIMS_EXPORT: '/claims/export',

  // Eligibility endpoints
  ELIGIBILITY: '/eligibility',
  ELIGIBILITY_BATCH: '/eligibility/batch',

  // Lookup endpoints
  LOOKUP: '/lookup',
  LOOKUP_ICD10: '/lookup/icd10',
  LOOKUP_CPT: '/lookup/cpt',
  LOOKUP_HCPCS: '/lookup/hcpcs',
  LOOKUP_POS: '/lookup/pos',
  LOOKUP_MODIFIERS: '/lookup/modifiers',
  LOOKUP_DENIAL_REASONS: '/lookup/denial-reasons',

  // User management endpoints
  USERS: '/users',
  ROLES: '/roles',
  PERMISSIONS: '/permissions',

  // LLM settings endpoints
  LLM_SETTINGS: '/llm-settings',
  LLM_PROVIDERS: '/llm-settings/providers',
  LLM_TEST: '/llm-settings/test',
  LLM_USAGE: '/llm-settings/usage/stats',

  // Document endpoints
  DOCUMENTS: '/documents',
  DOCUMENTS_UPLOAD: '/documents/upload',
  DOCUMENTS_PROCESS: '/documents/process',

  // Health endpoints
  HEALTH: '/health',
} as const;

/**
 * Default port configuration.
 * These should match the backend .env configuration.
 *
 * NOTE: During local development, the API runs on port 8002 to avoid
 * conflicts with other services. Production uses port 8000.
 */
export const DEFAULT_PORTS = {
  /** API port for local development */
  API: 8002,
  /** Frontend Angular app port */
  FRONTEND: 4200,
  /** Streamlit dashboard port */
  STREAMLIT: 8502,
  /** WebSocket port (same as API) */
  WEBSOCKET: 8002,
} as const;
