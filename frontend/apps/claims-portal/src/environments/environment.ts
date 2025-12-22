/**
 * ============================================================================
 * AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * ============================================================================
 * Source: config/ports.yaml
 * Generated: 2025-12-22 09:14:35
 * Regenerate: python scripts/generate-config.py
 * ============================================================================
 */
import { Environment } from './environment.interface';

export const environment: Environment = {
  production: false,

  // API Configuration (from config/ports.yaml)
  apiUrl: '/api/v1',
  wsUrl: 'ws://localhost:8002/ws',

  // Session Configuration
  sessionTimeout: 15 * 60 * 1000, // 15 minutes

  // Logging
  enableAuditLogging: true,
  logLevel: 'debug',

  // Feature Flags
  features: {
    enableWebSocket: true,
    enableOfflineMode: false,
    enableAnalytics: false,
  },
};
