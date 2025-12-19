import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from dateutil.relativedelta import relativedelta
from io import BytesIO

st.set_page_config(page_title="Mortgage Calculator & Amortization 2025", layout="wide")

st.title("🏠 Mortgage Calculator & Amortization Schedule")
st.caption("Accurate payments • Extended terms (40/50 years) • Property tax included • Extra payments • 2025 ready")

# --- SIDEBAR INPUTS ---
with st.sidebar:
    st.header("🔢 Loan Details")
    
    loan_amount = st.number_input("Home Price / Loan Amount ($)", min_value=0.0, value=400000.0, step=10000.0)
    down_payment_pct = st.slider("Down Payment (%)", min_value=0.0, max_value=80.0, value=20.0, step=0.5)
    down_payment = loan_amount * (down_payment_pct / 100)
    principal = loan_amount - down_payment
    
    st.metric("Loan Principal", f"${principal:,.2f}")
    
    interest_rate = st.slider("Annual Interest Rate (%)", min_value=2.0, max_value=12.0, value=6.75, step=0.125)
    
    # Extended terms added
    loan_term_years = st.selectbox("Loan Term (Years)", [15, 20, 30, 40, 50], index=2)
    
    st.markdown("---")
    st.header("🏡 Property Tax & Insurance (Optional)")
    annual_property_tax = st.number_input("Annual Property Tax ($)", min_value=0.0, value=4800.0, step=100.0, help="Typical: 1-1.5% of home value")
    annual_home_insurance = st.number_input("Annual Homeowners Insurance ($)", min_value=0.0, value=1200.0, step=100.0)
    
    monthly_tax = annual_property_tax / 12
    monthly_insurance = annual_home_insurance / 12
    
    st.metric("Monthly Tax + Insurance", f"${monthly_tax + monthly_insurance:,.2f}")
    
    st.markdown("---")
    st.header("📅 Extra Payments (Optional)")
    extra_monthly = st.number_input("Extra Monthly Payment ($)", min_value=0.0, value=0.0, step=50.0)
    extra_one_time = st.number_input("One-Time Extra Payment ($)", min_value=0.0, value=0.0, step=1000.0)
    extra_one_time_month = st.slider("Apply One-Time Payment in Month #", min_value=1, max_value=loan_term_years*12, value=12, disabled=(extra_one_time == 0))

# --- CALCULATIONS ---
monthly_rate = interest_rate / 100 / 12
num_payments = loan_term_years * 12

# Base P&I payment
if monthly_rate > 0:
    monthly_pi = principal * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
else:
    monthly_pi = principal / num_payments

# Total monthly payment including tax & insurance
monthly_payment = monthly_pi + monthly_tax + monthly_insurance

total_paid_standard = monthly_payment * num_payments
total_interest_standard = (monthly_pi * num_payments) - principal
total_tax_paid = monthly_tax * num_payments
total_insurance_paid = monthly_insurance * num_payments

# With extra payments (applied only to principal)
if extra_monthly > 0 or extra_one_time > 0:
    balance = principal
    schedule = []
    total_interest_extra = 0
    month = 0
    
    while balance > 0 and month < num_payments * 2:
        month += 1
        interest = balance * monthly_rate
        total_interest_extra += interest
        
        extra_this_month = extra_monthly
        if extra_one_time > 0 and month == extra_one_time_month:
            extra_this_month += extra_one_time
            extra_one_time = 0
        
        # Principal payment = base P&I minus interest + extras
        principal_payment = monthly_pi - interest + extra_this_month
        balance = max(0, balance - principal_payment)
        
        total_payment_this_month = monthly_pi + monthly_tax + monthly_insurance + extra_this_month
        
        schedule.append({
            "Month": month,
            "Total Payment": total_payment_this_month,
            "Principal": principal_payment,
            "Interest": interest,
            "Tax": monthly_tax,
            "Insurance": monthly_insurance,
            "Extra": extra_this_month,
            "Balance": balance
        })
        
        if balance <= 0:
            break
    
    df_amort = pd.DataFrame(schedule)
    actual_payments = len(df_amort)
    total_paid_extra = df_amort["Total Payment"].sum()
    total_interest_extra = df_amort["Interest"].sum()
    years_saved = (num_payments - actual_payments) / 12
else:
    df_amort = None
    years_saved = 0
    total_paid_extra = total_paid_standard
    total_interest_extra = total_interest_standard

# --- MAIN DASHBOARD ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Monthly Payment (PITI)", f"${monthly_payment:,.2f}")
col2.metric("Total Interest (Standard)", f"${total_interest_standard:,.2f}")
col3.metric("Total Paid (Standard)", f"${total_paid_standard:,.2f}")
col4.metric("Loan Term", f"{loan_term_years} years")

if extra_monthly > 0 or extra_one_time > 0:
    st.success(f"🎉 With extras: Pay off in ~{actual_payments//12}y {actual_payments%12}m "
               f"(saves ~{years_saved:.1f} years & ${total_interest_standard - total_interest_extra:,.0f} in interest!)")

st.markdown("---")

# Payment Breakdown Pie (First Month)
first_interest = principal * monthly_rate
first_principal = monthly_pi - first_interest

fig_pie = go.Figure(data=[go.Pie(
    labels=["Principal", "Interest", "Property Tax", "Insurance"],
    values=[first_principal, first_interest, monthly_tax, monthly_insurance],
    hole=0.4,
    marker_colors=["#00CC96", "#EF553B", "#FFA15A", "#AB63FA"],
    textinfo='label+percent'
)])
fig_pie.update_layout(title="First Month Payment Breakdown (PITI)")
st.plotly_chart(fig_pie, use_container_width=True)

# Interest Over Time Chart
st.subheader("💰 Cumulative Interest Paid")
if df_amort is not None:
    fig_interest = go.Figure()
    fig_interest.add_trace(go.Scatter(x=df_amort["Month"], y=df_amort["Interest"].cumsum(),
                                      name="With Extra Payments", line=dict(color="#636EFA")))
    standard_cum_interest = [(i * first_interest) for i in range(1, num_payments + 1)]
    fig_interest.add_trace(go.Scatter(x=list(range(1, num_payments + 1)), y=standard_cum_interest,
                                      name="Standard Schedule", line=dict(color="#EF553B", dash='dot')))
    fig_interest.update_layout(xaxis_title="Month", yaxis_title="Cumulative Interest ($)")
    st.plotly_chart(fig_interest, use_container_width=True)
else:
    st.info("Enter extra payments to see interest savings over time.")

# --- AMORTIZATION TABLE ---
st.markdown("---")
st.subheader("📅 Full Amortization Schedule")

if st.checkbox("Show full amortization table", value=False):
    if df_amort is None:
        balance = principal
        standard_schedule = []
        for month in range(1, num_payments + 1):
            interest = balance * monthly_rate
            principal_payment = monthly_pi - interest
            balance = max(0, balance - principal_payment)
            standard_schedule.append({
                "Month": month,
                "Total Payment": monthly_payment,
                "Principal": principal_payment,
                "Interest": interest,
                "Tax": monthly_tax,
                "Insurance": monthly_insurance,
                "Extra": 0.0,
                "Balance": balance
            })
        df_amort = pd.DataFrame(standard_schedule)
    
    df_display = df_amort.copy()
    for col in ["Total Payment", "Principal", "Interest", "Tax", "Insurance", "Extra", "Balance"]:
        df_display[col] = df_display[col].map("${:,.2f}".format)
    
    st.dataframe(df_display, use_container_width=True)

# --- EXPORT ---
st.markdown("---")
st.subheader("📥 Export Schedule")

if df_amort is not None:
    col_ex1, col_ex2 = st.columns(2)
    
    with col_ex1:
        csv = df_amort.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📄 Download CSV",
            data=csv,
            file_name=f"Mortgage_Schedule_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with col_ex2:
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_amort.to_excel(writer, index=False, sheet_name='Amortization')
            summary_data = {
                "Metric": ["Home Price", "Down Payment", "Loan Principal", "Interest Rate", "Term (Years)",
                           "Monthly P&I", "Monthly Tax + Insurance", "Total Monthly (PITI)",
                           "Total Paid", "Total Interest", "Extra Payments Savings"],
                "Value": [loan_amount, down_payment, principal, f"{interest_rate}%", loan_term_years,
                          monthly_pi, monthly_tax + monthly_insurance, monthly_payment,
                          total_paid_extra, total_interest_extra,
                          f"Saves {years_saved:.1f} years & ${total_interest_standard - total_interest_extra:,.0f} interest" if (extra_monthly > 0 or extra_one_time > 0) else "N/A"]
            }
            pd.DataFrame(summary_data).to_excel(writer, index=False, sheet_name='Summary')
        buffer.seek(0)
        st.download_button(
            "📈 Download Excel",
            data=buffer.getvalue(),
            file_name=f"Mortgage_{datetime.now().strftime('%Y%m%d')}.xlsx"
        )

st.caption("PITI calculations • 40/50-year terms • Extra payments • Current as of 2025 • Not financial advice")
