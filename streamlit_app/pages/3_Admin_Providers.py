"""
Provider Administration Page.
Source: Design Document Section 4.4 - Demo Mode
Verified: 2025-12-18
"""

import asyncio

import streamlit as st

from src.models.demo.provider import DemoProvider, ProviderType, NetworkStatus
from src.services.adapters import get_provider_adapter

st.set_page_config(
    page_title="Provider Admin",
    page_icon="🏥",
    layout="wide",
)

st.title("🏥 Provider Administration")
st.markdown("Manage healthcare providers for demo mode.")


def run_async(coro):
    """Run async coroutine in sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Get adapter
provider_adapter = get_provider_adapter()


# Sidebar - Add new provider
with st.sidebar:
    st.header("Add New Provider")

    with st.form("new_provider_form"):
        provider_name = st.text_input("Provider Name", value="New Provider")
        npi = st.text_input("NPI (10 digits)", value="1234567890", max_chars=10)
        tax_id = st.text_input("Tax ID", value="12-3456789")
        provider_type = st.selectbox(
            "Provider Type",
            options=[pt.value for pt in ProviderType],
            format_func=lambda x: x.replace("_", " ").title(),
        )
        specialty = st.text_input("Specialty", value="General Practice")
        network_status = st.selectbox(
            "Network Status",
            options=[ns.value for ns in NetworkStatus],
            format_func=lambda x: x.replace("_", " ").title(),
        )
        address = st.text_area("Address", value="123 Medical Way")
        city = st.text_input("City", value="Healthcare City")
        state = st.text_input("State", value="TX", max_chars=2)
        zip_code = st.text_input("ZIP Code", value="75001", max_chars=10)
        phone = st.text_input("Phone", value="555-123-4567")

        if st.form_submit_button("Create Provider"):
            if len(npi) != 10 or not npi.isdigit():
                st.error("NPI must be exactly 10 digits")
            else:
                new_provider = DemoProvider(
                    provider_name=provider_name,
                    npi=npi,
                    tax_id=tax_id,
                    provider_type=ProviderType(provider_type),
                    specialty=specialty,
                    network_status=NetworkStatus(network_status),
                    address=address,
                    city=city,
                    state=state,
                    zip_code=zip_code,
                    phone=phone,
                )
                created = run_async(provider_adapter.create(new_provider))
                st.success(f"Created provider: {created.provider_id}")
                st.rerun()


# Main content - List providers
st.subheader("Registered Providers")

# Filter options
col1, col2 = st.columns(2)
with col1:
    filter_type = st.selectbox(
        "Filter by Type",
        options=["All"] + [pt.value for pt in ProviderType],
    )
with col2:
    filter_network = st.selectbox(
        "Filter by Network",
        options=["All"] + [ns.value for ns in NetworkStatus],
    )

providers = run_async(provider_adapter.list_all())

# Apply filters
if filter_type != "All":
    providers = [p for p in providers if p.provider_type.value == filter_type]
if filter_network != "All":
    providers = [p for p in providers if p.network_status.value == filter_network]


if not providers:
    st.info("No providers found. Use the sidebar to create one.")
else:
    for provider in providers:
        status_icon = "✅" if provider.is_in_network() else "⚠️"
        with st.expander(
            f"{status_icon} {provider.provider_name} (NPI: {provider.npi})",
            expanded=False,
        ):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"**Provider ID:** {provider.provider_id}")
                st.markdown(f"**NPI:** {provider.npi}")
                st.markdown(f"**Tax ID:** {provider.tax_id}")
                st.markdown(f"**Type:** {provider.provider_type.value.replace('_', ' ').title()}")

            with col2:
                st.markdown(f"**Specialty:** {provider.specialty}")
                st.markdown(f"**Network:** {provider.network_status.value.replace('_', ' ').title()}")
                st.markdown(f"**Active:** {'Yes' if provider.is_active else 'No'}")

            with col3:
                st.markdown(f"**Address:** {provider.address}")
                st.markdown(f"**City:** {provider.city}, {provider.state} {provider.zip_code}")
                st.markdown(f"**Phone:** {provider.phone}")

            st.divider()

            # Edit form
            with st.form(f"edit_{provider.provider_id}"):
                st.markdown("**Edit Provider**")

                col1, col2 = st.columns(2)
                with col1:
                    new_name = st.text_input("Name", value=provider.provider_name)
                    new_specialty = st.text_input("Specialty", value=provider.specialty)
                with col2:
                    new_network = st.selectbox(
                        "Network Status",
                        options=[ns.value for ns in NetworkStatus],
                        index=[ns.value for ns in NetworkStatus].index(provider.network_status.value),
                    )
                    new_active = st.checkbox("Active", value=provider.is_active)

                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Update"):
                        updates = {
                            "provider_name": new_name,
                            "specialty": new_specialty,
                            "network_status": NetworkStatus(new_network),
                            "is_active": new_active,
                        }
                        run_async(provider_adapter.update(provider.provider_id, updates))
                        st.success("Provider updated!")
                        st.rerun()

                with col2:
                    if st.form_submit_button("Delete", type="secondary"):
                        run_async(provider_adapter.delete(provider.provider_id))
                        st.success("Provider deleted!")
                        st.rerun()


# Statistics
st.divider()
st.subheader("Provider Statistics")

all_providers = run_async(provider_adapter.list_all())
col1, col2, col3 = st.columns(3)

with col1:
    in_network = len([p for p in all_providers if p.is_in_network()])
    st.metric("In-Network Providers", in_network)

with col2:
    active = len([p for p in all_providers if p.is_active])
    st.metric("Active Providers", active)

with col3:
    by_type = {}
    for p in all_providers:
        t = p.provider_type.value
        by_type[t] = by_type.get(t, 0) + 1
    most_common = max(by_type, key=by_type.get) if by_type else "N/A"
    st.metric("Most Common Type", most_common.replace("_", " ").title())


# Footer
st.divider()
st.caption(f"Total Providers: {len(all_providers)} | Demo Mode")
