from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go  # For Figure type hint
import streamlit as st
from dateutil.relativedelta import relativedelta  # More robust date additions

# --- Configuration ---
st.set_page_config(page_title="USD/JPY Forward Rate Calculator", layout="wide")


# --- Helper Functions ---
def calculate_forward_rate(
    spot_rate: float,
    rate_base_pct: float,
    rate_quote_pct: float,
    value_date: date,
    forward_date: date,
    day_basis: int,
) -> Tuple[Optional[float], Optional[float], Optional[int]]:
    """
    Calculates the FX forward rate.

    Args:
        spot_rate: The current spot exchange rate (Quote / Base).
        rate_base_pct: The interest rate of the base currency (e.g., USD) as a percentage.
        rate_quote_pct: The interest rate of the quote currency (e.g., JPY) as a percentage.
        value_date: The settlement date for the spot transaction.
        forward_date: The settlement date for the forward transaction.
        day_basis: The day count basis convention (e.g., 360 or 365).

    Returns:
        A tuple containing:
        - The calculated forward rate (float), or None if calculation fails.
        - The forward points scaled by 100 (float), or None if calculation fails.
        - The number of days between value_date and forward_date (int), or None if forward_date is not after value_date.
    """
    if forward_date <= value_date:
        st.error("Forward date must be after the value date.")
        return None, None, None  # Return None for rate, points, and days

    # Convert percentage rates to decimals
    rate_base: float = rate_base_pct / 100.0
    rate_quote: float = rate_quote_pct / 100.0

    # Calculate days
    days: int = (forward_date - value_date).days

    # Calculate forward rate using the standard formula
    try:
        # Ensure day_basis is not zero before division
        if day_basis == 0:
            raise ZeroDivisionError("Day basis cannot be zero.")

        forward_rate: float = spot_rate * (
            (1 + rate_quote * (days / day_basis)) / (1 + rate_base * (days / day_basis))
        )
        # Calculate forward points (Forward - Spot) * 100 for JPY pairs
        forward_points: float = (forward_rate - spot_rate) * 100
        return forward_rate, forward_points, days
    except ZeroDivisionError:
        st.error("Day basis cannot be zero.")
        return None, None, None
    except Exception as e:
        st.error(f"An error occurred during calculation: {e}")
        return None, None, None


def get_future_date(start_date: date, tenor_str: str) -> date:
    """
    Calculates a future date based on a tenor string like '1W', '1M', '3M', '1Y'.

    Args:
        start_date: The date from which to calculate the future date.
        tenor_str: A string representing the tenor (e.g., '3M', '1Y').

    Returns:
        The calculated future date. Returns start_date if tenor unit is unrecognized.
    """
    try:
        num: int = int(tenor_str[:-1])
        unit: str = tenor_str[-1].upper()

        if unit == "W":
            return start_date + relativedelta(weeks=num)
        elif unit == "M":
            return start_date + relativedelta(months=num)
        elif unit == "Y":
            return start_date + relativedelta(years=num)
        else:
            st.warning(f"Unrecognized tenor unit: {unit}. Returning start date.")
            return start_date
    except ValueError:
        st.warning(f"Could not parse tenor string: {tenor_str}. Returning start date.")
        return start_date
    except Exception as e:
        st.error(f"Error calculating future date for tenor {tenor_str}: {e}")
        return start_date


# --- Streamlit App UI ---
st.title("📈 USD/JPY Forward FX Rate Calculator & Dashboard")
st.markdown(
    "Calculate the theoretical USD/JPY forward rate based on spot rate and interest rates."
)

# --- Inputs ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Inputs")
    # Although number_input can return float or int, we'll treat them as float for calculations
    spot_rate: float = st.number_input(
        "Spot Rate (USD/JPY)", min_value=0.01, value=145.50, step=0.01, format="%.4f"
    )
    usd_rate_pct: float = st.number_input(
        "USD Interest Rate (%) - (e.g., SOFR)", value=5.25, step=0.01, format="%.3f"
    )
    jpy_rate_pct: float = st.number_input(
        "JPY Interest Rate (%) - (e.g., TONA)", value=-0.10, step=0.01, format="%.3f"
    )

with col2:
    st.subheader("Dates & Convention")
    today: date = date.today()
    # Spot typically settles T+2, adjust if needed
    default_value_date: date = today + timedelta(days=2)
    value_date: date = st.date_input(
        "Value Date (Spot Settlement Date)", value=default_value_date
    )
    # Default forward date (e.g., 3 months)
    default_forward_date: date = value_date + relativedelta(months=3)
    forward_date_input: date = st.date_input(
        "Forward Settlement Date", value=default_forward_date
    )
    # selectbox returns the selected value; type hint based on options provided
    day_basis: int = st.selectbox(
        "Day Count Basis", [360, 365], index=0
    )  # Default to 360

# --- Calculation for Specific Date ---
st.markdown("---")
st.subheader("Calculation for Specific Forward Date")

# Initialize potentially None variables
fwd_rate: Optional[float] = None
fwd_points: Optional[float] = None
days_calc: Optional[int] = None

if forward_date_input > value_date:
    # Unpack the tuple returned by the function
    fwd_rate, fwd_points, days_calc = calculate_forward_rate(
        spot_rate, usd_rate_pct, jpy_rate_pct, value_date, forward_date_input, day_basis
    )

    if fwd_rate is not None and fwd_points is not None and days_calc is not None:
        col_res1, col_res2, col_res3 = st.columns(3)
        col_res1.metric("Calculated Forward Rate", f"{fwd_rate:.4f}")
        col_res2.metric("Forward Points (x100)", f"{fwd_points:.2f}")
        col_res3.metric("Number of Days", f"{days_calc}")

        # Use f-string with proper formatting for rates inside the info box
        st.info(f"""
        **Formula:**
        Forward Rate = Spot * [(1 + JPY Rate * (Days / Basis)) / (1 + USD Rate * (Days / Basis))]
        Forward Rate = {spot_rate:.4f} * [(1 + {(jpy_rate_pct / 100.0):.5f} * ({days_calc} / {day_basis})) / (1 + {(usd_rate_pct / 100.0):.5f} * ({days_calc} / {day_basis}))]
        """)
    else:
        # Error message already displayed by calculate_forward_rate
        st.warning("Could not calculate forward rate with the provided inputs.")
else:
    st.warning("Please ensure the Forward Settlement Date is after the Value Date.")


# --- Forward Curve Graph ---
st.markdown("---")
st.subheader("Forward Rate Curve")
st.markdown("Shows calculated forward rates for standard tenors.")

# Define standard tenors
tenors: List[str] = ["1W", "1M", "2M", "3M", "6M", "9M", "1Y", "2Y"]
# More specific type hint for the list of dictionaries
forward_data: List[Dict[str, Any]] = []

for tenor in tenors:
    f_date: date = get_future_date(value_date, tenor)
    # Handle case where get_future_date might return the start_date due to error
    if f_date > value_date:
        fw_rate: Optional[float]
        fw_points: Optional[float]
        days: Optional[int]
        fw_rate, fw_points, days = calculate_forward_rate(
            spot_rate, usd_rate_pct, jpy_rate_pct, value_date, f_date, day_basis
        )
        if fw_rate is not None and fw_points is not None and days is not None:
            forward_data.append(
                {
                    "Tenor": tenor,
                    "Settlement Date": f_date,
                    "Days": days,
                    "Forward Rate": fw_rate,
                    "Forward Points": fw_points,
                }
            )
    else:
        # Optionally log or warn if a tenor results in a non-future date
        # This might happen if get_future_date encountered an issue or if value_date is very close to today
        # and a short tenor like 1W doesn't push it past value_date (unlikely with T+2 default)
        pass


if forward_data:
    df_fwd: pd.DataFrame = pd.DataFrame(forward_data)

    # Create interactive plot
    # px.line returns a plotly.graph_objects.Figure
    fig: go.Figure = px.line(
        df_fwd,
        x="Settlement Date",
        y="Forward Rate",
        markers=True,
        text="Forward Rate",  # Show rate value on points
        title="USD/JPY Forward Rate Curve",
    )
    # Update text display format and position
    fig.update_traces(textposition="top center", texttemplate="%{y:.4f}")
    fig.update_layout(
        xaxis_title="Forward Settlement Date",
        yaxis_title="Calculated Forward Rate (USD/JPY)",
        hovermode="x unified",  # Enhanced hover information
    )

    st.plotly_chart(fig, use_container_width=True)

    # Display data table with improved formatting
    st.dataframe(
        df_fwd.style.format(
            {
                "Settlement Date": "{:%Y-%m-%d}",
                "Forward Rate": "{:.4f}",
                "Forward Points": "{:.2f}",
                "Days": "{:d}",  # Format days as integer
            }
        )
    )
else:
    st.warning(
        "Could not generate forward curve data based on inputs. Check dates and rates."
    )


# --- Disclaimer ---
st.markdown("---")
st.caption(
    "Disclaimer: This calculator provides theoretical forward rates based on the inputs. Actual market rates may differ due to various factors like liquidity, credit risk, transaction costs, and specific quoting conventions. Interest rates used should ideally be deposit/borrowing rates (like SOFR, TONA) for the corresponding periods."
)
