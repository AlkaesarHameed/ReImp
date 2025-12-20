/**
 * Production environment configuration.
 * Source: Design Document Section 5.0
 *
 * In production, API URLs are relative paths handled by reverse proxy.
 */
import { Environment } from './environment.interface';

export const environment: Environment = {
  production: true,
  apiUrl: '/api/v1',
  wsUrl: '/ws',
  sessionTimeout: 15 * 60 * 1000, // 15 minutes
  enableAuditLogging: true,
  logLevel: 'error',

  // Security settings (production only)
  security: {
    enableCSP: true,
    enableHSTS: true,
    maxIdleTime: 10 * 60 * 1000, // 10 minutes idle timeout
    maxSessionTime: 8 * 60 * 60 * 1000, // 8 hours max session
    requireHttps: true,
  },

  // Production feature flags
  features: {
    enableWebSocket: true,
    enableOfflineMode: false,
    enableAnalytics: true,
  },
};
