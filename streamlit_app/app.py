"""
Medical Claims Processing System - Main Application.
Source: Design Document Section 4.0 - User Interface
Verified: 2025-12-18

Healthcare-grade claims processing dashboard with HIPAA-compliant UI patterns.
"""

import streamlit as st
from datetime import datetime

# Page configuration - Healthcare theme
st.set_page_config(
    page_title="Claims Processing System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://support.claimsprocessor.com",
        "Report a bug": "https://support.claimsprocessor.com/issues",
        "About": "Medical Claims Processing System v1.0.0",
    },
)

# Custom CSS for healthcare professional theme
st.markdown(
    """
<style>
    /* Healthcare color palette */
    :root {
        --primary-blue: #0066CC;
        --secondary-blue: #004C99;
        --success-green: #28A745;
        --warning-yellow: #FFC107;
        --danger-red: #DC3545;
        --info-cyan: #17A2B8;
        --light-gray: #F8F9FA;
        --dark-gray: #343A40;
    }

    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #0066CC 0%, #004C99 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    .main-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 600;
    }

    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }

    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
    }

    .status-approved { background: #D4EDDA; color: #155724; }
    .status-pending { background: #FFF3CD; color: #856404; }
    .status-denied { background: #F8D7DA; color: #721C24; }
    .status-processing { background: #D1ECF1; color: #0C5460; }

    /* Card styling */
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
        border-left: 4px solid #0066CC;
        margin-bottom: 1rem;
    }

    .metric-card h3 {
        margin: 0;
        color: #666;
        font-size: 0.9rem;
        font-weight: 500;
    }

    .metric-card .value {
        font-size: 2rem;
        font-weight: 700;
        color: #0066CC;
        margin: 0.5rem 0;
    }

    /* Quick action buttons */
    .quick-action {
        background: linear-gradient(135deg, #F8F9FA 0%, #E9ECEF 100%);
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s ease;
        cursor: pointer;
        border: 1px solid #DEE2E6;
    }

    .quick-action:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    .quick-action .icon {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }

    /* Sidebar styling */
    .css-1d391kg {
        background-color: #F8F9FA;
    }

    /* Footer */
    .footer {
        text-align: center;
        padding: 1rem;
        color: #6C757D;
        font-size: 0.85rem;
        border-top: 1px solid #DEE2E6;
        margin-top: 2rem;
    }

    /* HIPAA notice */
    .hipaa-notice {
        background: #FFF3CD;
        border: 1px solid #FFEEBA;
        border-radius: 5px;
        padding: 0.75rem 1rem;
        font-size: 0.85rem;
        color: #856404;
        margin-bottom: 1rem;
    }

    /* Table enhancements */
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

# Main header
st.markdown(
    """
<div class="main-header">
    <h1>🏥 Medical Claims Processing System</h1>
    <p>Enterprise Healthcare Claims Management Platform</p>
</div>
""",
    unsafe_allow_html=True,
)

# HIPAA Notice
st.markdown(
    """
<div class="hipaa-notice">
    🔒 <strong>HIPAA Compliance Notice:</strong> This system contains Protected Health Information (PHI).
    Access is logged and monitored. Unauthorized access is prohibited.
</div>
""",
    unsafe_allow_html=True,
)

# Sidebar - User Info & Navigation
with st.sidebar:
    st.markdown("### 👤 User Session")

    # Demo user info
    user_role = st.selectbox(
        "Role",
        ["Claims Processor", "Claims Supervisor", "Administrator", "Auditor"],
        key="user_role",
    )

    st.markdown(f"**Session Started:** {datetime.now().strftime('%H:%M:%S')}")
    st.markdown("**Status:** 🟢 Active")

    st.divider()

    st.markdown("### 📋 Quick Navigation")
    st.markdown("""
    - [Claims Dashboard](Claims_Dashboard)
    - [Admin: Policies](Admin_Policies)
    - [Admin: Providers](Admin_Providers)
    - [Admin: Members](Admin_Members)
    - [Demo Data](Demo_Data)
    """)

    st.divider()

    st.markdown("### 🔔 Notifications")
    st.info("3 claims pending review")
    st.warning("1 prior auth expiring today")

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 🚀 Quick Actions")

    action_col1, action_col2, action_col3, action_col4 = st.columns(4)

    with action_col1:
        st.markdown(
            """
        <div class="quick-action">
            <div class="icon">📝</div>
            <strong>Submit Claim</strong>
            <p style="font-size: 0.8rem; color: #666; margin: 0.5rem 0 0 0;">
                New professional or institutional claim
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button("Submit New Claim", key="btn_submit", use_container_width=True):
            st.switch_page("pages/6_Submit_Claim.py")

    with action_col2:
        st.markdown(
            """
        <div class="quick-action">
            <div class="icon">🔍</div>
            <strong>Check Eligibility</strong>
            <p style="font-size: 0.8rem; color: #666; margin: 0.5rem 0 0 0;">
                Verify member coverage
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button("Verify Eligibility", key="btn_elig", use_container_width=True):
            st.switch_page("pages/7_Eligibility_Check.py")

    with action_col3:
        st.markdown(
            """
        <div class="quick-action">
            <div class="icon">📊</div>
            <strong>View Dashboard</strong>
            <p style="font-size: 0.8rem; color: #666; margin: 0.5rem 0 0 0;">
                Analytics & reports
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button("Open Dashboard", key="btn_dash", use_container_width=True):
            st.switch_page("pages/1_Claims_Dashboard.py")

    with action_col4:
        st.markdown(
            """
        <div class="quick-action">
            <div class="icon">📋</div>
            <strong>Prior Auth</strong>
            <p style="font-size: 0.8rem; color: #666; margin: 0.5rem 0 0 0;">
                Authorization requests
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button("Prior Auth", key="btn_auth", use_container_width=True):
            st.info("Prior Authorization module coming soon")

with col2:
    st.markdown("### 📈 Today's Summary")

    # Summary metrics
    st.metric("Claims Processed", "47", delta="12 vs yesterday")
    st.metric("Pending Review", "23", delta="-5")
    st.metric("Auto-Adjudicated", "89%", delta="3%")
    st.metric("Avg Processing Time", "2.3 min", delta="-0.4 min")

st.divider()

# System Status Panel
st.markdown("### 🖥️ System Status")

status_col1, status_col2, status_col3, status_col4 = st.columns(4)

with status_col1:
    st.markdown(
        """
    <div style="background: #D4EDDA; padding: 1rem; border-radius: 8px; text-align: center;">
        <strong style="color: #155724;">🟢 API Server</strong>
        <p style="margin: 0.5rem 0 0 0; color: #155724; font-size: 0.85rem;">Operational</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

with status_col2:
    st.markdown(
        """
    <div style="background: #D4EDDA; padding: 1rem; border-radius: 8px; text-align: center;">
        <strong style="color: #155724;">🟢 Database</strong>
        <p style="margin: 0.5rem 0 0 0; color: #155724; font-size: 0.85rem;">Connected</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

with status_col3:
    st.markdown(
        """
    <div style="background: #D4EDDA; padding: 1rem; border-radius: 8px; text-align: center;">
        <strong style="color: #155724;">🟢 Cache</strong>
        <p style="margin: 0.5rem 0 0 0; color: #155724; font-size: 0.85rem;">Active</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

with status_col4:
    st.markdown(
        """
    <div style="background: #D4EDDA; padding: 1rem; border-radius: 8px; text-align: center;">
        <strong style="color: #155724;">🟢 Clearinghouse</strong>
        <p style="margin: 0.5rem 0 0 0; color: #155724; font-size: 0.85rem;">Connected</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

st.divider()

# Recent Activity Feed
st.markdown("### 📜 Recent Activity")

activities = [
    {"time": "2 min ago", "action": "Claim CLM-2024-001234 approved", "user": "System", "type": "success"},
    {"time": "5 min ago", "action": "Eligibility verified for MEM-ABC123", "user": "jsmith", "type": "info"},
    {"time": "12 min ago", "action": "Prior auth PA-789 approved", "user": "supervisor1", "type": "success"},
    {"time": "15 min ago", "action": "Claim CLM-2024-001233 pending review", "user": "System", "type": "warning"},
    {"time": "20 min ago", "action": "New provider PRV-XYZ enrolled", "user": "admin", "type": "info"},
]

for activity in activities:
    icon = "✅" if activity["type"] == "success" else "⚠️" if activity["type"] == "warning" else "ℹ️"
    st.markdown(
        f"""
    <div style="background: #F8F9FA; padding: 0.75rem 1rem; border-radius: 5px; margin-bottom: 0.5rem;
                border-left: 3px solid {'#28A745' if activity['type'] == 'success' else '#FFC107' if activity['type'] == 'warning' else '#17A2B8'};">
        <span style="color: #6C757D; font-size: 0.8rem;">{activity['time']}</span>
        <strong style="margin-left: 1rem;">{icon} {activity['action']}</strong>
        <span style="float: right; color: #6C757D; font-size: 0.85rem;">by {activity['user']}</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

# Footer
st.markdown(
    """
<div class="footer">
    <p>Medical Claims Processing System v1.0.0 |
    <a href="#">Documentation</a> |
    <a href="#">Support</a> |
    <a href="#">HIPAA Policies</a></p>
    <p style="font-size: 0.75rem;">© 2024 Healthcare Solutions Inc. All rights reserved.</p>
</div>
""",
    unsafe_allow_html=True,
)
