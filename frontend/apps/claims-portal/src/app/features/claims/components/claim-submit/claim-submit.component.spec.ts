/**
 * Claim Submit Wizard Component Tests.
 * Source: Phase 3 Implementation Document
 * Verified: 2025-12-18
 *
 * Unit tests for the multi-step claim submission wizard.
 */
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router, ActivatedRoute } from '@angular/router';
import { ConfirmationService, MessageService } from 'primeng/api';

import { ClaimSubmitComponent } from './claim-submit.component';
import {
  MemberStepData,
  ProviderStepData,
  ServicesStepData,
  createInitialClaimFormState,
  createEmptyLineItem,
} from '@claims-processing/models';

describe('ClaimSubmitComponent', () => {
  let component: ClaimSubmitComponent;
  let fixture: ComponentFixture<ClaimSubmitComponent>;
  let routerSpy: jest.Mocked<Router>;
  let messageServiceSpy: jest.Mocked<MessageService>;
  let confirmationServiceSpy: jest.Mocked<ConfirmationService>;

  const mockMemberStepData: MemberStepData = {
    memberId: 'MEM-001',
    policyId: 'POL-001',
    eligibilityVerified: true,
    eligibilityResponse: {
      eligible: true,
      effectiveDate: '2024-01-01',
      terminationDate: '2024-12-31',
      coverageType: 'PPO',
      copay: 30,
      deductible: 500,
      deductibleMet: 250,
      outOfPocketMax: 5000,
      outOfPocketMet: 1000,
    },
  };

  const mockProviderStepData: ProviderStepData = {
    providerId: 'PRV-001',
    providerNPI: '1234567890',
    placeOfService: '11',
    priorAuthNumber: 'AUTH-001',
  };

  const mockServicesStepData: ServicesStepData = {
    serviceDateFrom: '2024-06-01',
    serviceDateTo: '2024-06-01',
    diagnosisCodes: ['J06.9', 'R05.9'],
    primaryDiagnosis: 'J06.9',
    lineItems: [
      {
        procedureCode: '99213',
        procedureCodeSystem: 'CPT',
        modifiers: [],
        serviceDate: '2024-06-01',
        quantity: 1,
        unitPrice: 150,
        chargedAmount: 150,
        diagnosisPointers: [1],
      },
    ],
  };

  beforeEach(async () => {
    routerSpy = {
      navigate: jest.fn().mockReturnValue(Promise.resolve(true)),
    } as unknown as jest.Mocked<Router>;

    messageServiceSpy = {
      add: jest.fn(),
    } as unknown as jest.Mocked<MessageService>;

    confirmationServiceSpy = {
      confirm: jest.fn(),
    } as unknown as jest.Mocked<ConfirmationService>;

    await TestBed.configureTestingModule({
      imports: [
        ClaimSubmitComponent,
        HttpClientTestingModule,
        NoopAnimationsModule,
      ],
      providers: [
        { provide: Router, useValue: routerSpy },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { params: {} },
          },
        },
        { provide: MessageService, useValue: messageServiceSpy },
        { provide: ConfirmationService, useValue: confirmationServiceSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ClaimSubmitComponent);
    component = fixture.componentInstance;
  });

  describe('Initialization', () => {
    it('should create the component', () => {
      expect(component).toBeTruthy();
    });

    it('should initialize with step 0', () => {
      fixture.detectChanges();
      expect(component.currentStep()).toBe(0);
    });

    it('should initialize with empty form state', () => {
      fixture.detectChanges();
      const state = component.formState();
      expect(state.member.memberId).toBe('');
      expect(state.provider.providerId).toBe('');
      expect(state.services.diagnosisCodes).toEqual([]);
    });

    it('should have 4 steps defined', () => {
      expect(component.steps.length).toBe(4);
      expect(component.steps[0].label).toBe('Member');
      expect(component.steps[1].label).toBe('Provider');
      expect(component.steps[2].label).toBe('Services');
      expect(component.steps[3].label).toBe('Review');
    });

    it('should not be dirty initially', () => {
      fixture.detectChanges();
      expect(component.isDirty()).toBe(false);
    });
  });

  describe('Step Navigation', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should advance to step 1 after member completion', () => {
      component.onMemberComplete(mockMemberStepData);
      expect(component.currentStep()).toBe(1);
    });

    it('should advance to step 2 after provider completion', () => {
      component.onMemberComplete(mockMemberStepData);
      component.onProviderComplete(mockProviderStepData);
      expect(component.currentStep()).toBe(2);
    });

    it('should advance to step 3 after services completion', () => {
      component.onMemberComplete(mockMemberStepData);
      component.onProviderComplete(mockProviderStepData);
      component.onServicesComplete(mockServicesStepData);
      expect(component.currentStep()).toBe(3);
    });

    it('should go back to previous step', () => {
      component.onMemberComplete(mockMemberStepData);
      expect(component.currentStep()).toBe(1);

      component.goBack();
      expect(component.currentStep()).toBe(0);
    });

    it('should not go back from step 0', () => {
      expect(component.currentStep()).toBe(0);
      component.goBack();
      expect(component.currentStep()).toBe(0);
    });

    it('should allow navigation to completed steps', () => {
      component.onMemberComplete(mockMemberStepData);
      component.onProviderComplete(mockProviderStepData);

      // Should be at step 2 now
      expect(component.currentStep()).toBe(2);

      // Should be able to go back to step 0
      component.goToStep(0);
      expect(component.currentStep()).toBe(0);
    });
  });

  describe('Form State Management', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should update member data in form state', () => {
      component.onMemberComplete(mockMemberStepData);

      const state = component.formState();
      expect(state.member.memberId).toBe('MEM-001');
      expect(state.member.policyId).toBe('POL-001');
      expect(state.member.eligibilityVerified).toBe(true);
    });

    it('should update provider data in form state', () => {
      component.onProviderComplete(mockProviderStepData);

      const state = component.formState();
      expect(state.provider.providerId).toBe('PRV-001');
      expect(state.provider.providerNPI).toBe('1234567890');
      expect(state.provider.placeOfService).toBe('11');
    });

    it('should update services data in form state', () => {
      component.onServicesComplete(mockServicesStepData);

      const state = component.formState();
      expect(state.services.diagnosisCodes).toContain('J06.9');
      expect(state.services.primaryDiagnosis).toBe('J06.9');
      expect(state.services.lineItems.length).toBe(1);
    });

    it('should preserve existing data when updating', () => {
      component.onMemberComplete(mockMemberStepData);
      component.onProviderComplete(mockProviderStepData);

      const state = component.formState();
      expect(state.member.memberId).toBe('MEM-001');
      expect(state.provider.providerId).toBe('PRV-001');
    });
  });

  describe('Dirty State', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should track dirty state changes', () => {
      expect(component.isDirty()).toBe(false);

      component.onDirtyChange(true);
      expect(component.isDirty()).toBe(true);

      component.onDirtyChange(false);
      expect(component.isDirty()).toBe(false);
    });

    it('should show confirmation when canceling with unsaved changes', () => {
      component.onDirtyChange(true);
      component.onCancel();

      expect(confirmationServiceSpy.confirm).toHaveBeenCalled();
    });

    it('should navigate directly when canceling without changes', () => {
      component.onDirtyChange(false);
      component.onCancel();

      expect(routerSpy.navigate).toHaveBeenCalledWith(['/claims']);
    });
  });

  describe('Submit Success', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should show success message on submit', fakeAsync(() => {
      component.onSubmitSuccess('CLM-001');

      expect(messageServiceSpy.add).toHaveBeenCalledWith(
        expect.objectContaining({
          severity: 'success',
          summary: 'Claim Submitted',
        })
      );
    }));

    it('should navigate to claim detail after submit', fakeAsync(() => {
      component.onSubmitSuccess('CLM-001');
      tick(1500);

      expect(routerSpy.navigate).toHaveBeenCalledWith(['/claims', 'CLM-001']);
    }));
  });

  describe('Draft Saved', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should show info message on draft save', () => {
      component.onDraftSaved('draft-123');

      expect(messageServiceSpy.add).toHaveBeenCalledWith(
        expect.objectContaining({
          severity: 'info',
          summary: 'Draft Saved',
        })
      );
    });

    it('should clear dirty state on draft save', () => {
      component.onDirtyChange(true);
      expect(component.isDirty()).toBe(true);

      component.onDraftSaved('draft-123');
      expect(component.isDirty()).toBe(false);
    });

    it('should update form state with draft ID', () => {
      component.onDraftSaved('draft-123');

      const state = component.formState();
      expect(state.draftId).toBe('draft-123');
    });
  });

  describe('Step Click Handling', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should allow clicking on current step', () => {
      component.onStepClick(0);
      expect(component.currentStep()).toBe(0);
    });

    it('should allow clicking on completed steps', () => {
      component.onMemberComplete(mockMemberStepData);
      component.onProviderComplete(mockProviderStepData);

      // Currently at step 2
      component.onStepClick(0);
      expect(component.currentStep()).toBe(0);
    });

    it('should not allow skipping to uncompleted steps', () => {
      // At step 0, should not be able to jump to step 3
      component.onStepClick(3);
      expect(component.currentStep()).toBe(0);
    });
  });

  describe('Completed Steps Tracking', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    it('should track step 0 as completed after member step', () => {
      component.onMemberComplete(mockMemberStepData);
      expect(component.completedSteps().has(0)).toBe(true);
    });

    it('should track step 1 as completed after provider step', () => {
      component.onMemberComplete(mockMemberStepData);
      component.onProviderComplete(mockProviderStepData);
      expect(component.completedSteps().has(1)).toBe(true);
    });

    it('should track step 2 as completed after services step', () => {
      component.onMemberComplete(mockMemberStepData);
      component.onProviderComplete(mockProviderStepData);
      component.onServicesComplete(mockServicesStepData);
      expect(component.completedSteps().has(2)).toBe(true);
    });

    it('should preserve completed steps when going back', () => {
      component.onMemberComplete(mockMemberStepData);
      component.onProviderComplete(mockProviderStepData);

      component.goBack();
      expect(component.completedSteps().has(0)).toBe(true);
      expect(component.completedSteps().has(1)).toBe(true);
    });
  });
});

describe('createInitialClaimFormState', () => {
  it('should create a valid initial state', () => {
    const state = createInitialClaimFormState();

    expect(state).toBeTruthy();
    expect(state.currentStep).toBe(0);
    expect(state.isDirty).toBe(false);
    expect(state.isValid).toBe(false);
  });

  it('should initialize member step data', () => {
    const state = createInitialClaimFormState();

    expect(state.member.memberId).toBe('');
    expect(state.member.policyId).toBe('');
    expect(state.member.eligibilityVerified).toBe(false);
  });

  it('should initialize provider step data', () => {
    const state = createInitialClaimFormState();

    expect(state.provider.providerId).toBe('');
    expect(state.provider.providerNPI).toBe('');
    expect(state.provider.placeOfService).toBe('');
  });

  it('should initialize services step data', () => {
    const state = createInitialClaimFormState();

    expect(state.services.serviceDateFrom).toBe('');
    expect(state.services.serviceDateTo).toBe('');
    expect(state.services.diagnosisCodes).toEqual([]);
    expect(state.services.primaryDiagnosis).toBe('');
    expect(state.services.lineItems).toEqual([]);
  });
});

describe('createEmptyLineItem', () => {
  it('should create a valid empty line item', () => {
    const lineItem = createEmptyLineItem();

    expect(lineItem).toBeTruthy();
    expect(lineItem.procedureCode).toBe('');
    expect(lineItem.procedureCodeSystem).toBe('CPT');
    expect(lineItem.modifiers).toEqual([]);
    expect(lineItem.serviceDate).toBeNull();
    expect(lineItem.quantity).toBe(1);
    expect(lineItem.unitPrice).toBe(0);
    expect(lineItem.chargedAmount).toBe(0);
    expect(lineItem.diagnosisPointers).toEqual([1]);
  });
});
