/**
 * Theme Service.
 * Source: Design Document - DESIGN_DUAL_INTERFACE_SYSTEM.md
 * Verified: 2024-12-19
 *
 * Manages dark/light theme switching for the application.
 * Persists user preference in localStorage and respects system preference.
 */
import { Injectable, signal, effect, PLATFORM_ID, inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

export type ThemeMode = 'light' | 'dark' | 'system';

@Injectable({
  providedIn: 'root',
})
export class ThemeService {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly STORAGE_KEY = 'claims-portal-theme';

  /**
   * Current theme mode setting (light, dark, or system).
   */
  readonly themeMode = signal<ThemeMode>(this.getStoredTheme());

  /**
   * Actual resolved theme (light or dark) based on mode and system preference.
   */
  readonly resolvedTheme = signal<'light' | 'dark'>('light');

  /**
   * Whether dark mode is currently active.
   */
  readonly isDarkMode = signal(false);

  constructor() {
    if (isPlatformBrowser(this.platformId)) {
      // Initialize theme on startup
      this.applyTheme(this.themeMode());

      // Listen for system theme changes
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      mediaQuery.addEventListener('change', () => {
        if (this.themeMode() === 'system') {
          this.applyTheme('system');
        }
      });

      // React to theme mode changes
      effect(() => {
        const mode = this.themeMode();
        this.applyTheme(mode);
        this.saveTheme(mode);
      });
    }
  }

  /**
   * Set the theme mode.
   */
  setTheme(mode: ThemeMode): void {
    this.themeMode.set(mode);
  }

  /**
   * Toggle between light and dark modes.
   */
  toggle(): void {
    const current = this.resolvedTheme();
    this.setTheme(current === 'light' ? 'dark' : 'light');
  }

  /**
   * Apply the theme to the document.
   */
  private applyTheme(mode: ThemeMode): void {
    if (!isPlatformBrowser(this.platformId)) return;

    let resolved: 'light' | 'dark';

    if (mode === 'system') {
      resolved = window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light';
    } else {
      resolved = mode;
    }

    this.resolvedTheme.set(resolved);
    this.isDarkMode.set(resolved === 'dark');

    // Apply to document
    const html = document.documentElement;
    html.setAttribute('data-bs-theme', resolved);
    html.setAttribute('data-theme', resolved);

    // Also set a class for additional styling hooks
    if (resolved === 'dark') {
      html.classList.add('dark-mode');
      html.classList.remove('light-mode');
      document.body.classList.add('dark-mode');
      document.body.classList.remove('light-mode');
    } else {
      html.classList.add('light-mode');
      html.classList.remove('dark-mode');
      document.body.classList.add('light-mode');
      document.body.classList.remove('dark-mode');
    }
  }

  /**
   * Get stored theme preference from localStorage.
   */
  private getStoredTheme(): ThemeMode {
    if (!isPlatformBrowser(this.platformId)) return 'light';

    const stored = localStorage.getItem(this.STORAGE_KEY);
    if (stored === 'light' || stored === 'dark' || stored === 'system') {
      return stored;
    }
    return 'light'; // Default to light
  }

  /**
   * Save theme preference to localStorage.
   */
  private saveTheme(mode: ThemeMode): void {
    if (!isPlatformBrowser(this.platformId)) return;
    localStorage.setItem(this.STORAGE_KEY, mode);
  }
}
