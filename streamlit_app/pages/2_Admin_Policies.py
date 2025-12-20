"""
Policy Administration Page.
Source: Design Document Section 4.4 - Demo Mode
Verified: 2025-12-18
"""

import asyncio
from datetime import date, timedelta
from decimal import Decimal

import streamlit as st

from src.models.demo.policy import DemoPolicy, PlanType
from src.services.adapters import get_policy_adapter

st.set_page_config(
    page_title="Policy Admin",
    page_icon="📋",
    layout="wide",
)

st.title("📋 Policy Administration")
st.markdown("Manage insurance policies for demo mode.")


def run_async(coro):
    """Run async coroutine in sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Get adapter
policy_adapter = get_policy_adapter()


# Sidebar - Add new policy
with st.sidebar:
    st.header("Add New Policy")

    with st.form("new_policy_form"):
        policy_name = st.text_input("Policy Name", value="New Policy")
        plan_type = st.selectbox(
            "Plan Type",
            options=[pt.value for pt in PlanType],
            format_func=lambda x: x.upper(),
        )
        deductible = st.number_input("Annual Deductible", min_value=0, value=1500)
        oop_max = st.number_input("Out-of-Pocket Maximum", min_value=0, value=6000)
        copay = st.number_input("Copay", min_value=0, value=25)
        coinsurance = st.slider("Coinsurance %", min_value=0, max_value=100, value=20)
        effective_date = st.date_input("Effective Date", value=date.today())
        termination_date = st.date_input(
            "Termination Date",
            value=date.today() + timedelta(days=365),
        )

        if st.form_submit_button("Create Policy"):
            new_policy = DemoPolicy(
                policy_name=policy_name,
                plan_type=PlanType(plan_type),
                deductible=Decimal(str(deductible)),
                out_of_pocket_max=Decimal(str(oop_max)),
                copay=Decimal(str(copay)),
                coinsurance_percent=coinsurance,
                effective_date=effective_date,
                termination_date=termination_date,
            )
            created = run_async(policy_adapter.create(new_policy))
            st.success(f"Created policy: {created.policy_id}")
            st.rerun()


# Main content - List policies
st.subheader("Current Policies")

policies = run_async(policy_adapter.list_all())

if not policies:
    st.info("No policies found. Use the sidebar to create one.")
else:
    for policy in policies:
        with st.expander(f"📋 {policy.policy_name} ({policy.policy_id})", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**Plan Type:** {policy.plan_type.value.upper()}")
                st.markdown(f"**Status:** {'✅ Active' if policy.is_active() else '❌ Inactive'}")
                st.markdown(f"**Effective:** {policy.effective_date}")
                st.markdown(f"**Termination:** {policy.termination_date}")

            with col2:
                st.markdown(f"**Deductible:** ${policy.deductible:,.2f}")
                st.markdown(f"**Deductible Met:** ${policy.deductible_met:,.2f}")
                st.markdown(f"**OOP Max:** ${policy.out_of_pocket_max:,.2f}")
                st.markdown(f"**Coinsurance:** {policy.coinsurance_percent}%")

            st.divider()

            # Edit form
            with st.form(f"edit_{policy.policy_id}"):
                st.markdown("**Edit Policy**")

                new_name = st.text_input("Policy Name", value=policy.policy_name)
                new_deductible_met = st.number_input(
                    "Deductible Met",
                    min_value=0.0,
                    max_value=float(policy.deductible),
                    value=float(policy.deductible_met),
                )
                new_oop_met = st.number_input(
                    "OOP Met",
                    min_value=0.0,
                    max_value=float(policy.out_of_pocket_max),
                    value=float(policy.out_of_pocket_met),
                )
                is_active = st.checkbox("Active", value=policy.is_active())

                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Update"):
                        updates = {
                            "policy_name": new_name,
                            "deductible_met": Decimal(str(new_deductible_met)),
                            "out_of_pocket_met": Decimal(str(new_oop_met)),
                        }
                        run_async(policy_adapter.update(policy.policy_id, updates))
                        st.success("Policy updated!")
                        st.rerun()

                with col2:
                    if st.form_submit_button("Delete", type="secondary"):
                        run_async(policy_adapter.delete(policy.policy_id))
                        st.success("Policy deleted!")
                        st.rerun()


# Footer
st.divider()
st.caption(f"Total Policies: {len(policies)} | Demo Mode")
