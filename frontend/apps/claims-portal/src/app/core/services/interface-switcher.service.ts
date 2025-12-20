/**
 * Interface Switcher Service.
 * Source: Design Document - DESIGN_DUAL_INTERFACE_SYSTEM.md Section 4.1
 * Verified: 2024-12-19
 *
 * Manages switching between Classic (PrimeNG) and Modern (Metronic) interfaces.
 * Both interfaces share the same data layer but provide different visual experiences.
 */
import { Injectable, inject, signal } from '@angular/core';
import { Router } from '@angular/router';

/**
 * Available interface types.
 */
export type InterfaceType = 'classic' | 'modern';

/**
 * Configuration for an interface.
 */
export interface InterfaceConfig {
  /** Interface type identifier */
  type: InterfaceType;
  /** Base route path for this interface */
  basePath: string;
  /** Display label for UI */
  label: string;
  /** Icon class (PrimeIcons for classic, Keenicons for modern) */
  icon: string;
  /** Description for accessibility */
  description: string;
}

/**
 * Service for managing interface switching between Classic and Modern views.
 *
 * @example
 * ```typescript
 * // In a component
 * readonly interfaceSwitcher = inject(InterfaceSwitcherService);
 *
 * // Switch to modern interface
 * this.interfaceSwitcher.switchTo('modern');
 *
 * // Get current interface
 * const current = this.interfaceSwitcher.currentInterface();
 * ```
 */
@Injectable({
  providedIn: 'root',
})
export class InterfaceSwitcherService {
  private readonly router = inject(Router);

  /**
   * Available interface configurations.
   */
  readonly interfaces: InterfaceConfig[] = [
    {
      type: 'classic',
      basePath: '/classic',
      label: 'Classic',
      icon: 'pi pi-th-large',
      description: 'PrimeNG-based interface with traditional layout',
    },
    {
      type: 'modern',
      basePath: '/modern',
      label: 'Modern',
      icon: 'ki-duotone ki-element-11',
      description: 'Metronic-based interface with modern dashboard',
    },
  ];

  /**
   * Current active interface type.
   * Default is 'modern' to showcase the new Metronic interface.
   */
  readonly currentInterface = signal<InterfaceType>('modern');

  /**
   * Switch to a different interface.
   *
   * @param type - The interface type to switch to
   */
  switchTo(type: InterfaceType): void {
    this.currentInterface.set(type);
    const config = this.getInterfaceConfig(type);
    if (config) {
      this.router.navigate([config.basePath, 'dashboard']);
    }
  }

  /**
   * Get the base path for the current interface.
   *
   * @returns The base route path (e.g., '/modern' or '/classic')
   */
  getCurrentBasePath(): string {
    const type = this.currentInterface();
    return this.getInterfaceConfig(type)?.basePath || '/modern';
  }

  /**
   * Get configuration for a specific interface type.
   *
   * @param type - The interface type to get config for
   * @returns The interface configuration or undefined if not found
   */
  getInterfaceConfig(type: InterfaceType): InterfaceConfig | undefined {
    return this.interfaces.find(i => i.type === type);
  }

  /**
   * Get the opposite interface type (for toggle functionality).
   *
   * @returns The other interface type
   */
  getAlternateInterface(): InterfaceType {
    return this.currentInterface() === 'modern' ? 'classic' : 'modern';
  }

  /**
   * Toggle between interfaces.
   */
  toggle(): void {
    this.switchTo(this.getAlternateInterface());
  }
}
