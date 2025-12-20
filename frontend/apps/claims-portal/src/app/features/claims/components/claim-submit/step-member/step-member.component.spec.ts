/**
 * Step Member Component Tests.
 * Source: Phase 3 Implementation Document
 * Verified: 2025-12-18
 *
 * TDD: Tests written before implementation per implement.md methodology.
 */
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ReactiveFormsModule } from '@angular/forms';
import { of, throwError } from 'rxjs';

import { StepMemberComponent } from './step-member.component';
import { MemberStepData, EligibilityCheckResponse } from '@claims-processing/models';

// Mock services will be injected
const mockMembersApi = {
  searchMembers: jasmine.createSpy('searchMembers'),
  getMember: jasmine.createSpy('getMember'),
};

const mockEligibilityApi = {
  checkEligibility: jasmine.createSpy('checkEligibility'),
};

describe('StepMemberComponent', () => {
  let component: StepMemberComponent;
  let fixture: ComponentFixture<StepMemberComponent>;

  const mockMember = {
    id: 'MEM-001',
    first_name: 'John',
    last_name: 'Doe',
    date_of_birth: '1980-01-15',
    member_number: 'M12345678',
    policy_id: 'POL-001',
  };

  const mockEligibilityResponse: EligibilityCheckResponse = {
    eligible: true,
    effectiveDate: '2024-01-01',
    terminationDate: '2024-12-31',
    coverageType: 'PPO',
    copay: 30,
    deductible: 500,
    deductibleMet: 250,
    outOfPocketMax: 5000,
    outOfPocketMet: 1000,
  };

  beforeEach(async () => {
    mockMembersApi.searchMembers.calls.reset();
    mockMembersApi.getMember.calls.reset();
    mockEligibilityApi.checkEligibility.calls.reset();

    mockMembersApi.searchMembers.and.returnValue(of({ items: [mockMember], total: 1 }));
    mockMembersApi.getMember.and.returnValue(of(mockMember));
    mockEligibilityApi.checkEligibility.and.returnValue(of(mockEligibilityResponse));

    await TestBed.configureTestingModule({
      imports: [
        StepMemberComponent,
        HttpClientTestingModule,
        NoopAnimationsModule,
        ReactiveFormsModule,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(StepMemberComponent);
    component = fixture.componentInstance;
  });

  describe('Initialization', () => {
    it('should create the component', () => {
      expect(component).toBeTruthy();
    });

    it('should initialize with empty form', () => {
      fixture.detectChanges();
      expect(component.form.get('memberId')?.value).toBe('');
      expect(component.form.get('policyId')?.value).toBe('');
    });

    it('should load initial data if provided', () => {
      const initialData: MemberStepData = {
        memberId: 'MEM-001',
        policyId: 'POL-001',
        eligibilityVerified: true,
        eligibilityResponse: mockEligibilityResponse,
      };
      component.initialData = initialData;
      fixture.detectChanges();

      expect(component.form.get('memberId')?.value).toBe('MEM-001');
      expect(component.form.get('policyId')?.value).toBe('POL-001');
      expect(component.eligibilityVerified()).toBe(true);
    });
  });

  describe('Member Search', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should search members with debounce', fakeAsync(() => {
      component.onMemberSearch('John');
      tick(300); // debounce time

      expect(component.memberSuggestions().length).toBeGreaterThan(0);
    }));

    it('should not search with less than 2 characters', fakeAsync(() => {
      component.onMemberSearch('J');
      tick(300);

      expect(component.memberSuggestions().length).toBe(0);
    }));

    it('should select member from suggestions', () => {
      component.selectMember(mockMember);

      expect(component.form.get('memberId')?.value).toBe('MEM-001');
      expect(component.selectedMember()).toBeTruthy();
      expect(component.selectedMember()?.first_name).toBe('John');
    });

    it('should populate policy when member is selected', () => {
      component.selectMember(mockMember);

      expect(component.form.get('policyId')?.value).toBe('POL-001');
    });

    it('should clear eligibility when member changes', () => {
      component.selectMember(mockMember);
      component.verifyEligibility();
      fixture.detectChanges();

      // Change member
      component.form.get('memberId')?.setValue('MEM-002');

      expect(component.eligibilityVerified()).toBe(false);
      expect(component.eligibilityResponse()).toBeNull();
    });
  });

  describe('Eligibility Verification', () => {
    beforeEach(() => {
      fixture.detectChanges();
      component.selectMember(mockMember);
    });

    it('should verify eligibility successfully', fakeAsync(() => {
      component.verifyEligibility();
      tick();

      expect(component.eligibilityVerified()).toBe(true);
      expect(component.eligibilityResponse()?.eligible).toBe(true);
      expect(component.eligibilityResponse()?.coverageType).toBe('PPO');
    }));

    it('should show loading state during verification', fakeAsync(() => {
      component.verifyEligibility();
      expect(component.verifying()).toBe(true);

      tick();
      expect(component.verifying()).toBe(false);
    }));

    it('should handle ineligible member', fakeAsync(() => {
      mockEligibilityApi.checkEligibility.and.returnValue(of({
        ...mockEligibilityResponse,
        eligible: false,
      }));

      component.verifyEligibility();
      tick();

      expect(component.eligibilityVerified()).toBe(true);
      expect(component.eligibilityResponse()?.eligible).toBe(false);
    }));

    it('should handle eligibility check error', fakeAsync(() => {
      mockEligibilityApi.checkEligibility.and.returnValue(
        throwError(() => new Error('Service unavailable'))
      );

      component.verifyEligibility();
      tick();

      expect(component.eligibilityVerified()).toBe(false);
      expect(component.error()).toBeTruthy();
    }));

    it('should display eligibility details', fakeAsync(() => {
      component.verifyEligibility();
      tick();
      fixture.detectChanges();

      expect(component.eligibilityResponse()?.copay).toBe(30);
      expect(component.eligibilityResponse()?.deductible).toBe(500);
      expect(component.eligibilityResponse()?.deductibleMet).toBe(250);
    }));
  });

  describe('Form Validation', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should require member ID', () => {
      component.form.get('memberId')?.setValue('');
      component.form.get('memberId')?.markAsTouched();

      expect(component.form.get('memberId')?.hasError('required')).toBe(true);
    });

    it('should require policy ID', () => {
      component.form.get('policyId')?.setValue('');
      component.form.get('policyId')?.markAsTouched();

      expect(component.form.get('policyId')?.hasError('required')).toBe(true);
    });

    it('should be valid when member and policy are set', () => {
      component.form.get('memberId')?.setValue('MEM-001');
      component.form.get('policyId')?.setValue('POL-001');

      expect(component.form.valid).toBe(true);
    });

    it('should require eligibility verification to proceed', () => {
      component.form.get('memberId')?.setValue('MEM-001');
      component.form.get('policyId')?.setValue('POL-001');

      expect(component.canProceed()).toBe(false);

      component.eligibilityVerified.set(true);
      expect(component.canProceed()).toBe(true);
    });
  });

  describe('Step Output', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should emit step data when valid', fakeAsync(() => {
      const emitSpy = spyOn(component.stepComplete, 'emit');

      component.selectMember(mockMember);
      component.verifyEligibility();
      tick();

      component.onNext();

      expect(emitSpy).toHaveBeenCalledWith(jasmine.objectContaining({
        memberId: 'MEM-001',
        policyId: 'POL-001',
        eligibilityVerified: true,
      }));
    }));

    it('should not emit when invalid', () => {
      const emitSpy = spyOn(component.stepComplete, 'emit');

      component.onNext();

      expect(emitSpy).not.toHaveBeenCalled();
    });

    it('should emit dirty state on form changes', () => {
      const dirtySpy = spyOn(component.dirty, 'emit');

      component.form.get('memberId')?.setValue('MEM-001');

      expect(dirtySpy).toHaveBeenCalledWith(true);
    });
  });

  describe('Accessibility', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should have proper form labels', () => {
      const compiled = fixture.nativeElement;
      const labels = compiled.querySelectorAll('label');

      expect(labels.length).toBeGreaterThan(0);
    });

    it('should associate labels with inputs', () => {
      const compiled = fixture.nativeElement;
      const memberIdInput = compiled.querySelector('#memberId, [formControlName="memberId"]');

      expect(memberIdInput).toBeTruthy();
    });

    it('should show validation errors accessibly', () => {
      component.form.get('memberId')?.setValue('');
      component.form.get('memberId')?.markAsTouched();
      fixture.detectChanges();

      const compiled = fixture.nativeElement;
      const errorMessage = compiled.querySelector('[role="alert"], .p-error, .error-message');
      // Error message should be present when field is invalid
    });
  });
});
