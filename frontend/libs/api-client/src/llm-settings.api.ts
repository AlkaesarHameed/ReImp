/**
 * LLM Settings API Service.
 * Source: Design Document 04_validation_engine_comprehensive_design.md
 * Verified: 2025-12-19
 *
 * HTTP client for LLM configuration management.
 */
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../../apps/claims-portal/src/environments/environment';

// ============================================================================
// Types
// ============================================================================

export type LLMProvider = 'azure' | 'openai' | 'anthropic' | 'ollama' | 'vllm';

export type LLMTaskType =
  | 'extraction'
  | 'validation'
  | 'necessity'
  | 'summarization'
  | 'translation'
  | 'fraud_review';

export interface LLMProviderInfo {
  provider: LLMProvider;
  display_name: string;
  models: string[];
  requires_api_key: boolean;
  requires_endpoint: boolean;
  description: string;
}

export interface LLMSettings {
  id: string;
  tenant_id: string;
  task_type: LLMTaskType;
  provider: LLMProvider;
  model_name: string;
  api_endpoint?: string;
  temperature: number;
  max_tokens: number;
  fallback_provider?: LLMProvider;
  fallback_model?: string;
  rate_limit_rpm: number;
  rate_limit_tpm?: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LLMSettingsCreate {
  task_type: LLMTaskType;
  provider: LLMProvider;
  model_name: string;
  api_endpoint?: string;
  temperature?: number;
  max_tokens?: number;
  fallback_provider?: LLMProvider;
  fallback_model?: string;
  rate_limit_rpm?: number;
  rate_limit_tpm?: number;
  is_active?: boolean;
}

export interface LLMSettingsUpdate {
  provider?: LLMProvider;
  model_name?: string;
  api_endpoint?: string;
  temperature?: number;
  max_tokens?: number;
  fallback_provider?: LLMProvider;
  fallback_model?: string;
  rate_limit_rpm?: number;
  rate_limit_tpm?: number;
  is_active?: boolean;
}

export interface LLMTestRequest {
  provider: LLMProvider;
  model_name: string;
  api_endpoint?: string;
  api_key?: string;
}

export interface LLMTestResponse {
  success: boolean;
  message: string;
  latency_ms?: number;
  model_info?: Record<string, unknown>;
  error?: string;
}

export interface LLMUsageStats {
  task_type: string;
  provider: string;
  model_name: string;
  total_requests: number;
  total_tokens: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  avg_latency_ms: number;
  success_rate: number;
  estimated_cost_usd: number;
  period_start: string;
  period_end: string;
}

export interface LLMUsageResponse {
  stats: LLMUsageStats[];
  total_cost_usd: number;
  total_tokens: number;
  period_start: string;
  period_end: string;
}

// ============================================================================
// Service
// ============================================================================

/**
 * LLM Settings API Service.
 *
 * Provides HTTP methods for LLM configuration management.
 */
@Injectable({
  providedIn: 'root',
})
export class LLMSettingsApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/llm-settings`;

  // ============================================================================
  // Provider Information
  // ============================================================================

  /**
   * Get available LLM providers.
   * Source: GET /api/v1/llm-settings/providers
   */
  getProviders(): Observable<{ providers: LLMProviderInfo[] }> {
    return this.http.get<{ providers: LLMProviderInfo[] }>(
      `${this.baseUrl}/providers`,
      { withCredentials: true }
    );
  }

  // ============================================================================
  // Settings CRUD
  // ============================================================================

  /**
   * Get all LLM settings for tenant.
   * Source: GET /api/v1/llm-settings
   */
  getAllSettings(): Observable<LLMSettings[]> {
    return this.http.get<LLMSettings[]>(this.baseUrl, {
      withCredentials: true,
    });
  }

  /**
   * Get settings for specific task type.
   * Source: GET /api/v1/llm-settings/{task_type}
   */
  getSettings(taskType: LLMTaskType): Observable<LLMSettings> {
    return this.http.get<LLMSettings>(`${this.baseUrl}/${taskType}`, {
      withCredentials: true,
    });
  }

  /**
   * Create settings for task type.
   * Source: POST /api/v1/llm-settings
   */
  createSettings(settings: LLMSettingsCreate): Observable<LLMSettings> {
    return this.http.post<LLMSettings>(this.baseUrl, settings, {
      withCredentials: true,
    });
  }

  /**
   * Update settings for task type.
   * Source: PUT /api/v1/llm-settings/{task_type}
   */
  updateSettings(
    taskType: LLMTaskType,
    settings: LLMSettingsUpdate
  ): Observable<LLMSettings> {
    return this.http.put<LLMSettings>(`${this.baseUrl}/${taskType}`, settings, {
      withCredentials: true,
    });
  }

  /**
   * Delete settings for task type.
   * Source: DELETE /api/v1/llm-settings/{task_type}
   */
  deleteSettings(taskType: LLMTaskType): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${taskType}`, {
      withCredentials: true,
    });
  }

  // ============================================================================
  // Testing and Usage
  // ============================================================================

  /**
   * Test LLM provider connection.
   * Source: POST /api/v1/llm-settings/test
   */
  testConnection(request: LLMTestRequest): Observable<LLMTestResponse> {
    return this.http.post<LLMTestResponse>(`${this.baseUrl}/test`, request, {
      withCredentials: true,
    });
  }

  /**
   * Get usage statistics.
   * Source: GET /api/v1/llm-settings/usage/stats
   */
  getUsageStats(): Observable<LLMUsageResponse> {
    return this.http.get<LLMUsageResponse>(`${this.baseUrl}/usage/stats`, {
      withCredentials: true,
    });
  }
}
