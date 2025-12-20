/**
 * Logger Service.
 * Source: Design Document Section 5.0
 *
 * Centralized logging service with level-based filtering.
 * Supports structured logging for production monitoring.
 */
import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  level: LogLevel;
  message: string;
  timestamp: string;
  context?: string;
  data?: unknown;
}

@Injectable({
  providedIn: 'root',
})
export class LoggerService {
  private readonly levels: Record<LogLevel, number> = {
    debug: 0,
    info: 1,
    warn: 2,
    error: 3,
  };

  private readonly currentLevel: number;

  constructor() {
    this.currentLevel = this.levels[environment.logLevel as LogLevel] ?? 0;
  }

  /**
   * Log debug message.
   */
  debug(message: string, context?: string, data?: unknown): void {
    this.log('debug', message, context, data);
  }

  /**
   * Log info message.
   */
  info(message: string, context?: string, data?: unknown): void {
    this.log('info', message, context, data);
  }

  /**
   * Log warning message.
   */
  warn(message: string, context?: string, data?: unknown): void {
    this.log('warn', message, context, data);
  }

  /**
   * Log error message.
   */
  error(message: string, context?: string, data?: unknown): void {
    this.log('error', message, context, data);
  }

  /**
   * Internal log method.
   */
  private log(level: LogLevel, message: string, context?: string, data?: unknown): void {
    if (this.levels[level] < this.currentLevel) {
      return;
    }

    const entry: LogEntry = {
      level,
      message,
      timestamp: new Date().toISOString(),
      context,
      data,
    };

    if (environment.production) {
      // In production, output structured JSON
      console[level](JSON.stringify(entry));
    } else {
      // In development, use formatted output
      const prefix = context ? `[${context}]` : '';
      const method = level === 'debug' ? 'log' : level;

      if (data) {
        console[method](`${prefix} ${message}`, data);
      } else {
        console[method](`${prefix} ${message}`);
      }
    }
  }
}
