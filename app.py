from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from dateutil.relativedelta import relativedelta  # More robust date additions

# --- Configuration ---
st.set_page_config(page_title="USD/JPY Forward Rate Calculator", layout="wide")


# --- Helper Functions ---
def calculate_forward_rate(
    spot_rate, rate_base_pct, rate_quote_pct, value_date, forward_date, day_basis
):
    """Calculates the FX forward rate."""
    if forward_date <= value_date:
        st.error("Forward date must be after the value date.")
        return None, None, None  # Return None for rate, points, and days

    # Convert percentage rates to decimals
    rate_base = rate_base_pct / 100.0
    rate_quote = rate_quote_pct / 100.0

    # Calculate days
    days = (forward_date - value_date).days

    # Calculate forward rate using the standard formula
    try:
        forward_rate = spot_rate * (
            (1 + rate_quote * (days / day_basis)) / (1 + rate_base * (days / day_basis))
        )
        # Calculate forward points (Forward - Spot) * 100 for JPY pairs
        forward_points = (forward_rate - spot_rate) * 100
        return forward_rate, forward_points, days
    except ZeroDivisionError:
        st.error("Day basis cannot be zero.")
        return None, None, None
    except Exception as e:
        st.error(f"An error occurred during calculation: {e}")
        return None, None, None


def get_future_date(start_date, tenor_str):
    """Calculates a future date based on a tenor string like '1M', '3M', '1Y'."""
    num = int(tenor_str[:-1])
    unit = tenor_str[-1].upper()

    if unit == "W":
        return start_date + relativedelta(weeks=num)
    elif unit == "M":
        return start_date + relativedelta(months=num)
    elif unit == "Y":
        return start_date + relativedelta(years=num)
    else:
        return start_date  # Should not happen with predefined tenors


# --- Streamlit App UI ---
st.title("📈 USD/JPY Forward FX Rate Calculator & Dashboard")
st.markdown(
    "Calculate the theoretical USD/JPY forward rate based on spot rate and interest rates."
)

# --- Inputs ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Inputs")
    spot_rate = st.number_input(
        "Spot Rate (USD/JPY)", min_value=0.01, value=145.50, step=0.01, format="%.4f"
    )
    usd_rate_pct = st.number_input(
        "USD Interest Rate (%) - (e.g., SOFR)", value=5.25, step=0.01, format="%.3f"
    )
    jpy_rate_pct = st.number_input(
        "JPY Interest Rate (%) - (e.g., TONA)", value=-0.10, step=0.01, format="%.3f"
    )

with col2:
    st.subheader("Dates & Convention")
    today = date.today()
    # Spot typically settles T+2, adjust if needed
    default_value_date = today + timedelta(days=2)
    value_date = st.date_input(
        "Value Date (Spot Settlement Date)", value=default_value_date
    )
    # Default forward date (e.g., 3 months)
    default_forward_date = value_date + relativedelta(months=3)
    forward_date_input = st.date_input(
        "Forward Settlement Date", value=default_forward_date
    )
    day_basis = st.selectbox("Day Count Basis", [360, 365], index=0)  # Default to 360

# --- Calculation for Specific Date ---
st.markdown("---")
st.subheader("Calculation for Specific Forward Date")

if forward_date_input > value_date:
    fwd_rate, fwd_points, days_calc = calculate_forward_rate(
        spot_rate, usd_rate_pct, jpy_rate_pct, value_date, forward_date_input, day_basis
    )

    if fwd_rate is not None:
        col_res1, col_res2, col_res3 = st.columns(3)
        col_res1.metric("Calculated Forward Rate", f"{fwd_rate:.4f}")
        col_res2.metric("Forward Points (x100)", f"{fwd_points:.2f}")
        col_res3.metric("Number of Days", f"{days_calc}")

        st.info(f"""
        **Formula:**
        Forward Rate = Spot * [(1 + JPY Rate * (Days / Basis)) / (1 + USD Rate * (Days / Basis))]
        Forward Rate = {spot_rate:.4f} * [(1 + {jpy_rate_pct / 100:.5f} * ({days_calc} / {day_basis})) / (1 + {usd_rate_pct / 100:.5f} * ({days_calc} / {day_basis}))]
        """)
    else:
        st.warning("Could not calculate forward rate with the provided inputs.")
else:
    st.warning("Please ensure the Forward Settlement Date is after the Value Date.")


# --- Forward Curve Graph ---
st.markdown("---")
st.subheader("Forward Rate Curve")
st.markdown("Shows calculated forward rates for standard tenors.")

# Define standard tenors
tenors = ["1W", "1M", "2M", "3M", "6M", "9M", "1Y", "2Y"]
forward_data = []

for tenor in tenors:
    f_date = get_future_date(value_date, tenor)
    fw_rate, fw_points, days = calculate_forward_rate(
        spot_rate, usd_rate_pct, jpy_rate_pct, value_date, f_date, day_basis
    )
    if fw_rate is not None:
        forward_data.append(
            {
                "Tenor": tenor,
                "Settlement Date": f_date,
                "Days": days,
                "Forward Rate": fw_rate,
                "Forward Points": fw_points,
            }
        )

if forward_data:
    df_fwd = pd.DataFrame(forward_data)

    # Create interactive plot
    fig = px.line(
        df_fwd,
        x="Settlement Date",
        y="Forward Rate",
        markers=True,
        text="Forward Rate",  # Show rate value on hover/points
        title="USD/JPY Forward Rate Curve",
    )
    fig.update_traces(textposition="top center", texttemplate="%{y:.4f}")
    fig.update_layout(
        xaxis_title="Forward Settlement Date",
        yaxis_title="Calculated Forward Rate (USD/JPY)",
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Display data table
    st.dataframe(
        df_fwd.style.format(
            {
                "Settlement Date": "{:%Y-%m-%d}",
                "Forward Rate": "{:.4f}",
                "Forward Points": "{:.2f}",
            }
        )
    )
else:
    st.warning("Could not generate forward curve data based on inputs.")


# --- Disclaimer ---
st.markdown("---")
st.caption(
    "Disclaimer: This calculator provides theoretical forward rates based on the inputs. Actual market rates may differ due to various factors like liquidity, credit risk, transaction costs, and specific quoting conventions. Interest rates used should ideally be deposit/borrowing rates (like SOFR, TONA) for the corresponding periods."
)
