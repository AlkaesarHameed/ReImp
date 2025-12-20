/**
 * LLM Settings Component.
 * Source: Design Document 04_validation_engine_comprehensive_design.md
 * Phase 4.2: Angular LLM Settings Component
 * Verified: 2025-12-19
 *
 * Configures LLM providers and models for different validation tasks.
 */
import {
  Component,
  ChangeDetectionStrategy,
  inject,
  signal,
  computed,
  OnInit,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CardModule } from 'primeng/card';
import { TabViewModule } from 'primeng/tabview';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { DropdownModule } from 'primeng/dropdown';
import { SliderModule } from 'primeng/slider';
import { InputNumberModule } from 'primeng/inputnumber';
import { InputSwitchModule } from 'primeng/inputswitch';
import { TooltipModule } from 'primeng/tooltip';
import { DialogModule } from 'primeng/dialog';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ToastModule } from 'primeng/toast';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { TagModule } from 'primeng/tag';
import { DividerModule } from 'primeng/divider';
import { PanelModule } from 'primeng/panel';
import { ChartModule } from 'primeng/chart';
import { TableModule } from 'primeng/table';
import { SkeletonModule } from 'primeng/skeleton';

import {
  LLMSettingsApiService,
  LLMSettings,
  LLMSettingsUpdate,
  LLMProviderInfo,
  LLMTaskType,
  LLMProvider,
  LLMUsageStats,
  LLMTestResponse,
} from '@claims-processing/api-client';

@Component({
  selector: 'app-llm-settings',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    CardModule,
    TabViewModule,
    ButtonModule,
    InputTextModule,
    DropdownModule,
    SliderModule,
    InputNumberModule,
    InputSwitchModule,
    TooltipModule,
    DialogModule,
    ConfirmDialogModule,
    ToastModule,
    ProgressSpinnerModule,
    TagModule,
    DividerModule,
    PanelModule,
    ChartModule,
    TableModule,
    SkeletonModule,
  ],
  providers: [ConfirmationService, MessageService],
  template: `
    <div class="llm-settings-container">
      <p-toast></p-toast>
      <p-confirmDialog></p-confirmDialog>

      <p-card>
        <ng-template pTemplate="header">
          <div class="card-header">
            <div class="header-title">
              <h2>LLM Settings</h2>
              <span class="subtitle">Configure AI providers for validation tasks</span>
            </div>
            <div class="header-actions">
              <p-button
                icon="pi pi-refresh"
                label="Refresh"
                [text]="true"
                (onClick)="loadData()"
              ></p-button>
            </div>
          </div>
        </ng-template>

        <p-tabView>
          <!-- Configuration Tab -->
          <p-tabPanel header="Configuration">
            @if (loading()) {
              <div class="loading-container">
                <p-progressSpinner></p-progressSpinner>
              </div>
            } @else {
              <div class="task-cards">
                @for (task of taskTypes; track task.value) {
                  <div class="task-card">
                    <div class="task-header">
                      <div class="task-info">
                        <i [class]="task.icon" class="task-icon"></i>
                        <div>
                          <h3>{{ task.label }}</h3>
                          <span class="task-description">{{ task.description }}</span>
                        </div>
                      </div>
                      <p-inputSwitch
                        [(ngModel)]="task.enabled"
                        (onChange)="toggleTask(task)"
                        pTooltip="Enable/Disable this task"
                      ></p-inputSwitch>
                    </div>

                    @if (getSettingsForTask(task.value); as settings) {
                      <p-divider></p-divider>
                      <div class="task-config">
                        <div class="config-row">
                          <label>Provider</label>
                          <p-dropdown
                            [options]="providerOptions"
                            [(ngModel)]="settings.provider"
                            placeholder="Select provider"
                            [style]="{ width: '100%' }"
                            (onChange)="onProviderChange(settings, task.value)"
                          ></p-dropdown>
                        </div>

                        <div class="config-row">
                          <label>Model</label>
                          <p-dropdown
                            [options]="getModelsForProvider(settings.provider)"
                            [(ngModel)]="settings.model_name"
                            placeholder="Select model"
                            [style]="{ width: '100%' }"
                          ></p-dropdown>
                        </div>

                        <div class="config-row">
                          <label>
                            Temperature
                            <span class="value-badge">{{ settings.temperature }}</span>
                          </label>
                          <p-slider
                            [(ngModel)]="settings.temperature"
                            [min]="0"
                            [max]="1"
                            [step]="0.1"
                          ></p-slider>
                          <span class="slider-labels">
                            <span>Precise</span>
                            <span>Creative</span>
                          </span>
                        </div>

                        <div class="config-row">
                          <label>Max Tokens</label>
                          <p-inputNumber
                            [(ngModel)]="settings.max_tokens"
                            [min]="100"
                            [max]="128000"
                            [step]="100"
                            [style]="{ width: '100%' }"
                          ></p-inputNumber>
                        </div>

                        <p-divider></p-divider>

                        <div class="fallback-section">
                          <h4>Fallback Configuration</h4>
                          <div class="config-row">
                            <label>Fallback Provider</label>
                            <p-dropdown
                              [options]="providerOptions"
                              [(ngModel)]="settings.fallback_provider"
                              placeholder="None"
                              [showClear]="true"
                              [style]="{ width: '100%' }"
                            ></p-dropdown>
                          </div>

                          @if (settings.fallback_provider) {
                            <div class="config-row">
                              <label>Fallback Model</label>
                              <p-dropdown
                                [options]="getModelsForProvider(settings.fallback_provider)"
                                [(ngModel)]="settings.fallback_model"
                                placeholder="Select model"
                                [style]="{ width: '100%' }"
                              ></p-dropdown>
                            </div>
                          }
                        </div>

                        <p-divider></p-divider>

                        <div class="config-row">
                          <label>Rate Limit (requests/min)</label>
                          <p-inputNumber
                            [(ngModel)]="settings.rate_limit_rpm"
                            [min]="1"
                            [max]="1000"
                            [style]="{ width: '100%' }"
                          ></p-inputNumber>
                        </div>

                        <div class="action-buttons">
                          <p-button
                            icon="pi pi-check"
                            label="Save"
                            (onClick)="saveSettings(task.value, settings)"
                            [loading]="saving()"
                          ></p-button>
                          <p-button
                            icon="pi pi-bolt"
                            label="Test Connection"
                            [text]="true"
                            (onClick)="testConnection(settings)"
                            [loading]="testing()"
                          ></p-button>
                        </div>
                      </div>
                    } @else {
                      <div class="no-config">
                        <p>No configuration for this task.</p>
                        <p-button
                          icon="pi pi-plus"
                          label="Create Configuration"
                          (onClick)="createSettings(task.value)"
                        ></p-button>
                      </div>
                    }
                  </div>
                }
              </div>
            }
          </p-tabPanel>

          <!-- Usage Statistics Tab -->
          <p-tabPanel header="Usage Statistics">
            @if (usageLoading()) {
              <div class="loading-container">
                <p-progressSpinner></p-progressSpinner>
              </div>
            } @else {
              <div class="usage-section">
                <!-- Summary Cards -->
                <div class="stats-cards">
                  <div class="stat-card">
                    <span class="stat-value">{{ totalTokens() | number }}</span>
                    <span class="stat-label">Total Tokens</span>
                  </div>
                  <div class="stat-card">
                    <span class="stat-value">\${{ totalCost() | number:'1.2-2' }}</span>
                    <span class="stat-label">Estimated Cost</span>
                  </div>
                  <div class="stat-card">
                    <span class="stat-value">{{ totalRequests() | number }}</span>
                    <span class="stat-label">Total Requests</span>
                  </div>
                  <div class="stat-card">
                    <span class="stat-value">{{ averageLatency() | number:'1.0-0' }}ms</span>
                    <span class="stat-label">Avg Latency</span>
                  </div>
                </div>

                <!-- Usage by Task -->
                <p-panel header="Usage by Task" [toggleable]="true">
                  <p-table [value]="usageStats()" styleClass="p-datatable-sm">
                    <ng-template pTemplate="header">
                      <tr>
                        <th>Task</th>
                        <th>Provider</th>
                        <th>Model</th>
                        <th>Requests</th>
                        <th>Tokens</th>
                        <th>Avg Latency</th>
                        <th>Success Rate</th>
                        <th>Cost</th>
                      </tr>
                    </ng-template>
                    <ng-template pTemplate="body" let-stat>
                      <tr>
                        <td>
                          <p-tag [value]="stat.task_type" severity="info"></p-tag>
                        </td>
                        <td>{{ stat.provider }}</td>
                        <td>{{ stat.model_name }}</td>
                        <td>{{ stat.total_requests | number }}</td>
                        <td>{{ stat.total_tokens | number }}</td>
                        <td>{{ stat.avg_latency_ms | number:'1.0-0' }}ms</td>
                        <td>
                          <p-tag
                            [value]="(stat.success_rate * 100 | number:'1.1-1') + '%'"
                            [severity]="stat.success_rate >= 0.95 ? 'success' : stat.success_rate >= 0.9 ? 'warning' : 'danger'"
                          ></p-tag>
                        </td>
                        <td>\${{ stat.estimated_cost_usd | number:'1.2-2' }}</td>
                      </tr>
                    </ng-template>
                    <ng-template pTemplate="emptymessage">
                      <tr>
                        <td colspan="8" class="text-center">No usage data available.</td>
                      </tr>
                    </ng-template>
                  </p-table>
                </p-panel>

                <!-- Usage Chart -->
                @if (chartData()) {
                  <p-panel header="Token Usage by Provider" [toggleable]="true">
                    <p-chart type="doughnut" [data]="chartData()" [options]="chartOptions"></p-chart>
                  </p-panel>
                }
              </div>
            }
          </p-tabPanel>

          <!-- Providers Tab -->
          <p-tabPanel header="Available Providers">
            <div class="providers-grid">
              @for (provider of providers(); track provider.provider) {
                <div class="provider-card">
                  <div class="provider-header">
                    <i [class]="getProviderIcon(provider.provider)"></i>
                    <h3>{{ provider.display_name }}</h3>
                  </div>
                  <p class="provider-description">{{ provider.description }}</p>
                  <div class="provider-details">
                    <div class="detail-row">
                      <span class="detail-label">Models:</span>
                      <span class="detail-value">{{ provider.models.length }}</span>
                    </div>
                    <div class="detail-row">
                      <span class="detail-label">API Key Required:</span>
                      <p-tag
                        [value]="provider.requires_api_key ? 'Yes' : 'No'"
                        [severity]="provider.requires_api_key ? 'warning' : 'success'"
                      ></p-tag>
                    </div>
                    <div class="detail-row">
                      <span class="detail-label">Custom Endpoint:</span>
                      <p-tag
                        [value]="provider.requires_endpoint ? 'Required' : 'Optional'"
                        [severity]="provider.requires_endpoint ? 'warning' : 'info'"
                      ></p-tag>
                    </div>
                  </div>
                  <div class="provider-models">
                    <span class="models-label">Available Models:</span>
                    <div class="model-tags">
                      @for (model of provider.models.slice(0, 5); track model) {
                        <p-tag [value]="model" severity="secondary"></p-tag>
                      }
                      @if (provider.models.length > 5) {
                        <span class="more-models">+{{ provider.models.length - 5 }} more</span>
                      }
                    </div>
                  </div>
                </div>
              }
            </div>
          </p-tabPanel>
        </p-tabView>
      </p-card>

      <!-- Test Result Dialog -->
      <p-dialog
        [(visible)]="testDialogVisible"
        header="Connection Test Result"
        [modal]="true"
        [style]="{ width: '400px' }"
      >
        @if (testResult()) {
          <div class="test-result">
            <div class="result-icon" [class.success]="testResult()!.success" [class.error]="!testResult()!.success">
              <i [class]="testResult()!.success ? 'pi pi-check-circle' : 'pi pi-times-circle'"></i>
            </div>
            <h3>{{ testResult()!.success ? 'Connection Successful' : 'Connection Failed' }}</h3>
            <p>{{ testResult()!.message }}</p>
            @if (testResult()!.latency_ms) {
              <div class="latency-info">
                <span>Response Time:</span>
                <strong>{{ testResult()!.latency_ms }}ms</strong>
              </div>
            }
            @if (testResult()!.error) {
              <div class="error-details">
                <span>Error:</span>
                <code>{{ testResult()!.error }}</code>
              </div>
            }
          </div>
        }
      </p-dialog>
    </div>
  `,
  styles: [`
    .llm-settings-container {
      padding: 1.5rem;
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem;
    }

    .header-title h2 {
      margin: 0;
      font-size: 1.25rem;
      font-weight: 600;
    }

    .header-title .subtitle {
      font-size: 0.875rem;
      color: var(--text-color-secondary);
    }

    .loading-container {
      display: flex;
      justify-content: center;
      padding: 3rem;
    }

    .task-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
      gap: 1.5rem;
    }

    .task-card {
      background: var(--surface-card);
      border: 1px solid var(--surface-border);
      border-radius: 8px;
      padding: 1.5rem;
    }

    .task-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }

    .task-info {
      display: flex;
      gap: 1rem;
      align-items: flex-start;
    }

    .task-icon {
      font-size: 1.5rem;
      color: var(--primary-color);
      background: var(--primary-100);
      padding: 0.75rem;
      border-radius: 8px;
    }

    .task-info h3 {
      margin: 0;
      font-size: 1rem;
      font-weight: 600;
    }

    .task-description {
      font-size: 0.875rem;
      color: var(--text-color-secondary);
    }

    .task-config {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .config-row {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .config-row label {
      font-weight: 500;
      font-size: 0.875rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .value-badge {
      background: var(--primary-100);
      color: var(--primary-color);
      padding: 0.125rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
    }

    .slider-labels {
      display: flex;
      justify-content: space-between;
      font-size: 0.75rem;
      color: var(--text-color-secondary);
    }

    .fallback-section h4 {
      margin: 0 0 1rem 0;
      font-size: 0.875rem;
      color: var(--text-color-secondary);
    }

    .action-buttons {
      display: flex;
      gap: 0.5rem;
      margin-top: 0.5rem;
    }

    .no-config {
      text-align: center;
      padding: 2rem;
      color: var(--text-color-secondary);
    }

    .stats-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }

    .stat-card {
      background: var(--surface-card);
      border: 1px solid var(--surface-border);
      border-radius: 8px;
      padding: 1rem;
      text-align: center;
    }

    .stat-value {
      display: block;
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--primary-color);
    }

    .stat-label {
      font-size: 0.875rem;
      color: var(--text-color-secondary);
    }

    .usage-section {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .providers-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 1.5rem;
    }

    .provider-card {
      background: var(--surface-card);
      border: 1px solid var(--surface-border);
      border-radius: 8px;
      padding: 1.5rem;
    }

    .provider-header {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 0.75rem;
    }

    .provider-header i {
      font-size: 1.5rem;
      color: var(--primary-color);
    }

    .provider-header h3 {
      margin: 0;
      font-size: 1.125rem;
    }

    .provider-description {
      color: var(--text-color-secondary);
      font-size: 0.875rem;
      margin-bottom: 1rem;
    }

    .provider-details {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      margin-bottom: 1rem;
    }

    .detail-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .detail-label {
      font-size: 0.875rem;
      color: var(--text-color-secondary);
    }

    .provider-models {
      border-top: 1px solid var(--surface-border);
      padding-top: 1rem;
    }

    .models-label {
      font-size: 0.75rem;
      color: var(--text-color-secondary);
      display: block;
      margin-bottom: 0.5rem;
    }

    .model-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .more-models {
      font-size: 0.75rem;
      color: var(--text-color-secondary);
      align-self: center;
    }

    .test-result {
      text-align: center;
      padding: 1rem;
    }

    .result-icon {
      font-size: 3rem;
      margin-bottom: 1rem;
    }

    .result-icon.success {
      color: var(--green-500);
    }

    .result-icon.error {
      color: var(--red-500);
    }

    .test-result h3 {
      margin: 0 0 0.5rem 0;
    }

    .latency-info {
      background: var(--surface-ground);
      padding: 0.5rem 1rem;
      border-radius: 4px;
      margin-top: 1rem;
    }

    .error-details {
      background: var(--red-50);
      padding: 0.5rem 1rem;
      border-radius: 4px;
      margin-top: 1rem;
      text-align: left;
    }

    .error-details code {
      display: block;
      font-size: 0.75rem;
      color: var(--red-700);
      word-break: break-all;
    }

    .text-center {
      text-align: center;
      padding: 2rem;
      color: var(--text-color-secondary);
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LlmSettingsComponent implements OnInit {
  private readonly api = inject(LLMSettingsApiService);
  private readonly messageService = inject(MessageService);

  // State
  loading = signal(false);
  saving = signal(false);
  testing = signal(false);
  usageLoading = signal(false);

  // Data
  settings = signal<LLMSettings[]>([]);
  providers = signal<LLMProviderInfo[]>([]);
  usageStats = signal<LLMUsageStats[]>([]);

  // Dialog state
  testDialogVisible = false;
  testResult = signal<LLMTestResponse | null>(null);

  // Task types configuration
  taskTypes = [
    {
      value: 'extraction' as LLMTaskType,
      label: 'Data Extraction',
      description: 'Extract patient data and codes from documents',
      icon: 'pi pi-file-export',
      enabled: true,
    },
    {
      value: 'validation' as LLMTaskType,
      label: 'Validation',
      description: 'Validate medical codes and crosswalks',
      icon: 'pi pi-check-circle',
      enabled: true,
    },
    {
      value: 'necessity' as LLMTaskType,
      label: 'Clinical Necessity',
      description: 'Assess medical necessity for procedures',
      icon: 'pi pi-heart',
      enabled: true,
    },
    {
      value: 'summarization' as LLMTaskType,
      label: 'Summarization',
      description: 'Summarize medical reports and findings',
      icon: 'pi pi-align-left',
      enabled: false,
    },
    {
      value: 'fraud_review' as LLMTaskType,
      label: 'Fraud Review',
      description: 'Analyze claims for potential fraud signals',
      icon: 'pi pi-shield',
      enabled: true,
    },
  ];

  // Computed values
  totalTokens = computed(() =>
    this.usageStats().reduce((sum, s) => sum + s.total_tokens, 0)
  );

  totalCost = computed(() =>
    this.usageStats().reduce((sum, s) => sum + s.estimated_cost_usd, 0)
  );

  totalRequests = computed(() =>
    this.usageStats().reduce((sum, s) => sum + s.total_requests, 0)
  );

  averageLatency = computed(() => {
    const stats = this.usageStats();
    if (stats.length === 0) return 0;
    return stats.reduce((sum, s) => sum + s.avg_latency_ms, 0) / stats.length;
  });

  chartData = computed(() => {
    const stats = this.usageStats();
    if (stats.length === 0) return null;

    const byProvider = stats.reduce((acc, s) => {
      acc[s.provider] = (acc[s.provider] || 0) + s.total_tokens;
      return acc;
    }, {} as Record<string, number>);

    return {
      labels: Object.keys(byProvider),
      datasets: [{
        data: Object.values(byProvider),
        backgroundColor: ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'],
      }],
    };
  });

  chartOptions = {
    plugins: {
      legend: {
        position: 'bottom',
      },
    },
    responsive: true,
    maintainAspectRatio: false,
  };

  // Dropdown options
  providerOptions = [
    { label: 'Azure OpenAI', value: 'azure' },
    { label: 'OpenAI', value: 'openai' },
    { label: 'Anthropic', value: 'anthropic' },
    { label: 'Ollama (Local)', value: 'ollama' },
    { label: 'vLLM (Self-hosted)', value: 'vllm' },
  ];

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.loading.set(true);
    this.usageLoading.set(true);

    // Load providers
    this.api.getProviders().subscribe({
      next: (response) => this.providers.set(response.providers),
      error: (error) => {
        console.error('Failed to load providers:', error);
        this.loadMockProviders();
      },
    });

    // Load settings
    this.api.getAllSettings().subscribe({
      next: (settings) => {
        this.settings.set(settings);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Failed to load settings:', error);
        this.loadMockSettings();
        this.loading.set(false);
      },
    });

    // Load usage stats
    this.api.getUsageStats().subscribe({
      next: (response) => {
        this.usageStats.set(response.stats);
        this.usageLoading.set(false);
      },
      error: (error) => {
        console.error('Failed to load usage stats:', error);
        this.loadMockUsage();
        this.usageLoading.set(false);
      },
    });
  }

  getSettingsForTask(taskType: LLMTaskType): LLMSettings | undefined {
    return this.settings().find(s => s.task_type === taskType);
  }

  getModelsForProvider(provider: LLMProvider | undefined): { label: string; value: string }[] {
    if (!provider) return [];

    const providerInfo = this.providers().find(p => p.provider === provider);
    if (!providerInfo) {
      // Fallback models
      const fallbackModels: Record<string, string[]> = {
        azure: ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'],
        openai: ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo', 'gpt-4o'],
        anthropic: ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku'],
        ollama: ['llama3', 'mistral', 'codellama', 'mixtral'],
        vllm: ['llama-3-70b', 'mistral-7b'],
      };
      return (fallbackModels[provider] || []).map(m => ({ label: m, value: m }));
    }

    return providerInfo.models.map(m => ({ label: m, value: m }));
  }

  getProviderIcon(provider: LLMProvider): string {
    const icons: Record<LLMProvider, string> = {
      azure: 'pi pi-microsoft',
      openai: 'pi pi-bolt',
      anthropic: 'pi pi-star',
      ollama: 'pi pi-server',
      vllm: 'pi pi-cloud',
    };
    return icons[provider] || 'pi pi-cog';
  }

  onProviderChange(settings: LLMSettings, _taskType: LLMTaskType): void {
    // Reset model when provider changes
    const models = this.getModelsForProvider(settings.provider);
    if (models.length > 0) {
      settings.model_name = models[0].value;
    }
  }

  toggleTask(task: { value: LLMTaskType; enabled: boolean }): void {
    const settings = this.getSettingsForTask(task.value);
    if (settings) {
      this.api.updateSettings(task.value, { is_active: task.enabled }).subscribe({
        next: () => {
          this.messageService.add({
            severity: 'success',
            summary: task.enabled ? 'Enabled' : 'Disabled',
            detail: `${task.value} has been ${task.enabled ? 'enabled' : 'disabled'}.`,
          });
        },
        error: () => {
          task.enabled = !task.enabled; // Revert
          this.messageService.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to update task status.',
          });
        },
      });
    }
  }

  createSettings(taskType: LLMTaskType): void {
    const defaultSettings: LLMSettings = {
      id: '',
      tenant_id: '',
      task_type: taskType,
      provider: 'azure',
      model_name: 'gpt-4',
      temperature: 0.1,
      max_tokens: 4096,
      rate_limit_rpm: 60,
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    this.settings.update(current => [...current, defaultSettings]);
  }

  saveSettings(taskType: LLMTaskType, settings: LLMSettings): void {
    this.saving.set(true);

    const update: LLMSettingsUpdate = {
      provider: settings.provider,
      model_name: settings.model_name,
      temperature: settings.temperature,
      max_tokens: settings.max_tokens,
      fallback_provider: settings.fallback_provider,
      fallback_model: settings.fallback_model,
      rate_limit_rpm: settings.rate_limit_rpm,
      is_active: settings.is_active,
    };

    this.api.updateSettings(taskType, update).subscribe({
      next: (updated) => {
        this.settings.update(current =>
          current.map(s => s.task_type === taskType ? updated : s)
        );
        this.messageService.add({
          severity: 'success',
          summary: 'Saved',
          detail: 'Settings have been saved successfully.',
        });
        this.saving.set(false);
      },
      error: (error) => {
        console.error('Failed to save settings:', error);
        this.messageService.add({
          severity: 'error',
          summary: 'Error',
          detail: 'Failed to save settings. Please try again.',
        });
        this.saving.set(false);
      },
    });
  }

  testConnection(settings: LLMSettings): void {
    this.testing.set(true);

    this.api.testConnection({
      provider: settings.provider,
      model_name: settings.model_name,
      api_endpoint: settings.api_endpoint,
    }).subscribe({
      next: (result) => {
        this.testResult.set(result);
        this.testDialogVisible = true;
        this.testing.set(false);
      },
      error: (error) => {
        this.testResult.set({
          success: false,
          message: 'Connection test failed',
          error: error.message || 'Unknown error',
        });
        this.testDialogVisible = true;
        this.testing.set(false);
      },
    });
  }

  // Mock data loaders for development
  private loadMockProviders(): void {
    this.providers.set([
      {
        provider: 'azure',
        display_name: 'Azure OpenAI',
        models: ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'],
        requires_api_key: true,
        requires_endpoint: true,
        description: 'Enterprise-grade OpenAI models hosted on Azure',
      },
      {
        provider: 'openai',
        display_name: 'OpenAI',
        models: ['gpt-4', 'gpt-4-turbo', 'gpt-4o', 'gpt-3.5-turbo'],
        requires_api_key: true,
        requires_endpoint: false,
        description: 'Direct access to OpenAI models',
      },
      {
        provider: 'anthropic',
        display_name: 'Anthropic',
        models: ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku'],
        requires_api_key: true,
        requires_endpoint: false,
        description: 'Claude models with strong reasoning capabilities',
      },
      {
        provider: 'ollama',
        display_name: 'Ollama (Local)',
        models: ['llama3', 'mistral', 'codellama', 'mixtral'],
        requires_api_key: false,
        requires_endpoint: true,
        description: 'Run models locally with Ollama',
      },
    ]);
  }

  private loadMockSettings(): void {
    this.settings.set([
      {
        id: '1',
        tenant_id: 'tenant-1',
        task_type: 'extraction',
        provider: 'azure',
        model_name: 'gpt-4',
        temperature: 0.1,
        max_tokens: 4096,
        fallback_provider: 'openai',
        fallback_model: 'gpt-3.5-turbo',
        rate_limit_rpm: 60,
        is_active: true,
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-12-15T00:00:00Z',
      },
      {
        id: '2',
        tenant_id: 'tenant-1',
        task_type: 'validation',
        provider: 'azure',
        model_name: 'gpt-4-turbo',
        temperature: 0.0,
        max_tokens: 2048,
        rate_limit_rpm: 120,
        is_active: true,
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-12-10T00:00:00Z',
      },
      {
        id: '3',
        tenant_id: 'tenant-1',
        task_type: 'necessity',
        provider: 'anthropic',
        model_name: 'claude-3-sonnet',
        temperature: 0.2,
        max_tokens: 8192,
        rate_limit_rpm: 30,
        is_active: true,
        created_at: '2025-06-01T00:00:00Z',
        updated_at: '2025-12-01T00:00:00Z',
      },
    ]);
  }

  private loadMockUsage(): void {
    this.usageStats.set([
      {
        task_type: 'extraction',
        provider: 'azure',
        model_name: 'gpt-4',
        total_requests: 15420,
        total_tokens: 12500000,
        total_prompt_tokens: 8000000,
        total_completion_tokens: 4500000,
        avg_latency_ms: 2340,
        success_rate: 0.987,
        estimated_cost_usd: 375.50,
        period_start: '2025-12-01T00:00:00Z',
        period_end: '2025-12-19T00:00:00Z',
      },
      {
        task_type: 'validation',
        provider: 'azure',
        model_name: 'gpt-4-turbo',
        total_requests: 8750,
        total_tokens: 3200000,
        total_prompt_tokens: 2100000,
        total_completion_tokens: 1100000,
        avg_latency_ms: 1850,
        success_rate: 0.995,
        estimated_cost_usd: 96.20,
        period_start: '2025-12-01T00:00:00Z',
        period_end: '2025-12-19T00:00:00Z',
      },
      {
        task_type: 'necessity',
        provider: 'anthropic',
        model_name: 'claude-3-sonnet',
        total_requests: 3200,
        total_tokens: 6400000,
        total_prompt_tokens: 4200000,
        total_completion_tokens: 2200000,
        avg_latency_ms: 3100,
        success_rate: 0.978,
        estimated_cost_usd: 192.00,
        period_start: '2025-12-01T00:00:00Z',
        period_end: '2025-12-19T00:00:00Z',
      },
    ]);
  }
}
