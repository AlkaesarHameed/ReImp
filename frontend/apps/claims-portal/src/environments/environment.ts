/**
 * Development environment configuration.
 * Source: Design Document Section 5.0
 *
 * API URL should match the backend .env API_PORT setting.
 * Default: http://localhost:8000/api/v1
 */
import { Environment, DEFAULT_PORTS } from './environment.interface';

export const environment: Environment = {
  production: false,
  apiUrl: `http://localhost:${DEFAULT_PORTS.API}/api/v1`,
  wsUrl: `ws://localhost:${DEFAULT_PORTS.API}/ws`,
  sessionTimeout: 15 * 60 * 1000, // 15 minutes
  enableAuditLogging: true,
  logLevel: 'debug',

  // Development feature flags
  features: {
    enableWebSocket: true,
    enableOfflineMode: false,
    enableAnalytics: false,
  },
};
