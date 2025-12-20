/**
 * Step Provider Component Tests.
 * Source: Phase 3 Implementation Document
 * Verified: 2025-12-18
 *
 * TDD: Tests written before implementation per implement.md methodology.
 */
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ReactiveFormsModule } from '@angular/forms';
import { of } from 'rxjs';

import { StepProviderComponent } from './step-provider.component';
import { ProviderStepData, PlaceOfServiceCode } from '@claims-processing/models';

describe('StepProviderComponent', () => {
  let component: StepProviderComponent;
  let fixture: ComponentFixture<StepProviderComponent>;

  const mockProvider = {
    id: 'PRV-001',
    npi: '1234567890',
    name: 'Dr. Jane Smith',
    specialty: 'Internal Medicine',
    address: '123 Medical Way',
    city: 'Boston',
    state: 'MA',
    zip: '02101',
  };

  const mockPOSCodes: PlaceOfServiceCode[] = [
    { code: '11', name: 'Office', description: 'Location where health care services are provided' },
    { code: '21', name: 'Inpatient Hospital', description: 'Hospital inpatient setting' },
    { code: '22', name: 'Outpatient Hospital', description: 'Hospital outpatient setting' },
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        StepProviderComponent,
        HttpClientTestingModule,
        NoopAnimationsModule,
        ReactiveFormsModule,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(StepProviderComponent);
    component = fixture.componentInstance;
  });

  describe('Initialization', () => {
    it('should create the component', () => {
      expect(component).toBeTruthy();
    });

    it('should initialize with empty form', () => {
      fixture.detectChanges();
      expect(component.form.get('providerId')?.value).toBe('');
      expect(component.form.get('providerNPI')?.value).toBe('');
      expect(component.form.get('placeOfService')?.value).toBe('');
    });

    it('should load initial data if provided', () => {
      const initialData: ProviderStepData = {
        providerId: 'PRV-001',
        providerNPI: '1234567890',
        placeOfService: '11',
        priorAuthNumber: 'PA123456',
      };
      component.initialData = initialData;
      fixture.detectChanges();

      expect(component.form.get('providerId')?.value).toBe('PRV-001');
      expect(component.form.get('providerNPI')?.value).toBe('1234567890');
      expect(component.form.get('placeOfService')?.value).toBe('11');
      expect(component.form.get('priorAuthNumber')?.value).toBe('PA123456');
    });

    it('should load POS codes on init', fakeAsync(() => {
      fixture.detectChanges();
      tick();

      expect(component.posCodeOptions().length).toBeGreaterThan(0);
    }));
  });

  describe('Provider Search', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should search providers with debounce', fakeAsync(() => {
      component.onProviderSearch('Smith');
      tick(300);

      expect(component.providerSuggestions().length).toBeGreaterThan(0);
    }));

    it('should search by NPI', fakeAsync(() => {
      component.onProviderSearch('1234567890');
      tick(300);

      expect(component.providerSuggestions().length).toBeGreaterThan(0);
    }));

    it('should select provider from suggestions', () => {
      component.selectProvider(mockProvider);

      expect(component.form.get('providerId')?.value).toBe('PRV-001');
      expect(component.form.get('providerNPI')?.value).toBe('1234567890');
      expect(component.selectedProvider()?.name).toBe('Dr. Jane Smith');
    });
  });

  describe('NPI Validation', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should validate NPI format (10 digits)', () => {
      component.form.get('providerNPI')?.setValue('123');
      component.form.get('providerNPI')?.markAsTouched();

      expect(component.form.get('providerNPI')?.hasError('pattern')).toBe(true);
    });

    it('should accept valid NPI', () => {
      component.form.get('providerNPI')?.setValue('1234567890');
      component.form.get('providerNPI')?.markAsTouched();

      expect(component.form.get('providerNPI')?.hasError('pattern')).toBe(false);
    });

    it('should verify NPI with registry', fakeAsync(() => {
      component.form.get('providerNPI')?.setValue('1234567890');
      component.verifyNPI();
      tick();

      expect(component.npiVerified()).toBe(true);
    }));
  });

  describe('Place of Service', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should require place of service', () => {
      component.form.get('placeOfService')?.setValue('');
      component.form.get('placeOfService')?.markAsTouched();

      expect(component.form.get('placeOfService')?.hasError('required')).toBe(true);
    });

    it('should display POS options', fakeAsync(() => {
      tick();
      fixture.detectChanges();

      expect(component.posCodeOptions().length).toBeGreaterThan(0);
    }));
  });

  describe('Prior Authorization', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should allow optional prior auth number', () => {
      component.form.get('providerId')?.setValue('PRV-001');
      component.form.get('providerNPI')?.setValue('1234567890');
      component.form.get('placeOfService')?.setValue('11');
      // priorAuthNumber is optional

      expect(component.form.valid).toBe(true);
    });

    it('should validate prior auth format if provided', () => {
      component.form.get('priorAuthNumber')?.setValue('PA123456');

      expect(component.form.get('priorAuthNumber')?.valid).toBe(true);
    });
  });

  describe('Form Validation', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should require provider ID', () => {
      component.form.get('providerId')?.setValue('');
      component.form.get('providerId')?.markAsTouched();

      expect(component.form.get('providerId')?.hasError('required')).toBe(true);
    });

    it('should require NPI', () => {
      component.form.get('providerNPI')?.setValue('');
      component.form.get('providerNPI')?.markAsTouched();

      expect(component.form.get('providerNPI')?.hasError('required')).toBe(true);
    });

    it('should be valid when all required fields are set', () => {
      component.form.get('providerId')?.setValue('PRV-001');
      component.form.get('providerNPI')?.setValue('1234567890');
      component.form.get('placeOfService')?.setValue('11');

      expect(component.form.valid).toBe(true);
    });
  });

  describe('Navigation', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should emit step data when valid and next clicked', () => {
      const emitSpy = spyOn(component.stepComplete, 'emit');

      component.form.patchValue({
        providerId: 'PRV-001',
        providerNPI: '1234567890',
        placeOfService: '11',
      });

      component.onNext();

      expect(emitSpy).toHaveBeenCalledWith(jasmine.objectContaining({
        providerId: 'PRV-001',
        providerNPI: '1234567890',
        placeOfService: '11',
      }));
    });

    it('should emit back event when back clicked', () => {
      const backSpy = spyOn(component.stepBack, 'emit');

      component.onBack();

      expect(backSpy).toHaveBeenCalled();
    });

    it('should not emit when invalid', () => {
      const emitSpy = spyOn(component.stepComplete, 'emit');

      component.onNext();

      expect(emitSpy).not.toHaveBeenCalled();
    });
  });
});
