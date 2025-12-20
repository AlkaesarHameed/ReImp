"""
Claims Submission Page.
Source: Design Document Section 4.0 - User Interface
Verified: 2025-12-18

Healthcare-grade claims submission workflow with validation.
"""

import asyncio
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import streamlit as st

from src.services.adapters import (
    get_policy_adapter,
    get_provider_adapter,
    get_member_adapter,
)

st.set_page_config(
    page_title="Submit Claim",
    page_icon="📝",
    layout="wide",
)

# Custom CSS
st.markdown(
    """
<style>
    /* Form styling */
    .form-section {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        border-left: 4px solid #0066CC;
    }

    .form-section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #0066CC;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #DEE2E6;
    }

    .required-field::after {
        content: " *";
        color: #DC3545;
    }

    /* Step indicator */
    .step-indicator {
        display: flex;
        justify-content: space-between;
        margin-bottom: 2rem;
    }

    .step {
        flex: 1;
        text-align: center;
        padding: 1rem;
        background: #F8F9FA;
        border-radius: 8px;
        margin: 0 0.25rem;
    }

    .step.active {
        background: #0066CC;
        color: white;
    }

    .step.completed {
        background: #28A745;
        color: white;
    }

    .step-number {
        font-size: 1.25rem;
        font-weight: bold;
    }

    .step-label {
        font-size: 0.85rem;
        margin-top: 0.25rem;
    }

    /* Validation messages */
    .validation-success {
        background: #D4EDDA;
        color: #155724;
        padding: 0.75rem 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
    }

    .validation-error {
        background: #F8D7DA;
        color: #721C24;
        padding: 0.75rem 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
    }

    /* Summary card */
    .summary-card {
        background: #F8F9FA;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }

    .summary-label {
        color: #6C757D;
        font-size: 0.85rem;
    }

    .summary-value {
        font-weight: 600;
        color: #343A40;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Header
st.markdown(
    """
<div style="background: linear-gradient(135deg, #0066CC 0%, #004C99 100%); color: white; padding: 1.5rem; border-radius: 10px; margin-bottom: 1.5rem;">
    <h1 style="margin: 0; font-size: 1.75rem;">📝 Submit New Claim</h1>
    <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Professional or Institutional Healthcare Claim Submission</p>
</div>
""",
    unsafe_allow_html=True,
)


def run_async(coro):
    """Run async coroutine in sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Get adapters
policy_adapter = get_policy_adapter()
provider_adapter = get_provider_adapter()
member_adapter = get_member_adapter()

# Get data for dropdowns
policies = run_async(policy_adapter.list_all())
providers = run_async(provider_adapter.list_all())
members = run_async(member_adapter.list_all())

# Initialize session state for form
if "claim_step" not in st.session_state:
    st.session_state.claim_step = 1
if "claim_data" not in st.session_state:
    st.session_state.claim_data = {}

# Step indicator
st.markdown(
    f"""
<div class="step-indicator">
    <div class="step {'active' if st.session_state.claim_step == 1 else 'completed' if st.session_state.claim_step > 1 else ''}">
        <div class="step-number">1</div>
        <div class="step-label">Member Info</div>
    </div>
    <div class="step {'active' if st.session_state.claim_step == 2 else 'completed' if st.session_state.claim_step > 2 else ''}">
        <div class="step-number">2</div>
        <div class="step-label">Provider Info</div>
    </div>
    <div class="step {'active' if st.session_state.claim_step == 3 else 'completed' if st.session_state.claim_step > 3 else ''}">
        <div class="step-number">3</div>
        <div class="step-label">Service Details</div>
    </div>
    <div class="step {'active' if st.session_state.claim_step == 4 else ''}">
        <div class="step-number">4</div>
        <div class="step-label">Review & Submit</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# STEP 1: Member Information
# =============================================================================
if st.session_state.claim_step == 1:
    st.markdown('<div class="form-section-header">Step 1: Member Information</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        # Member selection
        member_options = {f"{m.member_id} - {m.get_full_name()}": m for m in members}
        selected_member = st.selectbox(
            "Select Member *",
            options=list(member_options.keys()),
            key="member_select",
        )

        if selected_member:
            member = member_options[selected_member]
            st.session_state.claim_data["member"] = member

            # Display member info
            st.markdown(
                f"""
            <div class="summary-card">
                <div class="summary-label">Member ID</div>
                <div class="summary-value">{member.member_id}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Date of Birth</div>
                <div class="summary-value">{member.date_of_birth.strftime('%m/%d/%Y')} (Age: {member.get_age()})</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Policy ID</div>
                <div class="summary-value">{member.policy_id}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    with col2:
        # Policy selection
        policy_options = {f"{p.policy_id} - {p.policy_name}": p for p in policies if p.is_active()}
        selected_policy = st.selectbox(
            "Select Policy *",
            options=list(policy_options.keys()),
            key="policy_select",
        )

        if selected_policy:
            policy = policy_options[selected_policy]
            st.session_state.claim_data["policy"] = policy

            # Display policy info
            st.markdown(
                f"""
            <div class="summary-card">
                <div class="summary-label">Plan Type</div>
                <div class="summary-value">{policy.plan_type.value.upper()}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Deductible</div>
                <div class="summary-value">${policy.deductible:,.2f} (Met: ${policy.deductible_met:,.2f})</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Out-of-Pocket Max</div>
                <div class="summary-value">${policy.oop_max:,.2f} (Met: ${policy.oop_met:,.2f})</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    # Patient relationship
    relationship = st.selectbox(
        "Patient Relationship to Subscriber *",
        ["Self", "Spouse", "Child", "Other Dependent"],
        key="relationship",
    )
    st.session_state.claim_data["relationship"] = relationship

    st.divider()

    col_prev, col_next = st.columns([1, 1])
    with col_next:
        if st.button("Next: Provider Info", type="primary", use_container_width=True):
            if selected_member and selected_policy:
                st.session_state.claim_step = 2
                st.rerun()
            else:
                st.error("Please select both a member and a policy.")

# =============================================================================
# STEP 2: Provider Information
# =============================================================================
elif st.session_state.claim_step == 2:
    st.markdown('<div class="form-section-header">Step 2: Provider Information</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Rendering Provider")

        # Provider selection
        provider_options = {f"{p.provider_id} - {p.provider_name}": p for p in providers}
        selected_provider = st.selectbox(
            "Select Rendering Provider *",
            options=list(provider_options.keys()),
            key="provider_select",
        )

        if selected_provider:
            provider = provider_options[selected_provider]
            st.session_state.claim_data["provider"] = provider

            # Display provider info
            network_status = "In-Network" if provider.is_in_network() else "Out-of-Network"
            network_color = "#28A745" if provider.is_in_network() else "#DC3545"

            st.markdown(
                f"""
            <div class="summary-card">
                <div class="summary-label">NPI</div>
                <div class="summary-value">{provider.npi}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Specialty</div>
                <div class="summary-value">{provider.specialty}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Network Status</div>
                <div class="summary-value" style="color: {network_color};">{network_status}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    with col2:
        st.subheader("Facility Information")

        facility_type = st.selectbox(
            "Place of Service *",
            [
                "11 - Office",
                "21 - Inpatient Hospital",
                "22 - Outpatient Hospital",
                "23 - Emergency Room",
                "31 - Skilled Nursing Facility",
                "81 - Independent Laboratory",
            ],
            key="facility_type",
        )
        st.session_state.claim_data["place_of_service"] = facility_type

        # Referring provider (optional)
        st.markdown("**Referring Provider (if applicable)**")
        referring_npi = st.text_input("Referring Provider NPI", key="referring_npi")
        st.session_state.claim_data["referring_npi"] = referring_npi

    st.divider()

    col_prev, col_next = st.columns([1, 1])
    with col_prev:
        if st.button("Back: Member Info", use_container_width=True):
            st.session_state.claim_step = 1
            st.rerun()
    with col_next:
        if st.button("Next: Service Details", type="primary", use_container_width=True):
            if selected_provider:
                st.session_state.claim_step = 3
                st.rerun()
            else:
                st.error("Please select a provider.")

# =============================================================================
# STEP 3: Service Details
# =============================================================================
elif st.session_state.claim_step == 3:
    st.markdown('<div class="form-section-header">Step 3: Service Details</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Diagnosis Codes")

        primary_dx = st.text_input(
            "Primary Diagnosis (ICD-10) *",
            placeholder="e.g., J06.9",
            key="primary_dx",
        )
        st.session_state.claim_data["primary_dx"] = primary_dx

        secondary_dx = st.text_input(
            "Secondary Diagnosis (ICD-10)",
            placeholder="e.g., R05.9",
            key="secondary_dx",
        )
        st.session_state.claim_data["secondary_dx"] = secondary_dx

        st.subheader("Service Dates")

        service_date_from = st.date_input(
            "Service Date From *",
            value=date.today(),
            key="service_date_from",
        )
        st.session_state.claim_data["service_date_from"] = service_date_from

        service_date_to = st.date_input(
            "Service Date To *",
            value=date.today(),
            key="service_date_to",
        )
        st.session_state.claim_data["service_date_to"] = service_date_to

    with col2:
        st.subheader("Procedure Information")

        procedure_code = st.text_input(
            "CPT/HCPCS Code *",
            placeholder="e.g., 99213",
            key="procedure_code",
        )
        st.session_state.claim_data["procedure_code"] = procedure_code

        modifier = st.text_input(
            "Modifier (if applicable)",
            placeholder="e.g., 25",
            key="modifier",
        )
        st.session_state.claim_data["modifier"] = modifier

        units = st.number_input(
            "Units *",
            min_value=1,
            max_value=999,
            value=1,
            key="units",
        )
        st.session_state.claim_data["units"] = units

        st.subheader("Charges")

        billed_amount = st.number_input(
            "Billed Amount ($) *",
            min_value=0.01,
            max_value=999999.99,
            value=150.00,
            step=0.01,
            key="billed_amount",
        )
        st.session_state.claim_data["billed_amount"] = Decimal(str(billed_amount))

    st.divider()

    # Additional notes
    notes = st.text_area(
        "Additional Notes / Clinical Information",
        placeholder="Enter any additional clinical notes or special circumstances...",
        key="notes",
    )
    st.session_state.claim_data["notes"] = notes

    st.divider()

    col_prev, col_next = st.columns([1, 1])
    with col_prev:
        if st.button("Back: Provider Info", use_container_width=True):
            st.session_state.claim_step = 2
            st.rerun()
    with col_next:
        if st.button("Next: Review & Submit", type="primary", use_container_width=True):
            if primary_dx and procedure_code:
                st.session_state.claim_step = 4
                st.rerun()
            else:
                st.error("Please enter required diagnosis and procedure codes.")

# =============================================================================
# STEP 4: Review & Submit
# =============================================================================
elif st.session_state.claim_step == 4:
    st.markdown('<div class="form-section-header">Step 4: Review & Submit</div>', unsafe_allow_html=True)

    # Generate claim ID
    claim_id = f"CLM-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"

    # Display claim summary
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Member & Policy")

        member = st.session_state.claim_data.get("member")
        policy = st.session_state.claim_data.get("policy")

        if member:
            st.markdown(
                f"""
            <div class="summary-card">
                <div class="summary-label">Member</div>
                <div class="summary-value">{member.get_full_name()} ({member.member_id})</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        if policy:
            st.markdown(
                f"""
            <div class="summary-card">
                <div class="summary-label">Policy</div>
                <div class="summary-value">{policy.policy_name} ({policy.plan_type.value.upper()})</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        st.markdown("### Provider")

        provider = st.session_state.claim_data.get("provider")
        if provider:
            st.markdown(
                f"""
            <div class="summary-card">
                <div class="summary-label">Rendering Provider</div>
                <div class="summary-value">{provider.provider_name} (NPI: {provider.npi})</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Place of Service</div>
                <div class="summary-value">{st.session_state.claim_data.get('place_of_service', 'N/A')}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    with col2:
        st.markdown("### Service Details")

        st.markdown(
            f"""
        <div class="summary-card">
            <div class="summary-label">Primary Diagnosis</div>
            <div class="summary-value">{st.session_state.claim_data.get('primary_dx', 'N/A')}</div>
        </div>
        <div class="summary-card">
            <div class="summary-label">Procedure Code</div>
            <div class="summary-value">{st.session_state.claim_data.get('procedure_code', 'N/A')}</div>
        </div>
        <div class="summary-card">
            <div class="summary-label">Service Date</div>
            <div class="summary-value">{st.session_state.claim_data.get('service_date_from', 'N/A')}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown("### Financial Summary")

        billed = st.session_state.claim_data.get("billed_amount", Decimal("0.00"))
        st.markdown(
            f"""
        <div class="summary-card">
            <div class="summary-label">Billed Amount</div>
            <div class="summary-value" style="font-size: 1.5rem; color: #0066CC;">${billed:,.2f}</div>
        </div>
        <div class="summary-card">
            <div class="summary-label">Claim ID (Pending)</div>
            <div class="summary-value">{claim_id}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.divider()

    # Submission confirmation
    st.markdown(
        """
    <div style="background: #FFF3CD; border: 1px solid #FFEEBA; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
        <strong>Attestation:</strong> By submitting this claim, I certify that the services described were medically
        necessary and that all information provided is accurate and complete to the best of my knowledge.
    </div>
    """,
        unsafe_allow_html=True,
    )

    confirm = st.checkbox("I confirm that all information is accurate and I am authorized to submit this claim.")

    st.divider()

    col_prev, col_submit = st.columns([1, 1])
    with col_prev:
        if st.button("Back: Service Details", use_container_width=True):
            st.session_state.claim_step = 3
            st.rerun()
    with col_submit:
        if st.button("Submit Claim", type="primary", use_container_width=True, disabled=not confirm):
            # Simulate claim submission
            with st.spinner("Submitting claim..."):
                import time

                time.sleep(1.5)  # Simulate processing

            st.success(f"Claim {claim_id} submitted successfully!")

            st.markdown(
                f"""
            <div style="background: #D4EDDA; padding: 1.5rem; border-radius: 10px; margin-top: 1rem;">
                <h3 style="color: #155724; margin: 0;">Claim Submitted</h3>
                <p style="color: #155724; margin: 0.5rem 0;">Claim ID: <strong>{claim_id}</strong></p>
                <p style="color: #155724; margin: 0;">Status: <strong>Pending Review</strong></p>
                <p style="color: #155724; margin: 0.5rem 0 0 0; font-size: 0.9rem;">
                    Estimated processing time: 2-3 business days
                </p>
            </div>
            """,
                unsafe_allow_html=True,
            )

            # Reset form
            if st.button("Submit Another Claim"):
                st.session_state.claim_step = 1
                st.session_state.claim_data = {}
                st.rerun()

# Footer
st.divider()
st.caption(f"Demo Mode | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
