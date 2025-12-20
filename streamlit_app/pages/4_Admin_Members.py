"""
Member Administration Page.
Source: Design Document Section 4.4 - Demo Mode
Verified: 2025-12-18
"""

import asyncio
from datetime import date

import streamlit as st

from src.models.demo.member import DemoMember, Gender, RelationshipType
from src.services.adapters import get_member_adapter, get_policy_adapter

st.set_page_config(
    page_title="Member Admin",
    page_icon="👥",
    layout="wide",
)

st.title("👥 Member Administration")
st.markdown("Manage enrolled members for demo mode.")


def run_async(coro):
    """Run async coroutine in sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Get adapters
member_adapter = get_member_adapter()
policy_adapter = get_policy_adapter()


# Get available policies for dropdown
policies = run_async(policy_adapter.list_all())
policy_options = {p.policy_id: f"{p.policy_name} ({p.policy_id})" for p in policies}


# Sidebar - Add new member
with st.sidebar:
    st.header("Add New Member")

    with st.form("new_member_form"):
        first_name = st.text_input("First Name", value="John")
        last_name = st.text_input("Last Name", value="Doe")
        dob = st.date_input(
            "Date of Birth",
            value=date(1990, 1, 1),
            min_value=date(1900, 1, 1),
            max_value=date.today(),
        )
        gender = st.selectbox(
            "Gender",
            options=[g.value for g in Gender],
            format_func=lambda x: x.title(),
        )
        ssn_last4 = st.text_input("SSN Last 4", value="1234", max_chars=4)

        if policy_options:
            policy_id = st.selectbox(
                "Policy",
                options=list(policy_options.keys()),
                format_func=lambda x: policy_options[x],
            )
        else:
            policy_id = None
            st.warning("No policies available. Create a policy first.")

        relationship = st.selectbox(
            "Relationship",
            options=[r.value for r in RelationshipType],
            format_func=lambda x: x.title(),
        )

        address = st.text_input("Address", value="123 Main St")
        city = st.text_input("City", value="Anytown")
        state = st.text_input("State", value="TX", max_chars=2)
        zip_code = st.text_input("ZIP", value="75001", max_chars=10)
        phone = st.text_input("Phone", value="555-123-4567")
        email = st.text_input("Email", value="john.doe@example.com")

        if st.form_submit_button("Create Member"):
            if not policy_id:
                st.error("Please create a policy first")
            elif len(ssn_last4) != 4 or not ssn_last4.isdigit():
                st.error("SSN Last 4 must be exactly 4 digits")
            else:
                new_member = DemoMember(
                    first_name=first_name,
                    last_name=last_name,
                    date_of_birth=dob,
                    gender=Gender(gender),
                    ssn_last4=ssn_last4,
                    policy_id=policy_id,
                    relationship=RelationshipType(relationship),
                    address=address,
                    city=city,
                    state=state,
                    zip_code=zip_code,
                    phone=phone,
                    email=email,
                )
                created = run_async(member_adapter.create(new_member))
                st.success(f"Created member: {created.member_id}")
                st.rerun()


# Main content - List members
st.subheader("Enrolled Members")

# Filter by policy
filter_policy = st.selectbox(
    "Filter by Policy",
    options=["All"] + list(policy_options.keys()),
    format_func=lambda x: policy_options.get(x, "All Policies"),
)

members = run_async(member_adapter.list_all())

# Apply filter
if filter_policy != "All":
    members = [m for m in members if m.policy_id == filter_policy]


if not members:
    st.info("No members found. Use the sidebar to enroll a member.")
else:
    for member in members:
        status_icon = "✅" if member.is_active() else "❌"
        with st.expander(
            f"{status_icon} {member.first_name} {member.last_name} ({member.member_id})",
            expanded=False,
        ):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"**Member ID:** {member.member_id}")
                st.markdown(f"**Name:** {member.first_name} {member.last_name}")
                st.markdown(f"**DOB:** {member.date_of_birth}")
                st.markdown(f"**Age:** {member.age()}")
                st.markdown(f"**Gender:** {member.gender.value.title()}")

            with col2:
                st.markdown(f"**Policy ID:** {member.policy_id}")
                st.markdown(f"**Relationship:** {member.relationship.value.title()}")
                st.markdown(f"**SSN Last 4:** ***{member.ssn_last4}")
                st.markdown(f"**Active:** {'Yes' if member.is_active() else 'No'}")

            with col3:
                st.markdown(f"**Address:** {member.address}")
                st.markdown(f"**City:** {member.city}, {member.state} {member.zip_code}")
                st.markdown(f"**Phone:** {member.phone}")
                st.markdown(f"**Email:** {member.email}")

            st.divider()

            # Edit form
            with st.form(f"edit_{member.member_id}"):
                st.markdown("**Edit Member**")

                col1, col2 = st.columns(2)
                with col1:
                    new_first = st.text_input("First Name", value=member.first_name)
                    new_last = st.text_input("Last Name", value=member.last_name)
                    new_phone = st.text_input("Phone", value=member.phone)
                with col2:
                    new_email = st.text_input("Email", value=member.email)
                    new_address = st.text_input("Address", value=member.address)
                    new_active = st.checkbox(
                        "Active",
                        value=member.is_eligible,
                    )

                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Update"):
                        updates = {
                            "first_name": new_first,
                            "last_name": new_last,
                            "phone": new_phone,
                            "email": new_email,
                            "address": new_address,
                            "is_eligible": new_active,
                        }
                        run_async(member_adapter.update(member.member_id, updates))
                        st.success("Member updated!")
                        st.rerun()

                with col2:
                    if st.form_submit_button("Delete", type="secondary"):
                        run_async(member_adapter.delete(member.member_id))
                        st.success("Member deleted!")
                        st.rerun()


# Statistics
st.divider()
st.subheader("Member Statistics")

all_members = run_async(member_adapter.list_all())
col1, col2, col3, col4 = st.columns(4)

with col1:
    active = len([m for m in all_members if m.is_active()])
    st.metric("Active Members", active)

with col2:
    subscribers = len([m for m in all_members if m.relationship == RelationshipType.SELF])
    st.metric("Subscribers", subscribers)

with col3:
    dependents = len([m for m in all_members if m.relationship != RelationshipType.SELF])
    st.metric("Dependents", dependents)

with col4:
    if all_members:
        avg_age = sum(m.age() for m in all_members) / len(all_members)
        st.metric("Average Age", f"{avg_age:.1f}")
    else:
        st.metric("Average Age", "N/A")


# Footer
st.divider()
st.caption(f"Total Members: {len(all_members)} | Demo Mode")
