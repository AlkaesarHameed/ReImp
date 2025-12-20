/**
 * Step Services Component Tests.
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

import { StepServicesComponent } from './step-services.component';
import { ServicesStepData, ClaimLineItemForm } from '@claims-processing/models';

describe('StepServicesComponent', () => {
  let component: StepServicesComponent;
  let fixture: ComponentFixture<StepServicesComponent>;

  const mockLineItem: ClaimLineItemForm = {
    procedureCode: '99213',
    procedureCodeSystem: 'CPT',
    modifiers: ['25'],
    serviceDate: '2024-01-15',
    quantity: 1,
    unitPrice: 150.00,
    chargedAmount: 150.00,
    diagnosisPointers: [1],
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        StepServicesComponent,
        HttpClientTestingModule,
        NoopAnimationsModule,
        ReactiveFormsModule,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(StepServicesComponent);
    component = fixture.componentInstance;
  });

  describe('Initialization', () => {
    it('should create the component', () => {
      expect(component).toBeTruthy();
    });

    it('should initialize with empty service dates', () => {
      fixture.detectChanges();
      expect(component.form.get('serviceDateFrom')?.value).toBe('');
      expect(component.form.get('serviceDateTo')?.value).toBe('');
    });

    it('should initialize with empty diagnosis codes', () => {
      fixture.detectChanges();
      expect(component.diagnosisCodes().length).toBe(0);
    });

    it('should initialize with one empty line item', () => {
      fixture.detectChanges();
      expect(component.lineItems().length).toBe(1);
    });

    it('should load initial data if provided', () => {
      const initialData: ServicesStepData = {
        serviceDateFrom: '2024-01-15',
        serviceDateTo: '2024-01-15',
        diagnosisCodes: ['J06.9'],
        primaryDiagnosis: 'J06.9',
        lineItems: [mockLineItem],
      };
      component.initialData = initialData;
      fixture.detectChanges();

      expect(component.form.get('serviceDateFrom')?.value).toBe('2024-01-15');
      expect(component.diagnosisCodes().length).toBe(1);
      expect(component.lineItems().length).toBe(1);
    });
  });

  describe('Service Dates', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should require service date from', () => {
      component.form.get('serviceDateFrom')?.setValue('');
      component.form.get('serviceDateFrom')?.markAsTouched();

      expect(component.form.get('serviceDateFrom')?.hasError('required')).toBe(true);
    });

    it('should require service date to', () => {
      component.form.get('serviceDateTo')?.setValue('');
      component.form.get('serviceDateTo')?.markAsTouched();

      expect(component.form.get('serviceDateTo')?.hasError('required')).toBe(true);
    });

    it('should validate date range (from must be before to)', () => {
      component.form.get('serviceDateFrom')?.setValue('2024-01-20');
      component.form.get('serviceDateTo')?.setValue('2024-01-15');

      expect(component.form.hasError('dateRange')).toBe(true);
    });

    it('should not allow future dates', () => {
      const futureDate = new Date();
      futureDate.setDate(futureDate.getDate() + 30);
      component.form.get('serviceDateFrom')?.setValue(futureDate.toISOString().split('T')[0]);

      expect(component.form.get('serviceDateFrom')?.hasError('futureDate')).toBe(true);
    });
  });

  describe('Diagnosis Codes', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should search ICD-10 codes', fakeAsync(() => {
      component.onDiagnosisSearch('J06');
      tick(300);

      expect(component.diagnosisSuggestions().length).toBeGreaterThan(0);
    }));

    it('should add diagnosis code', () => {
      component.addDiagnosisCode({ code: 'J06.9', description: 'Acute URI' });

      expect(component.diagnosisCodes().length).toBe(1);
      expect(component.diagnosisCodes()[0].code).toBe('J06.9');
    });

    it('should set primary diagnosis automatically for first code', () => {
      component.addDiagnosisCode({ code: 'J06.9', description: 'Acute URI' });

      expect(component.form.get('primaryDiagnosis')?.value).toBe('J06.9');
    });

    it('should remove diagnosis code', () => {
      component.addDiagnosisCode({ code: 'J06.9', description: 'Acute URI' });
      component.addDiagnosisCode({ code: 'R05.9', description: 'Cough' });
      component.removeDiagnosisCode(0);

      expect(component.diagnosisCodes().length).toBe(1);
      expect(component.diagnosisCodes()[0].code).toBe('R05.9');
    });

    it('should allow changing primary diagnosis', () => {
      component.addDiagnosisCode({ code: 'J06.9', description: 'Acute URI' });
      component.addDiagnosisCode({ code: 'R05.9', description: 'Cough' });
      component.setPrimaryDiagnosis('R05.9');

      expect(component.form.get('primaryDiagnosis')?.value).toBe('R05.9');
    });

    it('should require at least one diagnosis', () => {
      expect(component.canProceed()).toBe(false);

      component.addDiagnosisCode({ code: 'J06.9', description: 'Acute URI' });
      component.form.get('serviceDateFrom')?.setValue('2024-01-15');
      component.form.get('serviceDateTo')?.setValue('2024-01-15');

      // Still need line items
    });
  });

  describe('Line Items', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should add new line item', () => {
      component.addLineItem();

      expect(component.lineItems().length).toBe(2);
    });

    it('should remove line item', () => {
      component.addLineItem();
      component.removeLineItem(0);

      expect(component.lineItems().length).toBe(1);
    });

    it('should not remove last line item', () => {
      expect(component.lineItems().length).toBe(1);
      component.removeLineItem(0);

      expect(component.lineItems().length).toBe(1);
    });

    it('should search CPT codes for procedure', fakeAsync(() => {
      component.onProcedureSearch(0, '9921');
      tick(300);

      expect(component.procedureSuggestions()[0]?.length).toBeGreaterThan(0);
    }));

    it('should update line item procedure code', () => {
      component.selectProcedure(0, { code: '99213', description: 'Office visit' });

      expect(component.lineItems()[0].procedureCode).toBe('99213');
    });

    it('should calculate charged amount from quantity and unit price', () => {
      component.updateLineItem(0, { quantity: 2, unitPrice: 100 });

      expect(component.lineItems()[0].chargedAmount).toBe(200);
    });

    it('should validate required line item fields', () => {
      const lineItem = component.lineItems()[0];

      expect(lineItem.procedureCode).toBe('');
      expect(component.isLineItemValid(0)).toBe(false);
    });
  });

  describe('Modifiers', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should load modifier options', fakeAsync(() => {
      tick();

      expect(component.modifierOptions().length).toBeGreaterThan(0);
    }));

    it('should add modifier to line item', () => {
      component.addModifier(0, '25');

      expect(component.lineItems()[0].modifiers).toContain('25');
    });

    it('should remove modifier from line item', () => {
      component.addModifier(0, '25');
      component.addModifier(0, '59');
      component.removeModifier(0, '25');

      expect(component.lineItems()[0].modifiers).not.toContain('25');
      expect(component.lineItems()[0].modifiers).toContain('59');
    });

    it('should limit modifiers to 4 per line', () => {
      component.addModifier(0, '25');
      component.addModifier(0, '59');
      component.addModifier(0, '76');
      component.addModifier(0, '77');
      component.addModifier(0, 'TC'); // Should not add

      expect(component.lineItems()[0].modifiers.length).toBe(4);
    });
  });

  describe('Total Calculation', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should calculate total charged', () => {
      component.updateLineItem(0, { procedureCode: '99213', quantity: 1, unitPrice: 150, chargedAmount: 150 });
      component.addLineItem();
      component.updateLineItem(1, { procedureCode: '99214', quantity: 1, unitPrice: 200, chargedAmount: 200 });

      expect(component.totalCharged()).toBe(350);
    });
  });

  describe('Navigation', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should emit step data when valid', () => {
      const emitSpy = spyOn(component.stepComplete, 'emit');

      // Fill required fields
      component.form.patchValue({
        serviceDateFrom: '2024-01-15',
        serviceDateTo: '2024-01-15',
        primaryDiagnosis: 'J06.9',
      });
      component.addDiagnosisCode({ code: 'J06.9', description: 'Acute URI' });
      component.updateLineItem(0, {
        procedureCode: '99213',
        procedureCodeSystem: 'CPT',
        serviceDate: '2024-01-15',
        quantity: 1,
        unitPrice: 150,
        chargedAmount: 150,
        diagnosisPointers: [1],
      });

      component.onNext();

      expect(emitSpy).toHaveBeenCalled();
    });

    it('should emit back event', () => {
      const backSpy = spyOn(component.stepBack, 'emit');

      component.onBack();

      expect(backSpy).toHaveBeenCalled();
    });
  });
});
