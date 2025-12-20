/**
 * Interface Switcher Service Tests.
 * Source: Design Document - DESIGN_DUAL_INTERFACE_SYSTEM.md
 * Verified: 2024-12-19
 */
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { InterfaceSwitcherService, InterfaceType } from './interface-switcher.service';

describe('InterfaceSwitcherService', () => {
  let service: InterfaceSwitcherService;
  let routerSpy: jest.Mocked<Router>;

  beforeEach(() => {
    routerSpy = {
      navigate: jest.fn().mockResolvedValue(true),
    } as unknown as jest.Mocked<Router>;

    TestBed.configureTestingModule({
      providers: [
        InterfaceSwitcherService,
        { provide: Router, useValue: routerSpy },
      ],
    });

    service = TestBed.inject(InterfaceSwitcherService);
  });

  describe('initialization', () => {
    it('should be created', () => {
      expect(service).toBeTruthy();
    });

    it('should have default interface as modern', () => {
      expect(service.currentInterface()).toBe('modern');
    });

    it('should have two interface configurations', () => {
      expect(service.interfaces.length).toBe(2);
    });

    it('should have classic interface config', () => {
      const classic = service.interfaces.find(i => i.type === 'classic');
      expect(classic).toBeDefined();
      expect(classic?.basePath).toBe('/classic');
      expect(classic?.label).toBe('Classic');
    });

    it('should have modern interface config', () => {
      const modern = service.interfaces.find(i => i.type === 'modern');
      expect(modern).toBeDefined();
      expect(modern?.basePath).toBe('/modern');
      expect(modern?.label).toBe('Modern');
    });
  });

  describe('switchTo', () => {
    it('should switch to classic interface', () => {
      service.switchTo('classic');
      expect(service.currentInterface()).toBe('classic');
    });

    it('should switch to modern interface', () => {
      service.switchTo('classic'); // First switch to classic
      service.switchTo('modern'); // Then back to modern
      expect(service.currentInterface()).toBe('modern');
    });

    it('should navigate to dashboard when switching to classic', () => {
      service.switchTo('classic');
      expect(routerSpy.navigate).toHaveBeenCalledWith(['/classic', 'dashboard']);
    });

    it('should navigate to dashboard when switching to modern', () => {
      service.switchTo('modern');
      expect(routerSpy.navigate).toHaveBeenCalledWith(['/modern', 'dashboard']);
    });
  });

  describe('getCurrentBasePath', () => {
    it('should return /modern when current interface is modern', () => {
      service.switchTo('modern');
      expect(service.getCurrentBasePath()).toBe('/modern');
    });

    it('should return /classic when current interface is classic', () => {
      service.switchTo('classic');
      expect(service.getCurrentBasePath()).toBe('/classic');
    });
  });

  describe('getInterfaceConfig', () => {
    it('should return config for classic', () => {
      const config = service.getInterfaceConfig('classic');
      expect(config?.type).toBe('classic');
    });

    it('should return config for modern', () => {
      const config = service.getInterfaceConfig('modern');
      expect(config?.type).toBe('modern');
    });

    it('should return undefined for invalid type', () => {
      const config = service.getInterfaceConfig('invalid' as InterfaceType);
      expect(config).toBeUndefined();
    });
  });
});
