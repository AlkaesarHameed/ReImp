/**
 * WebSocket Service.
 * Source: Design Document Section 4.2, 7.0
 *
 * Real-time communication service for claims updates.
 * Implements throttling for high-volume updates (4000 claims/minute).
 */
import { Injectable, signal, computed } from '@angular/core';
import { Observable, Subject, BehaviorSubject, timer, interval } from 'rxjs';
import {
  webSocket,
  WebSocketSubject,
  WebSocketSubjectConfig,
} from 'rxjs/webSocket';
import {
  tap,
  throttleTime,
  bufferTime,
  filter,
  takeUntil,
  shareReplay,
} from 'rxjs/operators';
import { environment } from '../../../environments/environment';

/**
 * Enable mock mode for development when backend is not available.
 * Set to true to simulate WebSocket connection with fake metrics.
 */
const ENABLE_MOCK_WEBSOCKET = !environment.production;

export interface WebSocketMessage<T = unknown> {
  type: 'claim_update' | 'metrics' | 'notification' | 'heartbeat';
  payload: T;
  timestamp: string;
}

export interface ClaimUpdatePayload {
  claim_id: string;
  status: string;
  tracking_number: string;
  updated_fields: string[];
}

export interface MetricsPayload {
  claims_per_minute: number;
  pending_count: number;
  processing_count: number;
  approved_today: number;
  denied_today: number;
}

export interface NotificationPayload {
  id: string;
  title: string;
  message: string;
  severity: 'info' | 'warning' | 'error' | 'success';
}

@Injectable({
  providedIn: 'root',
})
export class WebSocketService {
  private socket$: WebSocketSubject<WebSocketMessage> | null = null;
  private readonly destroy$ = new Subject<void>();
  private reconnectAttempts = 0;
  private readonly maxReconnectAttempts = 5;
  private readonly reconnectInterval = 3000;

  // Connection state
  private readonly connectionStateSignal = signal<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
  readonly connectionState = this.connectionStateSignal.asReadonly();
  readonly isConnected = computed(() => this.connectionStateSignal() === 'connected');

  // Message subjects for different types
  private readonly claimUpdates$ = new Subject<ClaimUpdatePayload>();
  private readonly metrics$ = new BehaviorSubject<MetricsPayload | null>(null);
  private readonly notifications$ = new Subject<NotificationPayload>();

  /**
   * Connect to WebSocket server.
   * In development mode with mock enabled, simulates connection with fake data.
   */
  connect(): void {
    if (this.socket$ || this.connectionStateSignal() === 'connected') {
      return; // Already connected
    }

    // Use mock mode in development when backend is unavailable
    if (ENABLE_MOCK_WEBSOCKET) {
      this.connectMock();
      return;
    }

    this.connectionStateSignal.set('connecting');

    const config: WebSocketSubjectConfig<WebSocketMessage> = {
      url: environment.wsUrl,
      openObserver: {
        next: () => {
          console.log('WebSocket connected');
          this.connectionStateSignal.set('connected');
          this.reconnectAttempts = 0;
        },
      },
      closeObserver: {
        next: () => {
          console.log('WebSocket closed');
          this.connectionStateSignal.set('disconnected');
          this.socket$ = null;
          this.attemptReconnect();
        },
      },
    };

    this.socket$ = webSocket(config);

    this.socket$.pipe(
      takeUntil(this.destroy$),
      tap({
        error: (error) => {
          console.error('WebSocket error:', error);
          this.connectionStateSignal.set('error');
        },
      }),
    ).subscribe({
      next: (message) => this.handleMessage(message),
      error: (error) => console.error('WebSocket subscription error:', error),
    });

    // Start heartbeat
    this.startHeartbeat();
  }

  /**
   * Connect in mock mode for development.
   * Simulates WebSocket connection with realistic fake metrics.
   */
  private connectMock(): void {
    console.log('WebSocket: Running in mock mode (backend not required)');
    this.connectionStateSignal.set('connected');

    // Emit initial mock metrics
    this.emitMockMetrics();

    // Update mock metrics every 5 seconds
    interval(5000).pipe(
      takeUntil(this.destroy$)
    ).subscribe(() => {
      this.emitMockMetrics();
    });
  }

  /**
   * Emit realistic mock metrics for development.
   */
  private emitMockMetrics(): void {
    const mockMetrics: MetricsPayload = {
      claims_per_minute: Math.floor(Math.random() * 50) + 30,
      pending_count: Math.floor(Math.random() * 20) + 15,
      processing_count: Math.floor(Math.random() * 10) + 5,
      approved_today: Math.floor(Math.random() * 100) + 150,
      denied_today: Math.floor(Math.random() * 20) + 10,
    };
    this.metrics$.next(mockMetrics);
  }

  /**
   * Disconnect from WebSocket server.
   */
  disconnect(): void {
    this.destroy$.next();
    this.destroy$.complete();

    if (this.socket$) {
      this.socket$.complete();
      this.socket$ = null;
    }

    this.connectionStateSignal.set('disconnected');
  }

  /**
   * Get claim updates stream with throttling for performance.
   * Throttles to 2 updates per second to prevent UI overload.
   */
  getClaimUpdates(): Observable<ClaimUpdatePayload[]> {
    return this.claimUpdates$.pipe(
      bufferTime(100), // Buffer updates for 100ms
      filter((updates) => updates.length > 0),
      throttleTime(500), // Throttle to 2 batches per second
      shareReplay(1),
    );
  }

  /**
   * Get metrics stream.
   */
  getMetrics(): Observable<MetricsPayload | null> {
    return this.metrics$.asObservable();
  }

  /**
   * Get notifications stream.
   */
  getNotifications(): Observable<NotificationPayload> {
    return this.notifications$.asObservable();
  }

  /**
   * Send message to WebSocket server.
   */
  send(message: Partial<WebSocketMessage>): void {
    if (this.socket$ && this.isConnected()) {
      this.socket$.next({
        type: message.type ?? 'notification',
        payload: message.payload,
        timestamp: new Date().toISOString(),
      } as WebSocketMessage);
    }
  }

  /**
   * Handle incoming WebSocket message.
   */
  private handleMessage(message: WebSocketMessage): void {
    switch (message.type) {
      case 'claim_update':
        this.claimUpdates$.next(message.payload as ClaimUpdatePayload);
        break;

      case 'metrics':
        this.metrics$.next(message.payload as MetricsPayload);
        break;

      case 'notification':
        this.notifications$.next(message.payload as NotificationPayload);
        break;

      case 'heartbeat':
        // Respond to heartbeat
        this.send({ type: 'heartbeat', payload: { pong: true } });
        break;

      default:
        console.warn('Unknown WebSocket message type:', message.type);
    }
  }

  /**
   * Attempt to reconnect with exponential backoff.
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.connectionStateSignal.set('error');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1);

    console.log(`Attempting reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);

    timer(delay).pipe(takeUntil(this.destroy$)).subscribe(() => {
      this.connect();
    });
  }

  /**
   * Start heartbeat to keep connection alive.
   */
  private startHeartbeat(): void {
    timer(30000, 30000).pipe(
      takeUntil(this.destroy$),
      filter(() => this.isConnected()),
    ).subscribe(() => {
      this.send({ type: 'heartbeat', payload: { ping: true } });
    });
  }
}
