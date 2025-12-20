"""
Eligibility Verification Page.
Source: Design Document Section 4.0 - User Interface
Verified: 2025-12-18

Healthcare-grade member eligibility verification with real-time checks.
"""

import asyncio
from datetime import date, datetime
from decimal import Decimal

import streamlit as st

from src.services.adapters import (
    get_policy_adapter,
    get_member_adapter,
)

st.set_page_config(
    page_title="Eligibility Check",
    page_icon="🔍",
    layout="wide",
)

# Custom CSS
st.markdown(
    """
<style>
    /* Eligibility result cards */
    .eligibility-card {
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }

    .eligibility-eligible {
        background: linear-gradient(135deg, #D4EDDA 0%, #C3E6CB 100%);
        border-left: 4px solid #28A745;
    }

    .eligibility-ineligible {
        background: linear-gradient(135deg, #F8D7DA 0%, #F5C6CB 100%);
        border-left: 4px solid #DC3545;
    }

    .eligibility-pending {
        background: linear-gradient(135deg, #FFF3CD 0%, #FFEEBA 100%);
        border-left: 4px solid #FFC107;
    }

    /* Benefit card */
    .benefit-card {
        background: white;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
        border-left: 3px solid #0066CC;
    }

    .benefit-label {
        color: #6C757D;
        font-size: 0.85rem;
        margin-bottom: 0.25rem;
    }

    .benefit-value {
        font-weight: 600;
        color: #343A40;
        font-size: 1rem;
    }

    /* Coverage bar */
    .coverage-bar-container {
        background: #E9ECEF;
        border-radius: 10px;
        height: 12px;
        margin-top: 0.5rem;
        overflow: hidden;
    }

    .coverage-bar {
        height: 100%;
        border-radius: 10px;
        transition: width 0.3s ease;
    }

    /* Section headers */
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #343A40;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #0066CC;
    }

    /* Info badge */
    .info-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
    }

    .badge-active { background: #D4EDDA; color: #155724; }
    .badge-inactive { background: #F8D7DA; color: #721C24; }
</style>
""",
    unsafe_allow_html=True,
)

# Header
st.markdown(
    """
<div style="background: linear-gradient(135deg, #0066CC 0%, #004C99 100%); color: white; padding: 1.5rem; border-radius: 10px; margin-bottom: 1.5rem;">
    <h1 style="margin: 0; font-size: 1.75rem;">🔍 Eligibility Verification</h1>
    <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Real-time member eligibility and benefits verification</p>
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
member_adapter = get_member_adapter()

# Get data
members = run_async(member_adapter.list_all())
policies = run_async(policy_adapter.list_all())

# Search Section
st.markdown('<div class="section-header">Member Search</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    search_type = st.selectbox(
        "Search By",
        ["Member ID", "Name", "Date of Birth"],
        key="search_type",
    )

with col2:
    search_value = st.text_input(
        "Search Value",
        placeholder="Enter search value...",
        key="search_value",
    )

with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    search_clicked = st.button("Search", type="primary", use_container_width=True)

# Alternatively, select from list
st.markdown("**Or select from enrolled members:**")

member_options = {"-- Select a member --": None}
for m in members:
    member_options[f"{m.member_id} - {m.get_full_name()}"] = m

selected_member_key = st.selectbox(
    "Select Member",
    options=list(member_options.keys()),
    key="member_dropdown",
)

selected_member = member_options.get(selected_member_key)

# If search clicked, filter members
if search_clicked and search_value:
    filtered_members = []
    for m in members:
        if search_type == "Member ID" and search_value.upper() in m.member_id.upper():
            filtered_members.append(m)
        elif search_type == "Name" and search_value.lower() in m.get_full_name().lower():
            filtered_members.append(m)
        elif search_type == "Date of Birth":
            try:
                search_date = datetime.strptime(search_value, "%m/%d/%Y").date()
                if m.date_of_birth == search_date:
                    filtered_members.append(m)
            except ValueError:
                pass

    if filtered_members:
        selected_member = filtered_members[0]
        st.success(f"Found {len(filtered_members)} matching member(s)")
    else:
        st.warning("No members found matching your search criteria.")

st.divider()

# Display eligibility results if member selected
if selected_member:
    # Find associated policy
    member_policy = None
    for p in policies:
        if p.policy_id == selected_member.policy_id:
            member_policy = p
            break

    # Default policy if not found
    if not member_policy and policies:
        member_policy = policies[0]

    # Check eligibility
    is_eligible = selected_member.is_active() and (member_policy.is_active() if member_policy else False)
    service_date = date.today()

    # =============================================================================
    # ELIGIBILITY STATUS
    # =============================================================================
    st.markdown('<div class="section-header">Eligibility Status</div>', unsafe_allow_html=True)

    if is_eligible:
        st.markdown(
            f"""
        <div class="eligibility-card eligibility-eligible">
            <h2 style="color: #155724; margin: 0 0 0.5rem 0;">✓ ELIGIBLE</h2>
            <p style="color: #155724; margin: 0;">
                <strong>{selected_member.get_full_name()}</strong> is eligible for services as of
                <strong>{service_date.strftime('%m/%d/%Y')}</strong>
            </p>
            <p style="color: #155724; margin: 0.5rem 0 0 0; font-size: 0.9rem;">
                Coverage is active through {member_policy.termination_date.strftime('%m/%d/%Y') if member_policy and member_policy.termination_date else 'ongoing'}
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        reason = "Member is not active" if not selected_member.is_active() else "Policy is not active"
        st.markdown(
            f"""
        <div class="eligibility-card eligibility-ineligible">
            <h2 style="color: #721C24; margin: 0 0 0.5rem 0;">✗ NOT ELIGIBLE</h2>
            <p style="color: #721C24; margin: 0;">
                <strong>{selected_member.get_full_name()}</strong> is not eligible for services.
            </p>
            <p style="color: #721C24; margin: 0.5rem 0 0 0; font-size: 0.9rem;">
                Reason: {reason}
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # =============================================================================
    # MEMBER INFORMATION
    # =============================================================================
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-header">Member Information</div>', unsafe_allow_html=True)

        status_badge = "badge-active" if selected_member.is_active() else "badge-inactive"
        status_text = "Active" if selected_member.is_active() else "Inactive"

        st.markdown(
            f"""
        <div class="benefit-card">
            <div class="benefit-label">Member ID</div>
            <div class="benefit-value">{selected_member.member_id}</div>
        </div>
        <div class="benefit-card">
            <div class="benefit-label">Name</div>
            <div class="benefit-value">{selected_member.get_full_name()}</div>
        </div>
        <div class="benefit-card">
            <div class="benefit-label">Date of Birth</div>
            <div class="benefit-value">{selected_member.date_of_birth.strftime('%m/%d/%Y')} (Age: {selected_member.get_age()})</div>
        </div>
        <div class="benefit-card">
            <div class="benefit-label">Gender</div>
            <div class="benefit-value">{selected_member.gender.value}</div>
        </div>
        <div class="benefit-card">
            <div class="benefit-label">Status</div>
            <div class="benefit-value"><span class="info-badge {status_badge}">{status_text}</span></div>
        </div>
        <div class="benefit-card">
            <div class="benefit-label">Effective Date</div>
            <div class="benefit-value">{selected_member.effective_date.strftime('%m/%d/%Y')}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown('<div class="section-header">Coverage Information</div>', unsafe_allow_html=True)

        if member_policy:
            st.markdown(
                f"""
            <div class="benefit-card">
                <div class="benefit-label">Policy ID</div>
                <div class="benefit-value">{member_policy.policy_id}</div>
            </div>
            <div class="benefit-card">
                <div class="benefit-label">Plan Name</div>
                <div class="benefit-value">{member_policy.policy_name}</div>
            </div>
            <div class="benefit-card">
                <div class="benefit-label">Plan Type</div>
                <div class="benefit-value">{member_policy.plan_type.value.upper()}</div>
            </div>
            <div class="benefit-card">
                <div class="benefit-label">Coverage Type</div>
                <div class="benefit-value">{member_policy.coverage_type.value.replace('_', ' ').title()}</div>
            </div>
            <div class="benefit-card">
                <div class="benefit-label">Network</div>
                <div class="benefit-value">{member_policy.network_name}</div>
            </div>
            <div class="benefit-card">
                <div class="benefit-label">Payer</div>
                <div class="benefit-value">{member_policy.payer_name}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            st.info("No policy information available for this member.")

    # =============================================================================
    # BENEFITS SUMMARY
    # =============================================================================
    if member_policy:
        st.divider()
        st.markdown('<div class="section-header">Benefits Summary</div>', unsafe_allow_html=True)

        ben_col1, ben_col2 = st.columns(2)

        with ben_col1:
            # Deductible progress
            deductible_pct = float(member_policy.deductible_met / member_policy.deductible * 100) if member_policy.deductible > 0 else 0
            deductible_color = "#28A745" if deductible_pct >= 100 else "#0066CC"

            st.markdown(
                f"""
            <div class="benefit-card">
                <div class="benefit-label">Individual Deductible</div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div class="benefit-value">${member_policy.deductible_met:,.2f} / ${member_policy.deductible:,.2f}</div>
                    <span style="color: {deductible_color}; font-weight: 600;">{deductible_pct:.0f}% met</span>
                </div>
                <div class="coverage-bar-container">
                    <div class="coverage-bar" style="width: {min(deductible_pct, 100)}%; background: {deductible_color};"></div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            # Out-of-pocket progress
            oop_pct = float(member_policy.oop_met / member_policy.oop_max * 100) if member_policy.oop_max > 0 else 0
            oop_color = "#28A745" if oop_pct >= 100 else "#FFC107"

            st.markdown(
                f"""
            <div class="benefit-card">
                <div class="benefit-label">Out-of-Pocket Maximum</div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div class="benefit-value">${member_policy.oop_met:,.2f} / ${member_policy.oop_max:,.2f}</div>
                    <span style="color: {oop_color}; font-weight: 600;">{oop_pct:.0f}% met</span>
                </div>
                <div class="coverage-bar-container">
                    <div class="coverage-bar" style="width: {min(oop_pct, 100)}%; background: {oop_color};"></div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with ben_col2:
            # Coinsurance
            st.markdown(
                f"""
            <div class="benefit-card">
                <div class="benefit-label">In-Network Coinsurance</div>
                <div class="benefit-value" style="color: #28A745;">Plan pays {member_policy.in_network_coinsurance}%</div>
            </div>
            <div class="benefit-card">
                <div class="benefit-label">Out-of-Network Coinsurance</div>
                <div class="benefit-value" style="color: #FFC107;">Plan pays {member_policy.out_of_network_coinsurance}%</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # =============================================================================
        # COPAY INFORMATION
        # =============================================================================
        st.divider()
        st.markdown('<div class="section-header">Copay Schedule</div>', unsafe_allow_html=True)

        copay_col1, copay_col2, copay_col3, copay_col4 = st.columns(4)

        with copay_col1:
            st.markdown(
                f"""
            <div class="benefit-card" style="text-align: center;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">🩺</div>
                <div class="benefit-label">PCP Visit</div>
                <div class="benefit-value" style="font-size: 1.25rem; color: #0066CC;">${member_policy.pcp_copay:,.0f}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with copay_col2:
            st.markdown(
                f"""
            <div class="benefit-card" style="text-align: center;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">👨‍⚕️</div>
                <div class="benefit-label">Specialist</div>
                <div class="benefit-value" style="font-size: 1.25rem; color: #0066CC;">${member_policy.specialist_copay:,.0f}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with copay_col3:
            st.markdown(
                f"""
            <div class="benefit-card" style="text-align: center;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">🏥</div>
                <div class="benefit-label">Urgent Care</div>
                <div class="benefit-value" style="font-size: 1.25rem; color: #0066CC;">${member_policy.urgent_care_copay:,.0f}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with copay_col4:
            st.markdown(
                f"""
            <div class="benefit-card" style="text-align: center;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">🚑</div>
                <div class="benefit-label">Emergency Room</div>
                <div class="benefit-value" style="font-size: 1.25rem; color: #DC3545;">${member_policy.er_copay:,.0f}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # Pharmacy copays
        st.markdown("**Pharmacy Benefits**")
        rx_col1, rx_col2 = st.columns(2)

        with rx_col1:
            st.markdown(
                f"""
            <div class="benefit-card">
                <div class="benefit-label">Generic Medications</div>
                <div class="benefit-value">${member_policy.rx_copay_generic:,.0f} copay</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with rx_col2:
            st.markdown(
                f"""
            <div class="benefit-card">
                <div class="benefit-label">Brand Name Medications</div>
                <div class="benefit-value">${member_policy.rx_copay_brand:,.0f} copay</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # =============================================================================
        # REQUIREMENTS
        # =============================================================================
        st.divider()
        st.markdown('<div class="section-header">Coverage Requirements</div>', unsafe_allow_html=True)

        req_col1, req_col2 = st.columns(2)

        with req_col1:
            prior_auth_status = "Required" if member_policy.requires_prior_auth else "Not Required"
            prior_auth_color = "#FFC107" if member_policy.requires_prior_auth else "#28A745"
            st.markdown(
                f"""
            <div class="benefit-card">
                <div class="benefit-label">Prior Authorization</div>
                <div class="benefit-value" style="color: {prior_auth_color};">{prior_auth_status}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with req_col2:
            referral_status = "Required" if member_policy.requires_referral else "Not Required"
            referral_color = "#FFC107" if member_policy.requires_referral else "#28A745"
            st.markdown(
                f"""
            <div class="benefit-card">
                <div class="benefit-label">Specialist Referral</div>
                <div class="benefit-value" style="color: {referral_color};">{referral_status}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    # =============================================================================
    # PRINT / EXPORT ACTIONS
    # =============================================================================
    st.divider()

    action_col1, action_col2, action_col3 = st.columns(3)

    with action_col1:
        if st.button("Print Eligibility Summary", use_container_width=True):
            st.info("Print functionality would open browser print dialog.")

    with action_col2:
        if st.button("Export to PDF", use_container_width=True):
            st.info("PDF export functionality coming soon.")

    with action_col3:
        if st.button("Send to Provider", use_container_width=True):
            st.info("Provider communication functionality coming soon.")

else:
    st.info("Select a member above or search to view eligibility information.")

# Footer
st.divider()
st.caption(f"Demo Mode | Eligibility as of {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
