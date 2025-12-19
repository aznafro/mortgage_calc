import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from dateutil.relativedelta import relativedelta
from io import BytesIO

st.set_page_config(page_title="Mortgage Calculator & Amortization 2025", layout="wide")

st.title("🏠 Mortgage Calculator & Amortization Schedule")
st.caption("Accurate monthly payments • Full amortization table • Extra payments impact • 2025 rates ready")

# --- SIDEBAR INPUTS ---
with st.sidebar:
    st.header("🔢 Loan Details")
    
    loan_amount = st.number_input("Home Price / Loan Amount ($)", min_value=0.0, value=400000.0, step=10000.0)
    down_payment_pct = st.slider("Down Payment (%)", min_value=0.0, max_value=80.0, value=20.0, step=0.5)
    down_payment = loan_amount * (down_payment_pct / 100)
    principal = loan_amount - down_payment
    
    st.metric("Loan Principal", f"${principal:,.2f}")
    
    interest_rate = st.slider("Annual Interest Rate (%)", min_value=2.0, max_value=12.0, value=6.75, step=0.125)
    loan_term_years = st.selectbox("Loan Term (Years)", [15, 20, 30], index=2)
    
    st.markdown("---")
    st.header("📅 Extra Payments (Optional)")
    extra_monthly = st.number_input("Extra Monthly Payment ($)", min_value=0.0, value=0.0, step=50.0)
    extra_one_time = st.number_input("One-Time Extra Payment ($)", min_value=0.0, value=0.0, step=1000.0)
    extra_one_time_month = st.slider("Apply One-Time Payment in Month #", min_value=1, max_value=loan_term_years*12, value=12, disabled=(extra_one_time == 0))

# --- CALCULATIONS ---
monthly_rate = interest_rate / 100 / 12
num_payments = loan_term_years * 12

# Standard monthly payment (without extras)
if monthly_rate > 0:
    monthly_payment = principal * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
else:
    monthly_payment = principal / num_payments

total_paid_standard = monthly_payment * num_payments
total_interest_standard = total_paid_standard - principal

# With extra payments
if extra_monthly > 0 or extra_one_time > 0:
    # Build amortization with extras
    balance = principal
    schedule = []
    total_interest_extra = 0
    month = 0
    
    while balance > 0 and month < num_payments * 2:  # safety limit
        month += 1
        interest = balance * monthly_rate
        total_interest_extra += interest
        
        # Apply one-time extra if applicable
        extra_this_month = extra_monthly
        if extra_one_time > 0 and month == extra_one_time_month:
            extra_this_month += extra_one_time
            extra_one_time = 0  # only once
        
        principal_payment = monthly_payment - interest + extra_this_month
        balance = max(0, balance - principal_payment)
        
        schedule.append({
            "Month": month,
            "Payment": monthly_payment + extra_this_month,
            "Principal": principal_payment,
            "Interest": interest,
            "Extra": extra_this_month,
            "Balance": balance
        })
        
        if balance <= 0:
            break
    
    df_amort = pd.DataFrame(schedule)
    actual_payments = len(df_amort)
    total_paid_extra = df_amort["Payment"].sum()
    total_interest_extra = df_amort["Interest"].sum()
    years_saved = (num_payments - actual_payments) / 12
else:
    df_amort = None
    years_saved = 0
    total_paid_extra = total_paid_standard
    total_interest_extra = total_interest_standard

# --- MAIN DASHBOARD ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Monthly Payment", f"${monthly_payment:,.2f}")
col2.metric("Total Interest (Standard)", f"${total_interest_standard:,.2f}")
col3.metric("Total Paid (Standard)", f"${total_paid_standard:,.2f}")
col4.metric("Loan Term", f"{loan_term_years} years")

if extra_monthly > 0 or extra_one_time > 0:
    st.success(f"🎉 With extras: Pay off in ~{actual_payments//12} years {actual_payments%12} months "
               f"(saves ~{years_saved:.1f} years & ${total_interest_standard - total_interest_extra:,.0f} in interest!)")

st.markdown("---")

# Summary Cards
col_a, col_b = st.columns(2)
with col_a:
    st.subheader("📊 Payment Breakdown (First Month)")
    fig_pie = go.Figure(data=[go.Pie(
        labels=["Principal", "Interest"],
        values=[monthly_payment - (principal * monthly_rate), principal * monthly_rate],
        hole=0.4,
        marker_colors=["#00CC96", "#EF553B"],
        textinfo='label+percent'
    )])
    fig_pie.update_layout(title="First Payment Split", showlegend=False)
    st.plotly_chart(fig_pie, use_container_width=True)

with col_b:
    st.subheader("💰 Interest Over Time")
    if df_amort is not None:
        fig_interest = go.Figure()
        fig_interest.add_trace(go.Scatter(x=df_amort["Month"], y=df_amort["Interest"].cumsum(),
                                          name="With Extras", line=dict(color="#636EFA")))
        fig_interest.add_trace(go.Scatter(x=list(range(1, num_payments+1)),
                                          y=[i * (monthly_payment - (principal * monthly_rate)) for i in range(1, num_payments+1)],
                                          name="Standard", line=dict(color="#EF553B", dash='dot')))
        fig_interest.update_layout(title="Cumulative Interest Paid", xaxis_title="Month", yaxis_title="Interest ($)")
        st.plotly_chart(fig_interest, use_container_width=True)
    else:
        st.info("Add extra payments to see interest savings over time")

# --- AMORTIZATION TABLE ---
st.markdown("---")
st.subheader("📅 Full Amortization Schedule")

if st.checkbox("Show full amortization table", value=False):
    # Generate standard schedule if no extras
    if df_amort is None:
        balance = principal
        standard_schedule = []
        for month in range(1, num_payments + 1):
            interest = balance * monthly_rate
            principal_payment = monthly_payment - interest
            balance -= principal_payment
            standard_schedule.append({
                "Month": month,
                "Payment": monthly_payment,
                "Principal": principal_payment,
                "Interest": interest,
                "Extra": 0.0,
                "Balance": max(0, balance)
            })
        df_amort = pd.DataFrame(standard_schedule)
    
    # Format for display
    df_display = df_amort.copy()
    df_display["Payment"] = df_display["Payment"].map("${:,.2f}".format)
    df_display["Principal"] = df_display["Principal"].map("${:,.2f}".format)
    df_display["Interest"] = df_display["Interest"].map("${:,.2f}".format)
    df_display["Extra"] = df_display["Extra"].map("${:,.2f}".format)
    df_display["Balance"] = df_display["Balance"].map("${:,.2f}".format)
    
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
            # Summary sheet
            summary_data = {
                "Metric": ["Loan Amount", "Down Payment", "Principal", "Interest Rate", "Term (Years)",
                           "Monthly Payment", "Total Paid", "Total Interest", "Extra Payments Impact"],
                "Value": [loan_amount, down_payment, principal, f"{interest_rate}%", loan_term_years,
                          monthly_payment, total_paid_extra, total_interest_extra,
                          f"Saves {years_saved:.1f} years & ${total_interest_standard - total_interest_extra:,.0f} interest" if (extra_monthly > 0 or extra_one_time > 0) else "N/A"]
            }
            pd.DataFrame(summary_data).to_excel(writer, index=False, sheet_name='Summary')
        buffer.seek(0)
        st.download_button(
            "📈 Download Excel",
            data=buffer.getvalue(),
            file_name=f"Mortgage_{datetime.now().strftime('%Y%m%d')}.xlsx"
        )

st.caption("Precise amortization • Extra payments supported • Current as of 2025 • Not financial advice")