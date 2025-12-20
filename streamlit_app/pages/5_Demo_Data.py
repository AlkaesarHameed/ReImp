"""
Demo Data Generator Page.
Source: Design Document Section 4.4 - Demo Mode
Verified: 2025-12-18
"""

import asyncio
import random
from datetime import date, timedelta
from decimal import Decimal

import streamlit as st

from src.models.demo.policy import DemoPolicy, PlanType
from src.models.demo.provider import DemoProvider, ProviderType, NetworkStatus
from src.models.demo.member import DemoMember, Gender, RelationshipType
from src.services.adapters import (
    get_policy_adapter,
    get_provider_adapter,
    get_member_adapter,
    get_payment_adapter,
)

st.set_page_config(
    page_title="Demo Data Generator",
    page_icon="🎲",
    layout="wide",
)

st.title("🎲 Demo Data Generator")
st.markdown("Generate sample data for testing and demonstrations.")


def run_async(coro):
    """Run async coroutine in sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Sample data pools
FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Ahmed", "Fatima", "Mohammed", "Aisha", "Omar", "Layla", "Hassan", "Noor",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Anderson", "Taylor", "Thomas", "Jackson", "White", "Harris",
    "Al-Rashid", "Al-Farsi", "Al-Hassan", "Al-Mahmoud", "Khan", "Rahman", "Patel", "Singh",
]

SPECIALTIES = [
    "Family Medicine", "Internal Medicine", "Pediatrics", "Cardiology",
    "Orthopedics", "Dermatology", "Neurology", "Oncology",
    "Psychiatry", "Emergency Medicine", "Radiology", "Surgery",
]

CITIES = [
    ("Austin", "TX", "78701"), ("Houston", "TX", "77001"), ("Dallas", "TX", "75201"),
    ("San Antonio", "TX", "78201"), ("Phoenix", "AZ", "85001"), ("Denver", "CO", "80201"),
    ("Chicago", "IL", "60601"), ("Miami", "FL", "33101"), ("Seattle", "WA", "98101"),
]

POLICY_NAMES = [
    "Gold Plus PPO", "Silver Standard HMO", "Bronze Basic", "Platinum Premier",
    "Family Advantage", "Individual Select", "Senior Care Plus", "Youth Essential",
]


# Get adapters
policy_adapter = get_policy_adapter()
provider_adapter = get_provider_adapter()
member_adapter = get_member_adapter()
payment_adapter = get_payment_adapter()


# Current counts
policies = run_async(policy_adapter.list_all())
providers = run_async(provider_adapter.list_all())
members = run_async(member_adapter.list_all())
payments = payment_adapter.get_payment_history()


st.subheader("Current Data Summary")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Policies", len(policies))
with col2:
    st.metric("Providers", len(providers))
with col3:
    st.metric("Members", len(members))
with col4:
    st.metric("Payments", len(payments))


st.divider()
st.subheader("Generate Sample Data")


def generate_npi():
    """Generate a random 10-digit NPI."""
    return "".join([str(random.randint(0, 9)) for _ in range(10)])


def generate_tax_id():
    """Generate a random tax ID."""
    return f"{random.randint(10, 99)}-{random.randint(1000000, 9999999)}"


def generate_phone():
    """Generate a random phone number."""
    return f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}"


def generate_ssn_last4():
    """Generate random SSN last 4."""
    return f"{random.randint(1000, 9999)}"


# Generation forms
col1, col2 = st.columns(2)

with col1:
    st.markdown("### Generate Policies")
    num_policies = st.number_input("Number of Policies", min_value=1, max_value=20, value=3)

    if st.button("Generate Policies"):
        with st.spinner("Generating policies..."):
            for i in range(num_policies):
                plan_type = random.choice(list(PlanType))
                deductible = Decimal(str(random.choice([500, 1000, 1500, 2000, 2500, 3000])))

                policy = DemoPolicy(
                    policy_name=f"{random.choice(POLICY_NAMES)} {random.randint(100, 999)}",
                    plan_type=plan_type,
                    deductible=deductible,
                    out_of_pocket_max=deductible * Decimal("4"),
                    copay=Decimal(str(random.choice([15, 20, 25, 30, 40, 50]))),
                    coinsurance_percent=random.choice([10, 15, 20, 25, 30]),
                    effective_date=date.today() - timedelta(days=random.randint(30, 365)),
                    termination_date=date.today() + timedelta(days=random.randint(180, 730)),
                )
                run_async(policy_adapter.create(policy))

            st.success(f"Generated {num_policies} policies!")
            st.rerun()


with col2:
    st.markdown("### Generate Providers")
    num_providers = st.number_input("Number of Providers", min_value=1, max_value=50, value=5)

    if st.button("Generate Providers"):
        with st.spinner("Generating providers..."):
            for i in range(num_providers):
                city, state, zip_code = random.choice(CITIES)
                provider_type = random.choice(list(ProviderType))
                network_status = random.choice([
                    NetworkStatus.IN_NETWORK,
                    NetworkStatus.IN_NETWORK,
                    NetworkStatus.PREFERRED,
                    NetworkStatus.OUT_OF_NETWORK,
                ])

                provider = DemoProvider(
                    provider_name=f"Dr. {random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                    npi=generate_npi(),
                    tax_id=generate_tax_id(),
                    provider_type=provider_type,
                    specialty=random.choice(SPECIALTIES),
                    network_status=network_status,
                    address=f"{random.randint(100, 9999)} Medical Dr",
                    city=city,
                    state=state,
                    zip_code=zip_code,
                    phone=generate_phone(),
                )
                run_async(provider_adapter.create(provider))

            st.success(f"Generated {num_providers} providers!")
            st.rerun()


st.divider()

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Generate Members")

    # Refresh policies list
    current_policies = run_async(policy_adapter.list_all())

    if not current_policies:
        st.warning("Create policies first before generating members.")
    else:
        num_members = st.number_input("Number of Members", min_value=1, max_value=100, value=10)

        if st.button("Generate Members"):
            with st.spinner("Generating members..."):
                for i in range(num_members):
                    city, state, zip_code = random.choice(CITIES)
                    gender = random.choice(list(Gender))
                    relationship = random.choice([
                        RelationshipType.SELF,
                        RelationshipType.SELF,
                        RelationshipType.SPOUSE,
                        RelationshipType.CHILD,
                        RelationshipType.DEPENDENT,
                    ])

                    # Random DOB (ages 1-80)
                    age_days = random.randint(365, 80 * 365)
                    dob = date.today() - timedelta(days=age_days)

                    member = DemoMember(
                        first_name=random.choice(FIRST_NAMES),
                        last_name=random.choice(LAST_NAMES),
                        date_of_birth=dob,
                        gender=gender,
                        ssn_last4=generate_ssn_last4(),
                        policy_id=random.choice(current_policies).policy_id,
                        relationship=relationship,
                        address=f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Elm', 'Park'])} St",
                        city=city,
                        state=state,
                        zip_code=zip_code,
                        phone=generate_phone(),
                        email=f"{random.choice(FIRST_NAMES).lower()}.{random.choice(LAST_NAMES).lower()}@example.com",
                    )
                    run_async(member_adapter.create(member))

                st.success(f"Generated {num_members} members!")
                st.rerun()


with col2:
    st.markdown("### Generate Payments")
    num_payments = st.number_input("Number of Payments", min_value=1, max_value=50, value=5)

    if st.button("Generate Payments"):
        with st.spinner("Generating payments..."):
            current_providers = run_async(provider_adapter.list_all())

            if not current_providers:
                st.warning("Create providers first!")
            else:
                for i in range(num_payments):
                    provider = random.choice(current_providers)
                    amount = Decimal(str(random.randint(50, 5000)))

                    payment = run_async(payment_adapter.create_payment(
                        claim_id=f"CLM-{random.randint(10000, 99999)}",
                        payee_id=provider.provider_id,
                        amount=amount,
                    ))

                    # Process some payments
                    if random.random() > 0.3:
                        run_async(payment_adapter.process_payment(payment.payment_id))

                st.success(f"Generated {num_payments} payments!")
                st.rerun()


st.divider()
st.subheader("Data Management")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Reset Data")
    st.warning("This will delete ALL demo data!")

    confirm = st.checkbox("I understand this will delete all data")

    if st.button("Reset All Data", disabled=not confirm, type="primary"):
        # Clear all adapters
        policy_adapter.clear_all()
        provider_adapter.clear_all()
        member_adapter.clear_all()
        payment_adapter.clear_all()
        st.success("All demo data cleared!")
        st.rerun()


with col2:
    st.markdown("### Quick Setup")
    st.info("Generate a complete demo dataset with one click.")

    if st.button("Generate Full Demo Dataset"):
        with st.spinner("Generating complete demo dataset..."):
            # Generate 5 policies
            for i in range(5):
                plan_type = list(PlanType)[i % len(PlanType)]
                deductible = Decimal(str([500, 1000, 1500, 2000, 2500][i]))

                policy = DemoPolicy(
                    policy_name=POLICY_NAMES[i % len(POLICY_NAMES)],
                    plan_type=plan_type,
                    deductible=deductible,
                    out_of_pocket_max=deductible * Decimal("4"),
                    copay=Decimal(str([20, 25, 30, 35, 40][i])),
                    coinsurance_percent=[10, 15, 20, 20, 25][i],
                    effective_date=date.today() - timedelta(days=180),
                    termination_date=date.today() + timedelta(days=365),
                )
                run_async(policy_adapter.create(policy))

            # Generate 10 providers
            for i in range(10):
                city, state, zip_code = CITIES[i % len(CITIES)]
                provider = DemoProvider(
                    provider_name=f"Dr. {FIRST_NAMES[i]} {LAST_NAMES[i]}",
                    npi=generate_npi(),
                    tax_id=generate_tax_id(),
                    provider_type=list(ProviderType)[i % len(ProviderType)],
                    specialty=SPECIALTIES[i % len(SPECIALTIES)],
                    network_status=NetworkStatus.IN_NETWORK if i < 7 else NetworkStatus.OUT_OF_NETWORK,
                    address=f"{100 + i * 100} Medical Dr",
                    city=city,
                    state=state,
                    zip_code=zip_code,
                    phone=generate_phone(),
                )
                run_async(provider_adapter.create(provider))

            # Generate 20 members
            current_policies = run_async(policy_adapter.list_all())
            for i in range(20):
                city, state, zip_code = CITIES[i % len(CITIES)]
                age_days = 365 * (25 + i * 2)  # Ages 25-65

                member = DemoMember(
                    first_name=FIRST_NAMES[i % len(FIRST_NAMES)],
                    last_name=LAST_NAMES[i % len(LAST_NAMES)],
                    date_of_birth=date.today() - timedelta(days=age_days),
                    gender=Gender.MALE if i % 2 == 0 else Gender.FEMALE,
                    ssn_last4=f"{1000 + i}",
                    policy_id=current_policies[i % len(current_policies)].policy_id,
                    relationship=RelationshipType.SELF if i % 3 == 0 else RelationshipType.DEPENDENT,
                    address=f"{200 + i * 50} Residential Ave",
                    city=city,
                    state=state,
                    zip_code=zip_code,
                    phone=generate_phone(),
                    email=f"{FIRST_NAMES[i % len(FIRST_NAMES)].lower()}.{LAST_NAMES[i % len(LAST_NAMES)].lower()}@demo.com",
                )
                run_async(member_adapter.create(member))

            # Generate 15 payments
            current_providers = run_async(provider_adapter.list_all())
            for i in range(15):
                provider = current_providers[i % len(current_providers)]
                amount = Decimal(str([150, 250, 500, 750, 1000, 1500, 2000][i % 7]))

                payment = run_async(payment_adapter.create_payment(
                    claim_id=f"CLM-{10000 + i}",
                    payee_id=provider.provider_id,
                    amount=amount,
                ))

                if i % 3 != 0:  # Process 2/3 of payments
                    run_async(payment_adapter.process_payment(payment.payment_id))

        st.success("Generated complete demo dataset: 5 policies, 10 providers, 20 members, 15 payments!")
        st.rerun()


# Footer
st.divider()
st.caption("Demo Data Generator | Claims Processing System")
