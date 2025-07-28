import streamlit as st
import pandas as pd
import yfinance as yf
from fredapi import Fred
import datetime

# --- CONFIG ---
FRED_API_KEY = '9da5eccef6f88b13f2eb32a44b342f67'
fred = Fred(api_key=FRED_API_KEY)

# --- PAGE SETUP ---
st.set_page_config(page_title="Recession Indicator Dashboard", layout="wide")
st.title("📉 Recession Indicator Dashboard")
st.markdown("Live updates of key macroeconomic and market-based indicators")

# --- DATE RANGE ---
today = datetime.date.today()
start_date = today - datetime.timedelta(days=365 * 5)

# --- HELPER FUNCTION ---
def plot_indicator(name, data, threshold=None):
    st.subheader(name)
    st.line_chart(data)
    if threshold:
        latest = data.iloc[-1]
        if latest < threshold:
            st.error(f"⚠️ Below threshold: {latest:.2f}")
        else:
            st.success(f"✅ Above threshold: {latest:.2f}")

# --- FRED DATA ---
def get_fred_series(series_id, label):
    series = fred.get_series(series_id, start_date)
    return pd.DataFrame(series, columns=[label])

yield_curve = get_fred_series('T10Y2Y', '10Y-2Y Spread')
unemployment = get_fred_series('UNRATE', 'Unemployment Rate')
cpi = get_fred_series('CPIAUCSL', 'CPI Index')

# --- Yahoo Finance Data ---
def get_yahoo_series(ticker, label):
    df = yf.download(ticker, start=start_date)
    return pd.DataFrame(df['Close'], columns=[label])

sp500 = get_yahoo_series('^GSPC', 'S&P 500')
vix = get_yahoo_series('^VIX', 'VIX')

# --- LAYOUT ---
col1, col2 = st.columns(2)

with col1:
    plot_indicator('10Y-2Y Yield Spread (FRED)', yield_curve, threshold=0)
    plot_indicator('Unemployment Rate (FRED)', unemployment)

with col2:
    plot_indicator('Consumer Price Index (FRED)', cpi)
    plot_indicator('S&P 500 (Yahoo Finance)', sp500)
    plot_indicator('VIX Index (Yahoo Finance)', vix)