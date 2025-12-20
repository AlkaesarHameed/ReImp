"""
Claims Dashboard Page.
Source: Design Document Section 4.0 - User Interface
Verified: 2025-12-18

Healthcare-grade claims dashboard with KPIs, charts, and real-time metrics.
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
import random

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from src.services.adapters import (
    get_policy_adapter,
    get_provider_adapter,
    get_member_adapter,
    get_payment_adapter,
)

st.set_page_config(
    page_title="Claims Dashboard",
    page_icon="📊",
    layout="wide",
)

# Custom CSS for healthcare dashboard
st.markdown(
    """
<style>
    /* KPI Cards */
    .kpi-card {
        background: white;
        border-radius: 10px;
        padding: 1.25rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        border-left: 4px solid #0066CC;
        margin-bottom: 1rem;
    }

    .kpi-card.success { border-left-color: #28A745; }
    .kpi-card.warning { border-left-color: #FFC107; }
    .kpi-card.danger { border-left-color: #DC3545; }
    .kpi-card.info { border-left-color: #17A2B8; }

    .kpi-label {
        font-size: 0.85rem;
        color: #6C757D;
        margin-bottom: 0.25rem;
        font-weight: 500;
    }

    .kpi-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #0066CC;
        margin-bottom: 0.25rem;
    }

    .kpi-delta {
        font-size: 0.8rem;
        padding: 0.15rem 0.5rem;
        border-radius: 12px;
        display: inline-block;
    }

    .kpi-delta.positive { background: #D4EDDA; color: #155724; }
    .kpi-delta.negative { background: #F8D7DA; color: #721C24; }
    .kpi-delta.neutral { background: #E2E3E5; color: #383D41; }

    /* Status badges */
    .status-approved { background: #D4EDDA; color: #155724; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.85rem; }
    .status-pending { background: #FFF3CD; color: #856404; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.85rem; }
    .status-denied { background: #F8D7DA; color: #721C24; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.85rem; }
    .status-processing { background: #D1ECF1; color: #0C5460; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.85rem; }

    /* Section headers */
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #343A40;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #0066CC;
    }

    /* Table styling */
    .dataframe {
        font-size: 0.9rem;
    }

    .dataframe th {
        background-color: #0066CC !important;
        color: white !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Header
st.markdown(
    """
<div style="background: linear-gradient(135deg, #0066CC 0%, #004C99 100%); color: white; padding: 1.5rem; border-radius: 10px; margin-bottom: 1.5rem;">
    <h1 style="margin: 0; font-size: 1.75rem;">📊 Claims Dashboard</h1>
    <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Real-time analytics and claims processing metrics</p>
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


# Get adapters and data
policy_adapter = get_policy_adapter()
provider_adapter = get_provider_adapter()
member_adapter = get_member_adapter()
payment_adapter = get_payment_adapter()

policies = run_async(policy_adapter.list_all())
providers = run_async(provider_adapter.list_all())
members = run_async(member_adapter.list_all())
payments = payment_adapter.get_payment_history()

# Calculate metrics
active_policies = len([p for p in policies if p.is_active()])
total_providers = len(providers)
active_members = len([m for m in members if m.is_active()])
completed_payments = len([p for p in payments if p.get("status") == "completed"])
pending_payments = len([p for p in payments if p.get("status") == "pending"])

# Generate demo claims data for visualization
claims_data = {
    "approved": random.randint(120, 180),
    "pending": random.randint(20, 40),
    "denied": random.randint(5, 15),
    "in_review": random.randint(10, 25),
}
total_claims = sum(claims_data.values())
approval_rate = (claims_data["approved"] / total_claims * 100) if total_claims > 0 else 0

# Financial metrics
total_billed = Decimal(str(random.uniform(150000, 250000)))
total_paid = total_billed * Decimal("0.82")
total_adjusted = total_billed * Decimal("0.12")
avg_processing_time = random.uniform(1.8, 3.2)

# =============================================================================
# KPI CARDS ROW 1 - Claims Overview
# =============================================================================
st.markdown('<div class="section-header">Claims Overview</div>', unsafe_allow_html=True)

kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)

with kpi_col1:
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="kpi-label">Total Claims (MTD)</div>
        <div class="kpi-value">{total_claims:,}</div>
        <span class="kpi-delta positive">+12% vs last month</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

with kpi_col2:
    st.markdown(
        f"""
    <div class="kpi-card success">
        <div class="kpi-label">Approved</div>
        <div class="kpi-value" style="color: #28A745;">{claims_data['approved']:,}</div>
        <span class="kpi-delta positive">{approval_rate:.1f}% rate</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

with kpi_col3:
    st.markdown(
        f"""
    <div class="kpi-card warning">
        <div class="kpi-label">Pending Review</div>
        <div class="kpi-value" style="color: #FFC107;">{claims_data['pending']:,}</div>
        <span class="kpi-delta neutral">Avg 2.1 days</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

with kpi_col4:
    st.markdown(
        f"""
    <div class="kpi-card danger">
        <div class="kpi-label">Denied</div>
        <div class="kpi-value" style="color: #DC3545;">{claims_data['denied']:,}</div>
        <span class="kpi-delta negative">{(claims_data['denied']/total_claims*100):.1f}% rate</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

with kpi_col5:
    st.markdown(
        f"""
    <div class="kpi-card info">
        <div class="kpi-label">In Processing</div>
        <div class="kpi-value" style="color: #17A2B8;">{claims_data['in_review']:,}</div>
        <span class="kpi-delta neutral">Auto-adj: 89%</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

# =============================================================================
# KPI CARDS ROW 2 - Financial & Performance
# =============================================================================
st.markdown('<div class="section-header">Financial Metrics</div>', unsafe_allow_html=True)

fin_col1, fin_col2, fin_col3, fin_col4 = st.columns(4)

with fin_col1:
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="kpi-label">Total Billed (MTD)</div>
        <div class="kpi-value">${total_billed:,.0f}</div>
        <span class="kpi-delta positive">+8% vs target</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

with fin_col2:
    st.markdown(
        f"""
    <div class="kpi-card success">
        <div class="kpi-label">Total Paid</div>
        <div class="kpi-value" style="color: #28A745;">${total_paid:,.0f}</div>
        <span class="kpi-delta positive">82% of billed</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

with fin_col3:
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="kpi-label">Adjustments</div>
        <div class="kpi-value">${total_adjusted:,.0f}</div>
        <span class="kpi-delta neutral">12% of billed</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

with fin_col4:
    st.markdown(
        f"""
    <div class="kpi-card info">
        <div class="kpi-label">Avg Processing Time</div>
        <div class="kpi-value" style="color: #17A2B8;">{avg_processing_time:.1f} min</div>
        <span class="kpi-delta positive">-0.4 vs target</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

st.divider()

# =============================================================================
# CHARTS ROW
# =============================================================================
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.markdown('<div class="section-header">Claims Status Distribution</div>', unsafe_allow_html=True)

    # Pie chart for claims status
    fig_pie = go.Figure(
        data=[
            go.Pie(
                labels=["Approved", "Pending", "Denied", "In Review"],
                values=[
                    claims_data["approved"],
                    claims_data["pending"],
                    claims_data["denied"],
                    claims_data["in_review"],
                ],
                hole=0.4,
                marker_colors=["#28A745", "#FFC107", "#DC3545", "#17A2B8"],
            )
        ]
    )
    fig_pie.update_layout(
        margin=dict(t=20, b=20, l=20, r=20),
        height=300,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with chart_col2:
    st.markdown('<div class="section-header">Claims Trend (Last 7 Days)</div>', unsafe_allow_html=True)

    # Generate trend data
    dates = [(datetime.now() - timedelta(days=i)).strftime("%m/%d") for i in range(6, -1, -1)]
    approved_trend = [random.randint(15, 30) for _ in range(7)]
    denied_trend = [random.randint(1, 5) for _ in range(7)]

    fig_trend = go.Figure()
    fig_trend.add_trace(
        go.Scatter(
            x=dates,
            y=approved_trend,
            name="Approved",
            line=dict(color="#28A745", width=3),
            fill="tozeroy",
            fillcolor="rgba(40, 167, 69, 0.1)",
        )
    )
    fig_trend.add_trace(
        go.Scatter(
            x=dates,
            y=denied_trend,
            name="Denied",
            line=dict(color="#DC3545", width=3),
            fill="tozeroy",
            fillcolor="rgba(220, 53, 69, 0.1)",
        )
    )
    fig_trend.update_layout(
        margin=dict(t=20, b=20, l=20, r=20),
        height=300,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        xaxis_title="",
        yaxis_title="Claims Count",
    )
    st.plotly_chart(fig_trend, use_container_width=True)

st.divider()

# =============================================================================
# DATA TABLES
# =============================================================================
table_col1, table_col2 = st.columns(2)

with table_col1:
    st.markdown('<div class="section-header">Active Policies</div>', unsafe_allow_html=True)
    if policies:
        policy_data = []
        for p in policies[:5]:
            policy_data.append(
                {
                    "Policy ID": p.policy_id,
                    "Plan Name": p.policy_name,
                    "Type": p.plan_type.value.upper() if p.plan_type else "N/A",
                    "Deductible": f"${p.deductible:,.2f}",
                    "Status": "Active" if p.is_active() else "Inactive",
                }
            )
        df_policies = pd.DataFrame(policy_data)
        st.dataframe(df_policies, use_container_width=True, hide_index=True)
    else:
        st.info("No policies configured. Add policies from Admin > Policies.")

with table_col2:
    st.markdown('<div class="section-header">Top Providers</div>', unsafe_allow_html=True)
    if providers:
        provider_data = []
        for p in providers[:5]:
            provider_data.append(
                {
                    "Provider ID": p.provider_id,
                    "Name": p.provider_name,
                    "NPI": p.npi,
                    "Specialty": p.specialty,
                    "Network": "In-Network" if p.is_in_network() else "Out-of-Network",
                }
            )
        df_providers = pd.DataFrame(provider_data)
        st.dataframe(df_providers, use_container_width=True, hide_index=True)
    else:
        st.info("No providers registered. Add providers from Admin > Providers.")

st.divider()

# =============================================================================
# PAYMENT ACTIVITY
# =============================================================================
st.markdown('<div class="section-header">Recent Payment Activity</div>', unsafe_allow_html=True)

if payments:
    payment_data = []
    for p in payments[-10:]:
        status = p.get("status", "N/A")
        status_class = {
            "completed": "status-approved",
            "pending": "status-pending",
            "failed": "status-denied",
        }.get(status, "status-processing")

        payment_data.append(
            {
                "Payment ID": p.get("payment_id", "N/A"),
                "Event": p.get("event", "N/A"),
                "Amount": f"${p.get('amount', 0):,.2f}",
                "Status": status.title(),
                "Timestamp": p.get("timestamp", "N/A"),
            }
        )

    df_payments = pd.DataFrame(payment_data[::-1])  # Show newest first
    st.dataframe(df_payments, use_container_width=True, hide_index=True)
else:
    st.info("No payment activity yet. Process claims to generate payment records.")

# =============================================================================
# SYSTEM STATUS
# =============================================================================
st.divider()
st.markdown('<div class="section-header">System Resources</div>', unsafe_allow_html=True)

sys_col1, sys_col2, sys_col3, sys_col4 = st.columns(4)

with sys_col1:
    st.metric("Active Policies", active_policies, delta=f"{len(policies)} total")

with sys_col2:
    st.metric("Registered Providers", total_providers, delta="In-network: 85%")

with sys_col3:
    st.metric("Enrolled Members", active_members, delta=f"{len(members)} total")

with sys_col4:
    st.metric("Payments Today", completed_payments, delta=f"{pending_payments} pending")

# Footer
st.divider()
st.markdown(
    f"""
<div style="text-align: center; color: #6C757D; font-size: 0.85rem;">
    <p>Claims Dashboard | Demo Mode | Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p style="font-size: 0.75rem;">Data shown is for demonstration purposes only.</p>
</div>
""",
    unsafe_allow_html=True,
)
