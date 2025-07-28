import streamlit as st
import pandas as pd
import yfinance as yf
from fredapi import Fred
import datetime
import altair as alt
import os

# --- CONFIG ---
FRED_API_KEY = st.secrets.get("FRED_API_KEY")
fred = Fred(api_key=FRED_API_KEY)

st.set_page_config(page_title="Recession Indicator Dashboard", layout="wide")
st.title("📉 Recession Indicator Dashboard")
st.markdown("Tracking recession risk using real-time macro, credit, and consumer indicators")

# --- TIMEFRAME SELECTOR ---
timeframe = st.selectbox("Select timeframe:", ["YTD", "1Y", "5Y", "10Y", "Max"])

today = datetime.date.today()
timeframe_map = {
    "YTD": datetime.date(today.year, 1, 1),
    "1Y": today - datetime.timedelta(days=365),
    "5Y": today - datetime.timedelta(days=5 * 365),
    "10Y": today - datetime.timedelta(days=10 * 365),
    "Max": datetime.date(2000, 1, 1)
}
start_date = timeframe_map[timeframe]

# --- HELPERS ---
def get_fred_series(series_id, label):
    series = fred.get_series(series_id, observation_start=start_date)
    df = pd.DataFrame(series, columns=[label])
    df.index = pd.to_datetime(df.index)
    return df.dropna()

def get_yahoo_series(ticker, label):
    df = yf.download(ticker, start=start_date, progress=False)
    if df.empty or 'Close' not in df:
        return pd.DataFrame(columns=[label])
    df = df[['Close']].dropna()
    df.columns = [label]
    return df

def plot_indicator(name, data, category, threshold=None, reverse=False):
    with st.container():
        st.markdown(f"**{category} → {name}**")

        latest_val = data.iloc[-1].values[0] if not data.empty else None
        status = ""
        if latest_val is not None and threshold is not None:
            if reverse:
                if latest_val > threshold:
                    status = "🔴"
                elif latest_val > threshold * 0.8:
                    status = "🟡"
                else:
                    status = "🟢"
            else:
                if latest_val < threshold:
                    status = "🔴"
                elif latest_val < threshold * 1.2:
                    status = "🟡"
                else:
                    status = "🟢"

        st.markdown(f"**Latest:** {latest_val:.2f} {status}" if latest_val else "No data")

        data = data.reset_index().rename(columns={"index": "Date"})
        chart = alt.Chart(data).mark_line().encode(
            x=alt.X("Date:T", axis=alt.Axis(format="%b-%y", title="Date")),
            y=alt.Y(data.columns[1], title=""),
            tooltip=["Date", data.columns[1]]
        ).properties(height=200)
        st.altair_chart(chart, use_container_width=True)

# --- MACROECONOMIC ---
st.header("📊 Macroeconomic Indicators")
col1, col2 = st.columns(2)
with col1:
    gdp = get_fred_series("A191RL1Q225SBEA", "GDP QoQ (%)")
    plot_indicator("GDP Growth (QoQ)", gdp, "Macroeconomic", threshold=0)
with col2:
    cci = get_fred_series("UMCSENT", "Consumer Confidence")
    plot_indicator("Consumer Confidence", cci, "Macroeconomic", threshold=80)

# --- MARKET-BASED ---
st.header("📈 Market-Based Indicators")
col1, col2 = st.columns(2)
with col1:
    sp500 = get_yahoo_series("^GSPC", "S&P 500")
    plot_indicator("S&P 500", sp500, "Market", threshold=3000)
with col2:
    vix = get_yahoo_series("^VIX", "VIX")
    plot_indicator("VIX Volatility Index", vix, "Market", threshold=20, reverse=True)

# --- CREDIT / LENDING ---
st.header("💳 Credit & Lending Indicators")
col1, col2 = st.columns(2)
with col1:
    yield_curve = get_fred_series("T10Y2Y", "10Y-2Y Spread")
    plot_indicator("10Y-2Y Treasury Spread", yield_curve, "Credit", threshold=0)
with col2:
    lending = get_fred_series("DRTSCILM", "Bank Lending Standards")
    plot_indicator("Bank Lending Standards", lending, "Credit", threshold=10, reverse=True)

# --- CONSUMER BEHAVIOR ---
st.header("🍽️ Consumer Activity Indicators")
col1, col2 = st.columns(2)
with col1:
    restaurants = get_fred_series("RSFS", "Restaurant & Bar Sales")
    plot_indicator("Restaurant/Bar Sales", restaurants, "Consumer", threshold=100)
with col2:
    air_traffic = get_fred_series("TOTTRNSA", "Airline Passengers")
    plot_indicator("Passenger Air Travel", air_traffic, "Consumer", threshold=60000)

st.markdown("---")
st.caption("Data from FRED & Yahoo Finance | Dashboard by Levi Jobe")